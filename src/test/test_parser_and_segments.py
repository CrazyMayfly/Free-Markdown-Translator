from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.parser.markdown_parser import MarkdownParser
from src.parser.segment_extractor import ProtectedSpanProcessor, SegmentExtractor

SAMPLE_MARKDOWN = """---
title: Sample Doc
description: Demo description
---
# Heading

Paragraph with `code` and [link](https://example.com).
"""


class ParserAndSegmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = MarkdownParser()
        self.extractor = SegmentExtractor()
        self.protector = ProtectedSpanProcessor()
        self.doc = self.parser.parse(SAMPLE_MARKDOWN, Path("README.md"), "zh-CN")

    def test_parse_keeps_front_matter(self) -> None:
        self.assertEqual(self.doc.metadata["front_matter"]["title"], "Sample Doc")
        self.assertIn("# Heading", self.doc.body_text)

    def test_extract_segments_from_front_matter_and_body(self) -> None:
        segments = self.extractor.extract(self.doc)
        segment_ids = {segment.segment_id for segment in segments}
        self.assertIn("fm-title", segment_ids)
        self.assertIn("fm-description", segment_ids)
        self.assertTrue(any(segment.node_type == "heading" for segment in segments))
        self.assertTrue(any(segment.node_type == "paragraph" for segment in segments))

    def test_protected_spans_are_restored(self) -> None:
        paragraph = next(segment for segment in self.extractor.extract(self.doc) if segment.node_type == "paragraph")
        self.assertIn("{{CODE_0}}", paragraph.source_text)
        restored = self.protector.restore(paragraph.source_text, paragraph)
        self.assertIn("`code`", restored)
        self.assertIn("https://example.com", restored)

    def test_table_emits_one_segment_per_row_with_header_context(self) -> None:
        markdown = "| A | B |\n| - | - |\n| 1 | 2 |\n| 3 | 4 |\n"
        doc = self.parser.parse(markdown, Path("table.md"), "zh-CN")
        segments = self.extractor.extract(doc)
        table_rows = [segment for segment in segments if segment.metadata.get("block_kind") == "table_row"]
        self.assertEqual(len(table_rows), 3)
        self.assertEqual([segment.metadata["table_row_index"] for segment in table_rows], [1, 2, 3])
        self.assertTrue(table_rows[0].metadata["is_header"])
        for row in table_rows:
            self.assertEqual(row.metadata["table_header"], "| A | B |")
            self.assertEqual(row.metadata["table_columns"], 2)

    def test_code_block_is_attached_as_read_only_context(self) -> None:
        markdown = "Run this:\n\n```python\nprint('hi')\n```\n\nThe output is hi.\n"
        doc = self.parser.parse(markdown, Path("code.md"), "zh-CN")
        segments = self.extractor.extract(doc)
        before = next(segment for segment in segments if segment.source_text.startswith("Run this"))
        after = next(segment for segment in segments if segment.source_text.startswith("The output"))
        self.assertTrue(before.metadata["context_after"][0].startswith("```python"))
        self.assertTrue(after.metadata["context_before"][0].startswith("```python"))

    def test_long_code_block_keeps_head_and_tail(self) -> None:
        code = "\n".join(f"print({index})" for index in range(60))
        markdown = f"Run this:\n\n```python\n{code}\n```\n"
        doc = self.parser.parse(markdown, Path("code.md"), "zh-CN")
        segments = self.extractor.extract(doc)
        intro = next(segment for segment in segments if segment.source_text.startswith("Run this"))
        snapshot = intro.metadata["context_after"][0]
        self.assertTrue(snapshot.startswith("```python"))
        self.assertIn("…", snapshot)
        self.assertIn("print(59)", snapshot)
        self.assertLess(len(snapshot), 400)

    def test_block_is_attached_to_the_nearest_segment_only(self) -> None:
        # Three consecutive table rows all sit within CONTEXT_LINE_GAP of the
        # block; attaching it to each of them repeated the same text in one
        # prompt. Only the closest row keeps it now.
        markdown = "```\n```\n\n| A |\n| - |\n| 1 |\n| 2 |\n"
        doc = self.parser.parse(markdown, Path("table.md"), "zh-CN")
        segments = self.extractor.extract(doc)
        with_context = [segment for segment in segments if segment.metadata.get("context_before")]
        self.assertEqual(len(with_context), 1)
        self.assertEqual(with_context[0].metadata["block_kind"], "table_row")


if __name__ == "__main__":
    unittest.main()
