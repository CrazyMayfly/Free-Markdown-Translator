from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agents.format_guard_agent import FormatGuardAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.translator_agent import TranslatorAgent
from src.cli.commands import (
    TranslationSource,
    _build_translation_tasks,
    _collect_translation_sources,
    translate_command,
)
from src.core.errors import TranslationPipelineError
from src.core.pipeline import TranslationPipeline
from src.core.types import ApiUsageSummary, DocumentContext, SegmentBundle, TranslationResult
from src.infra.config import TranslatorConfig
from src.llm.provider import LLMProvider
from src.parser.ast_mapper import AstMapper
from src.parser.markdown_parser import MarkdownParser
from src.parser.segment_extractor import ProtectedSpanProcessor, SegmentExtractor
from src.validators.markdown_validator import MarkdownValidator

SAMPLE_MARKDOWN = """---
title: Sample Doc
description: Demo description
---
# Heading

Paragraph with `code` and [link](https://example.com).
"""




def _payload_segments(payload: dict) -> list[tuple[str, str]]:
    """Read segments from either the compact translate payload or the legacy shape."""
    if "segs" in payload:
        return [(str(item[0]), str(item[1])) for item in payload["segs"]]
    if "sections" in payload:
        return [
            (str(item[0]), str(item[1]))
            for section in payload["sections"]
            for item in section.get("segs", [])
        ]
    return [(str(item["segment_id"]), str(item["text"])) for item in payload.get("segments", [])]

class FakeProvider(LLMProvider):
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.schemas: list[dict | None] = []

    @property
    def model(self) -> str:
        return "fake-model"

    def get_usage_summary(self):
        from src.core.types import ApiUsageSummary

        return ApiUsageSummary()

    async def chat_json_async(self, system_prompt: str, user_prompt: str, call_label: str = "llm", response_schema: dict | None = None):
        return self.chat_json(system_prompt, user_prompt, call_label, response_schema)

    def chat_json(self, system_prompt: str, user_prompt: str, call_label: str = "llm", response_schema: dict | None = None):
        del system_prompt
        import json

        self.schemas.append(response_schema)
        payload = json.loads(user_prompt)
        task = payload["task"]
        self.calls.append(call_label)
        if task == "translate":
            return {
                "t": [
                    {
                        "i": segment_id,
                        "x": f"[ZH]{text}",
                        "c": 0.99,
                        "a": {},
                        "n": [],
                    }
                    for segment_id, text in _payload_segments(payload)
                ],
                "q": [],
            }
        if task == "brief":
            return {"s": "Fake brief", "tone": "technical", "aud": "developers", "g": [], "sec": []}
        if task == "reflect":
            return {"issues": []}
        if task == "glossary":
            return {"terms": []}
        if task == "judge":
            return {
                "scores": {"accuracy": 5.0, "fluency": 4.0, "terminology": 4.5, "format": 5.0},
                "overall": 4.5,
                "comments": [],
                "weak_segments": [],
            }
        if task in {"review", "improve", "format_guard", "harmonize"}:
            items = payload["translations"]
            prefix = {"improve": "[IMPROVED]", "harmonize": "[HARMONIZED]"}.get(task, "")
            return {
                "translations": [
                    {
                        "segment_id": item["segment_id"],
                        "translated_text": f"{prefix}{item['text']}",
                        "notes": [],
                        "applied_terms": {},
                        "confidence": 0.99,
                    }
                    for item in items
                ]
            }
        raise AssertionError(f"Unexpected task: {task}")


class AstAndPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = MarkdownParser()
        self.extractor = SegmentExtractor()
        self.protector = ProtectedSpanProcessor()
        self.mapper = AstMapper()
        self.provider = FakeProvider()
        self.config = TranslatorConfig()
        self.config.pipeline.mode = "balanced"
        self.config.pipeline.enable_review = False
        self.config.pipeline.enable_format_guard = False
        self.config.pipeline.fail_on_validation_error = True

    def test_ast_mapper_applies_translations(self) -> None:
        doc = self.parser.parse(SAMPLE_MARKDOWN, Path("README.md"), "zh-CN")
        segments = self.extractor.extract(doc)
        doc.segments = segments  # type: ignore[attr-defined]
        translations = [
            TranslationResult(
                segment_id=segment.segment_id,
                translated_text=self.protector.restore(f"TR:{segment.source_text}", segment),
            )
            for segment in segments
        ]
        updated = self.mapper.apply(doc, translations)
        rendered = self.mapper.render(updated)
        self.assertIn("# TR:Heading", rendered)
        self.assertIn("TR:Demo description", rendered)

    def test_pipeline_runs_end_to_end_with_fake_provider(self) -> None:
        pipeline = TranslationPipeline(
            config=self.config,
            parser=self.parser,
            extractor=self.extractor,
            translator_agent=TranslatorAgent(self.provider),
            reviewer_agent=ReviewerAgent(self.provider),
            format_guard_agent=FormatGuardAgent(self.provider),
            validator=MarkdownValidator(),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "README.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            result = pipeline.run(input_path, "zh-CN", write_output=False)

        self.assertTrue(result.validation.passed)
        self.assertIn("# [ZH]Heading", result.translated_text)
        self.assertIn("`code`", result.translated_text)
        self.assertIn("https://example.com", result.translated_text)

    def test_pipeline_emits_one_segment_per_table_row(self) -> None:
        markdown = "# Doc\n\n| A | B |\n| - | - |\n| 1 | 2 |\n| 3 | 4 |\n"
        pipeline = TranslationPipeline(
            config=self.config,
            parser=self.parser,
            extractor=self.extractor,
            translator_agent=TranslatorAgent(self.provider),
            reviewer_agent=ReviewerAgent(self.provider),
            format_guard_agent=FormatGuardAgent(self.provider),
            validator=MarkdownValidator(),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "table.md"
            input_path.write_text(markdown, encoding="utf-8")
            result = pipeline.run(input_path, "zh-CN", write_output=False)

        rows = [segment for segment in result.segments if segment.metadata.get("block_kind") == "table_row"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({row.line_start for row in rows}), 3)
        self.assertTrue(result.validation.passed)

    def test_pipeline_splits_oversized_block_by_line_without_changing_line_count(self) -> None:
        long_paragraph = "\n".join(f"Source line {index} with a few words." for index in range(40))
        markdown = f"# Doc\n\n{long_paragraph}\n\nEnd.\n"
        self.config.segmentation.max_bundle_tokens = 90
        self.config.segmentation.min_bundle_tokens = 0
        pipeline = TranslationPipeline(
            config=self.config,
            parser=self.parser,
            extractor=self.extractor,
            translator_agent=TranslatorAgent(self.provider),
            reviewer_agent=ReviewerAgent(self.provider),
            format_guard_agent=FormatGuardAgent(self.provider),
            validator=MarkdownValidator(),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "long.md"
            input_path.write_text(markdown, encoding="utf-8")
            result = pipeline.run(input_path, "zh-CN", write_output=False)

        self.assertTrue(result.validation.passed)
        self.assertGreater(len(result.segments), 2)
        self.assertEqual(len(result.translated_text.splitlines()), len(markdown.splitlines()))

    def test_default_output_path_uses_primary_language_tag(self) -> None:
        pipeline = TranslationPipeline(
            config=self.config,
            parser=self.parser,
            extractor=self.extractor,
            translator_agent=TranslatorAgent(self.provider),
            reviewer_agent=ReviewerAgent(self.provider),
            format_guard_agent=FormatGuardAgent(self.provider),
            validator=MarkdownValidator(),
        )
        output_path = pipeline._build_output_path(Path("test.md"), "zh-CN")
        self.assertEqual(output_path.name, "test.zh.md")

    def test_translate_command_rejects_output_path_passed_to_to(self) -> None:
        with self.assertRaises(ValueError):
            translate_command(["README.md"], [".\\a.md"], self.config)

    def test_collect_translation_sources_from_directory_preserves_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "docs"
            nested = root / "guide"
            nested.mkdir(parents=True)
            (nested / "intro.md").write_text("# Intro", encoding="utf-8")
            (nested / "skip.txt").write_text("skip", encoding="utf-8")

            sources = _collect_translation_sources([str(root)], "*.md")

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].relative_output_path.as_posix(), "docs/guide/intro.md")

    def test_build_translation_tasks_uses_output_directory(self) -> None:
        source = TranslationSource(
            input_path=Path("docs/guide/intro.md"),
            relative_output_path=Path("docs/guide/intro.md"),
        )
        tasks = _build_translation_tasks([source], ["zh-CN"], Path("translated"), self.config)

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].output_path, Path("translated/docs/guide/intro.zh.md"))

    def test_translate_command_writes_directory_inputs_under_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_root = Path(temp_dir) / "docs"
            nested = input_root / "guide"
            nested.mkdir(parents=True)
            source_path = nested / "intro.md"
            source_path.write_text("# Intro", encoding="utf-8")

            output_root = Path(temp_dir) / "translated"
            self.config.output.directory = str(output_root)
            self.config.output.write_report = False
            self.config.execution.max_parallel_translations = 1

            class FakePipeline:
                async def run_async(self, input_path, target_lang, write_output=True, output_path=None, semaphore=None, bundle_progress_callback=None, stage_callback=None):
                    self.last_call = (input_path, target_lang, write_output, output_path)
                    if bundle_progress_callback is not None:
                        bundle_progress_callback(input_path, target_lang, "bundle-0")
                    if write_output and output_path is not None:
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        output_path.write_text("[ZH] translated", encoding="utf-8")
                    return SimpleNamespace(output_path=output_path, report={}, api_usage=ApiUsageSummary())

            with patch("src.cli.commands.build_pipeline", return_value=FakePipeline()):
                translate_command([str(input_root)], ["zh-CN"], self.config, match_pattern="*.md")

            translated_path = output_root / "docs" / "guide" / "intro.zh.md"
            self.assertTrue(translated_path.exists())
            self.assertEqual(translated_path.read_text(encoding="utf-8"), "[ZH] translated")

    def test_translator_agent_requires_provider(self) -> None:
        agent = TranslatorAgent()
        segments = self.extractor.extract(self.parser.parse(SAMPLE_MARKDOWN, Path("README.md"), "zh-CN"))
        bundle = SegmentBundle(
            bundle_id="bundle-0",
            segments=segments,
            summary_before="",
            summary_after="",
            style_instructions=[],
        )
        context = DocumentContext(
            title="",
            abstract="",
            section_summaries={},
            style_guide=[],
            audience="",
        )
        with self.assertRaises(TranslationPipelineError):
            agent.translate_bundle(bundle=bundle, context=context, target_lang="zh-CN")

    def test_fast_mode_skips_review_and_format_guard(self) -> None:
        self.config.pipeline.mode = "fast"
        pipeline = TranslationPipeline(
            config=self.config,
            parser=self.parser,
            extractor=self.extractor,
            translator_agent=TranslatorAgent(self.provider),
            reviewer_agent=ReviewerAgent(self.provider),
            format_guard_agent=FormatGuardAgent(self.provider),
            validator=MarkdownValidator(),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "README.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            pipeline.run(input_path, "zh-CN", write_output=False)

        self.assertEqual(self.provider.calls.count("translate"), 1)
        self.assertEqual(self.provider.calls.count("review"), 0)
        self.assertEqual(self.provider.calls.count("format_guard"), 0)

    def test_strict_mode_runs_review(self) -> None:
        self.config.pipeline.mode = "strict"
        pipeline = TranslationPipeline(
            config=self.config,
            parser=self.parser,
            extractor=self.extractor,
            translator_agent=TranslatorAgent(self.provider),
            reviewer_agent=ReviewerAgent(self.provider),
            format_guard_agent=FormatGuardAgent(self.provider),
            validator=MarkdownValidator(),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "README.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            pipeline.run(input_path, "zh-CN", write_output=False)

        self.assertEqual(self.provider.calls.count("translate"), 1)
        self.assertEqual(self.provider.calls.count("reflect"), 1)
        self.assertEqual(self.provider.calls.count("improve"), 0)


if __name__ == "__main__":
    unittest.main()
