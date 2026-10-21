from __future__ import annotations

from copy import deepcopy

from src.core.types import ParsedDocument, Segment, TranslationResult
from src.parser.frontmatter import dump_front_matter


class AstMapper:
    def apply(self, doc: ParsedDocument, translations: list[TranslationResult]) -> ParsedDocument:
        updated = deepcopy(doc)
        body_lines = list(updated.lines)
        translation_map = {item.segment_id: item.translated_text for item in translations}

        body_segments = [
            segment
            for segment in getattr(updated, "segments", [])
            if segment.segment_id in translation_map and segment.node_type != "front_matter"
        ]
        groups = self._group_segments(body_segments)
        ordered_groups = sorted(groups.values(), key=lambda group: group[0].metadata["body_line_start"])

        # Compute final line ranges before slicing: replacements above change
        # the line count, so later segments move by a running delta.
        line_ranges: dict[int, tuple[int, int]] = {}
        delta = 0
        for group in ordered_groups:
            start = int(group[0].metadata["body_line_start"])
            end = int(group[0].metadata["body_line_end"])
            text = self._group_text(group, translation_map)
            new_lines = self._lines_for(text)
            final_start = start + delta
            line_ranges[id(group)] = (final_start, final_start + len(new_lines))
            delta += len(new_lines) - (end - start)

        for group in sorted(ordered_groups, key=lambda item: item[0].metadata["body_line_start"], reverse=True):
            start = int(group[0].metadata["body_line_start"])
            end = int(group[0].metadata["body_line_end"])
            body_lines[start:end] = self._lines_for(self._group_text(group, translation_map))

        updated.lines = body_lines
        updated.body_text = "\n".join(body_lines)
        if doc.body_text.endswith("\n") and not updated.body_text.endswith("\n"):
            updated.body_text += "\n"

        front_matter = dict(updated.metadata.get("front_matter") or {})
        changed_frontmatter = False
        for segment in getattr(updated, "segments", []):
            if segment.node_type != "front_matter" or segment.segment_id not in translation_map:
                continue
            front_matter[segment.metadata["front_matter_key"]] = translation_map[segment.segment_id]
            changed_frontmatter = True
        if changed_frontmatter:
            updated.metadata["front_matter"] = front_matter

        prefix = ""
        if front_matter:
            prefix = f"---\n{dump_front_matter(front_matter)}\n---\n"
        updated.metadata["segment_spans"] = self._calculate_spans(
            body_lines, ordered_groups, line_ranges, len(prefix)
        )
        return updated

    @staticmethod
    def _group_segments(segments: list[Segment]) -> dict[tuple[int, int, str], list[Segment]]:
        groups: dict[tuple[int, int, str], list[Segment]] = {}
        for segment in segments:
            start = int(segment.metadata["body_line_start"])
            end = int(segment.metadata["body_line_end"])
            parent = str(segment.metadata.get("split_parent") or segment.segment_id)
            groups.setdefault((start, end, parent), []).append(segment)
        for group in groups.values():
            group.sort(key=lambda item: int(item.metadata.get("split_index", 0)))
        return {key: value for key, value in groups.items()}

    @staticmethod
    def _group_text(group: list[Segment], translation_map: dict[str, str]) -> str:
        return "".join(
            translation_map[segment.segment_id] + str(segment.metadata.get("split_sep", ""))
            for segment in group
        )

    @staticmethod
    def _lines_for(text: str) -> list[str]:
        lines = text.splitlines()
        if text.endswith("\n"):
            lines.append("")
        return lines

    @staticmethod
    def _calculate_spans(
        body_lines: list[str],
        groups: list[list[Segment]],
        line_ranges: dict[int, tuple[int, int]],
        prefix_length: int,
    ) -> dict[str, tuple[int, int]]:
        offsets = [0]
        for line in body_lines:
            offsets.append(offsets[-1] + len(line) + 1)

        spans: dict[str, tuple[int, int]] = {}
        for group in groups:
            if len(group) > 1 or group[0].metadata.get("split_parent"):
                # Split parts share one source line range; a single span would
                # not identify which part an edit belongs to. Leave them to the
                # text-search fallback in rerender_markdown.
                continue
            final_start, final_end = line_ranges[id(group)]
            start = prefix_length + offsets[final_start]
            text = "\n".join(body_lines[final_start:final_end])
            spans[group[0].segment_id] = (start, start + len(text))
        return spans

    def render(self, doc: ParsedDocument) -> str:
        front_matter = doc.metadata.get("front_matter") or {}
        prefix = ""
        if front_matter:
            prefix = f"---\n{dump_front_matter(front_matter)}\n---\n"
        return f"{prefix}{doc.body_text}"
