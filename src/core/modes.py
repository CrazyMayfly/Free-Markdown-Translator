from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModeProfile:
    """Per-mode context, review and payload policy.

    `fast` optimises prompt tokens and latency, `quality` (the old `strict`)
    spends tokens on a document brief and multiple review passes, and
    `balanced` sits between the two.
    """

    name: str
    bundle_scale: float
    min_bundle_scale: float
    brief_summary: bool
    section_summary: bool
    glossary: bool
    previous: bool
    previous_chars: int
    anchor: bool
    blocks: bool
    block_chars: int
    style_guide: bool
    outline: bool
    abstract: bool
    review: str  # none | targeted | full
    final_edit: bool
    schema: str  # minimal | compact | full
    context_pull: bool


_PROFILES: dict[str, ModeProfile] = {
    "fast": ModeProfile(
        name="fast",
        bundle_scale=1.3,
        min_bundle_scale=1.0,
        brief_summary=False,
        section_summary=False,
        glossary=True,
        previous=False,
        previous_chars=0,
        anchor=False,
        blocks=False,
        block_chars=0,
        style_guide=False,
        outline=False,
        abstract=False,
        review="none",
        final_edit=False,
        schema="minimal",
        context_pull=False,
    ),
    "balanced": ModeProfile(
        name="balanced",
        bundle_scale=1.0,
        min_bundle_scale=1.0,
        brief_summary=True,
        section_summary=True,
        glossary=True,
        previous=True,
        previous_chars=200,
        anchor=True,
        blocks=True,
        block_chars=160,
        style_guide=False,
        outline=False,
        abstract=False,
        review="targeted",
        final_edit=False,
        schema="compact",
        context_pull=True,
    ),
    "quality": ModeProfile(
        name="quality",
        bundle_scale=0.8,
        min_bundle_scale=0.75,
        brief_summary=True,
        section_summary=True,
        glossary=True,
        previous=True,
        previous_chars=400,
        anchor=True,
        blocks=True,
        block_chars=300,
        style_guide=True,
        outline=True,
        abstract=True,
        review="full",
        final_edit=True,
        schema="full",
        context_pull=True,
    ),
}


def normalize_mode(mode: str | None) -> str:
    """Canonical mode name; ``strict`` is a deprecated alias for quality."""
    normalized = (mode or "balanced").strip().lower()
    if normalized == "strict":
        return "quality"
    if normalized not in _PROFILES:
        return "balanced"
    return normalized


def profile_for(mode: str | None) -> ModeProfile:
    return _PROFILES[normalize_mode(mode)]
