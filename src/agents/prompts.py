from __future__ import annotations

import json

from src.core.types import DocumentContext, SegmentBundle, TranslationResult

_OUTPUT_CONTRACT = (
    'Return JSON only: {"translations":[{"segment_id":"...","translated_text":"...",'
    '"notes":["..."],"applied_terms":{"term":"rendering"},"confidence":0.0}]} '
    "with one object per input segment, every field required."
)


def _compact_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _document_context_payload(context: DocumentContext) -> dict:
    """Document-level hints shared by every bundle of the same document.

    Kept stable (same key order, same values) across bundles so providers can
    reuse the prompt prefix cache: this payload must be serialized before any
    bundle-specific fields.
    """
    payload: dict[str, object] = {}
    if context.title:
        payload["title"] = context.title[:120]
    if context.abstract:
        payload["abstract"] = context.abstract[:300]
    if context.audience:
        payload["audience"] = context.audience[:80]
    if context.style_guide:
        payload["style_guide"] = list(context.style_guide)
    return payload


def build_translator_prompts(bundle: SegmentBundle, context: DocumentContext, target_lang: str) -> tuple[str, str]:
    system_prompt = (
        f"You are an expert Markdown translation specialist. Detect the source language automatically and translate markdown text to {target_lang}. "
        "Input JSON fields: task=job type, ctx=shared document hints, prev_summary=running summary of the previously translated bundle (for continuity), "
        "segments=list of units to translate, segment_id=stable output key, context=local section path, text=source text. "
        f"{_OUTPUT_CONTRACT} "
        "notes=translation remarks, applied_terms=preserved terms and how they were rendered, confidence=your confidence 0.0-1.0. "
        "Translate only text, **preserve placeholders**, URLs, code, and markdown control syntax exactly, and follow ctx.style_guide including term preservation."
    )
    payload = {
        "task": "translate",
        "ctx": _document_context_payload(context),
        "prev_summary": bundle.summary_before[:400] if bundle.summary_before else "",
        "segments": [
            {
                "segment_id": segment.segment_id,
                "context": " / ".join(segment.context_path[-2:]) if segment.context_path else "",
                "text": segment.source_text,
            }
            for segment in bundle.segments
        ],
    }
    return system_prompt, _compact_json(payload)


def build_reviewer_prompts(bundle: SegmentBundle, context: DocumentContext, translations: list[TranslationResult]) -> tuple[str, str]:
    system_prompt = (
        "Review translations only if needed. "
        "Input JSON fields: task=job type, ctx=shared document hints, prev_summary=running summary of the previously translated bundle, "
        "translations=list of items with segment_id, source and current text. "
        f"{_OUTPUT_CONTRACT} "
        "Keep placeholders and markdown syntax unchanged; only fix meaning, terminology, fluency or style problems."
    )
    payload = {
        "task": "review",
        "ctx": _document_context_payload(context),
        "prev_summary": bundle.summary_before[:400] if bundle.summary_before else "",
        "translations": [
            {
                "segment_id": segment.segment_id,
                "source": segment.source_text,
                "text": translation.translated_text,
            }
            for segment, translation in zip(bundle.segments, translations)
        ],
    }
    return system_prompt, _compact_json(payload)


def build_guard_prompts(bundle: SegmentBundle, translations: list[TranslationResult]) -> tuple[str, str]:
    system_prompt = (
        "Repair markdown-format issues only. "
        f"{_OUTPUT_CONTRACT} "
        "Make minimal edits and keep placeholders unchanged."
    )
    payload = {
        "task": "format_guard",
        "translations": [
            {
                "segment_id": segment.segment_id,
                "source": segment.source_text,
                "text": translation.translated_text,
            }
            for segment, translation in zip(bundle.segments, translations)
        ],
    }
    return system_prompt, _compact_json(payload)
