from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections.abc import Callable
from pathlib import Path

from src.agents.format_guard_agent import FormatGuardAgent
from src.agents.glossary_agent import GlossaryAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.translator_agent import TranslatorAgent
from src.core.errors import OutputWriteError, TranslationPipelineError
from src.core.glossary import canonical_glossary, detect_glossary_conflicts
from src.core.orchestrator import Orchestrator
from src.core.types import ApiUsageSummary, MemoryStore, PipelineResult, SegmentBundle, TranslationResult
from src.infra.config import TranslatorConfig
from src.infra.logging import log_success
from src.memory.checkpoint import JobCheckpointStore
from src.memory.document_context import DocumentContextBuilder
from src.memory.translation_memory import NullMemory, TranslationMemory
from src.parser.anchor_rewriter import heading_pairs, rewrite_anchors
from src.parser.ast_mapper import AstMapper
from src.parser.markdown_parser import MarkdownParser
from src.parser.renderer import MarkdownRenderer
from src.parser.segment_extractor import ProtectedSpanProcessor, SegmentExtractor
from src.validators.markdown_validator import MarkdownValidator
from src.validators.output_report import OutputReportBuilder


class TranslationPipeline:
    def __init__(
        self,
        config: TranslatorConfig,
        parser: MarkdownParser,
        extractor: SegmentExtractor,
        translator_agent: TranslatorAgent,
        reviewer_agent: ReviewerAgent,
        format_guard_agent: FormatGuardAgent,
        validator: MarkdownValidator,
        memory: MemoryStore | None = None,
        checkpoint_store: JobCheckpointStore | None = None,
        glossary_agent: GlossaryAgent | None = None,
    ) -> None:
        self.config = config
        self.parser = parser
        self.extractor = extractor
        self.translator_agent = translator_agent
        self.reviewer_agent = reviewer_agent
        self.format_guard_agent = format_guard_agent
        self.validator = validator
        self.memory: MemoryStore = memory if memory is not None else NullMemory()
        self.checkpoint_store = checkpoint_store
        self.glossary_agent = glossary_agent
        self.context_builder = DocumentContextBuilder()
        self.orchestrator = Orchestrator()
        self.protected_span_processor = ProtectedSpanProcessor()
        self.mapper = AstMapper()
        self.renderer = MarkdownRenderer()
        self.report_builder = OutputReportBuilder()

    def run(
        self,
        input_path: Path,
        target_lang: str,
        write_output: bool = True,
        output_path: Path | None = None,
        bundle_progress_callback: Callable[[Path, str, str], None] | None = None,
    ) -> PipelineResult:
        return asyncio.run(
            self.run_async(
                input_path=input_path,
                target_lang=target_lang,
                write_output=write_output,
                output_path=output_path,
                bundle_progress_callback=bundle_progress_callback,
            )
        )

    async def run_async(
        self,
        input_path: Path,
        target_lang: str,
        write_output: bool = True,
        output_path: Path | None = None,
        semaphore: asyncio.Semaphore | None = None,
        bundle_progress_callback: Callable[[Path, str, str], None] | None = None,
    ) -> PipelineResult:
        logging.info("Pipeline: %s -> %s", input_path.name, target_lang)
        source_text = input_path.read_text(encoding="utf-8")
        parsed = self.parser.parse(source_text, input_path, target_lang)
        segments = self.extractor.extract(parsed)
        parsed.segments = segments  # type: ignore[attr-defined]

        context = self.context_builder.build(parsed, segments, self.config)
        fingerprint = self._memory_fingerprint(source_text)
        mode = self._normalized_mode()
        resumed_bundles = self.checkpoint_store.load(input_path, target_lang) if self.checkpoint_store is not None else {}
        context.glossary = await self._build_glossary(context, segments, fingerprint, target_lang, resumed_bundles)
        bundles = self.orchestrator.build_bundles(segments, context, self.config)
        logging.info("Prepared %s segments in %s bundles", len(segments), len(bundles))
        if resumed_bundles:
            logging.info("Resuming %s: %s/%s bundles already completed", input_path.name, len(resumed_bundles), len(bundles))

        segment_lookup = {segment.segment_id: segment for segment in segments}
        all_translations = await self._translate_bundles(
            bundles=bundles,
            context=context,
            target_lang=target_lang,
            segment_lookup=segment_lookup,
            mode=mode,
            input_path=input_path,
            semaphore=semaphore,
            bundle_progress_callback=bundle_progress_callback,
            resumed_bundles=resumed_bundles,
            fingerprint=fingerprint,
        )
        all_translations = await self._consistency_pass(bundles, all_translations, context, target_lang, fingerprint, segment_lookup)
        all_translations = self._restore_all(all_translations, segment_lookup)

        output_text, validation, all_translations = self._render_and_validate(
            parsed=parsed,
            segments=segments,
            translations=all_translations,
        )
        if not validation.passed and self._should_run_format_guard(validation):
            logging.warning("Validation failed, running guard (mode=%s errors=%s)", mode, len(validation.errors))
            repaired = []
            translations_by_bundle = self._translations_by_bundle(bundles, all_translations)
            for bundle in bundles:
                bundle_translations = translations_by_bundle[bundle.bundle_id]
                repaired.extend(await self.format_guard_agent.repair_bundle_async(bundle, bundle_translations))
            output_text, validation, all_translations = self._render_and_validate(
                parsed=parsed,
                segments=segments,
                translations=repaired,
            )

        if self.config.pipeline.fail_on_validation_error and not validation.passed:
            raise TranslationPipelineError("; ".join(validation.errors))

        final_output_path = output_path or self._build_output_path(input_path, target_lang)
        if write_output:
            try:
                final_output_path.parent.mkdir(parents=True, exist_ok=True)
                final_output_path.write_text(output_text, encoding="utf-8")
            except OSError as exc:
                # The translation itself succeeded; let callers salvage the
                # text instead of losing the whole run over a bad path.
                raise OutputWriteError(
                    f"写入输出文件失败: {exc}",
                    output_text=output_text,
                    output_path=final_output_path,
                    validation=validation,
                    segments=segments,
                    translations=all_translations,
                ) from exc
            log_success("Saved markdown: %s", final_output_path)

        if self.checkpoint_store is not None and validation.passed:
            self.checkpoint_store.clear(input_path, target_lang)

        provider = self.translator_agent.provider
        result = PipelineResult(
            input_path=input_path,
            output_path=final_output_path if write_output else None,
            translated_text=output_text,
            segments=segments,
            translations=all_translations,
            validation=validation,
            api_usage=provider.get_usage_summary() if provider is not None else ApiUsageSummary(),
            context=context,
        )
        memory_stats = self.memory.stats()
        if memory_stats["hits"] or memory_stats["misses"]:
            logging.info("Memory: hits=%s misses=%s", memory_stats["hits"], memory_stats["misses"])
        result.report = self.report_builder.build(result)
        return result

    def count_bundles(self, input_path: Path, target_lang: str) -> int:
        source_text = input_path.read_text(encoding="utf-8")
        parsed = self.parser.parse(source_text, input_path, target_lang)
        segments = self.extractor.extract(parsed)
        context = self.context_builder.build(parsed, segments, self.config)
        bundles = self.orchestrator.build_bundles(segments, context, self.config)
        return len(bundles)

    def _memory_fingerprint(self, source_text: str) -> str:
        document_id = ""
        scope = (self.config.memory.scope or "document").strip().lower()
        if scope != "global":
            # Same document content -> same key; different documents never
            # share entries, so short context-sensitive segments cannot bleed
            # across documents.
            document_id = hashlib.sha256(source_text.encode("utf-8")).hexdigest()[:16]
        return TranslationMemory.style_fingerprint(
            model=self.config.provider.model,
            tone=self.config.style.tone,
            audience=self.config.style.audience,
            instructions=self.config.style.instructions,
            preserve_terms=self.config.style.preserve_terms,
            document_id=document_id,
        )

    def _build_output_path(self, input_path: Path, target_lang: str) -> Path:
        normalized_lang = self._normalize_lang_for_filename(target_lang)
        file_name = self.config.output.file_suffix_template.format(stem=input_path.stem, lang=normalized_lang)
        return input_path.with_name(file_name)

    @staticmethod
    def _normalize_lang_for_filename(target_lang: str) -> str:
        return target_lang.split("-")[0].split("_")[0].lower()

    def _normalized_mode(self) -> str:
        mode = (self.config.pipeline.mode or "balanced").strip().lower()
        if mode not in {"fast", "balanced", "strict"}:
            return "balanced"
        return mode

    def _review_min_severity(self) -> str:
        mode = self._normalized_mode()
        if mode == "strict":
            return "low"
        if mode == "fast":
            return "high"
        # medium catches cross-bundle terminology drift, the most common
        # coherence defect, while still ignoring cosmetic nits.
        return "medium"

    def _should_run_review(self, bundle, translations: list[TranslationResult]) -> bool:
        if self.config.pipeline.enable_review:
            return True

        mode = self._normalized_mode()
        if mode == "fast":
            return False
        if mode == "strict":
            return True

        bundle_chars = sum(len(segment.source_text) for segment in bundle.segments)
        low_confidence = any(item.confidence < self.config.pipeline.review_confidence_threshold for item in translations)
        has_notes = any(item.notes for item in translations)
        return (
            len(bundle.segments) >= self.config.pipeline.review_min_segments
            or bundle_chars >= self.config.pipeline.review_min_bundle_chars
            or low_confidence
            or has_notes
        )

    def _should_run_format_guard(self, validation) -> bool:
        if self.config.pipeline.enable_format_guard:
            return True
        return self._normalized_mode() in {"balanced", "strict"} and not validation.passed

    def _render_and_validate(self, parsed, segments, translations):
        updated = self.mapper.apply(parsed, translations)
        updated.segments = segments  # type: ignore[attr-defined]
        output_text = self.renderer.render(updated)
        # Heading anchors change once headings are translated; remap
        # intra-document links so they keep pointing at their sections.
        output_text = rewrite_anchors(output_text, heading_pairs(segments, translations))
        validation = self.validator.validate(parsed, output_text)
        if validation.passed:
            logging.info("Validation passed")
        else:
            logging.warning("Validation: %s errors, %s warnings", len(validation.errors), len(validation.warnings))
        return output_text, validation, translations

    async def _build_glossary(self, context, segments, fingerprint: str, target_lang: str, resumed_bundles: dict) -> dict[str, str]:
        """Authoritative term -> rendering glossary shared by all bundles."""
        if self.glossary_agent is None or not self.config.pipeline.enable_glossary:
            return {}
        if self._normalized_mode() == "fast":
            return {}
        resumed_ids = {item.segment_id for items in resumed_bundles.values() for item in items}
        pending = [
            segment
            for segment in segments
            if segment.segment_id not in resumed_ids
            and self.memory.peek(segment.source_text, target_lang, fingerprint) is None
        ]
        if not pending:
            # Everything comes from memory or a checkpoint: reuse must stay free.
            return {}
        sample_text = " ".join(segment.source_text for segment in pending[:8])
        try:
            extracted = await self.glossary_agent.extract_async(context, sample_text, target_lang)
        except Exception as exc:
            logging.warning("Glossary extraction failed (%s); continuing without it", exc)
            return {}
        glossary = {term: term for term in self.config.style.preserve_terms}
        glossary.update(extracted)
        if glossary:
            logging.info("Glossary: %s term(s)", len(glossary))
        return glossary

    async def _consistency_pass(
        self,
        bundles,
        translations: list[TranslationResult],
        context,
        target_lang: str,
        fingerprint: str,
        segment_lookup: dict,
    ) -> list[TranslationResult]:
        """Rewrite segments whose term renderings drifted from the glossary."""
        if self.glossary_agent is None or not self.config.pipeline.enable_glossary:
            return translations
        if self._normalized_mode() == "fast":
            return translations
        conflicts = detect_glossary_conflicts(translations, context.glossary)
        if not conflicts:
            return translations
        canonical = canonical_glossary(conflicts)
        affected_ids: set[str] = set()
        for conflict in conflicts:
            affected_ids.update(conflict.affected_segment_ids)
        logging.info(
            "Glossary conflicts: %s",
            "; ".join(f"{conflict.term} -> {conflict.canonical}" for conflict in conflicts),
        )
        translations_by_bundle = self._translations_by_bundle(bundles, translations)
        updated_by_id: dict[str, TranslationResult] = {}
        for bundle in bundles:
            affected = [item for item in translations_by_bundle[bundle.bundle_id] if item.segment_id in affected_ids]
            if not affected:
                continue
            try:
                fixed = await self.glossary_agent.harmonize_bundle_async(bundle, context, affected, canonical)
            except Exception as exc:
                logging.warning("Harmonization failed for %s (%s); keeping original translations", bundle.bundle_id, exc)
                continue
            for item in fixed:
                if "glossary-harmonized" not in item.notes:
                    continue
                updated_by_id[item.segment_id] = item
                segment = segment_lookup.get(item.segment_id)
                if segment is not None:
                    self.memory.store(segment.source_text, target_lang, item.translated_text, fingerprint, item.confidence)
        if not updated_by_id:
            return translations
        logging.info("Harmonized %s segment(s) across %s conflict term(s)", len(updated_by_id), len(conflicts))
        return [updated_by_id.get(item.segment_id, item) for item in translations]

    def _restore_all(self, translations: list[TranslationResult], segment_lookup: dict) -> list[TranslationResult]:
        for item in translations:
            segment = segment_lookup.get(item.segment_id)
            if segment is not None:
                item.translated_text = self.protected_span_processor.restore(item.translated_text, segment)
        return translations

    async def _translate_bundles(
        self,
        bundles,
        context,
        target_lang: str,
        segment_lookup,
        mode: str,
        input_path: Path,
        semaphore: asyncio.Semaphore | None,
        bundle_progress_callback: Callable[[Path, str, str], None] | None,
        resumed_bundles: dict[str, list[TranslationResult]],
        fingerprint: str,
    ) -> list[TranslationResult]:
        if not bundles:
            return []

        limit = semaphore or asyncio.Semaphore(max(1, self.config.execution.max_parallel_translations))
        resumed_ids = set(resumed_bundles)

        async def worker(bundle: SegmentBundle) -> list[TranslationResult]:
            async with limit:
                if bundle.bundle_id in resumed_ids:
                    translations = resumed_bundles[bundle.bundle_id]
                    if bundle_progress_callback is not None:
                        bundle_progress_callback(input_path, target_lang, bundle.bundle_id)
                    return translations
                translations = await self._process_bundle(bundle, context, target_lang, segment_lookup, mode, fingerprint)
                if self.checkpoint_store is not None:
                    self.checkpoint_store.save_bundle(input_path, target_lang, bundle.bundle_id, translations)
                if bundle_progress_callback is not None:
                    bundle_progress_callback(input_path, target_lang, bundle.bundle_id)
                return translations

        logging.info("Translating %s bundles (concurrency=%s)", len(bundles), getattr(limit, "_value", "?"))
        async with asyncio.TaskGroup() as task_group:
            futures = [task_group.create_task(worker(bundle)) for bundle in bundles]
        all_translations: list[TranslationResult] = []
        for future in futures:
            all_translations.extend(future.result())
        return all_translations

    async def _process_bundle(
        self,
        bundle,
        context,
        target_lang: str,
        segment_lookup,
        mode: str,
        fingerprint: str,
    ) -> list[TranslationResult]:
        logging.info("Translating %s (%s segments)", bundle.bundle_id, len(bundle.segments))

        cached: dict[str, str] = {}
        for segment in bundle.segments:
            hit = self.memory.find(segment.source_text, target_lang, fingerprint)
            if hit is not None:
                cached[segment.segment_id] = hit

        if cached:
            logging.info("Memory reuse: %s/%s segments in %s", len(cached), len(bundle.segments), bundle.bundle_id)

        pending_segments = [segment for segment in bundle.segments if segment.segment_id not in cached]
        translations: list[TranslationResult] | None = None
        if pending_segments:
            pending_bundle = SegmentBundle(
                bundle_id=bundle.bundle_id,
                segments=pending_segments,
                summary_before=bundle.summary_before,
                summary_after=bundle.summary_after,
                style_instructions=bundle.style_instructions,
            )
            translations = await self._translate_with_retry(pending_bundle, context, target_lang)

        merged: dict[str, TranslationResult] = {item.segment_id: item for item in (translations or [])}
        for segment in bundle.segments:
            if segment.segment_id in cached:
                merged[segment.segment_id] = TranslationResult(
                    segment_id=segment.segment_id,
                    translated_text=cached[segment.segment_id],
                    notes=["translation-memory"],
                    applied_terms={},
                    confidence=1.0,
                )
        ordered = [merged[segment.segment_id] for segment in bundle.segments]

        if not pending_segments:
            # Every segment came from memory and was already reviewed in a
            # previous run; skip reflection to make reuse free.
            return ordered

        if self._should_run_review(bundle, ordered):
            logging.info("Reviewing %s (%s)", bundle.bundle_id, mode)
            ordered = await self.reviewer_agent.review_bundle_async(
                bundle,
                ordered,
                context,
                min_severity=self._review_min_severity(),
                max_rounds=self.config.pipeline.review_max_rounds,
            )

        for item in ordered:
            if item.segment_id in cached and item.notes == ["translation-memory"]:
                continue
            self.memory.store(segment_lookup[item.segment_id].source_text, target_lang, item.translated_text, fingerprint, item.confidence)

        return ordered

    async def _translate_with_retry(self, bundle, context, target_lang: str) -> list[TranslationResult]:
        last_exc: Exception | None = None
        max_attempts = 5  # Retry budget for LLM output format issues.
        for attempt in range(1, max_attempts + 1):
            try:
                return await self.translator_agent.translate_bundle_async(
                    bundle=bundle,
                    context=context,
                    target_lang=target_lang,
                )
            except Exception as exc:
                last_exc = exc
                if not self._looks_like_llm_output_format_error(exc):
                    raise
                if attempt >= max_attempts:
                    raise
                logging.warning(
                    "LLM output format invalid for bundle=%s attempt=%s/%s; retrying. error=%s",
                    bundle.bundle_id,
                    attempt,
                    max_attempts,
                    exc,
                )
        assert last_exc is not None
        raise last_exc

    @staticmethod
    def _looks_like_llm_output_format_error(exc: Exception) -> bool:
        """
        Retry only when the failure is plausibly caused by the model returning
        malformed/incomplete JSON (or otherwise missing required translation fields).
        """
        if isinstance(exc, TranslationPipelineError):
            msg = str(exc)
            return (
                "missing translations for segments" in msg
                or "Model returned no translations" in msg
            )

        # Provider-side JSON parsing failures (LLM didn't return valid JSON).
        if isinstance(exc, json.JSONDecodeError):
            return True

        # Output schema violations (e.g., missing required keys in returned items).
        if isinstance(exc, KeyError):
            missing_key = str(exc)
            return "segment_id" in missing_key or "translated_text" in missing_key

        # Output type violations (e.g., confidence is not numeric).
        if isinstance(exc, ValueError):
            # Typical message: "could not convert string to float: '...'"
            return "could not convert string to float" in str(exc)

        return False

    @staticmethod
    def _translations_by_bundle(bundles, translations: list[TranslationResult]) -> dict[str, list[TranslationResult]]:
        translation_map = {item.segment_id: item for item in translations}
        output: dict[str, list[TranslationResult]] = {}
        for bundle in bundles:
            output[bundle.bundle_id] = [translation_map[segment.segment_id] for segment in bundle.segments if segment.segment_id in translation_map]
        return output
