from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from src.core.types import TranslationResult


@dataclass
class GlossaryConflict:
    term: str
    canonical: str
    renderings: list[str]
    affected_segment_ids: set[str]


def detect_glossary_conflicts(translations: list[TranslationResult], authoritative: dict[str, str]) -> list[GlossaryConflict]:
    """Find terms whose reported renderings disagree across the document.

    For authoritative terms (extracted glossary / preserve_terms) any usage
    that differs from the canonical rendering is a conflict. For terms the
    model reported on its own, more than one distinct rendering is a conflict
    and the canonical rendering is chosen by frequency, ties broken by first
    appearance in document order.
    """
    usages: dict[str, list[tuple[str, str]]] = {}
    for item in translations:
        for raw_term, raw_rendering in (item.applied_terms or {}).items():
            term = str(raw_term).strip()
            rendering = str(raw_rendering or "").strip()
            if not term or not rendering:
                continue
            usages.setdefault(term, []).append((rendering, item.segment_id))

    conflicts: list[GlossaryConflict] = []
    for term, uses in usages.items():
        ordered_renderings: list[str] = []
        for rendering, _segment_id in uses:
            if rendering not in ordered_renderings:
                ordered_renderings.append(rendering)

        canonical = str(authoritative.get(term, "")).strip()
        if canonical:
            affected = {segment_id for rendering, segment_id in uses if rendering != canonical}
            if affected:
                conflicts.append(
                    GlossaryConflict(
                        term=term,
                        canonical=canonical,
                        renderings=ordered_renderings,
                        affected_segment_ids=affected,
                    )
                )
            continue

        if len(ordered_renderings) < 2:
            continue
        counts = Counter(rendering for rendering, _segment_id in uses)
        canonical = max(ordered_renderings, key=lambda rendering: (counts[rendering], -ordered_renderings.index(rendering)))
        affected = {segment_id for rendering, segment_id in uses if rendering != canonical}
        conflicts.append(
            GlossaryConflict(
                term=term,
                canonical=canonical,
                renderings=ordered_renderings,
                affected_segment_ids=affected,
            )
        )
    return conflicts


def canonical_glossary(conflicts: list[GlossaryConflict]) -> dict[str, str]:
    return {conflict.term: conflict.canonical for conflict in conflicts}
