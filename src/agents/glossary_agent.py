from __future__ import annotations

from src.agents.prompts import build_glossary_prompts, build_harmonize_prompts
from src.core.types import DocumentContext, SegmentBundle, TranslationResult
from src.llm.provider import LLMProvider
from src.llm.schemas import GLOSSARY_RESPONSE_SCHEMA, TRANSLATION_RESPONSE_SCHEMA


class GlossaryAgent:
    """Document-level terminology coordination.

    extract() runs once before translation and turns the document map plus a
    source sample into an authoritative term -> rendering glossary that every
    bundle prompt carries. harmonize_bundle() runs after translation to rewrite
    segments whose renderings drifted from the canonical glossary.
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def extract(self, context: DocumentContext, sample_text: str, target_lang: str) -> dict[str, str]:
        if self.provider is None:
            return {}
        system_prompt, user_prompt = build_glossary_prompts(context, sample_text, target_lang)
        payload = self.provider.chat_json(
            system_prompt,
            user_prompt,
            call_label="glossary",
            response_schema=GLOSSARY_RESPONSE_SCHEMA,
        )
        return self._parse_terms(payload)

    async def extract_async(self, context: DocumentContext, sample_text: str, target_lang: str) -> dict[str, str]:
        if self.provider is None:
            return {}
        system_prompt, user_prompt = build_glossary_prompts(context, sample_text, target_lang)
        payload = await self.provider.chat_json_async(
            system_prompt,
            user_prompt,
            call_label="glossary",
            response_schema=GLOSSARY_RESPONSE_SCHEMA,
        )
        return self._parse_terms(payload)

    def harmonize_bundle(
        self,
        bundle: SegmentBundle,
        context: DocumentContext,
        translations: list[TranslationResult],
        canonical: dict[str, str],
    ) -> list[TranslationResult]:
        if self.provider is None:
            return translations
        system_prompt, user_prompt = build_harmonize_prompts(bundle, context, translations, canonical)
        payload = self.provider.chat_json(
            system_prompt,
            user_prompt,
            call_label="harmonize",
            response_schema=TRANSLATION_RESPONSE_SCHEMA,
        )
        return self._merge(translations, payload)

    async def harmonize_bundle_async(
        self,
        bundle: SegmentBundle,
        context: DocumentContext,
        translations: list[TranslationResult],
        canonical: dict[str, str],
    ) -> list[TranslationResult]:
        if self.provider is None:
            return translations
        system_prompt, user_prompt = build_harmonize_prompts(bundle, context, translations, canonical)
        payload = await self.provider.chat_json_async(
            system_prompt,
            user_prompt,
            call_label="harmonize",
            response_schema=TRANSLATION_RESPONSE_SCHEMA,
        )
        return self._merge(translations, payload)

    @staticmethod
    def _parse_terms(payload: dict) -> dict[str, str]:
        glossary: dict[str, str] = {}
        for item in payload.get("terms", []):
            term = str(item.get("term", "")).strip()
            rendering = str(item.get("rendering", "")).strip()
            if term and rendering:
                glossary[term] = rendering
        return glossary

    @staticmethod
    def _merge(translations: list[TranslationResult], payload: dict) -> list[TranslationResult]:
        harmonized = {item["segment_id"]: item for item in payload.get("translations", [])}
        results: list[TranslationResult] = []
        for item in translations:
            current = harmonized.get(item.segment_id)
            if current is None:
                results.append(item)
                continue
            notes = list(item.notes)
            if "glossary-harmonized" not in notes:
                notes.append("glossary-harmonized")
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
