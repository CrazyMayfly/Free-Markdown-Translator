from __future__ import annotations

import re
from dataclasses import dataclass

from src.core.types import Segment, TranslationResult

_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_0-9]+\}\}")
_NUMBER_RE = re.compile(r"\d+")


@dataclass
class SentinelFinding:
    segment_id: str
    check: str
    detail: str


def _numbers(text: str) -> list[str]:
    # Normalize thousand separators only; decimal points and versions stay.
    return _NUMBER_RE.findall(text.replace(",", "").replace("，", ""))


def run_sentinels(
    segments: list[Segment],
    translations: list[TranslationResult],
    min_ratio: float = 0.35,
    max_ratio: float = 3.0,
) -> list[SentinelFinding]:
    """Cheap deterministic checks that catch lost or hallucinated content.

    These run on placeholder-bearing texts (before restore), so placeholder
    parity is checked first; number parity and length ratio are only
    meaningful on texts whose placeholders survived intact.
    """
    segment_by_id = {segment.segment_id: segment for segment in segments}
    findings: list[SentinelFinding] = []
    for item in translations:
        segment = segment_by_id.get(item.segment_id)
        if segment is None:
            continue
        source, target = segment.source_text, item.translated_text

        source_placeholders = _PLACEHOLDER_RE.findall(source)
        target_placeholders = _PLACEHOLDER_RE.findall(target)
        if len(source_placeholders) != len(target_placeholders):
            findings.append(
                SentinelFinding(
                    item.segment_id,
                    "placeholder_parity",
                    f"source has {len(source_placeholders)} protected spans, translation has {len(target_placeholders)}",
                )
            )
            continue

        source_plain = _PLACEHOLDER_RE.sub("", source).strip()
        target_plain = _PLACEHOLDER_RE.sub("", target).strip()
        if sorted(_numbers(source_plain)) != sorted(_numbers(target_plain)):
            source_numbers = sorted(_numbers(source_plain))
            target_numbers = sorted(_numbers(target_plain))
            findings.append(
                SentinelFinding(
                    item.segment_id,
                    "number_parity",
                    f"numbers differ: {source_numbers} vs {target_numbers}",
                )
            )

        source_len = len(source_plain)
        target_len = len(target_plain)
        if source_len >= 20:
            ratio = target_len / source_len
            if ratio < min_ratio or ratio > max_ratio:
                findings.append(
                    SentinelFinding(
                        item.segment_id,
                        "length_ratio",
                        f"length ratio {ratio:.2f} outside [{min_ratio}, {max_ratio}] ({source_len} -> {target_len} chars)",
                    )
                )
    return findings
