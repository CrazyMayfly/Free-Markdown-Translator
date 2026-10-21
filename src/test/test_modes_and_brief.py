from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agents.brief_agent import BriefAgent
from src.agents.format_guard_agent import FormatGuardAgent
from src.agents.prompts import build_translator_prompts
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.translator_agent import TranslatorAgent
from src.cli.commands import build_pipeline
from src.core.modes import normalize_mode, profile_for
from src.core.pipeline import TranslationPipeline
from src.core.types import DocumentBrief, DocumentContext, SegmentBundle
from src.infra.config import TranslatorConfig
from src.llm.schemas import (
    BRIEF_FAST_SCHEMA,
    BRIEF_RESPONSE_SCHEMA,
    TRANSLATION_COMPACT_SCHEMA,
    TRANSLATION_FAST_SCHEMA,
    TRANSLATION_QUALITY_SCHEMA,
)
from src.memory.brief_cache import BriefCache
from src.parser.markdown_parser import MarkdownParser
from src.parser.segment_extractor import SegmentExtractor
from src.test.test_ast_pipeline import FakeProvider
from src.validators.markdown_validator import MarkdownValidator

SAMPLE = "# Ops\n\nRotate the agent keys for production.\n"


class ModeProfileTests(unittest.TestCase):
    def test_strict_is_a_quality_alias(self) -> None:
        self.assertEqual(normalize_mode("strict"), "quality")
        self.assertEqual(normalize_mode("QUALITY"), "quality")
        self.assertEqual(normalize_mode("unknown"), "balanced")

    def test_profiles_scale_bundle_budget(self) -> None:
        self.assertGreater(profile_for("fast").bundle_scale, profile_for("quality").bundle_scale)
        self.assertFalse(profile_for("fast").previous)
        self.assertTrue(profile_for("quality").final_edit)


class TranslatorSchemaAndPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        parser = MarkdownParser()
        extractor = SegmentExtractor()
        self.segments = extractor.extract(parser.parse(SAMPLE, Path("a.md"), "zh-CN"))
        self.bundle = SegmentBundle(
            bundle_id="b0",
            segments=self.segments,
            summary_before="Previous source text",
            summary_after="",
            style_instructions=[],
        )
        self.context = DocumentContext(
            title="Ops",
            abstract="Operations guide",
            section_summaries={},
            style_guide=["Tone: technical"],
            audience="operators",
            heading_outline=["Ops"],
            glossary={"agent": "智能体", "unused": "未使用"},
            brief=DocumentBrief(
                summary="Operations guide about key rotation.",
                tone="formal",
                audience="operators",
                glossary={"agent": "智能体", "unused": "未使用"},
                section_summaries={"Ops": "Key rotation"},
            ),
        )

    def test_mode_selects_output_schema(self) -> None:
        provider = FakeProvider()
        agent = TranslatorAgent(provider)
        agent.translate_bundle(self.bundle, self.context, "zh-CN", mode="fast")
        self.assertIs(provider.schemas[-1], TRANSLATION_FAST_SCHEMA)
        agent.translate_bundle(self.bundle, self.context, "zh-CN", mode="balanced")
        self.assertIs(provider.schemas[-1], TRANSLATION_COMPACT_SCHEMA)
        agent.translate_bundle(self.bundle, self.context, "zh-CN", mode="quality")
        self.assertIs(provider.schemas[-1], TRANSLATION_QUALITY_SCHEMA)

    def test_fast_array_output_is_parsed(self) -> None:
        agent = TranslatorAgent()
        payload = {"t": [[segment.segment_id, f"[ZH]{segment.source_text}"] for segment in self.bundle.segments]}
        outcome = agent._parse_outcome(self.bundle, payload)
        self.assertEqual(len(outcome.translations), len(self.bundle.segments))
        self.assertEqual(outcome.translations[0].confidence, 1.0)

    def test_fast_prompt_has_terms_and_tone_but_no_sections(self) -> None:
        _, user_prompt = build_translator_prompts(self.bundle, self.context, "zh-CN", mode="fast")
        payload = json.loads(user_prompt)
        self.assertEqual(list(payload.keys()), ["task", "lang", "brief", "segs"])
        self.assertEqual(payload["brief"]["tone"], "formal")
        self.assertEqual(payload["brief"]["aud"], "operators")
        self.assertEqual(payload["brief"]["g"], [["agent", "智能体"]])
        self.assertNotIn("sections", payload)
        self.assertNotIn("blocks", payload)

    def test_balanced_prompt_uses_sections_and_brief_summary(self) -> None:
        _, user_prompt = build_translator_prompts(self.bundle, self.context, "zh-CN")
        payload = json.loads(user_prompt)
        self.assertEqual(payload["brief"]["s"], "Operations guide about key rotation.")
        self.assertIn("sections", payload)
        self.assertEqual(payload["prev"], "Previous source text")
        self.assertNotIn("segments", payload)

    def test_quality_prompt_keeps_style_outline_and_full_schema(self) -> None:
        _, user_prompt = build_translator_prompts(self.bundle, self.context, "zh-CN", mode="quality")
        payload = json.loads(user_prompt)
        self.assertEqual(payload["guide"], ["Tone: technical"])
        self.assertEqual(payload["outline"], ["Ops"])
        self.assertIn("a", json.dumps(payload))


class BriefAgentTests(unittest.TestCase):
    def test_brief_filters_hallucinated_terms_and_keeps_sections(self) -> None:
        class Provider(FakeProvider):
            def chat_json(self, system_prompt, user_prompt, call_label="llm", response_schema=None):
                payload = json.loads(user_prompt)
                if payload["task"] == "brief":
                    self.schemas.append(response_schema)
                    return {
                        "s": "Ops runbook",
                        "tone": "formal",
                        "aud": "operators",
                        "g": [
                            {"term": "agent", "rendering": "智能体"},
                            {"term": "never-in-document", "rendering": "幻觉"},
                        ],
                        "sec": [{"h": "Ops", "sum": "Key rotation"}],
                    }
                return super().chat_json(system_prompt, user_prompt, call_label, response_schema)

        provider = Provider()
        parser = MarkdownParser()
        segments = SegmentExtractor().extract(parser.parse(SAMPLE, Path("a.md"), "zh-CN"))
        context = DocumentContext(
            title="Ops",
            abstract="",
            section_summaries={},
            style_guide=[],
            audience="",
            heading_outline=["Ops"],
        )
        brief = BriefAgent(provider).generate(context, segments, "zh-CN")
        self.assertEqual(brief.glossary, {"agent": "智能体"})
        self.assertEqual(brief.section_summaries, {"Ops": "Key rotation"})
        self.assertEqual(provider.schemas[-1], BRIEF_RESPONSE_SCHEMA)

    def test_fast_brief_uses_compact_schema(self) -> None:
        provider = FakeProvider()
        parser = MarkdownParser()
        segments = SegmentExtractor().extract(parser.parse(SAMPLE, Path("a.md"), "zh-CN"))
        context = DocumentContext(
            title="Ops",
            abstract="",
            section_summaries={},
            style_guide=[],
            audience="",
        )
        BriefAgent(provider).generate(context, segments, "zh-CN", mode="fast")
        self.assertIs(provider.schemas[-1], BRIEF_FAST_SCHEMA)


class BriefPipelineTests(unittest.TestCase):
    def test_pipeline_injects_brief_terms_in_fast_mode(self) -> None:
        class Provider(FakeProvider):
            def __init__(self) -> None:
                super().__init__()
                self.translate_payloads: list[dict] = []

            def chat_json(self, system_prompt, user_prompt, call_label="llm", response_schema=None):
                payload = json.loads(user_prompt)
                if payload["task"] == "brief":
                    self.calls.append(call_label)
                    return {
                        "s": "Ops runbook",
                        "tone": "formal",
                        "aud": "operators",
                        "g": [{"term": "agent", "rendering": "智能体"}],
                        "sec": [{"h": "Ops", "sum": "Key rotation"}],
                    }
                if payload["task"] == "translate":
                    self.translate_payloads.append(payload)
                return super().chat_json(system_prompt, user_prompt, call_label, response_schema)

        provider = Provider()
        config = TranslatorConfig()
        config.pipeline.mode = "fast"
        config.memory.path = ":memory:"
        pipeline = TranslationPipeline(
            config=config,
            parser=MarkdownParser(),
            extractor=SegmentExtractor(),
            translator_agent=TranslatorAgent(provider),
            reviewer_agent=ReviewerAgent(provider),
            format_guard_agent=FormatGuardAgent(provider),
            validator=MarkdownValidator(),
            brief_agent=BriefAgent(provider),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "doc.md"
            input_path.write_text(SAMPLE, encoding="utf-8")
            result = pipeline.run(input_path, "zh-CN", write_output=False)

        self.assertTrue(result.validation.passed)
        self.assertEqual(provider.calls.count("brief"), 1)
        payload = provider.translate_payloads[0]
        self.assertEqual(payload["brief"]["g"], [["agent", "智能体"]])
        self.assertEqual(payload["brief"]["tone"], "formal")


class ReviewGatingTests(unittest.TestCase):
    @staticmethod
    def _pipeline(mode: str, provider: FakeProvider) -> TranslationPipeline:
        config = TranslatorConfig()
        config.pipeline.mode = mode
        config.pipeline.enable_glossary = False
        config.pipeline.enable_sentinels = False
        return TranslationPipeline(
            config=config,
            parser=MarkdownParser(),
            extractor=SegmentExtractor(),
            translator_agent=TranslatorAgent(provider),
            reviewer_agent=ReviewerAgent(provider),
            format_guard_agent=FormatGuardAgent(provider),
            validator=MarkdownValidator(),
        )

    def _run(self, mode: str) -> FakeProvider:
        provider = FakeProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "doc.md"
            input_path.write_text(SAMPLE, encoding="utf-8")
            self._pipeline(mode, provider).run(input_path, "zh-CN", write_output=False)
        return provider

    def test_fast_and_balanced_skip_review_for_clean_small_bundle(self) -> None:
        self.assertEqual(self._run("fast").calls.count("reflect"), 0)
        self.assertEqual(self._run("balanced").calls.count("reflect"), 0)

    def test_quality_always_reviews(self) -> None:
        self.assertGreaterEqual(self._run("quality").calls.count("reflect"), 1)






class BriefMapReduceTests(unittest.TestCase):
    @staticmethod
    def _context() -> DocumentContext:
        return DocumentContext(
            title="Ops",
            abstract="",
            section_summaries={},
            style_guide=[],
            audience="operators",
            heading_outline=["Ops"],
        )

    def test_long_document_maps_chunks_then_reduces(self) -> None:
        markdown = "# Ops\n\n" + "\n\n".join(
            f"Paragraph {index} about the agent runtime and the deployment pipeline." for index in range(12)
        )
        parser = MarkdownParser()
        segments = SegmentExtractor().extract(parser.parse(markdown, Path("long.md"), "zh-CN"))

        class MapProvider(FakeProvider):
            def __init__(self) -> None:
                super().__init__()
                self.brief_calls = 0
                self.merge_calls = 0

            def chat_json(self, system_prompt, user_prompt, call_label="llm", response_schema=None):
                payload = json.loads(user_prompt)
                if payload["task"] == "brief":
                    self.brief_calls += 1
                    self.calls.append(call_label)
                    return {
                        "s": f"part {payload.get('part', '')}",
                        "tone": "technical",
                        "aud": "operators",
                        "g": [{"term": "agent", "rendering": "智能体"}],
                        "sec": [{"h": "Ops", "sum": payload.get("part", "")}],
                    }
                if payload["task"] == "brief_merge":
                    self.merge_calls += 1
                    self.calls.append(call_label)
                    return {
                        "s": "merged summary",
                        "tone": "technical",
                        "aud": "operators",
                        "g": [{"term": "agent", "rendering": "智能体"}],
                        "sec": [{"h": "Ops", "sum": "merged section"}],
                    }
                return super().chat_json(system_prompt, user_prompt, call_label, response_schema)

        provider = MapProvider()
        with patch("src.agents.brief_agent.FULL_INPUT_LIMIT", 180):
            brief = BriefAgent(provider).generate(self._context(), segments, "zh-CN", mode="balanced")
        self.assertGreaterEqual(provider.brief_calls, 2)
        self.assertEqual(provider.merge_calls, 1)
        self.assertEqual(brief.summary, "merged summary")
        self.assertEqual(brief.glossary["agent"], "智能体")

    def test_fast_long_document_merges_partials_without_reduce_call(self) -> None:
        markdown = "# Ops\n\n" + "\n\n".join(
            f"Paragraph {index} about the agent runtime." for index in range(12)
        )
        segments = SegmentExtractor().extract(MarkdownParser().parse(markdown, Path("long.md"), "zh-CN"))

        class MapProvider(FakeProvider):
            def __init__(self) -> None:
                super().__init__()
                self.brief_calls = 0

            def chat_json(self, system_prompt, user_prompt, call_label="llm", response_schema=None):
                payload = json.loads(user_prompt)
                if payload["task"] == "brief":
                    self.brief_calls += 1
                    self.calls.append(call_label)
                    return {"tone": "technical", "aud": "operators", "g": [{"term": "agent", "rendering": "智能体"}]}
                return super().chat_json(system_prompt, user_prompt, call_label, response_schema)

        provider = MapProvider()
        with patch("src.agents.brief_agent.FAST_INPUT_LIMIT", 150):
            brief = BriefAgent(provider).generate(self._context(), segments, "zh-CN", mode="fast")
        self.assertGreaterEqual(provider.brief_calls, 2)
        self.assertNotIn("brief_merge", provider.calls)
        self.assertEqual(brief.glossary["agent"], "智能体")


class BriefCacheTests(unittest.TestCase):
    def test_second_generation_hits_cache_without_llm(self) -> None:
        segments = SegmentExtractor().extract(MarkdownParser().parse(SAMPLE, Path("a.md"), "zh-CN"))
        context = DocumentContext(
            title="Ops",
            abstract="",
            section_summaries={},
            style_guide=[],
            audience="operators",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = BriefCache(Path(temp_dir) / "briefs.sqlite3")
            provider = FakeProvider()
            agent = BriefAgent(provider, cache=cache)
            first = agent.generate(context, segments, "zh-CN", source_text=SAMPLE)
            calls_after_first = len(provider.calls)
            second = agent.generate(context, segments, "zh-CN", source_text=SAMPLE)
        self.assertEqual(len(provider.calls), calls_after_first)
        self.assertEqual(first, second)

    def test_cache_key_changes_with_model_language_and_mode(self) -> None:
        base = BriefCache.make_key("doc", "m1", "zh-CN", "balanced", "v1")
        self.assertNotEqual(base, BriefCache.make_key("doc", "m2", "zh-CN", "balanced", "v1"))
        self.assertNotEqual(base, BriefCache.make_key("doc", "m1", "en", "balanced", "v1"))
        self.assertNotEqual(base, BriefCache.make_key("doc", "m1", "zh-CN", "quality", "v1"))
        self.assertNotEqual(base, BriefCache.make_key("doc", "m1", "zh-CN", "balanced", "v2"))
        self.assertEqual(base, BriefCache.make_key("doc", "m1", "zh-CN", "balanced", "v1"))

class ModelRoutingTests(unittest.TestCase):
    def test_fast_brief_and_quality_models_are_routed(self) -> None:
        class ModelProvider(FakeProvider):
            def __init__(self, model: str) -> None:
                super().__init__()
                self._model = model

            @property
            def model(self) -> str:
                return self._model

        models: list[str] = []

        def fake_build(config, model=None):
            resolved = model or config.provider.model
            models.append(resolved)
            return ModelProvider(resolved)

        config = TranslatorConfig()
        config.pipeline.mode = "fast"
        config.pipeline.fast_model = "fast-model"
        config.pipeline.brief_model = "brief-model"
        with patch("src.cli.commands._build_provider", side_effect=fake_build):
            pipeline = build_pipeline(config)
        translator_provider = pipeline.translator_agent.provider
        assert translator_provider is not None
        self.assertEqual(translator_provider.model, "fast-model")
        brief_agent = pipeline.brief_agent
        assert brief_agent is not None and brief_agent.provider is not None
        self.assertEqual(brief_agent.provider.model, "brief-model")
        self.assertIn("fast-model", models)
        self.assertIn("brief-model", models)

        config = TranslatorConfig()
        config.pipeline.mode = "quality"
        config.pipeline.quality_model = "quality-model"
        with patch("src.cli.commands._build_provider", side_effect=fake_build):
            pipeline = build_pipeline(config)
        translator_provider = pipeline.translator_agent.provider
        assert translator_provider is not None
        self.assertEqual(translator_provider.model, "quality-model")

if __name__ == "__main__":
    unittest.main()
