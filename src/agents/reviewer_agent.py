from __future__ import annotations

import logging

from src.agents.prompts import build_improve_prompts, build_reflection_prompts
from src.core.types import DocumentContext, SegmentBundle, TranslationResult
from src.llm.provider import LLMProvider
from src.llm.schemas import REFLECTION_RESPONSE_SCHEMA, TRANSLATION_RESPONSE_SCHEMA

_SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}


class ReviewerAgent:
    """Reflect -> improve loop with re-verification of every fix.

    Each round asks the model for structured critiques, improves only the
    segments whose issues are at or above min_severity, then re-reflects on
    exactly the segments that were just improved (rounds > 1) so a bad fix is
    caught instead of shipped. The loop stops when a round finds no
    qualifying issues.
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def review_bundle(
        self,
        bundle: SegmentBundle,
        translations: list[TranslationResult],
        context: DocumentContext,
        min_severity: str = "high",
        max_rounds: int = 1,
    ) -> list[TranslationResult]:
        if self.provider is None:
            return translations
        current = list(translations)
        scope_ids: set[str] | None = None
        for _round in range(max(1, max_rounds)):
            round_bundle, round_translations = self._restrict(bundle, current, scope_ids)
            if not round_bundle.segments:
                break
            system_prompt, user_prompt = build_reflection_prompts(round_bundle, context, round_translations)
            payload = self.provider.chat_json(
                system_prompt,
                user_prompt,
                call_label="reflect",
                response_schema=REFLECTION_RESPONSE_SCHEMA,
            )
            issues = self._qualifying_issues(payload, min_severity)
            if not issues:
                break
            logging.info("Review flagged %s issue(s); improving affected segments", len(issues))
            current = self._improve(bundle, context, current, issues)
            scope_ids = {str(issue.get("segment_id")) for issue in issues}
        return current

    async def review_bundle_async(
        self,
        bundle: SegmentBundle,
        translations: list[TranslationResult],
        context: DocumentContext,
        min_severity: str = "high",
        max_rounds: int = 1,
    ) -> list[TranslationResult]:
        if self.provider is None:
            return translations
        current = list(translations)
        scope_ids: set[str] | None = None
        for _round in range(max(1, max_rounds)):
            round_bundle, round_translations = self._restrict(bundle, current, scope_ids)
            if not round_bundle.segments:
                break
            system_prompt, user_prompt = build_reflection_prompts(round_bundle, context, round_translations)
            payload = await self.provider.chat_json_async(
                system_prompt,
                user_prompt,
                call_label="reflect",
                response_schema=REFLECTION_RESPONSE_SCHEMA,
            )
            issues = self._qualifying_issues(payload, min_severity)
            if not issues:
                break
            logging.info("Review flagged %s issue(s); improving affected segments", len(issues))
            current = await self._improve_async(bundle, context, current, issues)
            scope_ids = {str(issue.get("segment_id")) for issue in issues}
        return current

    @staticmethod
    def _restrict(
        bundle: SegmentBundle,
        translations: list[TranslationResult],
        scope_ids: set[str] | None,
    ) -> tuple[SegmentBundle, list[TranslationResult]]:
        if scope_ids is None:
            return bundle, translations
        segments = [segment for segment in bundle.segments if segment.segment_id in scope_ids]
        by_id = {item.segment_id: item for item in translations}
        scoped = SegmentBundle(
            bundle_id=bundle.bundle_id,
            segments=segments,
            summary_before=bundle.summary_before,
            summary_after=bundle.summary_after,
            style_instructions=bundle.style_instructions,
        )
        return scoped, [by_id[segment.segment_id] for segment in segments if segment.segment_id in by_id]

    def _improve(
        self,
        bundle: SegmentBundle,
        context: DocumentContext,
        translations: list[TranslationResult],
        issues: list[dict],
    ) -> list[TranslationResult]:
        system_prompt, user_prompt = build_improve_prompts(bundle, context, translations, issues)
        payload = self.provider.chat_json(
            system_prompt,
            user_prompt,
            call_label="improve",
            response_schema=TRANSLATION_RESPONSE_SCHEMA,
        )
        return self._merge_improvements(translations, issues, payload)

    async def _improve_async(
        self,
        bundle: SegmentBundle,
        context: DocumentContext,
        translations: list[TranslationResult],
        issues: list[dict],
    ) -> list[TranslationResult]:
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
