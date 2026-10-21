from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict

from src.agents.prompts import build_brief_merge_prompts, build_brief_prompts
from src.core.modes import profile_for
from src.core.types import DocumentBrief, DocumentContext, Segment
from src.llm.provider import LLMProvider
from src.llm.schemas import BRIEF_FAST_SCHEMA, BRIEF_RESPONSE_SCHEMA
from src.memory.brief_cache import BriefCache

BRIEF_PROMPT_VERSION = "brief-v2"
FAST_INPUT_LIMIT = 12000
FULL_INPUT_LIMIT = 24000

_MAX_GLOSSARY_TERMS = 40
_MAX_SECTION_SUMMARIES = 80


class BriefAgent:
    """Build one reusable document brief from the whole source text.

    Long documents are split into section-aligned chunks (map), each chunk is
    summarized with the same brief schema, and the partial briefs are merged
    (reduce) into the final summary/glossary. Quality/balanced use an LLM
    reduce step; fast merges deterministically because it only consumes
    tone/audience/glossary.
    """

    def __init__(self, provider: LLMProvider | None = None, cache: BriefCache | None = None) -> None:
        self.provider = provider
        self.cache = cache

    @property
    def model(self) -> str:
        return self.provider.model if self.provider is not None else ""

    def generate(
        self,
        context: DocumentContext,
        segments: list[Segment],
        target_lang: str,
        mode: str = "balanced",
        source_text: str = "",
    ) -> DocumentBrief:
        return asyncio.run(self.generate_async(context, segments, target_lang, mode=mode, source_text=source_text))

    async def generate_async(
        self,
        context: DocumentContext,
        segments: list[Segment],
        target_lang: str,
        mode: str = "balanced",
        source_text: str = "",
    ) -> DocumentBrief:
        if self.provider is None:
            return DocumentBrief()
        full_sample = source_text or self._sample(segments)
        if not full_sample.strip():
            return DocumentBrief()

        key: str | None = None
        if self.cache is not None:
            key = self.cache.make_key(
                full_sample,
                self.model,
                target_lang,
                mode,
                BRIEF_PROMPT_VERSION,
            )
            try:
                cached = self.cache.get(key)
            except Exception as exc:
                logging.warning("Brief cache read failed (%s); regenerating", exc)
                cached = None
            if cached is not None:
                logging.info("Brief cache hit: %s", key[:12])
                return self._from_dict(cached)

        limit = FAST_INPUT_LIMIT if profile_for(mode).schema == "minimal" else FULL_INPUT_LIMIT
        chunks = self._chunks(segments, limit)
        if not chunks:
            return DocumentBrief()
        if len(chunks) == 1:
            brief = await self._generate_one(context, chunks[0], target_lang, mode)
        else:
            logging.info("Brief map-reduce: %s chunks, mode=%s", len(chunks), mode)
            partials: list[DocumentBrief] = []
            for index, chunk in enumerate(chunks):
                try:
                    partials.append(
                        await self._generate_one(
                            context,
                            chunk,
                            target_lang,
                            mode,
                            part=f"{index + 1}/{len(chunks)}",
                        )
                    )
                except Exception as exc:
                    logging.warning("Brief map chunk %s/%s failed (%s); skipping", index + 1, len(chunks), exc)
            brief = await self._merge(context, partials, target_lang, mode, full_sample)

        if (
            self.cache is not None
            and key is not None
            and (brief.summary or brief.tone or brief.audience or brief.glossary or brief.section_summaries)
        ):
            try:
                self.cache.put(key, asdict(brief))
            except Exception as exc:
                logging.warning("Brief cache write failed (%s); continuing", exc)
        return brief

    async def _generate_one(
        self,
        context: DocumentContext,
        sample: str,
        target_lang: str,
        mode: str,
        part: str = "",
    ) -> DocumentBrief:
        if self.provider is None:
            return DocumentBrief()
        system_prompt, user_prompt = build_brief_prompts(context, sample, target_lang, mode=mode, part=part)
        payload = await self.provider.chat_json_async(
            system_prompt,
            user_prompt,
            call_label="brief",
            response_schema=self._schema_for(mode),
        )
        return self._parse(payload, sample)

    async def _merge(
        self,
        context: DocumentContext,
        partials: list[DocumentBrief],
        target_lang: str,
        mode: str,
        full_sample: str,
    ) -> DocumentBrief:
        if not partials:
            return DocumentBrief()
        if profile_for(mode).schema == "minimal" or len(partials) == 1:
            return self._deterministic_merge(partials, full_sample)
        if self.provider is None:
            return self._deterministic_merge(partials, full_sample)
        try:
            system_prompt, user_prompt = build_brief_merge_prompts(context, partials, target_lang)
            payload = await self.provider.chat_json_async(
                system_prompt,
                user_prompt,
                call_label="brief_merge",
                response_schema=BRIEF_RESPONSE_SCHEMA,
            )
            return self._parse(payload, full_sample)
        except Exception as exc:
            logging.warning("Brief reduce failed (%s); merging partials deterministically", exc)
            return self._deterministic_merge(partials, full_sample)

    def _deterministic_merge(self, partials: list[DocumentBrief], full_sample: str) -> DocumentBrief:
        summary = " ".join(part.summary.strip() for part in partials if part.summary.strip())[:1200]
        tone = next((part.tone for part in partials if part.tone), "")
        audience = next((part.audience for part in partials if part.audience), "")
        glossary: list[dict[str, str]] = []
        seen: set[str] = set()
        for part in partials:
            for term, rendering in part.glossary.items():
                if term in seen:
                    continue
                seen.add(term)
                glossary.append({"term": term, "rendering": rendering})
        sections: list[dict[str, str]] = []
        seen_sections: set[str] = set()
        for part in partials:
            for heading, text in part.section_summaries.items():
                if heading in seen_sections:
                    continue
                seen_sections.add(heading)
                sections.append({"h": heading, "sum": text})
        return self._parse(
            {"s": summary, "tone": tone, "aud": audience, "g": glossary, "sec": sections},
            full_sample,
        )

    @staticmethod
    def _sample(segments: list[Segment]) -> str:
        # Code blocks are not segments; the prose is what the brief needs.
        return "\n\n".join(segment.source_text for segment in segments)

    @staticmethod
    def _chunks(segments: list[Segment], limit: int) -> list[str]:
        chunks: list[str] = []
        current: list[str] = []
        chars = 0
        for segment in segments:
            for piece in BriefAgent._split_long(segment.source_text, limit):
                extra = len(piece) + (2 if current else 0)
                if current and chars + extra > limit:
                    chunks.append("\n\n".join(current))
                    current = []
                    chars = 0
                current.append(piece)
                chars += len(piece) + (2 if len(current) > 1 else 0)
        if current:
            chunks.append("\n\n".join(current))
        return chunks

    @staticmethod
    def _split_long(text: str, limit: int) -> list[str]:
        pieces: list[str] = []
        remaining = text
        while len(remaining) > limit:
            cut = remaining.rfind("\n", 0, limit)
            if cut <= 0:
                cut = remaining.rfind(" ", 0, limit)
            if cut <= 0:
                cut = limit
            pieces.append(remaining[:cut])
            remaining = remaining[cut:].lstrip("\n")
        if remaining:
            pieces.append(remaining)
        return pieces

    @staticmethod
    def _schema_for(mode: str) -> dict:
        return BRIEF_FAST_SCHEMA if profile_for(mode).schema == "minimal" else BRIEF_RESPONSE_SCHEMA

    @classmethod
    def _parse(cls, payload: dict, sample: str) -> DocumentBrief:
        if not isinstance(payload, dict):
            return DocumentBrief()
        summary = str(payload.get("s", "") or "").strip()[:1200]
        tone = str(payload.get("tone", "") or "").strip()[:80]
        audience = str(payload.get("aud", "") or "").strip()[:80]

        sample_lower = sample.casefold()
        glossary: dict[str, str] = {}
        for item in payload.get("g") or []:
            if not isinstance(item, dict):
                continue
            term = str(item.get("term", "") or "").strip()
            rendering = str(item.get("rendering", "") or "").strip()
            if not term or not rendering or len(term) > 80:
                continue
            if term.casefold() not in sample_lower:
                # Reject hallucinated terms that never occur in the document.
                continue
            glossary[term] = rendering[:120]
            if len(glossary) >= _MAX_GLOSSARY_TERMS:
                break

        section_summaries: dict[str, str] = {}
        for item in payload.get("sec") or []:
            if not isinstance(item, dict):
                continue
            heading = str(item.get("h", "") or "").strip()
            summary_text = str(item.get("sum", "") or "").strip()
            if not heading or not summary_text:
                continue
            section_summaries[heading] = summary_text[:200]
            if len(section_summaries) >= _MAX_SECTION_SUMMARIES:
                break

        if not (summary or tone or audience or glossary or section_summaries):
            logging.warning("Brief response had no usable content; falling back to deterministic context")
        return DocumentBrief(
            summary=summary,
            tone=tone,
            audience=audience,
            glossary=glossary,
            section_summaries=section_summaries,
        )

    @staticmethod
    def _from_dict(payload: dict) -> DocumentBrief:
        return DocumentBrief(
            summary=str(payload.get("summary", "") or ""),
            tone=str(payload.get("tone", "") or ""),
            audience=str(payload.get("audience", "") or ""),
            glossary={str(k): str(v) for k, v in (payload.get("glossary") or {}).items()},
            section_summaries={
                str(k): str(v) for k, v in (payload.get("section_summaries") or {}).items()
            },
        )
