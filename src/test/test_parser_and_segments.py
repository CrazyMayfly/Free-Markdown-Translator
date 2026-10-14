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


if __name__ == "__main__":
    unittest.main()
