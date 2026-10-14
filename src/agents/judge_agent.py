from __future__ import annotations

from src.agents.prompts import build_judge_prompts
from src.core.types import DocumentContext, Segment, TranslationResult
from src.llm.provider import LLMProvider
from src.llm.schemas import JUDGE_RESPONSE_SCHEMA

SCORE_DIMENSIONS = ("accuracy", "fluency", "terminology", "format")


class JudgeAgent:
    """LLM-as-judge quality evaluation for a translated document.

    Scores accuracy / fluency / terminology / format on a 1-5 scale plus an
    overall score and free-form comments. An optional reference translation
    (segment_id -> text) anchors the judgement when one exists.
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def evaluate(
        self,
        segments: list[Segment],
        translations: list[TranslationResult],
        context: DocumentContext | None,
        target_lang: str,
        reference: dict[str, str] | None = None,
    ) -> dict:
        if self.provider is None:
            raise ValueError("JudgeAgent requires an LLM provider.")
        if context is None:
            context = DocumentContext(title="", abstract="", section_summaries={}, style_guide=[], audience="")
        system_prompt, user_prompt = build_judge_prompts(context, target_lang, segments, translations, reference)
        payload = self.provider.chat_json(
            system_prompt,
            user_prompt,
            call_label="judge",
            response_schema=JUDGE_RESPONSE_SCHEMA,
        )
        scores = {dimension: float(payload.get("scores", {}).get(dimension, 0.0)) for dimension in SCORE_DIMENSIONS}
        return {
            "target_lang": target_lang,
            "scores": scores,
            "overall": float(payload.get("overall", 0.0)),
            "comments": list(payload.get("comments", [])),
        }
