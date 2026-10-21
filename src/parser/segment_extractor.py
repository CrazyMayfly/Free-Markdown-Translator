from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from src.core.types import ParsedDocument, ProtectedSpan, Segment

_TABLE_PARENT_TYPES = {"td_open", "th_open"}


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
    # A code/HTML block is not translated, but the model needs to see it when
    # prose immediately above or below refers to "this code" / "the output".
    CONTEXT_LINE_GAP = 3
    # Snapshot of a block is head + tail, not a plain prefix: the first lines
    # carry the language/signature and the last lines carry the return value or
    # the printed output, which is exactly what "this code" / "the output"
    # refers to. Measured over the bundled READMEs, the median block is only
    # ~55 characters, so this only trims the long tail.
    CONTEXT_BLOCK_HEAD = 120
    CONTEXT_BLOCK_TAIL = 48

    @classmethod
    def _context_snapshot(cls, raw: str) -> str:
        if len(raw) <= cls.CONTEXT_BLOCK_HEAD + cls.CONTEXT_BLOCK_TAIL:
            return raw
        head = raw[: cls.CONTEXT_BLOCK_HEAD].rstrip()
        tail = raw[-cls.CONTEXT_BLOCK_TAIL :].lstrip()
        return f"{head}\n…\n{tail}"

    def extract(self, doc: ParsedDocument) -> list[Segment]:
        segments: list[Segment] = []
        heading_stack: list[str] = []
        pending_heading_level: int | None = None
        protector = ProtectedSpanProcessor()

        list_stack: list[dict[str, Any]] = []
        quote_stack: list[str] = []
        table_state: dict[str, Any] | None = None
        seen_table_rows: set[tuple[int, int]] = set()

        section_counter = 0
        section_id = "front-matter"
        section_level = 0
        section_title = ""

        for index, token in enumerate(doc.ast):
            token_type = token.type

            if token_type == "heading_open":
                pending_heading_level = int(token.tag[1])
                continue

            if token_type in {"bullet_list_open", "ordered_list_open"}:
                list_stack.append({"id": f"list-{len(list_stack)}-{index}", "items": 0, "top_item": None})
                continue
            if token_type == "list_item_open":
                entry = list_stack[-1]
                entry["items"] = int(entry["items"]) + 1
                if len(list_stack) == 1:
                    entry["top_item"] = f"{entry['id']}-item-{entry['items']}"
                elif entry["top_item"] is None:
                    entry["top_item"] = list_stack[-2]["top_item"]
                continue
            if token_type in {"bullet_list_close", "ordered_list_close"}:
                if list_stack:
                    list_stack.pop()
                continue

            if token_type == "blockquote_open":
                quote_stack.append(f"quote-{len(quote_stack)}-{index}")
                continue
            if token_type == "blockquote_close":
                if quote_stack:
                    quote_stack.pop()
                continue

            # Tables are special: every cell's inline token maps to the whole
            # row, so emitting one segment per cell duplicates the row 3x (and
            # makes the last cell overwrite the other translations on render).
            # Emit exactly one segment per row instead, and keep the table
            # header on every row for prompt context.
            if token_type == "table_open" and token.map is not None:
                table_state = {
                    "id": f"table-{index}",
                    "start": token.map[0],
                    "end": token.map[1],
                    "header": "",
                    "row_index": 0,
                    "in_thead": False,
                    "cells": 0,
                    "row_segment": None,
                }
                continue
            if token_type == "thead_open" and table_state is not None:
                table_state["in_thead"] = True
                continue
            if token_type == "thead_close" and table_state is not None:
                table_state["in_thead"] = False
                continue
            if token_type == "tr_open" and table_state is not None:
                table_state["row_index"] = int(table_state["row_index"]) + 1
                table_state["cells"] = 0
                table_state["row_segment"] = None
                continue
            if token_type in {"td_open", "th_open"} and table_state is not None:
                table_state["cells"] = int(table_state["cells"]) + 1
                continue
            if token_type == "tr_close" and table_state is not None:
                row_segment = table_state.get("row_segment")
                if row_segment is not None:
                    row_segment.metadata["table_columns"] = int(table_state["cells"])
                continue
            if token_type == "table_close":
                table_state = None
                continue

            if token_type != "inline" or token.map is None:
                continue

            parent_type = doc.ast[index - 1].type if index > 0 else ""
            if parent_type not in self.SUPPORTED_PARENT_TYPES:
                continue

            if parent_type == "heading_open" and pending_heading_level is not None:
                heading_stack = heading_stack[: pending_heading_level - 1]
                heading_stack.append(token.content.strip())
                section_counter += 1
                section_id = f"section-{section_counter}"
                section_level = pending_heading_level
                section_title = token.content.strip()
                pending_heading_level = None

            line_start, line_end = token.map
            block_text = "\n".join(doc.lines[line_start:line_end]).rstrip("\n")
            if not block_text.strip():
                continue

            metadata: dict[str, object] = {
                "body_line_start": line_start,
                "body_line_end": line_end,
                "inline_content": token.content,
                "section_id": section_id,
                "section_level": section_level,
                "section_title": section_title,
            }

            list_id = str(list_stack[0]["id"]) if list_stack else ""
            list_item_id = str(list_stack[-1]["top_item"]) if list_stack else ""
            quote_id = quote_stack[0] if quote_stack else ""
            if list_id:
                metadata.update(
                    block_kind="list_item",
                    container_id=list_id,
                    container_kind="list",
                    list_id=list_id,
                    list_item_id=list_item_id,
                )
            elif quote_id:
                metadata.update(block_kind="quote", container_id=quote_id, container_kind="quote")
            else:
                metadata["block_kind"] = "heading" if parent_type == "heading_open" else "paragraph"

            if parent_type == "heading_open":
                metadata["block_kind"] = "heading"
                metadata["heading_level"] = int(doc.ast[index - 1].tag[1])

            if table_state is not None and parent_type in _TABLE_PARENT_TYPES:
                row_key = (line_start, line_end)
                if row_key in seen_table_rows:
                    # Same row, a later cell: the row segment already exists.
                    continue
                seen_table_rows.add(row_key)
                is_header = bool(table_state["in_thead"]) or int(table_state["row_index"]) == 1
                if is_header:
                    # Keep the raw (unprotected) header row so every body row
                    # carries readable column context, even across bundles.
                    table_state["header"] = block_text
                header_text = str(table_state["header"]) or block_text
                metadata.update(
                    block_kind="table_row",
                    container_id=str(table_state["id"]),
                    container_kind="table",
                    table_id=str(table_state["id"]),
                    table_row_index=int(table_state["row_index"]),
                    table_header=header_text,
                    is_header=is_header,
                    table_start_line=int(table_state["start"]) + doc.body_line_offset,
                    table_end_line=int(table_state["end"]) + doc.body_line_offset,
                )

            segment = Segment(
                segment_id=f"body-{len(segments)}",
                node_type=parent_type.replace("_open", ""),
                source_text=block_text,
                context_path=list(heading_stack),
                line_start=line_start + doc.body_line_offset,
                line_end=line_end + doc.body_line_offset,
                metadata=metadata,
            )
            protected = protector.protect(segment)
            segments.append(protected)
            if table_state is not None and parent_type in _TABLE_PARENT_TYPES:
                table_state["row_segment"] = protected

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
                metadata={
                    "front_matter_key": key,
                    "block_kind": "front_matter",
                    "section_id": "front-matter",
                    "section_level": 0,
                    "section_title": "",
                },
            )
            segments.insert(0, protector.protect(fm_segment))

        self._attach_context_blocks(doc, segments)
        return segments

    def _attach_context_blocks(self, doc: ParsedDocument, segments: list[Segment]) -> None:
        blocks: list[dict[str, Any]] = []
        for token in doc.ast:
            if token.type not in {"fence", "code_block", "html_block"} or token.map is None:
                continue
            start, end = token.map
            raw = "\n".join(doc.lines[start:end]).strip()
            if not raw:
                continue
            blocks.append(
                {
                    "start": start + doc.body_line_offset,
                    "end": end + doc.body_line_offset,
                    "kind": token.type,
                    "text": self._context_snapshot(raw),
                }
            )
        if not blocks:
            return

        # One block is adjacency for *every* paragraph within CONTEXT_LINE_GAP,
        # so a naive per-segment attach repeats the same block for each of them:
        # measured on the bundled READMEs that was 2.1x duplicated tokens, and a
        # code block above a table was repeated for every row. Attach each block
        # to the nearest segment on each side instead — the paragraph that
        # introduces it above and the one that comments on it below — which
        # keeps both readings while dropping the copies in between.
        before_best: dict[int, tuple[int, Segment]] = {}
        after_best: dict[int, tuple[int, Segment]] = {}
        for segment in segments:
            if segment.node_type in {"front_matter", "heading"}:
                continue
            for block_index, block in enumerate(blocks):
                block_end = int(block["end"])
                block_start = int(block["start"])
                if block_end <= segment.line_start and segment.line_start - block_end <= self.CONTEXT_LINE_GAP:
                    distance = segment.line_start - block_end
                    current = before_best.get(block_index)
                    if current is None or distance < current[0]:
                        before_best[block_index] = (distance, segment)
                elif block_start >= segment.line_end and block_start - segment.line_end <= self.CONTEXT_LINE_GAP:
                    distance = block_start - segment.line_end
                    current = after_best.get(block_index)
                    if current is None or distance < current[0]:
                        after_best[block_index] = (distance, segment)

        for block_index in sorted(before_best):
            before_best[block_index][1].metadata.setdefault("context_before", []).append(str(blocks[block_index]["text"]))
        for block_index in sorted(after_best):
            after_best[block_index][1].metadata.setdefault("context_after", []).append(str(blocks[block_index]["text"]))
