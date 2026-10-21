from __future__ import annotations

import logging

from src.agents.prompts import build_final_review_prompts, build_improve_prompts
from src.agents.reviewer_agent import ReviewerAgent
from src.core.types import DocumentContext, Segment, SegmentBundle, TranslationResult
from src.llm.provider import LLMProvider
from src.llm.schemas import REFLECTION_RESPONSE_SCHEMA, TRANSLATION_RESPONSE_SCHEMA


class EditorAgent:
    """Document-level final edit pass (quality mode).

    Reviews the complete ordered segment list for defects that only appear
    across bundles — broken cross-references, terminology or tone drift
    between distant sections, dangling pronouns — then improves only the
    flagged segments with their document-order neighbours as context.
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    async def edit_document_async(
        self,
        segments: list[Segment],
        translations: list[TranslationResult],
        context: DocumentContext,
        max_segments: int = 300,
        min_severity: str = "medium",
    ) -> list[TranslationResult]:
        if self.provider is None:
            return translations
        translations_by_id = {item.segment_id: item for item in translations}
        scoped_segments = [segment for segment in segments if segment.segment_id in translations_by_id][: max(1, max_segments)]
        if len(scoped_segments) < 2:
            return translations
        virtual_bundle = SegmentBundle(
            bundle_id="final-edit",
            segments=scoped_segments,
            summary_before="",
            summary_after="",
            style_instructions=context.style_guide,
        )
        scoped_translations = [translations_by_id[segment.segment_id] for segment in scoped_segments]

        system_prompt, user_prompt = build_final_review_prompts(virtual_bundle, context, scoped_translations)
        payload = await self.provider.chat_json_async(
            system_prompt,
            user_prompt,
            call_label="final_edit",
            response_schema=REFLECTION_RESPONSE_SCHEMA,
        )
        issues = ReviewerAgent._qualifying_issues(payload, min_severity)
        if not issues:
            return translations

        logging.info("Final edit flagged %s document-level issue(s); improving affected segments", len(issues))
        system_prompt, user_prompt = build_improve_prompts(virtual_bundle, context, scoped_translations, issues)
        improved = await self.provider.chat_json_async(
            system_prompt,
            user_prompt,
            call_label="final_edit_improve",
            response_schema=TRANSLATION_RESPONSE_SCHEMA,
        )
        updated_by_id = {
            item["segment_id"]: item
            for item in improved.get("translations", [])
        }
        comments_by_segment: dict[str, list[str]] = {}
        for issue in issues:
            comments_by_segment.setdefault(str(issue.get("segment_id", "")), []).append(str(issue.get("comment", "")))

        results: list[TranslationResult] = []
        for item in translations:
            current = updated_by_id.get(item.segment_id)
            notes = list(item.notes)
            for comment in comments_by_segment.get(item.segment_id, []):
                review_note = f"final-edit: {comment}"
                if review_note not in notes:
                    notes.append(review_note)
            if current is None:
                results.append(item)
                continue
            results.append(
                TranslationResult(
                    segment_id=item.segment_id,
                    translated_text=current.get("translated_text", item.translated_text),
                    notes=notes,
                    applied_terms=current.get("applied_terms", item.applied_terms),
                    confidence=float(current.get("confidence", item.confidence)),
                )
            )
        return results
