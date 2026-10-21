from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agents.glossary_agent import GlossaryAgent
from src.agents.judge_agent import JudgeAgent, apply_judge_feedback
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.translator_agent import TranslatorAgent
from src.cli.commands import _build_provider, build_pipeline, evaluate_command, regression_command
from src.core.errors import LLMResponseTruncatedError
from src.core.pipeline import TranslationPipeline
from src.core.types import Segment, TranslationResult
from src.infra.config import TranslatorConfig
from src.llm.client import OpenAIProvider
from src.llm.schemas import TRANSLATION_RESPONSE_SCHEMA
from src.memory.glossary_store import GlossaryStore
from src.memory.translation_memory import TranslationMemory, similarity
from src.parser.markdown_parser import MarkdownParser
from src.parser.segment_extractor import SegmentExtractor
from src.test.test_ast_pipeline import SAMPLE_MARKDOWN, FakeProvider, FormatGuardAgent, _payload_segments
from src.validators.markdown_validator import MarkdownValidator
from src.validators.semantic_sentinel import run_sentinels


def _config(**overrides) -> TranslatorConfig:
    config = TranslatorConfig()
    config.pipeline.mode = overrides.get("mode", "balanced")
    config.pipeline.enable_review = False
    config.pipeline.enable_format_guard = False
    config.pipeline.enable_glossary = overrides.get("enable_glossary", False)
    config.pipeline.enable_anchor_scheduling = overrides.get("enable_anchor_scheduling", True)
    config.memory.fuzzy_examples = overrides.get("fuzzy_examples", True)
    config.memory.reuse_min_confidence = overrides.get("reuse_min_confidence", 0.3)
    return config


def _pipeline(provider, config, memory=None, glossary_store=None) -> TranslationPipeline:
    return TranslationPipeline(
        config=config,
        parser=MarkdownParser(),
        extractor=SegmentExtractor(),
        translator_agent=TranslatorAgent(provider),
        reviewer_agent=ReviewerAgent(provider),
        format_guard_agent=FormatGuardAgent(provider),
        validator=MarkdownValidator(),
        memory=memory,
        glossary_agent=GlossaryAgent(provider) if config.pipeline.enable_glossary else None,
        glossary_store=glossary_store,
    )


class PromptCaptureProvider(FakeProvider):
    """Records every translate prompt payload for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.translate_payloads: list[dict] = []

    def chat_json(self, system_prompt, user_prompt, call_label="llm", response_schema=None):
        payload = json.loads(user_prompt)
        if payload.get("task") == "translate":
            self.translate_payloads.append(payload)
        return super().chat_json(system_prompt, user_prompt, call_label, response_schema)


class SimilarityTests(unittest.TestCase):
    def test_similarity_basics(self) -> None:
        self.assertGreater(similarity("Install the server component", "Install the server components"), 0.8)
        self.assertLess(similarity("Install the server", "Bake a cake for dinner tonight please"), 0.2)
        self.assertEqual(similarity("", "abc"), 0.0)
        self.assertLess(similarity("short text", "a" * 200), 0.01)


class FuzzyMemoryTests(unittest.TestCase):
    def test_find_similar_orders_and_filters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = TranslationMemory(Path(temp_dir) / "memory.sqlite3")
            memory.store("Install the server on the host machine", "zh-CN", "在主机上安装服务端", "fp", style_key="sk")
            memory.store("Remove the server from the host machine", "zh-CN", "从主机上移除服务端", "fp", style_key="sk")
            memory.store("Completely unrelated baking instructions", "zh-CN", "完全无关的烘焙说明", "fp", style_key="sk")
            memory.store("Exact same source line", "zh-CN", "完全相同的源文", "fp", style_key="sk")

            hits = memory.find_similar("Exact same source line", "zh-CN", style_key="sk", limit=5, min_score=0.1)
            sources = [source for _score, source, _translation in hits]
            self.assertNotIn("Exact same source line", sources)  # exact row excluded

            hits = memory.find_similar("Install the server on the guest machine", "zh-CN", style_key="sk", limit=2, min_score=0.1)
            self.assertEqual(hits[0][1], "Install the server on the host machine")
            self.assertTrue(all(score >= 0.1 for score, _s, _t in hits))

    def test_reuse_confidence_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = TranslationMemory(Path(temp_dir) / "memory.sqlite3")
            memory.store("hello world", "zh-CN", "你好世界", "fp", confidence=1.0)
            memory.store("downweighted", "zh-CN", "降权", "fp", confidence=0.0)
            self.assertEqual(memory.find("hello world", "zh-CN", "fp", min_confidence=0.3), "你好世界")
            self.assertIsNone(memory.find("downweighted", "zh-CN", "fp", min_confidence=0.3))
            self.assertTrue(memory.downweight("hello world", "zh-CN", "fp", confidence=0.0))
            self.assertIsNone(memory.find("hello world", "zh-CN", "fp", min_confidence=0.3))
            self.assertFalse(memory.downweight("missing", "zh-CN", "fp"))

    def test_pipeline_reuses_near_identical_segment_without_llm(self) -> None:
        long_paragraph = (
            "Deploy the application service on every host in the cluster and verify that "
            "the health endpoint responds before moving on to the next machine in the list. "
        ) * 2
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = TranslationMemory(Path(temp_dir) / "memory.sqlite3")
            base_doc = Path(temp_dir) / "base.md"
            base_doc.write_text(f"# Title\n\n{long_paragraph}\n", encoding="utf-8")
            first = PromptCaptureProvider()
            _pipeline(first, _config(), memory=memory).run(base_doc, "zh-CN", write_output=False)

            tweaked = Path(temp_dir) / "tweaked.md"
            tweaked.write_text(f"# Title\n\n{long_paragraph.replace('every host', 'every hosts')}\n", encoding="utf-8")
            second = PromptCaptureProvider()
            result = _pipeline(second, _config(), memory=memory).run(tweaked, "zh-CN", write_output=False)

            # Only the heading needs an LLM call: identical across documents
            # but document-scoped memory does not reuse it; the near-identical
            # paragraph is served by fuzzy reuse.
            self.assertEqual(second.calls.count("translate"), 1)
            fuzzy_hits = [item for item in result.translations if item.notes == ["translation-memory-fuzzy"]]
            self.assertTrue(fuzzy_hits)

    def test_pipeline_injects_similar_examples_as_fewshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = TranslationMemory(Path(temp_dir) / "memory.sqlite3")
            base_doc = Path(temp_dir) / "base.md"
            base_doc.write_text("# Guide\n\nConfigure the cache size for production deployments.\n\nAnother unrelated paragraph about gardening tools and seeds.\n", encoding="utf-8")
            first = PromptCaptureProvider()
            _pipeline(first, _config(), memory=memory).run(base_doc, "zh-CN", write_output=False)

            related = Path(temp_dir) / "related.md"
            related.write_text("# Guide\n\nConfigure the cache size for staging deployments.\n", encoding="utf-8")
            second = PromptCaptureProvider()
            _pipeline(second, _config(), memory=memory).run(related, "zh-CN", write_output=False)

            self.assertEqual(second.calls.count("translate"), 1)
            payload = second.translate_payloads[0]
            self.assertIn("similar", payload)
            self.assertTrue(payload["similar"])
            self.assertTrue(any("production" in item[0] for examples in payload["similar"].values() for item in examples))


class GlossaryStoreTests(unittest.TestCase):
    def test_user_entries_shadow_model_upserts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = GlossaryStore(Path(temp_dir) / "glossary.sqlite3")
            store.upsert("zh-CN", "agent", "代理", origin="model")
            store.upsert("zh-CN", "agent", "智能体", origin="user")
            store.upsert("zh-CN", "agent", "另一译法", origin="model")  # must not clobber the user row
            self.assertEqual(store.load("zh-CN"), {"agent": "智能体"})
            entry = store.entries("zh-CN")[0]
            self.assertEqual(entry["origin"], "user")
            self.assertTrue(store.delete("zh-CN", "agent"))
            self.assertEqual(store.load("zh-CN"), {})
            self.assertEqual(store.languages(), [])

    def test_pipeline_merges_persisted_glossary_over_extraction(self) -> None:
        class ExtractingProvider(FakeProvider):
            def chat_json(self, system_prompt, user_prompt, call_label="llm", response_schema=None):
                payload = json.loads(user_prompt)
                if payload["task"] == "glossary":
                    self.calls.append(call_label)
                    self.schemas.append(response_schema)
                    return {"terms": [{"term": "agent", "rendering": "模型抽取的译法"}, {"term": "cache", "rendering": "缓存"}]}
                return super().chat_json(system_prompt, user_prompt, call_label, response_schema)

        with tempfile.TemporaryDirectory() as temp_dir:
            store = GlossaryStore(Path(temp_dir) / "glossary.sqlite3")
            store.upsert("zh-CN", "agent", "用户指定", origin="user")

            provider = ExtractingProvider()
            config = _config(enable_glossary=True)
            input_path = Path(temp_dir) / "doc.md"
            input_path.write_text("# Doc\n\nThe agent uses the cache layer heavily.\n", encoding="utf-8")
            pipeline = _pipeline(provider, config, glossary_store=store)
            result = pipeline.run(input_path, "zh-CN", write_output=False)

            # Extraction result was persisted (model origin, does not clobber user rows).
            self.assertEqual(store.load("zh-CN")["agent"], "用户指定")
            # The model-extracted "cache" term starts pending (1 document seen),
            # so it is persisted but not yet injected via load().
            entries = {e["term"]: e for e in store.entries("zh-CN")}
            self.assertEqual(entries["cache"]["rendering"], "缓存")
            self.assertEqual(entries["cache"]["status"], "pending")
            self.assertEqual(entries["cache"]["doc_count"], 1)
            self.assertNotIn("cache", store.load("zh-CN"))
            # The runtime glossary honoured the user entry over the extraction.
            self.assertIsNotNone(result.context)
            assert result.context is not None
            self.assertEqual(result.context.glossary["agent"], "用户指定")
            self.assertEqual(result.context.glossary["cache"], "缓存")


class SentinelTests(unittest.TestCase):
    @staticmethod
    def _segment(segment_id: str, text: str):
        return Segment(
            segment_id=segment_id,
            node_type="paragraph",
            source_text=text,
            context_path=[],
            line_start=0,
            line_end=0,
        )

    def test_placeholder_parity_detected(self) -> None:
        segments = [self._segment("s0", "Use {{CODE_0}} here and {{URL_0}} too")]
        translations = [TranslationResult(segment_id="s0", translated_text="在 {{CODE_0}} 使用")]
        findings = run_sentinels(segments, translations)
        self.assertEqual([finding.check for finding in findings], ["placeholder_parity"])

    def test_number_parity_detected(self) -> None:
        segments = [self._segment("s0", "Set the timeout to 30 seconds over 3 retries")]
        translations = [TranslationResult(segment_id="s0", translated_text="将超时设置为 3 0 秒并重试 3 次")]
        findings = run_sentinels(segments, translations)
        self.assertIn("number_parity", [finding.check for finding in findings])

    def test_thousand_separator_normalized(self) -> None:
        segments = [self._segment("s0", "Costs 1,000 dollars per month")]
        translations = [TranslationResult(segment_id="s0", translated_text="每月花费 1000 美元")]
        findings = run_sentinels(segments, translations)
        self.assertNotIn("number_parity", [finding.check for finding in findings])

    def test_length_ratio_detected_for_long_segments_only(self) -> None:
        long_source = "word " * 40
        segments = [self._segment("s0", long_source)]
        translations = [TranslationResult(segment_id="s0", translated_text="短")]
        findings = run_sentinels(segments, translations)
        self.assertIn("length_ratio", [finding.check for finding in findings])
        # Short segments are exempt from the ratio check.
        short = [self._segment("s1", "tiny"), ]
        short_translations = [TranslationResult(segment_id="s1", translated_text="长得多的翻译文本")]
        self.assertEqual(run_sentinels(short, short_translations), [])

    def test_pipeline_sentinel_forces_review(self) -> None:
        class NumberDroppingProvider(FakeProvider):
            def chat_json(self, system_prompt, user_prompt, call_label="llm", response_schema=None):
                payload = json.loads(user_prompt)
                if payload["task"] == "translate":
                    self.calls.append(call_label)
                    return {
                        "t": [
                            {
                                "i": segment_id,
                                "x": "翻译丢失了数字" if "30" in text else f"[ZH]{text}",
                                "c": 0.99,
                                "a": {},
                                "n": [],
                            }
                            for segment_id, text in _payload_segments(payload)
                        ],
                        "q": [],
                    }
                return super().chat_json(system_prompt, user_prompt, call_label, response_schema)

        provider = NumberDroppingProvider()
        config = _config()
        config.pipeline.enable_sentinels = True
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "doc.md"
            input_path.write_text("# Doc\n\nSet the timeout to 30 seconds for the worker.\n", encoding="utf-8")
            result = _pipeline(provider, config).run(input_path, "zh-CN", write_output=False)

        # balanced would normally skip review for this small bundle; the
        # sentinel finding forces it.
        self.assertGreaterEqual(provider.calls.count("reflect"), 1)
        self.assertTrue(any(note.startswith("sentinel:") for item in result.translations for note in item.notes))
        self.assertIn("sentinel_findings", result.report)


class TruncationDetectionTests(unittest.TestCase):
    @staticmethod
    def _truncated_response() -> SimpleNamespace:
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"translations": [{"segment_i'), finish_reason="length")],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=8, total_tokens=18),
        )

    def test_length_finish_reason_raises_specific_error(self) -> None:
        with patch("src.llm.client.OpenAI"):
            provider = OpenAIProvider(base_url="http://localhost:1", api_key="k", api_key_env="", model="m", temperature=0.1, max_tokens=8)
        with patch.object(provider.client.chat.completions, "create", return_value=self._truncated_response()) as create:
            with self.assertRaises(LLMResponseTruncatedError):
                provider.chat_json("s", "{}", call_label="translate", response_schema=TRANSLATION_RESPONSE_SCHEMA)
        self.assertEqual(create.call_count, 1)  # no retry loop burn

    def test_pipeline_does_not_retry_truncation(self) -> None:
        class TruncatingProvider(FakeProvider):
            def __init__(self) -> None:
                super().__init__()
                self.translate_calls = 0

            async def chat_json_async(self, system_prompt, user_prompt, call_label="llm", response_schema=None):
                if json.loads(user_prompt).get("task") == "translate":
                    self.translate_calls += 1
                    raise LLMResponseTruncatedError("truncated by max_tokens=8")
                return await super().chat_json_async(system_prompt, user_prompt, call_label, response_schema)

        provider = TruncatingProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "doc.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            with self.assertRaises(LLMResponseTruncatedError):
                _pipeline(provider, _config()).run(input_path, "zh-CN", write_output=False)
        self.assertEqual(provider.translate_calls, 1)


class AnchorSchedulingTests(unittest.TestCase):
    def test_parallel_bundles_carry_anchor_translations(self) -> None:
        section_a = " ".join(f"Alpha paragraph {i} with some body text." for i in range(20))
        section_b = " ".join(f"Beta paragraph {i} with other body text." for i in range(20))
        markdown = f"# Doc\n\n{section_a}\n\n## Section B\n\n{section_b}\n"

        provider = PromptCaptureProvider()
        config = _config()
        # Keep one bundle per section: the default min_bundle_tokens (800) would
        # merge these two ~240-token sections into a single bundle.
        config.segmentation.min_bundle_tokens = 0
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "anchors.md"
            input_path.write_text(markdown, encoding="utf-8")
            _pipeline(provider, config).run(input_path, "zh-CN", write_output=False)

        # Two section-aligned bundles, both start with a heading -> both are
        # anchors; no non-anchor exists, so nothing to assert about carrying.
        # Use a three-bundle doc instead for the carrying assertion.
        self.assertGreaterEqual(len(provider.translate_payloads), 2)

    def test_non_anchor_bundle_prompt_contains_anchor_context(self) -> None:
        section_a = " ".join(f"Alpha paragraph number {i} with body text." for i in range(30))
        section_b = " ".join(f"Beta paragraph number {i} with body text." for i in range(30))
        tail_b = " ".join(f"Tail paragraph number {i} with body text." for i in range(20))
        markdown = f"# Doc\n\n{section_a}\n\n## Section B\n\n{section_b}\n\n{tail_b}\n"

        provider = PromptCaptureProvider()
        config = _config()
        # Force several bundles so a non-anchor bundle exists after section B.
        config.segmentation.max_bundle_tokens = 240
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "anchors.md"
            input_path.write_text(markdown, encoding="utf-8")
            _pipeline(provider, config).run(input_path, "zh-CN", write_output=False)

        self.assertGreaterEqual(len(provider.translate_payloads), 3)
        anchorless = [payload for payload in provider.translate_payloads if "anchor" in payload]
        self.assertTrue(anchorless, "at least one non-anchor bundle should carry anchor context")
        anchors = anchorless[0]["anchor"]
        self.assertTrue(anchors)
        self.assertTrue(any("[ZH]" in entry[1] for entry in anchors))

    def test_anchor_scheduling_disabled_keeps_prompt_without_anchor(self) -> None:
        section_a = " ".join(f"Alpha paragraph number {i} with body text." for i in range(30))
        section_b = " ".join(f"Beta paragraph number {i} with body text." for i in range(30))
        tail_b = " ".join(f"Tail paragraph number {i} with body text." for i in range(20))
        markdown = f"# Doc\n\n{section_a}\n\n## Section B\n\n{section_b}\n\n{tail_b}\n"

        provider = PromptCaptureProvider()
        config = _config(enable_anchor_scheduling=False)
        config.segmentation.max_bundle_tokens = 240
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "anchors.md"
            input_path.write_text(markdown, encoding="utf-8")
            _pipeline(provider, config).run(input_path, "zh-CN", write_output=False)

        self.assertTrue(all("anchor" not in payload for payload in provider.translate_payloads))


class ModelRoutingTests(unittest.TestCase):
    def test_reviewer_gets_dedicated_model_when_configured(self) -> None:
        config = _config()
        config.pipeline.enable_review = True
        config.pipeline.reviewer_model = "strong-reviewer-model"
        with patch("src.llm.client.AsyncOpenAI"):
            pipeline = build_pipeline(config)
        translator_model = pipeline.translator_agent.provider.model if pipeline.translator_agent.provider else None
        reviewer_model = pipeline.reviewer_agent.provider.model if pipeline.reviewer_agent.provider else None
        self.assertEqual(translator_model, config.provider.model)
        self.assertEqual(reviewer_model, "strong-reviewer-model")
        self.assertIsNot(pipeline.reviewer_agent.provider, pipeline.translator_agent.provider)

    def test_no_reviewer_model_shares_provider(self) -> None:
        config = _config()
        config.pipeline.enable_review = True
        with patch("src.llm.client.AsyncOpenAI"):
            pipeline = build_pipeline(config)
        self.assertIs(pipeline.reviewer_agent.provider, pipeline.translator_agent.provider)

    def test_build_provider_accepts_model_override(self) -> None:
        config = _config()
        with patch("src.llm.client.AsyncOpenAI"):
            provider = _build_provider(config, model="judge-model")
        self.assertEqual(provider.model, "judge-model")


class JudgeFeedbackTests(unittest.TestCase):
    def test_weak_segments_parsed_and_applied(self) -> None:
        class WeakJudgeProvider(FakeProvider):
            def chat_json(self, system_prompt, user_prompt, call_label="llm", response_schema=None):
                payload = json.loads(user_prompt)
                if payload.get("task") == "judge":
                    return {
                        "scores": {"accuracy": 3.0, "fluency": 3.0, "terminology": 3.0, "format": 4.0},
                        "overall": 3.2,
                        "comments": [],
                        "weak_segments": ["body-1"],
                    }
                return super().chat_json(system_prompt, user_prompt, call_label, response_schema)

        provider = WeakJudgeProvider()
        segments = SegmentExtractor().extract(MarkdownParser().parse(SAMPLE_MARKDOWN, Path("a.md"), "zh-CN"))
        report = JudgeAgent(provider).evaluate(segments, [], None, "zh-CN")
        self.assertEqual(report["weak_segments"], ["body-1"])

        with tempfile.TemporaryDirectory() as temp_dir:
            memory = TranslationMemory(Path(temp_dir) / "memory.sqlite3")
            fingerprint = "fp"
            for segment in segments:
                memory.store(segment.source_text, "zh-CN", f"[ZH]{segment.source_text}", fingerprint, confidence=1.0)
            downweighted = apply_judge_feedback(memory, fingerprint, "zh-CN", segments, report["weak_segments"])
            self.assertEqual(downweighted, 1)
            weak_segment = next(segment for segment in segments if segment.segment_id == "body-1")
            self.assertIsNone(memory.find(weak_segment.source_text, "zh-CN", fingerprint, min_confidence=0.3))

    def test_evaluate_command_downweights_memory(self) -> None:
        provider = FakeProvider()

        class JudgeStub(JudgeAgent):
            async def evaluate_async(self, segments, translations, context, target_lang, reference=None):
                return {
                    "target_lang": target_lang,
                    "scores": {"accuracy": 3.0, "fluency": 3.0, "terminology": 3.0, "format": 4.0},
                    "overall": 3.2,
                    "comments": [],
                    "weak_segments": ["body-1"],
                }

        segments = SegmentExtractor().extract(MarkdownParser().parse(SAMPLE_MARKDOWN, Path("a.md"), "zh-CN"))

        class FakePipeline:
            def __init__(self, memory) -> None:
                self.memory = memory

            async def run_async(self, input_path, target_lang, write_output=True, output_path=None, semaphore=None, bundle_progress_callback=None, stage_callback=None):
                return SimpleNamespace(
                    segments=segments,
                    translations=[TranslationResult(segment_id=s.segment_id, translated_text=f"[ZH]{s.source_text}") for s in segments],
                    context=None,
                    validation=SimpleNamespace(passed=True),
                    api_usage=SimpleNamespace(total=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3, call_count=1)),
                )

            def memory_fingerprint_for(self, source_text: str) -> str:
                return "fp"

        import contextlib
        import io

        with tempfile.TemporaryDirectory() as temp_dir:
            memory = TranslationMemory(Path(temp_dir) / "memory.sqlite3")
            for segment in segments:
                memory.store(segment.source_text, "zh-CN", f"[ZH]{segment.source_text}", "fp", confidence=1.0)

            input_path = Path(temp_dir) / "README.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            config = _config()
            config.memory.path = str(Path(temp_dir) / "memory.sqlite3")
            with (
                patch("src.cli.commands.build_pipeline", return_value=FakePipeline(memory)),
                patch("src.cli.commands.build_memory", return_value=memory),
                patch("src.cli.commands._build_provider", return_value=provider),
                patch("src.cli.commands.JudgeAgent", JudgeStub),
            ):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    exit_code = evaluate_command(str(input_path), "zh-CN", config)

            self.assertEqual(exit_code, 0)
            printed = json.loads(buffer.getvalue())
            self.assertEqual(printed["weak_segments"], ["body-1"])
            self.assertEqual(printed["memory_downweighted"], 1)
            weak_segment = next(segment for segment in segments if segment.segment_id == "body-1")
            self.assertIsNone(memory.find(weak_segment.source_text, "zh-CN", "fp", min_confidence=0.3))


class RegressionCommandTests(unittest.TestCase):
    def test_regression_command_judges_against_references(self) -> None:
        provider = FakeProvider()
        segments = SegmentExtractor().extract(MarkdownParser().parse("First golden source.\n\nSecond golden source.\n", Path("g.md"), "zh-CN"))

        class FakePipeline:
            async def run_async(self, input_path, target_lang, write_output=True, output_path=None, semaphore=None, bundle_progress_callback=None, stage_callback=None):
                return SimpleNamespace(
                    segments=segments,
                    translations=[TranslationResult(segment_id=s.segment_id, translated_text=f"[ZH]{s.source_text}") for s in segments],
                    context=None,
                    validation=SimpleNamespace(passed=True),
                    api_usage=SimpleNamespace(total=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3, call_count=1)),
                )

        seen: dict = {}

        class JudgeStub(JudgeAgent):
            async def evaluate_async(self, segs, translations, context, target_lang, reference=None):
                seen["reference"] = reference
                seen["segment_ids"] = [item.segment_id for item in translations]
                return {
                    "target_lang": target_lang,
                    "scores": {"accuracy": 5.0, "fluency": 4.0, "terminology": 4.5, "format": 5.0},
                    "overall": 4.5,
                    "comments": [],
                    "weak_segments": [],
                }

        import contextlib
        import io

        with tempfile.TemporaryDirectory() as temp_dir:
            golden_path = Path(temp_dir) / "golden.json"
            golden_path.write_text(
                json.dumps(
                    {
                        "items": [
                            {"source": "First golden source.", "reference": "第一条黄金样例。"},
                            {"source": "Second golden source.", "reference": "第二条黄金样例。"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            with (
                patch("src.cli.commands.build_pipeline", return_value=FakePipeline()),
                patch("src.cli.commands._build_provider", return_value=provider),
                patch("src.cli.commands.JudgeAgent", JudgeStub),
            ):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    exit_code = regression_command(str(golden_path), _config())

        self.assertEqual(exit_code, 0)
        self.assertEqual(seen["reference"], {"body-0": "第一条黄金样例。", "body-1": "第二条黄金样例。"})
        printed = json.loads(buffer.getvalue())
        self.assertEqual(printed["segments"], 2)
        self.assertEqual(printed["overall"], 4.5)


if __name__ == "__main__":
    unittest.main()
