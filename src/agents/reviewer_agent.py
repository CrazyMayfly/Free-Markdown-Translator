from __future__ import annotations

import logging

from src.agents.prompts import build_improve_prompts, build_reflection_prompts
from src.core.types import DocumentContext, SegmentBundle, TranslationResult
from src.llm.provider import LLMProvider
from src.llm.schemas import REFLECTION_RESPONSE_SCHEMA, TRANSLATION_RESPONSE_SCHEMA

_SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}


class ReviewerAgent:
    """Two-step reflection loop (translate -> critique -> improve).

    Step 1 asks the model for structured critiques of the bundle; step 2 asks
    it to improve only the segments whose issues are at or above min_severity.
    min_severity routes by pipeline mode: strict improves everything ("low"),
    balanced only acts on "high" severity issues.
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def review_bundle(
        self,
        bundle: SegmentBundle,
        translations: list[TranslationResult],
        context: DocumentContext,
        min_severity: str = "high",
    ) -> list[TranslationResult]:
        if self.provider is None:
            return translations
        system_prompt, user_prompt = build_reflection_prompts(bundle, context, translations)
        payload = self.provider.chat_json(
            system_prompt,
            user_prompt,
            call_label="reflect",
            response_schema=REFLECTION_RESPONSE_SCHEMA,
        )
        return self._improve_if_needed(bundle, context, translations, payload, min_severity)

    async def review_bundle_async(
        self,
        bundle: SegmentBundle,
        translations: list[TranslationResult],
        context: DocumentContext,
        min_severity: str = "high",
    ) -> list[TranslationResult]:
        if self.provider is None:
            return translations
        system_prompt, user_prompt = build_reflection_prompts(bundle, context, translations)
        payload = await self.provider.chat_json_async(
            system_prompt,
            user_prompt,
            call_label="reflect",
            response_schema=REFLECTION_RESPONSE_SCHEMA,
        )
        return await self._improve_if_needed_async(bundle, context, translations, payload, min_severity)

    def _improve_if_needed(
        self,
        bundle: SegmentBundle,
        context: DocumentContext,
        translations: list[TranslationResult],
        reflection_payload: dict,
        min_severity: str,
    ) -> list[TranslationResult]:
        issues = self._qualifying_issues(reflection_payload, min_severity)
        if not issues:
            return translations
        logging.info("Review flagged %s issue(s); improving affected segments", len(issues))
        system_prompt, user_prompt = build_improve_prompts(bundle, context, translations, issues)
        payload = self.provider.chat_json(
            system_prompt,
            user_prompt,
            call_label="improve",
            response_schema=TRANSLATION_RESPONSE_SCHEMA,
        )
        return self._merge_improvements(translations, issues, payload)

    async def _improve_if_needed_async(
        self,
        bundle: SegmentBundle,
        context: DocumentContext,
        translations: list[TranslationResult],
        reflection_payload: dict,
        min_severity: str,
    ) -> list[TranslationResult]:
        issues = self._qualifying_issues(reflection_payload, min_severity)
        if not issues:
            return translations
        logging.info("Review flagged %s issue(s); improving affected segments", len(issues))
        system_prompt, user_prompt = build_improve_prompts(bundle, context, translations, issues)
        payload = await self.provider.chat_json_async(
            system_prompt,
            user_prompt,
            call_label="improve",
            response_schema=TRANSLATION_RESPONSE_SCHEMA,
        )
        return self._merge_improvements(translations, issues, payload)

    @staticmethod
    def _qualifying_issues(reflection_payload: dict, min_severity: str) -> list[dict]:
        threshold = _SEVERITY_ORDER.get(min_severity, _SEVERITY_ORDER["high"])
        return [
            issue
            for issue in reflection_payload.get("issues", [])
            if _SEVERITY_ORDER.get(str(issue.get("severity", "")).lower(), 0) >= threshold
        ]

    @staticmethod
    def _merge_improvements(translations: list[TranslationResult], issues: list[dict], improve_payload: dict) -> list[TranslationResult]:
        updated = {item["segment_id"]: item for item in improve_payload.get("translations", [])}
        comments_by_segment: dict[str, list[str]] = {}
        for issue in issues:
            comments_by_segment.setdefault(str(issue.get("segment_id", "")), []).append(str(issue.get("comment", "")))

        results: list[TranslationResult] = []
        for item in translations:
            current = updated.get(item.segment_id)
            notes = list(item.notes)
            for comment in comments_by_segment.get(item.segment_id, []):
                review_note = f"review: {comment}"
                if review_note not in notes:
                    notes.append(review_note)
            if current is None:
                results.append(
                    TranslationResult(
                        segment_id=item.segment_id,
                        translated_text=item.translated_text,
                        notes=notes,
                        applied_terms=item.applied_terms,
                        confidence=item.confidence,
                    )
                )
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
