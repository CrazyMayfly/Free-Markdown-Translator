from __future__ import annotations

from src.agents.prompts import build_translator_prompts
from src.core.errors import TranslationPipelineError
from src.core.modes import normalize_mode
from src.core.types import DocumentContext, SegmentBundle, TranslationOutcome, TranslationResult
from src.llm.provider import LLMProvider
from src.llm.schemas import (
    TRANSLATION_COMPACT_SCHEMA,
    TRANSLATION_FAST_SCHEMA,
    TRANSLATION_QUALITY_SCHEMA,
)


class TranslatorAgent:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def translate_bundle(
        self,
        bundle: SegmentBundle,
        context: DocumentContext,
        target_lang: str,
        mode: str = "balanced",
    ) -> TranslationOutcome:
        if self.provider is None:
            raise TranslationPipelineError("No LLM provider configured; cannot perform translation.")
        system_prompt, user_prompt = build_translator_prompts(bundle, context, target_lang, mode=mode)
        payload = self.provider.chat_json(
            system_prompt,
            user_prompt,
            call_label="translate",
            response_schema=self._schema_for(mode),
        )
        return self._parse_outcome(bundle, payload)

    async def translate_bundle_async(
        self,
        bundle: SegmentBundle,
        context: DocumentContext,
        target_lang: str,
        mode: str = "balanced",
    ) -> TranslationOutcome:
        if self.provider is None:
            raise TranslationPipelineError("No LLM provider configured; cannot perform translation.")
        system_prompt, user_prompt = build_translator_prompts(bundle, context, target_lang, mode=mode)
        payload = await self.provider.chat_json_async(
            system_prompt,
            user_prompt,
            call_label="translate",
            response_schema=self._schema_for(mode),
        )
        return self._parse_outcome(bundle, payload)

    @staticmethod
    def _schema_for(mode: str) -> dict:
        normalized = normalize_mode(mode)
        if normalized == "fast":
            return TRANSLATION_FAST_SCHEMA
        if normalized == "quality":
            return TRANSLATION_QUALITY_SCHEMA
        return TRANSLATION_COMPACT_SCHEMA

    @staticmethod
    def _parse_outcome(bundle: SegmentBundle, payload: dict) -> TranslationOutcome:
        raw_items = payload.get("t")
        if raw_items is None:
            raw_items = payload.get("translations") or []
        results: list[TranslationResult] = []
        for item in raw_items:
            parsed = TranslatorAgent._parse_item(item)
            if parsed is not None:
                results.append(parsed)
        if not results:
            raise TranslationPipelineError("Model returned no translations for the current bundle.")
        translated_ids = {item.segment_id for item in results}
        expected_ids = {segment.segment_id for segment in bundle.segments}
        missing_ids = sorted(expected_ids - translated_ids)
        if missing_ids:
            raise TranslationPipelineError(
                "Model response is missing translations for segments: " + ", ".join(missing_ids)
            )
        requests = TranslatorAgent._parse_requests(payload.get("q") or payload.get("context_requests") or [])
        return TranslationOutcome(translations=results, context_requests=requests)

    @staticmethod
    def _parse_item(item: object) -> TranslationResult | None:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            segment_id = str(item[0])
            translated_text = str(item[1])
            return TranslationResult(segment_id=segment_id, translated_text=translated_text, confidence=1.0)
        if not isinstance(item, dict):
            return None
        raw_segment_id = item.get("i", item.get("segment_id"))
        raw_text = item.get("x", item.get("translated_text"))
        if raw_segment_id is None or raw_text is None:
            return None
        confidence = item.get("c", item.get("confidence", 1.0))
        return TranslationResult(
            segment_id=str(raw_segment_id),
            translated_text=str(raw_text),
            notes=[str(note) for note in item.get("n", item.get("notes", [])) or []],
            applied_terms={
                str(term): str(rendering)
                for term, rendering in (item.get("a", item.get("applied_terms", {})) or {}).items()
            },
            confidence=float(confidence) if confidence is not None else 1.0,
        )

    @staticmethod
    def _parse_requests(items: list) -> list[dict]:
        requests: list[dict] = []
        for item in items:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                segment_id, need = str(item[0]), str(item[1])
                reason = str(item[2]) if len(item) > 2 else ""
            elif isinstance(item, dict):
                segment_id = str(item.get("i", item.get("segment_id", "")))
                need = str(item.get("need", ""))
                reason = str(item.get("why", item.get("reason", "")))
            else:
                continue
            if segment_id and need:
                requests.append({"segment_id": segment_id, "need": need, "reason": reason[:200]})
        return requests
