from __future__ import annotations

from src.agents.prompts import build_guard_prompts
from src.core.types import SegmentBundle, TranslationResult
from src.llm.provider import LLMProvider
from src.llm.schemas import TRANSLATION_RESPONSE_SCHEMA


class FormatGuardAgent:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def repair_bundle(self, bundle: SegmentBundle, translations: list[TranslationResult]) -> list[TranslationResult]:
        if self.provider is None:
            return translations

        system_prompt, user_prompt = build_guard_prompts(bundle, translations)
        payload = self.provider.chat_json(
            system_prompt,
            user_prompt,
            call_label="format_guard",
            response_schema=TRANSLATION_RESPONSE_SCHEMA,
        )
        repaired = {item["segment_id"]: item for item in payload.get("translations", [])}
        results: list[TranslationResult] = []
        for item in translations:
            current = repaired.get(item.segment_id)
            if current is None:
                results.append(item)
                continue
            results.append(
                TranslationResult(
                    segment_id=item.segment_id,
                    translated_text=current.get("translated_text", item.translated_text),
                    notes=current.get("notes", item.notes),
                    applied_terms=current.get("applied_terms", item.applied_terms),
                    confidence=float(current.get("confidence", item.confidence)),
                )
            )
        return results
