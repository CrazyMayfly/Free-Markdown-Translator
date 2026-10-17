"""Structure-preservation checks over the real Markdown fixtures.

Every file under src/test/fixtures/markdown runs through the full offline
pipeline (FakeProvider, no network) and the translated output is re-parsed
with the same markdown-it config as production. The invariants guarded here
are the ones users actually notice when a translation mangles a document:
fenced code blocks byte-identical, links/images pointing where they did,
table shapes intact, heading levels intact, math and raw syntax untouched.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from markdown_it import MarkdownIt

from src.agents.format_guard_agent import FormatGuardAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.translator_agent import TranslatorAgent
from src.core.pipeline import TranslationPipeline
from src.infra.config import TranslatorConfig
from src.parser.markdown_parser import MarkdownParser
from src.parser.segment_extractor import SegmentExtractor
from src.test.test_ast_pipeline import FakeProvider
from src.test.test_concurrency import ConcurrencyTrackingProvider
from src.validators.markdown_validator import MarkdownValidator

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "markdown"
# README.md documents the fixtures instead of exercising the parser.
FIXTURES = sorted(path for path in FIXTURE_DIR.glob("*.md") if path.name != "README.md")


def _tokens(text: str):
    parser = MarkdownIt("commonmark", {"html": True}).enable("table")
    return parser.parse(text)


def _front_matter_body(text: str) -> str:
    return MarkdownParser().parse(text, Path("fixture.md"), "zh-CN").body_text


def _structure(text: str) -> dict:
    headings: list[str] = []
    fences: list[tuple[str, str]] = []
    hrefs: list[str] = []
    tables: list[int] = []
    inside_table = False
    cells_in_row = 0
    for token in _tokens(_front_matter_body(text)):
        if token.type == "heading_open":
            headings.append(token.tag)
        elif token.type == "fence":
            fences.append((token.info, token.content))
        elif token.type in {"link_open", "image"}:
            href = token.attrGet("href") if token.type == "link_open" else token.attrGet("src")
            if href is not None:
                hrefs.append(href)
        elif token.type == "table_open":
            inside_table = True
        elif token.type == "table_close":
            inside_table = False
        elif inside_table and token.type in {"td_open", "th_open"}:
            cells_in_row += 1
        elif inside_table and token.type == "tr_close":
            tables.append(cells_in_row)
            cells_in_row = 0
    return {"headings": headings, "fences": fences, "hrefs": hrefs, "table_rows": tables}


class FixtureStructureTests(unittest.TestCase):
    def _config(self) -> TranslatorConfig:
        config = TranslatorConfig()
        config.pipeline.mode = "balanced"
        config.pipeline.enable_review = False
        config.pipeline.enable_format_guard = False
        config.pipeline.fail_on_validation_error = True
        return config

    def test_fixtures_exist(self) -> None:
        self.assertGreaterEqual(len(FIXTURES), 6)

    def test_every_fixture_preserves_structure(self) -> None:
        for fixture in FIXTURES:
            with self.subTest(fixture=fixture.name):
                source_text = fixture.read_text(encoding="utf-8")
                provider = ConcurrencyTrackingProvider()
                pipeline = TranslationPipeline(
                    config=self._config(),
                    parser=MarkdownParser(),
                    extractor=SegmentExtractor(),
                    translator_agent=TranslatorAgent(provider),
                    reviewer_agent=ReviewerAgent(provider),
                    format_guard_agent=FormatGuardAgent(provider),
                    validator=MarkdownValidator(),
                )
                result = pipeline.run(fixture, "zh-CN", write_output=False)

                self.assertTrue(result.validation.passed, result.validation.errors)
                self.assertTrue(result.translations)
                self.assertTrue(all(item.translated_text.strip() for item in result.translations))

                source = _structure(source_text)
                translated = _structure(result.translated_text)

                # Heading count and levels survive; text may change, shapes may not.
                self.assertEqual(translated["headings"], source["headings"])

                # Fenced blocks: same languages, byte-identical content.
                self.assertEqual(translated["fences"], source["fences"])

                # Every source link/image target must still be reachable.
                self.assertEqual(sorted(translated["hrefs"]), sorted(source["hrefs"]))

                # Table shapes: same rows, same cells per row.
                self.assertEqual(translated["table_rows"], source["table_rows"])

    def test_math_and_raw_syntax_pass_through(self) -> None:
        source_text = (FIXTURE_DIR / "docs-frontmatter.md").read_text(encoding="utf-8")
        provider = FakeProvider()
        pipeline = TranslationPipeline(
            config=self._config(),
            parser=MarkdownParser(),
            extractor=SegmentExtractor(),
            translator_agent=TranslatorAgent(provider),
            reviewer_agent=ReviewerAgent(provider),
            format_guard_agent=FormatGuardAgent(provider),
            validator=MarkdownValidator(),
        )
        result = pipeline.run(FIXTURE_DIR / "docs-frontmatter.md", "zh-CN", write_output=False)

        self.assertEqual(result.translated_text.count("$$"), source_text.count("$$"))
        self.assertIn("```mermaid", result.translated_text)
        # Front matter is re-serialized by the pipeline, so compare keys and
        # values semantically instead of matching the raw text.
        source_meta = MarkdownParser().parse(source_text, Path("f.md"), "zh-CN").metadata["front_matter"]
        output_meta = MarkdownParser().parse(result.translated_text, Path("f.md"), "zh-CN").metadata["front_matter"]
        self.assertEqual(set(output_meta), set(source_meta))
        self.assertEqual(output_meta["tags"], source_meta["tags"])

    def test_chinese_source_document_translates(self) -> None:
        provider = FakeProvider()
        pipeline = TranslationPipeline(
            config=self._config(),
            parser=MarkdownParser(),
            extractor=SegmentExtractor(),
            translator_agent=TranslatorAgent(provider),
            reviewer_agent=ReviewerAgent(provider),
            format_guard_agent=FormatGuardAgent(provider),
            validator=MarkdownValidator(),
        )
        result = pipeline.run(FIXTURE_DIR / "zh-blog.md", "en", write_output=False)
        self.assertTrue(result.validation.passed, result.validation.errors)
        self.assertIn("```yaml", result.translated_text)
        self.assertIn("https://example.com/docs", result.translated_text)


if __name__ == "__main__":
    unittest.main()
