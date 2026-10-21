from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agents.glossary_agent import GlossaryAgent
from src.agents.prompts import build_glossary_prompts, build_improve_prompts, build_translator_prompts
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.translator_agent import TranslatorAgent
from src.core.glossary import canonical_glossary, detect_glossary_conflicts
from src.core.orchestrator import Orchestrator
from src.core.pipeline import TranslationPipeline
from src.core.tokens import estimate_tokens
from src.core.types import DocumentContext, Segment, SegmentBundle, TranslationResult
from src.infra.config import TranslatorConfig
from src.memory.document_context import DocumentContextBuilder
from src.memory.translation_memory import TranslationMemory
from src.parser.anchor_rewriter import heading_pairs, rewrite_anchors, slugify
from src.parser.markdown_parser import MarkdownParser
from src.parser.segment_extractor import SegmentExtractor
from src.test.test_ast_pipeline import SAMPLE_MARKDOWN, FakeProvider, FormatGuardAgent, _payload_segments
from src.validators.markdown_validator import MarkdownValidator


def _segment(
    segment_id: str,
    node_type: str,
    text: str,
    line_start: int,
    line_end: int,
    metadata: dict | None = None,
) -> Segment:
    return Segment(
        segment_id=segment_id,
        node_type=node_type,
        source_text=text,
        context_path=[],
        line_start=line_start,
        line_end=line_end,
        metadata=metadata or {},
    )


def estimate_tokens_of(segments) -> int:
    return sum(estimate_tokens(segment.source_text) for segment in segments)


def _config(**overrides) -> TranslatorConfig:
    config = TranslatorConfig()
    config.pipeline.mode = overrides.get("mode", "balanced")
    config.pipeline.enable_review = False
    config.pipeline.enable_format_guard = False
    config.pipeline.enable_glossary = overrides.get("enable_glossary", True)
    config.segmentation.max_bundle_tokens = overrides.get("max_bundle_tokens", 3000)
    config.segmentation.min_bundle_tokens = overrides.get("min_bundle_tokens", 0)
    return config


class SemanticBundlingTests(unittest.TestCase):
    def _bundles(self, segments, config):
        context = DocumentContext(title="", abstract="", section_summaries={}, style_guide=[], audience="")
        return Orchestrator().build_bundles(segments, context, config)

    def test_section_boundary_starts_a_bundle_when_min_is_zero(self) -> None:
        segments = [
            _segment("s0", "paragraph", "A" * 450, 0, 0),
            _segment("s1", "heading", "Section B", 2, 2),
            _segment("s2", "paragraph", "content of section b", 4, 4),
        ]
        bundles = self._bundles(segments, _config())
        self.assertEqual([bundle.bundle_id for bundle in bundles], ["bundle-0", "bundle-1"])
        self.assertEqual([segment.segment_id for segment in bundles[1].segments], ["s1", "s2"])

    def test_small_sections_merge_until_min_bundle_tokens(self) -> None:
        segments = [
            _segment("s0", "paragraph", "A" * 100, 0, 0),
            _segment("s1", "heading", "Section B", 2, 2),
            _segment("s2", "paragraph", "content", 4, 4),
        ]
        bundles = self._bundles(segments, _config(min_bundle_tokens=200))
        self.assertEqual(len(bundles), 1)

    def test_small_sections_stay_separate_without_minimum(self) -> None:
        segments = [
            _segment("s0", "paragraph", "A" * 100, 0, 0),
            _segment("s1", "heading", "Section B", 2, 2),
            _segment("s2", "paragraph", "content", 4, 4),
        ]
        bundles = self._bundles(segments, _config(min_bundle_tokens=0))
        self.assertEqual(len(bundles), 2)

    def test_consecutive_headings_merge_with_small_sections(self) -> None:
        segments = [
            _segment("s0", "paragraph", "A" * 450, 0, 0),
            _segment("s1", "heading", "H1", 2, 2),
            _segment("s2", "heading", "H2", 3, 3),
            _segment("s3", "paragraph", "content", 5, 5),
        ]
        bundles = self._bundles(segments, _config(min_bundle_tokens=200))
        self.assertEqual(len(bundles), 1)

    def test_table_rows_stay_together_when_they_fit(self) -> None:
        rows = [
            _segment(
                f"r{i}",
                "th" if i == 0 else "td",
                "C" * 40,
                i,
                i,
                {
                    "block_kind": "table_row",
                    "table_id": "t0",
                    "is_header": i == 0,
                    "table_header": "| h |",
                },
            )
            for i in range(4)
        ]
        bundles = self._bundles(rows, _config(max_bundle_tokens=60))
        self.assertEqual(len(bundles), 1)
        self.assertEqual([segment.segment_id for segment in bundles[0].segments], ["r0", "r1", "r2", "r3"])

    def test_table_splits_only_at_row_boundaries_and_keeps_header_first(self) -> None:
        rows = [
            _segment(
                f"r{i}",
                "th" if i == 0 else "td",
                "C" * 40,
                i,
                i,
                {
                    "block_kind": "table_row",
                    "table_id": "t0",
                    "is_header": i == 0,
                    "table_header": "| h |",
                },
            )
            for i in range(6)
        ]
        bundles = self._bundles(rows, _config(max_bundle_tokens=30))
        self.assertEqual([segment.segment_id for segment in bundles[0].segments], ["r0", "r1"])
        flattened = [segment.segment_id for bundle in bundles for segment in bundle.segments]
        self.assertEqual(flattened, [f"r{i}" for i in range(6)])
        self.assertTrue(all(estimate_tokens_of(b.segments) <= 30 for b in bundles))

    def test_line_gap_ends_table_group(self) -> None:
        rows = [
            _segment("c0", "td", "C" * 40, 0, 0),
            _segment("c1", "td", "C" * 40, 1, 1),
            _segment("c2", "td", "C" * 40, 10, 10),
        ]
        bundles = self._bundles(rows, _config(max_bundle_tokens=30))
        self.assertEqual([len(bundle.segments) for bundle in bundles], [2, 1])

    def test_oversized_paragraph_splits_by_lines_and_keeps_source_order(self) -> None:
        text = "line one. " * 40 + "\n" + "line two. " * 40 + "\n" + "line three."
        segments = [_segment("s0", "paragraph", text, 0, 2)]
        bundles = self._bundles(segments, _config(max_bundle_tokens=120))
        flattened = [segment for bundle in bundles for segment in bundle.segments]
        self.assertGreater(len(flattened), 1)
        self.assertTrue(all(segment.segment_id.startswith("s0~") for segment in flattened))
        rebuilt = "".join(segment.source_text + segment.metadata.get("split_sep", "") for segment in flattened)
        self.assertEqual(rebuilt, text)
        self.assertTrue(all(estimate_tokens_of(b.segments) <= 120 for b in bundles))

    def test_min_bundle_tokens_merges_small_trailing_bundle(self) -> None:
        segments = [
            _segment("s0", "paragraph", "A" * 400, 0, 0),
            _segment("s1", "heading", "Section B", 2, 2),
            _segment("s2", "paragraph", "tiny", 4, 4),
        ]
        bundles = self._bundles(segments, _config(max_bundle_tokens=180, min_bundle_tokens=180))
        self.assertEqual(len(bundles), 1)

    def test_bundle_summary_covers_head_and_tail(self) -> None:
        segments = [
            _segment("s0", "paragraph", "HEAD" + "a" * 200, 0, 0),
            _segment("s1", "paragraph", "b" * 200, 2, 2),
            _segment("s2", "paragraph", "c" * 200 + "TAIL", 4, 4),
        ]
        summary = Orchestrator._build_bundle_summary(segments)
        self.assertIn(" ... ", summary)
        self.assertTrue(summary.startswith("HEAD"))
        self.assertTrue(summary.endswith("TAIL"))
        self.assertLessEqual(len(summary), 320)


class GlossaryConflictTests(unittest.TestCase):
    def test_frequency_wins_for_unmanaged_terms(self) -> None:
        translations = [
            TranslationResult(segment_id="a", translated_text="", applied_terms={"agent": "智B"}),
            TranslationResult(segment_id="b", translated_text="", applied_terms={"agent": "智A"}),
            TranslationResult(segment_id="c", translated_text="", applied_terms={"agent": "智A"}),
        ]
        conflicts = detect_glossary_conflicts(translations, {})
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].canonical, "智A")
        self.assertEqual(conflicts[0].affected_segment_ids, {"a"})

    def test_tie_breaks_by_first_appearance(self) -> None:
        translations = [
            TranslationResult(segment_id="a", translated_text="", applied_terms={"agent": "智B"}),
            TranslationResult(segment_id="b", translated_text="", applied_terms={"agent": "智A"}),
        ]
        conflicts = detect_glossary_conflicts(translations, {})
        self.assertEqual(conflicts[0].canonical, "智B")

    def test_authoritative_glossary_overrides_usage(self) -> None:
        translations = [
            TranslationResult(segment_id="a", translated_text="", applied_terms={"agent": "智能体"}),
            TranslationResult(segment_id="b", translated_text="", applied_terms={"agent": "代理"}),
        ]
        conflicts = detect_glossary_conflicts(translations, {"agent": "智能体"})
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].canonical, "智能体")
        self.assertEqual(conflicts[0].affected_segment_ids, {"b"})

    def test_consistent_renderings_produce_no_conflict(self) -> None:
        translations = [
            TranslationResult(segment_id="a", translated_text="", applied_terms={"agent": "智能体"}),
            TranslationResult(segment_id="b", translated_text="", applied_terms={"agent": "智能体"}),
        ]
        self.assertEqual(detect_glossary_conflicts(translations, {}), [])
        self.assertEqual(canonical_glossary([]), {})


class AnchorRewriterTests(unittest.TestCase):
    def test_slugify_variants(self) -> None:
        self.assertEqual(slugify("Getting Started"), "getting-started")
        self.assertEqual(slugify("What's New?"), "whats-new")
        self.assertEqual(slugify("快速 入门"), "快速-入门")

    def test_rewrites_known_source_anchor(self) -> None:
        output = rewrite_anchors("See [intro](#introduction) and [web](https://example.com).", [("Introduction", "简介")])
        self.assertIn("[intro](#简介)", output)
        self.assertIn("(https://example.com)", output)

    def test_unknown_anchor_untouched(self) -> None:
        output = rewrite_anchors("See [x](#elsewhere).", [("Introduction", "简介")])
        self.assertEqual(output, "See [x](#elsewhere).")

    def test_duplicate_headings_use_occurrence_suffixes(self) -> None:
        pairs = [("Foo", "富"), ("Foo", "富二")]
        output = rewrite_anchors("[a](#foo) [b](#foo-1)", pairs)
        self.assertEqual(output, "[a](#富) [b](#富二)")

    def test_heading_pairs_strip_markers_and_placeholders(self) -> None:
        segments = [
            _segment("h0", "heading", "{{MD_0}}Introduction", 0, 0),
            _segment("p0", "paragraph", "text", 2, 2),
        ]
        translations = [
            TranslationResult(segment_id="h0", translated_text="# [ZH]Introduction"),
            TranslationResult(segment_id="p0", translated_text="text"),
        ]
        self.assertEqual(heading_pairs(segments, translations), [("Introduction", "[ZH]Introduction")])


class MemoryDocumentScopeTests(unittest.TestCase):
    @staticmethod
    def _fingerprint(document_id: str = "") -> str:
        return TranslationMemory.style_fingerprint(
            model="m", tone="t", audience="a", instructions=[], preserve_terms=[], document_id=document_id
        )

    def test_document_id_changes_fingerprint_only_when_set(self) -> None:
        global_fp = self._fingerprint()
        self.assertEqual(self._fingerprint(), global_fp)
        self.assertNotEqual(self._fingerprint("doc1"), global_fp)
        self.assertNotEqual(self._fingerprint("doc1"), self._fingerprint("doc2"))

    def test_peek_does_not_touch_counters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = TranslationMemory(Path(temp_dir) / "memory.sqlite3")
            memory.store("hello", "zh-CN", "你好", "fp")
            self.assertIsNotNone(memory.peek("hello", "zh-CN", "fp"))
            self.assertEqual(memory.stats(), {"hits": 0, "misses": 0})
            self.assertEqual(memory.find("hello", "zh-CN", "fp"), "你好")
            self.assertEqual(memory.stats(), {"hits": 1, "misses": 0})

    def test_identical_segment_is_not_reused_across_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = TranslationMemory(Path(temp_dir) / "memory.sqlite3")
            doc_a = Path(temp_dir) / "a.md"
            doc_b = Path(temp_dir) / "b.md"
            doc_a.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            doc_b.write_text(SAMPLE_MARKDOWN + "\nA different trailing paragraph.\n", encoding="utf-8")

            first = FakeProvider()
            self._pipeline(first, memory).run(doc_a, "zh-CN", write_output=False)
            second = FakeProvider()
            self._pipeline(second, memory).run(doc_b, "zh-CN", write_output=False)

            self.assertGreaterEqual(first.calls.count("translate"), 1)
            self.assertGreaterEqual(second.calls.count("translate"), 1)

    @staticmethod
    def _pipeline(provider, memory) -> TranslationPipeline:
        config = _config(enable_glossary=False)
        return TranslationPipeline(
            config=config,
            parser=MarkdownParser(),
            extractor=SegmentExtractor(),
            translator_agent=TranslatorAgent(provider),
            reviewer_agent=ReviewerAgent(provider),
            format_guard_agent=FormatGuardAgent(provider),
            validator=MarkdownValidator(),
            memory=memory,
        )


class PromptCoherenceTests(unittest.TestCase):
    def _context(self) -> DocumentContext:
        return DocumentContext(
            title="Doc",
            abstract="abstract",
            section_summaries={},
            style_guide=["Tone: technical"],
            audience="developers",
            heading_outline=["Introduction", "Advanced Usage"],
            glossary={"agent": "智能体"},
        )

    def test_translator_prompt_carries_outline_and_glossary(self) -> None:
        segments = [_segment("s0", "paragraph", "The agent runtime.", 0, 0)]
        bundle = SegmentBundle(bundle_id="b", segments=segments, summary_before="", summary_after="", style_instructions=[])
        _, user_prompt = build_translator_prompts(bundle, self._context(), "zh-CN", mode="quality")
        payload = json.loads(user_prompt)
        self.assertEqual(payload["outline"], ["Introduction", "Advanced Usage"])
        self.assertEqual(payload["brief"]["g"], [["agent", "智能体"]])
        self.assertEqual(payload["guide"], ["Tone: technical"])

    def test_improve_prompt_carries_neighbour_context(self) -> None:
        segments = [
            _segment("s0", "paragraph", "first", 0, 0),
            _segment("s1", "paragraph", "middle", 2, 2),
            _segment("s2", "paragraph", "last", 4, 4),
        ]
        bundle = SegmentBundle(bundle_id="b", segments=segments, summary_before="", summary_after="", style_instructions=[])
        translations = [TranslationResult(segment_id=s.segment_id, translated_text=f"T:{s.source_text}") for s in segments]
        issues = [{"segment_id": "s1", "type": "fluency", "severity": "high", "comment": "awkward"}]
        _, user_prompt = build_improve_prompts(bundle, self._context(), translations, issues)
        payload = json.loads(user_prompt)
        self.assertEqual([item["segment_id"] for item in payload["translations"]], ["s1"])
        neighbors = payload["translations"][0]["neighbors"]
        self.assertEqual(neighbors["prev"]["segment_id"], "s0")
        self.assertEqual(neighbors["prev"]["text"], "T:first")
        self.assertEqual(neighbors["next"]["segment_id"], "s2")

    def test_bundle_carries_a_shared_block_once(self) -> None:
        block = "```python\nprint('x')\n```"
        segments = [
            _segment("s0", "paragraph", "Run this:", 0, 0, {"context_after": [block]}),
            _segment("s1", "paragraph", "The output is x.", 2, 2, {"context_before": [block]}),
        ]
        bundle = SegmentBundle(bundle_id="b", segments=segments, summary_before="", summary_after="", style_instructions=[])
        _, user_prompt = build_translator_prompts(bundle, self._context(), "zh-CN")
        payload = json.loads(user_prompt)
        self.assertEqual(list(payload["blocks"].values()), [block])
        segments_payload = payload["sections"][0]["segs"]
        self.assertEqual(segments_payload[0][2], "b0")
        self.assertEqual(segments_payload[1][2], "b0")

    def test_glossary_prompt_shape(self) -> None:
        system_prompt, user_prompt = build_glossary_prompts(self._context(), "sample text about agents", "zh-CN")
        payload = json.loads(user_prompt)
        self.assertEqual(payload["task"], "glossary")
        self.assertEqual(payload["sample"], "sample text about agents")
        self.assertIn("glossary", system_prompt)


class DriftProvider(FakeProvider):
    """Reports alternating renderings for the same term to force drift."""

    def chat_json(self, system_prompt, user_prompt, call_label="llm", response_schema=None):
        payload = json.loads(user_prompt)
        if payload["task"] == "translate":
            self.schemas.append(response_schema)
            self.calls.append(call_label)
            return {
                "t": [
                    {
                        "i": segment_id,
                        "x": f"[ZH]{text}",
                        "c": 0.99,
                        "a": {"agent": "智A" if index % 2 == 0 else "智B"},
                        "n": [],
                    }
                    for index, (segment_id, text) in enumerate(_payload_segments(payload))
                ],
                "q": [],
            }
        return super().chat_json(system_prompt, user_prompt, call_label, response_schema)


def _drift_markdown() -> str:
    section_a = " ".join(f"Alpha paragraph {i} about the agent runtime." for i in range(12))
    section_b = " ".join(f"Beta paragraph {i} about the agent tools." for i in range(12))
    return (
        "# Drift Doc\n\n"
        f"{section_a}\n\n"
        "## Section B\n\n"
        f"{section_b}\n"
    )


def _drift_pipeline(provider, config, memory=None) -> TranslationPipeline:
    return TranslationPipeline(
        config=config,
        parser=MarkdownParser(),
        extractor=SegmentExtractor(),
        translator_agent=TranslatorAgent(provider),
        reviewer_agent=ReviewerAgent(provider),
        format_guard_agent=FormatGuardAgent(provider),
        validator=MarkdownValidator(),
        memory=memory,
        glossary_agent=GlossaryAgent(provider),
    )


class GlossaryPipelineTests(unittest.TestCase):
    def test_extraction_runs_and_conflicts_get_harmonized(self) -> None:
        provider = DriftProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "drift.md"
            input_path.write_text(_drift_markdown(), encoding="utf-8")
            result = _drift_pipeline(provider, _config()).run(input_path, "zh-CN", write_output=False)

        self.assertGreaterEqual(provider.calls.count("glossary"), 1)
        self.assertGreaterEqual(provider.calls.count("harmonize"), 1)
        harmonized = [item for item in result.translations if "glossary-harmonized" in item.notes]
        self.assertTrue(harmonized)
        self.assertIn("[HARMONIZED]", result.translated_text)

    def test_fast_mode_skips_glossary_coordination(self) -> None:
        provider = DriftProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "drift.md"
            input_path.write_text(_drift_markdown(), encoding="utf-8")
            _drift_pipeline(provider, _config(mode="fast")).run(input_path, "zh-CN", write_output=False)

        self.assertEqual(provider.calls.count("glossary"), 0)
        self.assertEqual(provider.calls.count("harmonize"), 0)

    def test_full_memory_reuse_skips_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = TranslationMemory(Path(temp_dir) / "memory.sqlite3")
            input_path = Path(temp_dir) / "drift.md"
            input_path.write_text(_drift_markdown(), encoding="utf-8")

            first = DriftProvider()
            _drift_pipeline(first, _config(), memory=memory).run(input_path, "zh-CN", write_output=False)
            second = DriftProvider()
            result = _drift_pipeline(second, _config(), memory=memory).run(input_path, "zh-CN", write_output=False)

            self.assertEqual(second.calls.count("glossary"), 0)
            self.assertEqual(second.calls.count("translate"), 0)
            memory_hits = [item for item in result.translations if item.notes == ["translation-memory"]]
            self.assertTrue(memory_hits)


class DocumentContextOutlineTests(unittest.TestCase):
    def test_heading_outline_is_extracted_from_document(self) -> None:
        markdown = "# Title\n\nIntro paragraph.\n\n## Sub\n\nMore text.\n"
        parsed = MarkdownParser().parse(markdown, Path("a.md"), "zh-CN")
        segments = SegmentExtractor().extract(parsed)
        context = DocumentContextBuilder().build(parsed, segments, TranslatorConfig())
        self.assertEqual(context.heading_outline, ["Title", "Sub"])


class AnchorPipelineTests(unittest.TestCase):
    def test_internal_links_follow_translated_headings(self) -> None:
        provider = FakeProvider()
        config = _config(enable_glossary=False)
        pipeline = TranslationPipeline(
            config=config,
            parser=MarkdownParser(),
            extractor=SegmentExtractor(),
            translator_agent=TranslatorAgent(provider),
            reviewer_agent=ReviewerAgent(provider),
            format_guard_agent=FormatGuardAgent(provider),
            validator=MarkdownValidator(),
        )
        markdown = "# Introduction\n\nSee [details](#introduction).\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "anchors.md"
            input_path.write_text(markdown, encoding="utf-8")
            result = pipeline.run(input_path, "zh-CN", write_output=False)

        self.assertIn("# [ZH]Introduction", result.translated_text)
        self.assertIn("](#zhintroduction)", result.translated_text)
        self.assertNotIn("](#introduction)", result.translated_text)


if __name__ == "__main__":
    unittest.main()
