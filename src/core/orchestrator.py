from __future__ import annotations

from src.core.types import DocumentContext, Segment, SegmentBundle
from src.infra.config import TranslatorConfig

_TABLE_CELL_TYPES = {"td", "th"}


class Orchestrator:
    def build_bundles(self, segments: list[Segment], context: DocumentContext, config: TranslatorConfig) -> list[SegmentBundle]:
        bundles: list[SegmentBundle] = []
        current: list[Segment] = []
        current_chars = 0

        def flush() -> None:
            nonlocal current_chars
            if not current:
                return
            bundles.append(
                SegmentBundle(
                    bundle_id=f"bundle-{len(bundles)}",
                    segments=list(current),
                    summary_before=bundles[-1].summary_after if bundles else context.abstract[:200],
                    summary_after=self._build_bundle_summary(current),
                    style_instructions=context.style_guide,
                )
            )
            current.clear()
            current_chars = 0

        for segment in segments:
            if current and self._should_flush(current, current_chars, segment, config):
                flush()
            current.append(segment)
            current_chars += len(segment.source_text)
        flush()
        return bundles

    @staticmethod
    def _should_flush(current: list[Segment], current_chars: int, segment: Segment, config: TranslatorConfig) -> bool:
        limits_exceeded = (
            len(current) >= config.segmentation.max_bundle_segments
            or current_chars + len(segment.source_text) > config.segmentation.max_bundle_chars
        )
        if not limits_exceeded:
            # Section alignment: start a new bundle at a heading so bundle
            # boundaries follow the document's semantic structure.
            return (
                segment.node_type == "heading"
                and current_chars >= config.segmentation.section_align_min_chars
                and current[-1].node_type != "heading"
            )
        # Size limit reached, but keep table cells of the same table together
        # up to a hard cap so cell context (header row <-> data rows) survives.
        if (
            Orchestrator._same_table(current[-1], segment)
            and current_chars < config.segmentation.max_bundle_chars * 2
            and len(current) < config.segmentation.max_bundle_segments * 2
        ):
            return False
        return True

    @staticmethod
    def _same_table(previous: Segment, segment: Segment) -> bool:
        if previous.node_type not in _TABLE_CELL_TYPES or segment.node_type not in _TABLE_CELL_TYPES:
            return False
        return segment.line_start <= previous.line_end + 2

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
