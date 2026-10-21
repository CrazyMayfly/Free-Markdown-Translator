from __future__ import annotations

import bisect
import logging
import re
from dataclasses import dataclass, replace

from src.core.modes import profile_for
from src.core.tokens import estimate_tokens, prefix_costs
from src.core.types import DocumentContext, Segment, SegmentBundle
from src.infra.config import TranslatorConfig

_HEADING = "heading"
_TABLE_NODE_TYPES = {"td", "th"}
_SENTENCE_ENDS = "。！？；.!?;"
_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_0-9]+\}\}")


@dataclass
class _Block:
    """A structural unit that must not be cut unless it exceeds the budget."""

    kind: str
    segments: list[Segment]
    tokens: int


@dataclass
class _Section:
    """A heading plus its body, or the leading front-matter/heading-less part."""

    blocks: list[_Block]
    tokens: int


class Orchestrator:
    """Pack Markdown structure into translation bundles.

    Boundaries follow the document: sections, lists, tables and blockquotes are
    kept whole while they fit, and only oversized blocks are split — by table
    row, list item, or source line. One token budget (`max_bundle_tokens`)
    therefore replaces the old segment-count and heading-threshold heuristics.

    The budget is counted in estimated tokens, not characters: characters mean
    different amounts of work per language, so a character ceiling silently
    tripled the truncation risk on Chinese documents.
    """

    def build_bundles(self, segments: list[Segment], context: DocumentContext, config: TranslatorConfig) -> list[SegmentBundle]:
        sections = self._build_sections(segments)
        profile = profile_for(config.pipeline.mode)
        max_tokens = max(1, int(config.segmentation.max_bundle_tokens * profile.bundle_scale))
        min_tokens = max(0, int(config.segmentation.min_bundle_tokens * profile.min_bundle_scale))
        packed = self._pack_sections(sections, max_tokens, min_tokens)
        self._merge_small_trailing(packed, min_tokens, max_tokens)
        return self._build_bundles(packed, context)

    # ------------------------------------------------------------------
    # Structure detection
    # ------------------------------------------------------------------

    def _build_sections(self, segments: list[Segment]) -> list[_Section]:
        blocks = self._build_blocks(segments)
        sections: list[_Section] = []
        current: list[_Block] = []
        current_tokens = 0

        def flush() -> None:
            nonlocal current, current_tokens
            if current:
                sections.append(_Section(blocks=current, tokens=current_tokens))
            current = []
            current_tokens = 0

        for block in blocks:
            first = block.segments[0] if block.segments else None
            starts_section = bool(
                block.kind == "heading"
                or (first is not None and first.node_type == _HEADING and first.metadata.get("block_kind") == "heading")
            )
            if starts_section and current:
                flush()
            current.append(block)
            current_tokens += block.tokens
        flush()
        return sections

    def _build_blocks(self, segments: list[Segment]) -> list[_Block]:
        blocks: list[_Block] = []
        index = 0
        while index < len(segments):
            segment = segments[index]
            metadata = segment.metadata
            block_kind = str(metadata.get("block_kind") or "")

            if block_kind == "table_row" or (
                not block_kind and segment.node_type in _TABLE_NODE_TYPES
            ):
                group = [segment]
                index += 1
                while index < len(segments):
                    candidate = segments[index]
                    candidate_kind = str(candidate.metadata.get("block_kind") or "")
                    if block_kind:
                        if candidate_kind != "table_row":
                            break
                        if candidate.metadata.get("table_id") != metadata.get("table_id"):
                            break
                    else:
                        if candidate.node_type not in _TABLE_NODE_TYPES:
                            break
                        if candidate.line_start > group[-1].line_end + 2:
                            break
                    group.append(candidate)
                    index += 1
                blocks.append(_Block("table", group, _tokens_of(group)))
                continue

            if block_kind == "list_item":
                container = metadata.get("container_id")
                group = [segment]
                index += 1
                while index < len(segments):
                    candidate = segments[index]
                    if candidate.metadata.get("block_kind") != "list_item":
                        break
                    if candidate.metadata.get("container_id") != container:
                        break
                    group.append(candidate)
                    index += 1
                blocks.append(_Block("list", group, _tokens_of(group)))
                continue

            if block_kind == "quote":
                container = metadata.get("container_id")
                group = [segment]
                index += 1
                while index < len(segments):
                    candidate = segments[index]
                    if candidate.metadata.get("block_kind") != "quote":
                        break
                    if candidate.metadata.get("container_id") != container:
                        break
                    group.append(candidate)
                    index += 1
                blocks.append(_Block("quote", group, _tokens_of(group)))
                continue

            if block_kind == "front_matter":
                group = [segment]
                index += 1
                while index < len(segments) and segments[index].metadata.get("block_kind") == "front_matter":
                    group.append(segments[index])
                    index += 1
                blocks.append(_Block("front_matter", group, _tokens_of(group)))
                continue

            kind = "heading" if segment.node_type == _HEADING else block_kind or "paragraph"
            blocks.append(_Block(kind, [segment], _tokens_of([segment])))
            index += 1
        return blocks

    # ------------------------------------------------------------------
    # Packing
    # ------------------------------------------------------------------

    def _pack_sections(
        self, sections: list[_Section], max_tokens: int, min_tokens: int
    ) -> list[list[Segment]]:
        # Keep section boundaries as bundle boundaries, but merge consecutive
        # small sections until the group reaches min_bundle_tokens. This is what
        # replaces section_align_min_chars: a heading is always a structural
        # boundary, while the minimum only stops one-line sections from each
        # becoming their own API call.
        groups: list[list[_Section]] = []
        current: list[_Section] = []
        current_tokens = 0
        for section in sections:
            if not section.blocks:
                continue
            if current and current_tokens >= min_tokens:
                groups.append(current)
                current = []
                current_tokens = 0
            current.append(section)
            current_tokens += section.tokens
        if current:
            groups.append(current)

        packed: list[list[Segment]] = []
        for group in groups:
            group_tokens = sum(section.tokens for section in group)
            if group_tokens <= max_tokens:
                packed.append(
                    [segment for section in group for block in section.blocks for segment in block.segments]
                )
                continue
            packed.extend(self._pack_blocks([block for section in group for block in section.blocks], max_tokens))
        return packed

    def _pack_blocks(self, blocks: list[_Block], max_tokens: int) -> list[list[Segment]]:
        packed: list[list[Segment]] = []
        current: list[Segment] = []
        current_tokens = 0

        def flush() -> None:
            nonlocal current, current_tokens
            if current:
                packed.append(current)
            current = []
            current_tokens = 0

        for block in blocks:
            if block.tokens <= max_tokens:
                if current and current_tokens + block.tokens > max_tokens:
                    flush()
                current.extend(block.segments)
                current_tokens += block.tokens
                continue
            for chunk in self._split_block(block, max_tokens):
                if chunk.tokens > max_tokens:
                    # Unsplittable (a single overlong line): keep it whole
                    # rather than cutting a protected span in half.
                    logging.warning(
                        "Bundle block still exceeds max_bundle_tokens after splitting: %s tokens", chunk.tokens
                    )
                    flush()
                    current.extend(chunk.segments)
                    current_tokens = chunk.tokens
                    flush()
                    continue
                if current and current_tokens + chunk.tokens > max_tokens:
                    flush()
                current.extend(chunk.segments)
                current_tokens += chunk.tokens
        flush()
        return packed

    @staticmethod
    def _merge_small_trailing(packed: list[list[Segment]], min_tokens: int, max_tokens: int) -> None:
        if min_tokens <= 0:
            return
        index = len(packed) - 1
        while index > 0:
            tokens = _tokens_of(packed[index])
            previous_tokens = _tokens_of(packed[index - 1])
            if tokens < min_tokens and previous_tokens + tokens <= max_tokens:
                packed[index - 1].extend(packed.pop(index))
            index -= 1

    def _build_bundles(self, packed: list[list[Segment]], context: DocumentContext) -> list[SegmentBundle]:
        bundles: list[SegmentBundle] = []
        previous_summary = context.abstract[:200]
        for index, segments in enumerate(packed):
            summary_after = self._build_bundle_summary(segments)
            bundles.append(
                SegmentBundle(
                    bundle_id=f"bundle-{index}",
                    segments=segments,
                    summary_before=previous_summary,
                    summary_after=summary_after,
                    style_instructions=context.style_guide,
                )
            )
            previous_summary = summary_after
        return bundles

    # ------------------------------------------------------------------
    # Splitting oversized structural blocks
    # ------------------------------------------------------------------

    def _split_block(self, block: _Block, max_tokens: int) -> list[_Block]:
        if block.tokens <= max_tokens:
            return [block]
        if block.kind == "table":
            return self._split_table(block, max_tokens)
        if block.kind == "list":
            return self._split_list(block, max_tokens)
        return self._split_plain(block, max_tokens)

    def _split_table(self, block: _Block, max_tokens: int) -> list[_Block]:
        header = [segment for segment in block.segments if segment.metadata.get("is_header")]
        body = [segment for segment in block.segments if not segment.metadata.get("is_header")]
        chunks: list[_Block] = []
        current = list(header)
        current_tokens = _tokens_of(current)

        for row in body:
            row_tokens = estimate_tokens(row.source_text)
            if current and current_tokens + row_tokens > max_tokens:
                chunks.append(_Block("table", current, current_tokens))
                current = []
                current_tokens = 0
            if row_tokens > max_tokens and not current:
                chunks.append(_Block("table", [row], row_tokens))
                continue
            current.append(row)
            current_tokens += row_tokens
        if current:
            chunks.append(_Block("table", current, current_tokens))
        return chunks

    def _split_list(self, block: _Block, max_tokens: int) -> list[_Block]:
        grouped: list[list[Segment]] = []
        for segment in block.segments:
            item_id = segment.metadata.get("list_item_id")
            if grouped and item_id is not None and grouped[-1][0].metadata.get("list_item_id") == item_id:
                grouped[-1].append(segment)
            else:
                grouped.append([segment])

        chunks: list[_Block] = []
        current: list[Segment] = []
        current_tokens = 0
        for item_segments in grouped:
            item_tokens = _tokens_of(item_segments)
            if item_tokens <= max_tokens:
                if current and current_tokens + item_tokens > max_tokens:
                    chunks.append(_Block("list", current, current_tokens))
                    current = []
                    current_tokens = 0
                current.extend(item_segments)
                current_tokens += item_tokens
                continue
            if current:
                chunks.append(_Block("list", current, current_tokens))
                current = []
                current_tokens = 0
            chunks.extend(self._split_plain(_Block("list", item_segments, item_tokens), max_tokens))
        if current:
            chunks.append(_Block("list", current, current_tokens))
        return chunks

    def _split_plain(self, block: _Block, max_tokens: int) -> list[_Block]:
        chunks: list[_Block] = []
        current: list[Segment] = []
        current_tokens = 0

        def flush() -> None:
            nonlocal current, current_tokens
            if current:
                chunks.append(_Block(block.kind, current, current_tokens))
            current = []
            current_tokens = 0

        for segment in block.segments:
            pieces = self._split_segment(segment, max_tokens)
            for piece in pieces:
                piece_tokens = estimate_tokens(piece.source_text)
                if current and current_tokens + piece_tokens > max_tokens:
                    flush()
                current.append(piece)
                current_tokens += piece_tokens
        flush()
        return chunks

    def _split_segment(self, segment: Segment, max_tokens: int) -> list[Segment]:
        if estimate_tokens(segment.source_text) <= max_tokens:
            return [segment]
        if segment.node_type == _HEADING:
            # Splitting a heading inserts a line break and changes its level;
            # keep an overlong heading whole and let validation/model handle it.
            return [segment]
        pieces = split_text(segment.source_text, max_tokens)
        if len(pieces) <= 1:
            return [segment]
        parts: list[Segment] = []
        count = len(pieces)
        for index, (text, separator) in enumerate(pieces):
            metadata = dict(segment.metadata)
            metadata.update(
                split_parent=segment.segment_id,
                split_index=index,
                split_count=count,
                split_sep=separator,
            )
            parts.append(
                replace(
                    segment,
                    segment_id=f"{segment.segment_id}~{index}",
                    source_text=text,
                    metadata=metadata,
                    protected_spans=list(segment.protected_spans),
                )
            )
        return parts

    @staticmethod
    def _build_bundle_summary(segments: list[Segment]) -> str:
        # Cover the whole bundle (head + tail excerpt) instead of only its
        # first characters, so downstream bundles see how it ends.
        text = " ".join(segment.source_text.replace("\n", " ") for segment in segments).strip()
        if not text:
            return ""
        if len(text) <= 320:
            return text
        return text[:180] + " ... " + text[-120:]


def _tokens_of(segments: list[Segment]) -> int:
    return sum(estimate_tokens(segment.source_text) for segment in segments)


def split_text(text: str, limit_tokens: int) -> list[tuple[str, str]]:
    """Split ``text`` into ``(piece, separator_after)`` pairs under a token budget.

    The concatenation ``piece + separator_after + next_piece...`` reproduces
    the input byte-for-byte, so the renderer can join translated pieces without
    guessing how the source was wrapped. Cuts prefer newlines, then sentence
    boundaries, then whitespace, and never fall inside a protected placeholder.

    The budget is a token estimate, so the character window that fits it is
    derived from a cumulative cost array instead of a fixed slice width.
    """
    if limit_tokens <= 0 or estimate_tokens(text) <= limit_tokens:
        return [(text, "")]

    costs = prefix_costs(text)
    pieces: list[tuple[str, str]] = []
    start = 0
    length = len(text)
    while costs[length] - costs[start] > limit_tokens:
        window_end = _window_within_budget(costs, start, limit_tokens)
        newline = text.rfind("\n", start, window_end)
        if newline > start:
            pieces.append((text[start:newline], "\n"))
            start = newline + 1
            continue
        if newline == start:
            # The previous cut already consumed the trailing spaces and left
            # the cursor on a newline. Fold it into that separator instead of
            # emitting an empty piece the translator would still be asked about.
            if pieces:
                last_text, last_separator = pieces[-1]
                pieces[-1] = (last_text, last_separator + "\n")
            else:
                pieces.append(("", "\n"))
            start += 1
            continue

        punctuation = max((text.rfind(char, start, window_end) for char in _SENTENCE_ENDS), default=-1)
        if punctuation > start:
            cut = punctuation + 1
            separator_end = cut
            while separator_end < length and text[separator_end] in " \t":
                separator_end += 1
            pieces.append((text[start:cut], text[cut:separator_end]))
            start = separator_end
            continue

        space = max(text.rfind(" ", start, window_end), text.rfind("\t", start, window_end))
        if space > start:
            separator_end = space
            while separator_end < length and text[separator_end] in " \t":
                separator_end += 1
            pieces.append((text[start:space], text[space:separator_end]))
            start = separator_end
            continue

        cut = _safe_cut(text, start, window_end)
        pieces.append((text[start:cut], ""))
        start = cut

    pieces.append((text[start:], ""))
    return pieces


def _window_within_budget(costs: list[float], start: int, limit_tokens: int) -> int:
    """Largest end index whose ``[start:end)`` slice still fits the budget.

    Always advances at least one character so the caller's loop terminates even
    when a single character costs more than the whole budget.
    """
    target = costs[start] + limit_tokens
    end = bisect.bisect_right(costs, target) - 1
    return max(start + 1, min(end, len(costs) - 1))


def _safe_cut(text: str, start: int, cut: int) -> int:
    """Move a hard cut out of the middle of a protected placeholder."""
    for match in _PLACEHOLDER_RE.finditer(text, start):
        if match.start() >= cut:
            break
        if match.start() <= start:
            return match.end()
        if match.start() < cut < match.end():
            # Prefer keeping the whole placeholder in the current piece; if it
            # is longer than the budget, put it at the start of the next piece.
            return match.end() if match.end() - start <= cut - start else match.start()
    return cut
