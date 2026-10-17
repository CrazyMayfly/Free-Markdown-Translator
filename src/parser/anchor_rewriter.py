from __future__ import annotations

import re

from src.core.types import Segment, TranslationResult

# Inline links only: HTML tags are protected as opaque placeholders during
# translation, so anchors inside raw HTML cannot be rewritten here.
_ANCHOR_LINK_RE = re.compile(r"\]\(#([^)\s]+)\)")
_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_0-9]+\}\}")
_HEADING_MARKER_RE = re.compile(r"^\s*#+\s*|\s*#+\s*$")
_STRIP_SLUG_CHARS_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_SPACES_RE = re.compile(r"[\s_]+", re.UNICODE)


def _plain_heading_text(text: str) -> str:
    text = _PLACEHOLDER_RE.sub("", text)
    text = _HEADING_MARKER_RE.sub("", text)
    return text.replace("`", "").strip()


def slugify(text: str) -> str:
    """GitHub-style slug: lowercase, punctuation dropped, spaces to hyphens.

    Non-ASCII letters and digits (CJK, kana, hangul, ...) are kept as-is,
    matching how GitHub renders anchors for translated headings.
    """
    lowered = text.strip().lower()
    lowered = _STRIP_SLUG_CHARS_RE.sub("", lowered)
    lowered = _SPACES_RE.sub("-", lowered)
    return lowered.strip("-")


def _occurrence_slug(base: str, seen: dict[str, int]) -> str:
    count = seen.get(base, 0)
    seen[base] = count + 1
    if count == 0:
        return base
    return f"{base}-{count}"


def heading_pairs(segments: list[Segment], translations: list[TranslationResult]) -> list[tuple[str, str]]:
    translated_by_id = {item.segment_id: item.translated_text for item in translations}
    pairs: list[tuple[str, str]] = []
    for segment in segments:
        if segment.node_type != "heading":
            continue
        translated = translated_by_id.get(segment.segment_id)
        if translated is None:
            continue
        pairs.append((_plain_heading_text(segment.source_text), _plain_heading_text(translated)))
    return pairs


def rewrite_anchors(output_text: str, pairs: list[tuple[str, str]]) -> str:
    """Point intra-document `](#anchor)` links at the translated headings.

    A link written against a source heading anchor stays valid in the output
    only if its target slug is remapped to the translated heading's slug.
    Duplicate headings get GitHub's -1/-2 occurrence suffixes on both sides.
    """
    if not pairs:
        return output_text
    source_seen: dict[str, int] = {}
    target_seen: dict[str, int] = {}
    mapping: dict[str, str] = {}
    for source_text, target_text in pairs:
        source_slug = _occurrence_slug(slugify(source_text), source_seen)
        target_slug = _occurrence_slug(slugify(target_text), target_seen)
        if source_slug and target_slug:
            mapping[source_slug] = target_slug
    if not mapping:
        return output_text

    def _replace(match: re.Match[str]) -> str:
        fixed = mapping.get(match.group(1))
        if fixed is None:
            return match.group(0)
        return f"](#{fixed})"

    return _ANCHOR_LINK_RE.sub(_replace, output_text)
