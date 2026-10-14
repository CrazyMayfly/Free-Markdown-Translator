from __future__ import annotations

from src.core.errors import TranslationPipelineError
from src.agents.prompts import build_translator_prompts
from src.core.types import DocumentContext, SegmentBundle, TranslationResult
from src.llm.provider import LLMProvider
from src.llm.schemas import TRANSLATION_RESPONSE_SCHEMA


class TranslatorAgent:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def translate_bundle(self, bundle: SegmentBundle, context: DocumentContext, target_lang: str) -> list[TranslationResult]:
        if self.provider is None:
            raise TranslationPipelineError("No LLM provider configured; cannot perform translation.")

        system_prompt, user_prompt = build_translator_prompts(bundle, context, target_lang)
        payload = self.provider.chat_json(
            system_prompt,
            user_prompt,
            call_label="translate",
            response_schema=TRANSLATION_RESPONSE_SCHEMA,
        )
        results = [
            TranslationResult(
                segment_id=item["segment_id"],
                translated_text=item["translated_text"],
                notes=item.get("notes", []),
                applied_terms=item.get("applied_terms", {}),
                confidence=float(item.get("confidence", 0.0)),
            )
            for item in payload.get("translations", [])
        ]
        if not results:
            raise TranslationPipelineError("Model returned no translations for the current bundle.")
        translated_ids = {item.segment_id for item in results}
        expected_ids = {segment.segment_id for segment in bundle.segments}
        missing_ids = sorted(expected_ids - translated_ids)
        if missing_ids:
            raise TranslationPipelineError(
                "Model response is missing translations for segments: " + ", ".join(missing_ids)
            )
        return results
