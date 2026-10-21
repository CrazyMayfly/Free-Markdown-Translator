from __future__ import annotations

import re

from src.core.types import DocumentContext, ParsedDocument, Segment
from src.infra.config import TranslatorConfig

_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_0-9]+\}\}")

# The UI offers tone as an enum (SubmitView TONES); map each value to the
# wording actually injected into prompts. Unknown values pass through as-is so
# a hand-edited config keeps working.
TONE_PROMPTS = {
    "technical": "Technical documentation: precise terminology, developer-oriented",
    "formal": "Formal business writing: rigorous and professional",
    "casual": "Casual conversational: natural, everyday phrasing",
    "marketing": "Marketing copy: engaging and persuasive",
    "academic": "Academic: formal, objective, standards-compliant",
    "preserve": "Preserve the tone and register of the source text",
}


def _tone_prompt(tone: str) -> str:
    return TONE_PROMPTS.get(tone.strip().lower(), tone)


def _plain_heading_text(text: str) -> str:
    return _PLACEHOLDER_RE.sub("", text).replace("`", "").strip()


class DocumentContextBuilder:
    def build(self, doc: ParsedDocument, segments: list[Segment], config: TranslatorConfig) -> DocumentContext:
        title = str((doc.metadata.get("front_matter") or {}).get("title", ""))
        if not title:
            title = next((" / ".join(segment.context_path) for segment in segments if segment.context_path), "")
        abstract = next((segment.source_text for segment in segments if segment.node_type == "paragraph"), "")
        heading_outline = [
            plain
            for segment in segments
            if segment.node_type == "heading"
            for plain in [_plain_heading_text(segment.source_text)]
            if plain
        ]
        section_summaries: dict[str, str] = {}
        for segment in segments:
            if not segment.context_path:
                continue
            path = " / ".join(segment.context_path)
            if path not in section_summaries and segment.node_type == "paragraph":
                section_summaries[path] = segment.source_text[:200]
        style_guide = [f"Tone: {_tone_prompt(config.style.tone)}", f"Audience: {config.style.audience}", *config.style.instructions]
        if config.style.preserve_terms:
            style_guide.append("Preserve these terms: " + ", ".join(config.style.preserve_terms))
        return DocumentContext(
            title=title,
            abstract=abstract,
            section_summaries=section_summaries,
            style_guide=style_guide,
            audience=config.style.audience,
            heading_outline=heading_outline,
        )
