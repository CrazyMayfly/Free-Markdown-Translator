from __future__ import annotations

import re
from dataclasses import replace

from src.core.types import ParsedDocument, ProtectedSpan, Segment


class ProtectedSpanProcessor:
    def protect(self, segment: Segment) -> Segment:
        text = segment.source_text
        spans: list[ProtectedSpan] = []

        def store(value: str, span_type: str) -> str:
            placeholder = f"{{{{{span_type.upper()}_{len(spans)}}}}}"
            spans.append(ProtectedSpan(placeholder=placeholder, original_text=value, span_type=span_type))
            return placeholder

        text = re.sub(r"(?m)^(#{1,6}\s+)", lambda match: store(match.group(1), "md"), text)
        text = re.sub(r"(?m)^((?:>\s?)+)", lambda match: store(match.group(1), "md"), text)
        text = re.sub(r"(?m)^(\s*(?:[-+*]|\d+\.)\s+)", lambda match: store(match.group(1), "md"), text)
        # A table row's leading pipe is structural like list/quote markers:
        # without protection, any preamble a model prepends to the row breaks
        # GFM table recognition on the way back in.
        text = re.sub(r"(?m)^(\s*\|)", lambda match: store(match.group(1), "md"), text)
        text = re.sub(r"`[^`\n]+`", lambda match: store(match.group(0), "code"), text)
        text = re.sub(r"</?[^>\n]+?>", lambda match: store(match.group(0), "html"), text)
        text = re.sub(
            r"(!?\[[^\]]*]\()([^)]+)(\))",
            lambda match: f"{match.group(1)}{store(match.group(2), 'url')}{match.group(3)}",
            text,
        )
        text = re.sub(r"https?://[^\s)>]+", lambda match: store(match.group(0), "url"), text)
        return replace(segment, source_text=text, protected_spans=spans)

    def restore(self, translated_text: str, segment: Segment) -> str:
        restored = translated_text
        leading_placeholders = re.match(r"^(?:\{\{[A-Z_0-9]+\}\})+", segment.source_text)
        if leading_placeholders:
            prefix = leading_placeholders.group(0)
            restored = re.sub(r"^(?:\{\{[A-Z_0-9]+\}\})+", "", restored)
            restored = prefix + restored.replace(prefix, "")
        for span in segment.protected_spans:
            restored = restored.replace(span.placeholder, span.original_text)
        return restored


class SegmentExtractor:
    SUPPORTED_PARENT_TYPES = {"paragraph_open", "heading_open", "blockquote_open", "td_open", "th_open"}
    FRONTMATTER_TRANSLATABLE_KEYS = {"title", "description"}

    def extract(self, doc: ParsedDocument) -> list[Segment]:
        segments: list[Segment] = []
        heading_stack: list[str] = []
        pending_heading_level: int | None = None
        protector = ProtectedSpanProcessor()

        for index, token in enumerate(doc.ast):
            if token.type == "heading_open":
                pending_heading_level = int(token.tag[1])
                continue
            if token.type != "inline" or token.map is None:
                continue

            parent_type = doc.ast[index - 1].type if index > 0 else ""
            if parent_type not in self.SUPPORTED_PARENT_TYPES:
                continue

            if parent_type == "heading_open" and pending_heading_level is not None:
                heading_stack = heading_stack[: pending_heading_level - 1]
                heading_stack.append(token.content.strip())
                pending_heading_level = None

            line_start, line_end = token.map
            block_text = "\n".join(doc.lines[line_start:line_end]).rstrip("\n")
            if not block_text.strip():
                continue

            segment = Segment(
                segment_id=f"body-{len(segments)}",
                node_type=parent_type.replace("_open", ""),
                source_text=block_text,
                context_path=list(heading_stack),
                line_start=line_start + doc.body_line_offset,
                line_end=line_end + doc.body_line_offset,
                metadata={
                    "body_line_start": line_start,
                    "body_line_end": line_end,
                    "inline_content": token.content,
                },
            )
            segments.append(protector.protect(segment))

        front_matter = doc.metadata.get("front_matter") or {}
        for key, value in front_matter.items():
            if key not in self.FRONTMATTER_TRANSLATABLE_KEYS or not isinstance(value, str) or not value.strip():
                continue
            fm_segment = Segment(
                segment_id=f"fm-{key}",
                node_type="front_matter",
                source_text=value,
                context_path=[front_matter.get("title", "")] if front_matter.get("title") else [],
                line_start=0,
                line_end=doc.body_line_offset,
                metadata={"front_matter_key": key},
            )
            segments.insert(0, protector.protect(fm_segment))

        return segments
