from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agents.prompts import build_reviewer_prompts, build_translator_prompts
from src.agents.translator_agent import TranslatorAgent
from src.core.types import DocumentContext, SegmentBundle, TranslationResult
from src.llm.client import OpenAIProvider
from src.llm.schemas import TRANSLATION_RESPONSE_SCHEMA
from src.parser.markdown_parser import MarkdownParser
from src.parser.segment_extractor import SegmentExtractor
from src.test.test_ast_pipeline import SAMPLE_MARKDOWN, FakeProvider


class _FakeBadRequest(Exception):
    def __init__(self) -> None:
        super().__init__("simulated 400: response_format unsupported")
        self.status_code = 400


def _fake_response(content: str = '{"translations":[]}') -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


def _make_provider(mode: str = "auto") -> OpenAIProvider:
    with patch("src.llm.client.OpenAI"):
        return OpenAIProvider(
            base_url="http://localhost:1",
            api_key="test-key",
            api_key_env="",
            model="test-model",
            temperature=0.1,
            max_tokens=64,
            structured_outputs=mode,
        )


def _make_bundle() -> tuple[SegmentBundle, DocumentContext]:
    parser = MarkdownParser()
    extractor = SegmentExtractor()
    segments = extractor.extract(parser.parse(SAMPLE_MARKDOWN, Path("README.md"), "zh-CN"))
    bundle = SegmentBundle(
        bundle_id="bundle-0",
        segments=segments,
        summary_before="PREV BUNDLE SUMMARY about installation steps",
        summary_after="",
        style_instructions=[],
    )
    context = DocumentContext(
        title="Sample Doc",
        abstract="Intro paragraph about the tool.",
        section_summaries={},
        style_guide=["Tone: technical", "Audience: developers", "Preserve these terms: FooBar, BazQux"],
        audience="developers",
    )
    return bundle, context


class PromptContextInjectionTests(unittest.TestCase):
    def test_translator_prompt_injects_prev_summary_and_terms(self) -> None:
        bundle, context = _make_bundle()
        _, user_prompt = build_translator_prompts(bundle, context, "zh-CN")
        self.assertIn("PREV BUNDLE SUMMARY", user_prompt)
        self.assertIn("Preserve these terms: FooBar, BazQux", user_prompt)
        self.assertIn("Sample Doc", user_prompt)
        self.assertIn("developers", user_prompt)

    def test_translator_prompt_orders_stable_context_first(self) -> None:
        bundle, context = _make_bundle()
        _, user_prompt = build_translator_prompts(bundle, context, "zh-CN")
        payload = json.loads(user_prompt)
        self.assertEqual(list(payload.keys()), ["task", "ctx", "prev_summary", "segments"])
        # ctx must be identical across bundles of one document for prefix caching.
        other = SegmentBundle(
            bundle_id="bundle-1",
            segments=bundle.segments[:1],
            summary_before="DIFFERENT SUMMARY",
            summary_after="",
            style_instructions=[],
        )
        other_payload = json.loads(build_translator_prompts(other, context, "zh-CN")[1])
        self.assertEqual(payload["ctx"], other_payload["ctx"])

    def test_reviewer_prompt_injects_prev_summary(self) -> None:
        bundle, context = _make_bundle()
        translations = [
            TranslationResult(segment_id=segment.segment_id, translated_text=f"ZH:{segment.source_text}")
            for segment in bundle.segments
        ]
        _, user_prompt = build_reviewer_prompts(bundle, context, translations)
        payload = json.loads(user_prompt)
        self.assertIn("PREV BUNDLE SUMMARY", user_prompt)
        self.assertEqual(list(payload.keys()), ["task", "ctx", "prev_summary", "translations"])

    def test_translator_agent_passes_schema(self) -> None:
        bundle, context = _make_bundle()
        provider = FakeProvider()
        TranslatorAgent(provider).translate_bundle(bundle=bundle, context=context, target_lang="zh-CN")
        self.assertIs(provider.schemas[-1], TRANSLATION_RESPONSE_SCHEMA)


class StructuredOutputsTests(unittest.TestCase):
    def test_auto_mode_uses_json_schema_when_supported(self) -> None:
        provider = _make_provider("auto")
        with patch.object(provider.client.chat.completions, "create", return_value=_fake_response()) as create:
            provider.chat_json("s", '{"task":"translate"}', call_label="translate", response_schema=TRANSLATION_RESPONSE_SCHEMA)
        response_format = create.call_args.kwargs["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertIs(response_format["json_schema"]["schema"], TRANSLATION_RESPONSE_SCHEMA)

    def test_auto_mode_falls_back_permanently_on_400(self) -> None:
        provider = _make_provider("auto")
        outcomes = [_FakeBadRequest(), _fake_response(), _fake_response()]
        with patch.object(provider.client.chat.completions, "create", side_effect=outcomes) as create:
            provider.chat_json("s", "{}", call_label="translate", response_schema=TRANSLATION_RESPONSE_SCHEMA)
            provider.chat_json("s", "{}", call_label="translate", response_schema=TRANSLATION_RESPONSE_SCHEMA)
        formats = [call.kwargs["response_format"] for call in create.call_args_list]
        self.assertEqual([fmt["type"] for fmt in formats], ["json_schema", "json_object", "json_object"])

    def test_off_mode_never_uses_schema(self) -> None:
        provider = _make_provider("off")
        with patch.object(provider.client.chat.completions, "create", return_value=_fake_response()) as create:
            provider.chat_json("s", "{}", call_label="translate", response_schema=TRANSLATION_RESPONSE_SCHEMA)
        self.assertEqual(create.call_args.kwargs["response_format"], {"type": "json_object"})

    def test_on_mode_does_not_fallback(self) -> None:
        provider = _make_provider("on")
        with patch.object(provider.client.chat.completions, "create", side_effect=_FakeBadRequest()):
            with self.assertRaises(_FakeBadRequest):
                provider.chat_json("s", "{}", call_label="translate", response_schema=TRANSLATION_RESPONSE_SCHEMA)

    def test_no_schema_uses_json_object(self) -> None:
        provider = _make_provider("auto")
        with patch.object(provider.client.chat.completions, "create", return_value=_fake_response()) as create:
            provider.chat_json("s", "{}", call_label="translate")
        self.assertEqual(create.call_args.kwargs["response_format"], {"type": "json_object"})


if __name__ == "__main__":
    unittest.main()
