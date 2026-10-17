from __future__ import annotations

from markdown_it import MarkdownIt

from src.core.types import ParsedDocument, ValidationReport
from src.parser.frontmatter import split_front_matter


class StructureValidator:
    IMMUTABLE_TOKEN_TYPES = {"fence", "code_block", "bullet_list_open", "ordered_list_open", "heading_open", "table_open"}

    def __init__(self) -> None:
        self.md = MarkdownIt("commonmark", {"html": True}).enable("table")

    def validate(self, source_doc: ParsedDocument, output_text: str) -> ValidationReport:
        try:
            target_body = split_front_matter(output_text).body
            target_tokens = self.md.parse(target_body)
        except Exception as exc:
            return ValidationReport(passed=False, errors=[f"Markdown parse failed: {exc}"])

        source_signature = [(token.type, token.tag, token.nesting) for token in source_doc.ast if token.type in self.IMMUTABLE_TOKEN_TYPES]
        target_signature = [(token.type, token.tag, token.nesting) for token in target_tokens if token.type in self.IMMUTABLE_TOKEN_TYPES]
        if source_signature != target_signature:
            return ValidationReport(
                passed=False,
                errors=["Structural token signature changed unexpectedly."],
                metrics={"source_signature_len": len(source_signature), "target_signature_len": len(target_signature)},
            )
        return ValidationReport(passed=True, metrics={"token_count": len(target_tokens)})
