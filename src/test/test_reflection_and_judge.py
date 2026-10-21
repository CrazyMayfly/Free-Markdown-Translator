from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agents.judge_agent import JudgeAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.cli.commands import evaluate_command
from src.core.pipeline import TranslationPipeline
from src.core.types import DocumentContext, TranslationResult
from src.infra.config import TranslatorConfig
from src.llm.schemas import JUDGE_RESPONSE_SCHEMA, REFLECTION_RESPONSE_SCHEMA, TRANSLATION_RESPONSE_SCHEMA
from src.parser.markdown_parser import MarkdownParser
from src.parser.segment_extractor import SegmentExtractor
from src.test.test_ast_pipeline import SAMPLE_MARKDOWN, FakeProvider, FormatGuardAgent, TranslatorAgent
from src.validators.markdown_validator import MarkdownValidator


class IssueFakeProvider(FakeProvider):
    """Returns one critique of a configurable severity, echoing improved text."""

    def __init__(self, severity: str = "high", segment_index: int = 0) -> None:
        super().__init__()
        self.severity = severity
        self.segment_index = segment_index
        self.reflect_payloads: list[dict] = []

    def chat_json(self, system_prompt, user_prompt, call_label="llm", response_schema=None):
        payload = json.loads(user_prompt)
        if payload["task"] == "reflect":
            self.calls.append(call_label)
            self.schemas.append(response_schema)
            segment_id = payload["translations"][self.segment_index]["segment_id"]
            return {
                "issues": [
                    {
                        "segment_id": segment_id,
                        "type": "fluency",
                        "severity": self.severity,
                        "comment": "awkward phrasing in first sentence",
                    }
                ]
            }
        return super().chat_json(system_prompt, user_prompt, call_label, response_schema)


def _build_pipeline(provider, config) -> TranslationPipeline:
    return TranslationPipeline(
        config=config,
        parser=MarkdownParser(),
        extractor=SegmentExtractor(),
        translator_agent=TranslatorAgent(provider),
        reviewer_agent=ReviewerAgent(provider),
        format_guard_agent=FormatGuardAgent(provider),
        validator=MarkdownValidator(),
    )


def _default_config(mode: str) -> TranslatorConfig:
    config = TranslatorConfig()
    config.pipeline.mode = mode
    config.pipeline.enable_review = False
    config.pipeline.enable_format_guard = False
    config.pipeline.fail_on_validation_error = True
    return config


class ReflectionLoopTests(unittest.TestCase):
    def test_high_severity_issue_triggers_improve_in_strict_mode(self) -> None:
        provider = IssueFakeProvider(severity="high")
        pipeline = _build_pipeline(provider, _default_config("strict"))
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "README.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            result = pipeline.run(input_path, "zh-CN", write_output=False)

        # review_max_rounds=2: the fix from round 1 is re-verified in round 2.
        self.assertEqual(provider.calls.count("reflect"), 2)
        self.assertEqual(provider.calls.count("improve"), 2)
        self.assertIn("[IMPROVED]", result.translated_text)
        flagged_notes = [item for item in result.translations if any(note.startswith("review:") for note in item.notes)]
        self.assertTrue(flagged_notes)

    def test_low_severity_issue_skipped_in_balanced_mode(self) -> None:
        provider = IssueFakeProvider(severity="low")
        pipeline = _build_pipeline(provider, _default_config("balanced"))
        # balanced only reviews by condition; force it
        pipeline.config.pipeline.enable_review = True
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "README.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            result = pipeline.run(input_path, "zh-CN", write_output=False)

        self.assertEqual(provider.calls.count("reflect"), 1)
        self.assertEqual(provider.calls.count("improve"), 0)
        self.assertNotIn("[IMPROVED]", result.translated_text)

    def test_low_severity_issue_improved_in_strict_mode(self) -> None:
        provider = IssueFakeProvider(severity="low")
        pipeline = _build_pipeline(provider, _default_config("strict"))
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "README.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            pipeline.run(input_path, "zh-CN", write_output=False)

        # Round 1 improves; round 2 re-verifies the improved segment.
        self.assertEqual(provider.calls.count("improve"), 2)

    def test_medium_severity_issue_improved_in_balanced_mode(self) -> None:
        provider = IssueFakeProvider(severity="medium")
        pipeline = _build_pipeline(provider, _default_config("balanced"))
        pipeline.config.pipeline.enable_review = True
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "README.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            result = pipeline.run(input_path, "zh-CN", write_output=False)

        # balanced acts on medium severity so terminology drift gets fixed.
        self.assertGreaterEqual(provider.calls.count("improve"), 1)
        self.assertIn("[IMPROVED]", result.translated_text)

    def test_round_two_reflect_only_covers_improved_segments(self) -> None:
        class RecordingProvider(IssueFakeProvider):
            def chat_json(self, system_prompt, user_prompt, call_label="llm", response_schema=None):
                import json as _json

                if _json.loads(user_prompt)["task"] == "reflect":
                    self.reflect_payloads.append(_json.loads(user_prompt))
                return super().chat_json(system_prompt, user_prompt, call_label, response_schema)

        provider = RecordingProvider(severity="high")
        pipeline = _build_pipeline(provider, _default_config("strict"))
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "README.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            pipeline.run(input_path, "zh-CN", write_output=False)

        self.assertEqual(len(provider.reflect_payloads), 2)
        self.assertGreater(len(provider.reflect_payloads[0]["translations"]), 1)
        self.assertEqual(len(provider.reflect_payloads[1]["translations"]), 1)

    def test_reflection_uses_structured_schemas(self) -> None:
        provider = IssueFakeProvider(severity="high")
        bundle_segments = SegmentExtractor().extract(MarkdownParser().parse(SAMPLE_MARKDOWN, Path("a.md"), "zh-CN"))
        from src.core.types import SegmentBundle, TranslationResult

        bundle = SegmentBundle(
            bundle_id="b0",
            segments=bundle_segments,
            summary_before="",
            summary_after="",
            style_instructions=[],
        )
        translations = [TranslationResult(segment_id=s.segment_id, translated_text=f"T:{s.source_text}") for s in bundle_segments]
        context = DocumentContext(title="t", abstract="", section_summaries={}, style_guide=[], audience="")
        ReviewerAgent(provider).review_bundle(bundle, translations, context, min_severity="low")
        self.assertIn(REFLECTION_RESPONSE_SCHEMA, provider.schemas)
        self.assertIn(TRANSLATION_RESPONSE_SCHEMA, provider.schemas)


class JudgeTests(unittest.TestCase):
    def test_judge_agent_parses_scores(self) -> None:
        provider = FakeProvider()
        segments = SegmentExtractor().extract(MarkdownParser().parse(SAMPLE_MARKDOWN, Path("a.md"), "zh-CN"))
        translations: list[TranslationResult] = []
        report = JudgeAgent(provider).evaluate(segments, translations, None, "zh-CN")
        self.assertEqual(report["overall"], 4.5)
        self.assertEqual(report["scores"]["accuracy"], 5.0)
        self.assertEqual(report["target_lang"], "zh-CN")
        self.assertIn(JUDGE_RESPONSE_SCHEMA, provider.schemas)

    def test_judge_agent_requires_provider(self) -> None:
        with self.assertRaises(ValueError):
            JudgeAgent(None).evaluate([], [], None, "zh-CN")

    def test_evaluate_command_prints_report(self) -> None:
        provider = FakeProvider()

        class FakePipeline:
            async def run_async(self, input_path, target_lang, write_output=True, output_path=None, semaphore=None, bundle_progress_callback=None, stage_callback=None):
                parsed_segments = SegmentExtractor().extract(MarkdownParser().parse(SAMPLE_MARKDOWN, Path(input_path), target_lang))
                return SimpleNamespace(
                    segments=parsed_segments,
                    translations=[],
                    context=None,
                    validation=SimpleNamespace(passed=True),
                    api_usage=SimpleNamespace(total=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3, call_count=1)),
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "README.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            config = TranslatorConfig()
            # Keep the command from touching a real memory db during the test.
            config.memory.enabled = False
            with patch("src.cli.commands.build_pipeline", return_value=FakePipeline()), patch(
                "src.cli.commands._build_provider", return_value=provider
            ):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    exit_code = evaluate_command(str(input_path), "zh-CN", config)

        self.assertEqual(exit_code, 0)
        printed = json.loads(buffer.getvalue())
        self.assertEqual(printed["overall"], 4.5)
        self.assertIn("scores", printed)
        self.assertTrue(printed["validation_passed"])


if __name__ == "__main__":
    unittest.main()
