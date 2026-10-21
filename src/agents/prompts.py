from __future__ import annotations

import json

from src.core.modes import ModeProfile, profile_for
from src.core.types import DocumentBrief, DocumentContext, SegmentBundle, TranslationResult

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
    if context.heading_outline:
        payload["heading_outline"] = [heading[:80] for heading in context.heading_outline[:60]]
    if context.glossary:
        payload["glossary"] = dict(list(context.glossary.items())[:40])
    return payload


def _fallback_brief(context: DocumentContext) -> DocumentBrief:
    """Use deterministic context when the Brief pass was skipped or failed."""
    brief = context.brief
    tone = brief.tone
    if not tone:
        for line in context.style_guide:
            if line.lower().startswith("tone:"):
                tone = line.split(":", 1)[1].strip()
                break
    return DocumentBrief(
        summary=brief.summary or context.abstract,
        tone=tone,
        audience=brief.audience or context.audience,
        glossary=brief.glossary or dict(context.glossary),
        section_summaries=brief.section_summaries or dict(context.section_summaries),
    )


def _brief_glossary_pairs(brief: DocumentBrief, bundle: SegmentBundle, limit: int = 30) -> list[list[str]]:
    text = " ".join(segment.source_text for segment in bundle.segments).casefold()
    pairs: list[list[str]] = []
    for term, rendering in brief.glossary.items():
        if term.casefold() not in text:
            continue
        pairs.append([term, rendering])
        if len(pairs) >= limit:
            break
    return pairs


def _bundle_blocks(bundle: SegmentBundle, profile: ModeProfile) -> tuple[dict[str, str], dict[str, str]]:
    """Return (block id -> text, segment id -> space separated block ids)."""
    if not profile.blocks or profile.block_chars <= 0:
        return {}, {}
    by_text: dict[str, str] = {}
    refs: dict[str, str] = {}

    def add(text: str) -> str:
        truncated = str(text)[: profile.block_chars]
        if truncated not in by_text:
            by_text[truncated] = f"b{len(by_text)}"
        return by_text[truncated]

    for segment in bundle.segments:
        segment_refs: list[str] = []
        for key in ("context_before", "context_after"):
            for text in segment.metadata.get(key) or []:
                segment_refs.append(add(str(text)))
        header = segment.metadata.get("table_header")
        if header and not segment.metadata.get("is_header"):
            segment_refs.append(add(str(header)))
        if segment_refs:
            # Preserve order but drop duplicates from the same segment.
            refs[segment.segment_id] = " ".join(dict.fromkeys(segment_refs))

    blocks = {block_id: text for text, block_id in by_text.items()}
    return blocks, refs


def _sections_payload(
    bundle: SegmentBundle,
    context: DocumentContext,
    brief: DocumentBrief,
    profile: ModeProfile,
    refs: dict[str, str],
) -> list[dict[str, object]]:
    grouped: dict[str, list] = {}
    for segment in bundle.segments:
        path = " / ".join(segment.context_path) if segment.context_path else "Document"
        grouped.setdefault(path, []).append(segment)

    sections: list[dict[str, object]] = []
    for path, segments in grouped.items():
        heading = " / ".join(path.split(" / ")[-2:]) if path != "Document" else "Document"
        entry: dict[str, object] = {"h": heading[:160]}
        summary = brief.section_summaries.get(path) or context.section_summaries.get(path)
        if profile.section_summary and summary:
            entry["sum"] = summary[:200]
        segment_entries: list[list[str]] = []
        for segment in segments:
            item = [segment.segment_id, segment.source_text]
            if segment.segment_id in refs:
                item.append(refs[segment.segment_id])
            segment_entries.append(item)
        entry["segs"] = segment_entries
        sections.append(entry)
    return sections


def build_translator_prompts(
    bundle: SegmentBundle,
    context: DocumentContext,
    target_lang: str,
    mode: str = "balanced",
) -> tuple[str, str]:
    profile = profile_for(mode)
    brief = _fallback_brief(context)
    glossary_pairs = _brief_glossary_pairs(brief, bundle) if profile.glossary else []

    if profile.schema == "minimal":
        system_prompt = (
            f"Translate Markdown to {target_lang}. Return JSON only: "
            '{"t":[["segment_id","translation"],...]} with exactly one pair per input segment. '
            "Input fields: brief={tone,aud,g[term,rendering]}, segs=[[segment_id,text]]. "
            "Keep placeholders, URLs, code and Markdown control syntax exactly. "
            "Use every brief.g rendering verbatim and follow brief.tone and brief.aud. "
            "Do not add notes, confidence or any other fields."
        )
        payload: dict[str, object] = {"task": "translate", "lang": target_lang}
        brief_payload: dict[str, object] = {}
        if brief.tone:
            brief_payload["tone"] = brief.tone[:80]
        if brief.audience:
            brief_payload["aud"] = brief.audience[:80]
        if glossary_pairs:
            brief_payload["g"] = glossary_pairs
        if brief_payload:
            payload["brief"] = brief_payload
        payload["segs"] = [[segment.segment_id, segment.source_text] for segment in bundle.segments]
        return system_prompt, _compact_json(payload)

    output_fields = (
        '{"t":[{"i":"segment_id","x":"translation","c":0.0,"a":{},"n":[]}],"q":[]}'
        if profile.schema == "full"
        else '{"t":[{"i":"segment_id","x":"translation","c":0.0}],"q":[]}'
    )
    system_prompt = (
        f"Translate Markdown to {target_lang}. Return JSON only: {output_fields} with one t entry per input segment. "
        "Input fields: brief={s,tone,aud,g[term,rendering]}, prev, anchor=[[source,translation]], "
        "blocks={block_id:read-only text}, sections=[{h,sum,segs:[[segment_id,text,refs?]]}], "
        "similar={segment_id:[[source,translation],...]} (prior renderings; follow unless clearly wrong). "
        "refs is a space-separated list of block ids (code/HTML/table header) for context only; never translate blocks. "
        "Use brief.g renderings verbatim, match brief.tone/aud, and keep placeholders, URLs, code and Markdown syntax exactly. "
        "q is for context requests: [[segment_id,need,why]] where need is similar_translations or neighbour_translations; "
        "leave it empty when the visible context is enough."
    )
    payload = {"task": "translate", "lang": target_lang}
    brief_payload = {}
    if profile.brief_summary and brief.summary:
        brief_payload["s"] = brief.summary[:1200]
    if brief.tone:
        brief_payload["tone"] = brief.tone[:80]
    if brief.audience:
        brief_payload["aud"] = brief.audience[:80]
    if glossary_pairs:
        brief_payload["g"] = glossary_pairs
    if brief_payload:
        payload["brief"] = brief_payload
    if profile.previous and bundle.summary_before:
        payload["prev"] = bundle.summary_before[: profile.previous_chars]
    if profile.anchor and bundle.anchor_translations:
        payload["anchor"] = [
            [entry.get("source", "")[:240], entry.get("text", "")[:240]]
            for entry in bundle.anchor_translations
        ]
    blocks, refs = _bundle_blocks(bundle, profile)
    if blocks:
        payload["blocks"] = blocks
    payload["sections"] = _sections_payload(bundle, context, brief, profile, refs)
    if bundle.similar_examples:
        payload["similar"] = {
            segment_id: [[entry.get("source", ""), entry.get("translation", "")] for entry in examples]
            for segment_id, examples in bundle.similar_examples.items()
        }

    if profile.style_guide and context.style_guide:
        payload["guide"] = context.style_guide[:8]
    if profile.abstract and not brief.summary and context.abstract:
        payload["abs"] = context.abstract[:300]
    if profile.outline and context.heading_outline:
        payload["outline"] = [heading[:80] for heading in context.heading_outline[:60]]

    return system_prompt, _compact_json(payload)


def build_reviewer_prompts(bundle: SegmentBundle, context: DocumentContext, translations: list[TranslationResult]) -> tuple[str, str]:
    system_prompt = (
        "Review translations only if needed. "
        "Input JSON fields: task=job type, ctx=shared document hints, prev_summary=source digest of the preceding bundle, "
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
            for segment, translation in zip(bundle.segments, translations, strict=False)
        ],
    }
    return system_prompt, _compact_json(payload)


def build_reflection_prompts(bundle: SegmentBundle, context: DocumentContext, translations: list[TranslationResult]) -> tuple[str, str]:
    system_prompt = (
        "You are a critical translation reviewer. Compare each translation against its source and the document context. "
        "Input JSON fields: task=job type, ctx=shared document hints, prev_summary=source digest of the preceding bundle, "
        "translations=list of items with segment_id, source and current text. "
        'Return JSON only: {"issues":[{"segment_id":"...","type":"accuracy|fluency|terminology|style|format","severity":"low|medium|high","comment":"specific critique"}]}. '
        "Report only real problems: meaning errors, awkward target-language phrasing, wrong or missing preserved terms, "
        "renderings that violate ctx.glossary, style-guide violations, or broken markdown/placeholders. "
        "An empty issues list is a valid answer when the translation is good."
    )
    payload = {
        "task": "reflect",
        "ctx": _document_context_payload(context),
        "prev_summary": bundle.summary_before[:400] if bundle.summary_before else "",
        "translations": [
            {
                "segment_id": segment.segment_id,
                "source": segment.source_text,
                "text": translation.translated_text,
            }
            for segment, translation in zip(bundle.segments, translations, strict=False)
        ],
    }
    return system_prompt, _compact_json(payload)


def _neighbor_payload(bundle: SegmentBundle, index: int, translations_by_id: dict[str, TranslationResult]) -> dict[str, dict[str, str] | None]:
    segments = bundle.segments
    neighbors: dict[str, dict[str, str] | None] = {"prev": None, "next": None}

    def describe(segment) -> dict[str, str]:
        previous = translations_by_id.get(segment.segment_id)
        entry = {
            "segment_id": segment.segment_id,
            "source": segment.source_text[:300],
            "text": previous.translated_text[:300] if previous else "",
        }
        return entry

    if index > 0:
        neighbors["prev"] = describe(segments[index - 1])
    if index < len(segments) - 1:
        neighbors["next"] = describe(segments[index + 1])
    return neighbors


def build_improve_prompts(
    bundle: SegmentBundle,
    context: DocumentContext,
    translations: list[TranslationResult],
    issues: list[dict],
) -> tuple[str, str]:
    flagged_ids = {str(issue.get("segment_id")) for issue in issues}
    segment_index = {segment.segment_id: index for index, segment in enumerate(bundle.segments)}
    translations_by_id = {item.segment_id: item for item in translations}
    system_prompt = (
        "You are an expert Markdown translation fixer. Improve only the translations flagged by review, guided by the critique for each. "
        "Input JSON fields: task=job type, ctx=shared document hints, issues=critique items to address, "
        "translations=list of flagged items with segment_id, source, current text and neighbors=adjacent segments (source and current translation) for context. "
        f"{_OUTPUT_CONTRACT} "
        "Address every issue comment; stay consistent with the neighbouring segments; "
        "keep placeholders, URLs, code and markdown control syntax exactly; do not change unflagged meaning."
    )
    payload = {
        "task": "improve",
        "ctx": _document_context_payload(context),
        "issues": [
            {
                "segment_id": str(issue.get("segment_id", "")),
                "type": str(issue.get("type", "")),
                "severity": str(issue.get("severity", "")),
                "comment": str(issue.get("comment", ""))[:500],
            }
            for issue in issues
        ],
        "translations": [
            {
                "segment_id": item.segment_id,
                "source": bundle.segments[segment_index[item.segment_id]].source_text if item.segment_id in segment_index else "",
                "text": item.translated_text,
                "neighbors": _neighbor_payload(bundle, segment_index[item.segment_id], translations_by_id)
                if item.segment_id in segment_index
                else {"prev": None, "next": None},
            }
            for item in translations
            if item.segment_id in flagged_ids
        ],
    }
    return system_prompt, _compact_json(payload)


def build_glossary_prompts(context: DocumentContext, sample_text: str, target_lang: str) -> tuple[str, str]:
    system_prompt = (
        f"You are a translation terminology specialist. Build a compact glossary for translating a Markdown document to {target_lang}. "
        "Input JSON fields: task=job type, ctx=document hints (title, heading_outline=document map), sample=representative source text. "
        'Return JSON only: {"terms":[{"term":"source term","rendering":"required translation"}]}. '
        "List only domain-specific terms, product names and recurring technical concepts whose translation must stay consistent across the document; "
        "skip common words. Keep each rendering short and natural."
    )
    payload = {
        "task": "glossary",
        "ctx": _document_context_payload(context),
        "sample": sample_text[:1500],
    }
    return system_prompt, _compact_json(payload)


def build_harmonize_prompts(
    bundle: SegmentBundle,
    context: DocumentContext,
    translations: list[TranslationResult],
    canonical: dict[str, str],
) -> tuple[str, str]:
    system_prompt = (
        "You are a translation consistency editor. Some segments use term renderings that disagree with the document glossary. "
        "Input JSON fields: task=job type, ctx=shared document hints, glossary=term->required rendering, "
        "translations=list of affected items with segment_id, source and current text. "
        f"{_OUTPUT_CONTRACT} "
        "Rewrite each item so every glossary term uses the required rendering verbatim; "
        "change nothing else: keep meaning, placeholders, URLs, code and markdown control syntax exactly."
    )
    payload = {
        "task": "harmonize",
        "ctx": _document_context_payload(context),
        "glossary": canonical,
        "translations": [
            {
                "segment_id": item.segment_id,
                "source": next((segment.source_text for segment in bundle.segments if segment.segment_id == item.segment_id), ""),
                "text": item.translated_text,
            }
            for item in translations
        ],
    }
    return system_prompt, _compact_json(payload)


def build_judge_prompts(
    context: DocumentContext,
    target_lang: str,
    segments: list,
    translations: list[TranslationResult],
    reference: dict[str, str] | None = None,
) -> tuple[str, str]:
    system_prompt = (
        f"You are an impartial translation quality judge. Score the {target_lang} translations of the given Markdown document. "
        "Input JSON fields: task=job type, ctx=document hints, reference=optional reference translations keyed by segment_id, "
        "translations=list of items with segment_id, source and text. "
        'Return JSON only: {"scores":{"accuracy":n,"fluency":n,"terminology":n,"format":n},"overall":n,"comments":["..."],"weak_segments":["..."]} '
        "with every score on a 1-5 scale (5=excellent) and overall as the weighted general quality. "
        "accuracy=fidelity to source meaning; fluency=natural target-language phrasing; terminology=correct use of domain terms "
        "and consistent renderings across the document (including ctx.glossary); format=markdown structure, placeholders and code kept intact. "
        "weak_segments=segment_ids of the few weakest translations (at most 3, empty list when none stand out)."
    )
    payload: dict[str, object] = {
        "task": "judge",
        "ctx": _document_context_payload(context),
        "translations": [
            {
                "segment_id": item.segment_id,
                "source": next((segment.source_text for segment in segments if segment.segment_id == item.segment_id), ""),
                "text": item.translated_text,
            }
            for item in translations
        ],
    }
    if reference:
        payload["reference"] = {key: value[:600] for key, value in reference.items()}
    return system_prompt, _compact_json(payload)


def build_guard_prompts(bundle: SegmentBundle, translations: list[TranslationResult]) -> tuple[str, str]:
    system_prompt = (
        "Repair markdown-format issues only. "
        f"{_OUTPUT_CONTRACT} "
        "Make minimal edits and keep code spans, URLs and markdown syntax unchanged."
    )
    payload = {
        "task": "format_guard",
        "translations": [
            {
                "segment_id": segment.segment_id,
                "source": segment.source_text,
                "text": translation.translated_text,
            }
            for segment, translation in zip(bundle.segments, translations, strict=False)
        ],
    }
    return system_prompt, _compact_json(payload)


def build_final_review_prompts(bundle: SegmentBundle, context: DocumentContext, translations: list[TranslationResult]) -> tuple[str, str]:
    system_prompt = (
        "You are a document-level translation editor reviewing the COMPLETE document after section-by-section translation. "
        "Input JSON fields: task=job type, ctx=shared document hints, translations=the document's segments in order with segment_id, source and current text. "
        'Return JSON only: {"issues":[{"segment_id":"...","type":"accuracy|fluency|terminology|style|format","severity":"low|medium|high","comment":"specific critique"}]}. '
        "Focus on defects that only appear across segments: broken references between sections, inconsistent terminology or tone drift between distant parts, "
        "abrupt transitions, pronouns or demonstratives with no resolvable antecedent, repeated translations of the same source rendered differently. "
        "Do NOT flag local defects a per-section reviewer would catch; do not rewrite style for taste. "
        "An empty issues list is a valid answer when the document reads coherently."
    )
    payload = {
        "task": "reflect",
        "ctx": _document_context_payload(context),
        "prev_summary": "",
        "translations": [
            {
                "segment_id": segment.segment_id,
                "source": segment.source_text[:240],
                "text": translation.translated_text[:240],
            }
            for segment, translation in zip(bundle.segments, translations, strict=False)
        ],
    }
    return system_prompt, _compact_json(payload)


def build_brief_prompts(
    context: DocumentContext,
    sample_text: str,
    target_lang: str,
    mode: str = "balanced",
    part: str = "",
) -> tuple[str, str]:
    """One document-level pass producing the reusable summary/glossary brief.

    fast asks only for tone/audience/glossary because its translate prompt does
    not inject a summary or section map.
    """
    if profile_for(mode).schema == "minimal":
        system_prompt = (
            f"You are a translation planner for a Markdown document translated to {target_lang}. "
            "Read it and return only the tone, audience and glossary that later calls must reuse. "
            'Return JSON only: {"tone":"tone","aud":"target audience",'
            '"g":[{"term":"source term","rendering":"required target rendering"}]}. '
            "Only domain terms/product names/recurring technical concepts; each term must literally appear "
            "in the document; skip common words; at most 30 entries; keep it compact and do not translate the document."
        )
    else:
        system_prompt = (
            f"You are a translation planner for a Markdown document that will be translated to {target_lang}. "
            "Read the whole document and return a compact brief that every later translation call can reuse. "
            'Return JSON only: {"s":"document summary","tone":"tone","aud":"target audience",'
            '"g":[{"term":"source term","rendering":"required target rendering"}],'
            '"sec":[{"h":"heading path","sum":"one-line section summary"}]}. '
            "s: at most 200 words, focus on purpose and domain, not a translation. "
            "g: only domain terms/product names/recurring technical concepts whose rendering must stay consistent; "
            "each term must literally appear in the document; skip common words; at most 30 entries. "
            "sec: one short summary per heading, using the same heading path. "
            "Do not translate the document, do not copy long passages, and keep the JSON compact."
        )
    doc_limit = 12000 if profile_for(mode).schema == "minimal" else 24000
    payload = {
        "task": "brief",
        "lang": target_lang,
        "title": context.title[:120],
        "outline": [heading[:80] for heading in context.heading_outline[:80]],
        "doc": sample_text[:doc_limit],
    }
    if part:
        payload["part"] = part
    return system_prompt, _compact_json(payload)


def build_brief_merge_prompts(context: DocumentContext, partials: list, target_lang: str) -> tuple[str, str]:
    system_prompt = (
        f"You merge partial translation briefs for a Markdown document translated to {target_lang}. "
        'Return JSON only: {"s":"document summary","tone":"tone","aud":"target audience",'
        '"g":[{"term":"source term","rendering":"required target rendering"}],'
        '"sec":[{"h":"heading path","sum":"one-line section summary"}]}. '
        "Keep the summary under 200 words, preserve every distinct section summary, deduplicate glossary terms, "
        "drop terms that never occur in the document, and do not translate the document."
    )
    payload = {
        "task": "brief_merge",
        "lang": target_lang,
        "title": context.title[:120],
        "parts": [
            {
                "s": part.summary,
                "tone": part.tone,
                "aud": part.audience,
                "g": [{"term": term, "rendering": rendering} for term, rendering in part.glossary.items()],
                "sec": [{"h": heading, "sum": summary} for heading, summary in part.section_summaries.items()],
            }
            for part in partials
        ],
    }
    return system_prompt, _compact_json(payload)
