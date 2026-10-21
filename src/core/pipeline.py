from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections.abc import Callable
from pathlib import Path

from src.agents.brief_agent import BriefAgent
from src.agents.editor_agent import EditorAgent
from src.agents.format_guard_agent import FormatGuardAgent
from src.agents.glossary_agent import GlossaryAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.translator_agent import TranslatorAgent
from src.core.errors import OutputWriteError, TranslationPipelineError
from src.core.glossary import canonical_glossary, detect_glossary_conflicts
from src.core.modes import normalize_mode, profile_for
from src.core.orchestrator import Orchestrator
from src.core.tokens import estimate_tokens
from src.core.types import (
    ApiUsageSummary,
    DocumentBrief,
    MemoryStore,
    PipelineResult,
    SegmentBundle,
    TranslationOutcome,
    TranslationResult,
)
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
from src.validators.semantic_sentinel import SentinelFinding, run_sentinels

_ANCHOR_EXAMPLE_LIMIT = 3


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
        glossary_store=None,
        editor_agent: EditorAgent | None = None,
        brief_agent: BriefAgent | None = None,
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
        self.glossary_store = glossary_store
        self.editor_agent = editor_agent
        self.brief_agent = brief_agent
        self.context_builder = DocumentContextBuilder()
        self.orchestrator = Orchestrator()
        self.protected_span_processor = ProtectedSpanProcessor()
        self.mapper = AstMapper()
        self.renderer = MarkdownRenderer()
        self.report_builder = OutputReportBuilder()
        self._sentinel_findings: list[SentinelFinding] = []

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
        stage_callback: Callable[[str, str], None] | None = None,
    ) -> PipelineResult:
        logging.info("Pipeline: %s -> %s", input_path.name, target_lang)
        if stage_callback:
            stage_callback("parse", "解析与分块")
        source_text = input_path.read_text(encoding="utf-8")
        parsed = self.parser.parse(source_text, input_path, target_lang)
        segments = self.extractor.extract(parsed)
        parsed.segments = segments  # type: ignore[attr-defined]

        context = self.context_builder.build(parsed, segments, self.config)
        fingerprint = self._memory_fingerprint(source_text)
        style_key = self._style_fingerprint()
        mode = self._normalized_mode()
        self._sentinel_findings = []
        resumed_bundles = self.checkpoint_store.load(input_path, target_lang) if self.checkpoint_store is not None else {}
        if stage_callback:
            stage_callback("brief", "生成文档摘要")
        context.brief = await self._build_brief(context, segments, target_lang, source_text)
        if stage_callback:
            stage_callback("glossary", "抽取术语表")
        context.glossary = await self._build_glossary(context, segments, fingerprint, target_lang, resumed_bundles)
        bundles = self.orchestrator.build_bundles(segments, context, self.config)
        # The bundler may split one oversized block into several segments that
        # share a source line range. Everything downstream (rendering, memory,
        # review, API results) works on that final segment list.
        segments = [segment for bundle in bundles for segment in bundle.segments]
        parsed.segments = segments  # type: ignore[attr-defined]
        logging.info("Prepared %s segments in %s bundles", len(segments), len(bundles))
        if resumed_bundles:
            logging.info("Resuming %s: %s/%s bundles already completed", input_path.name, len(resumed_bundles), len(bundles))

        segment_lookup = {segment.segment_id: segment for segment in segments}
        if stage_callback:
            stage_callback("translate", "翻译文本包")
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
            style_key=style_key,
        )
        all_translations = await self._consistency_pass(bundles, all_translations, context, target_lang, fingerprint, style_key, segment_lookup)
        if self._should_run_final_edit() and self.editor_agent is not None:
            logging.info("Running document-level final edit (quality mode)")
            all_translations = await self.editor_agent.edit_document_async(
                segments,
                all_translations,
                context,
                max_segments=self.config.pipeline.final_edit_max_segments,
            )
        all_translations = self._restore_all(all_translations, segment_lookup)
        self._record_term_appearances(all_translations, context, target_lang)
        if stage_callback:
            stage_callback("render", "渲染与写文件")

        output_text, validation, all_translations = self._render_and_validate(
            parsed=parsed,
            segments=segments,
            translations=all_translations,
        )
        if not validation.passed and self._should_run_format_guard(validation):
            logging.warning("Validation failed, running guard (mode=%s errors=%s)", mode, len(validation.errors))
            translations_by_bundle = self._translations_by_bundle(bundles, all_translations)
            guard_limit = semaphore or asyncio.Semaphore(max(1, self.config.execution.max_parallel_translations))

            async def guard_worker(bundle, bundle_translations):
                async with guard_limit:
                    return await self.format_guard_agent.repair_bundle_async(bundle, bundle_translations)

            repaired_lists = await asyncio.gather(
                *(guard_worker(bundle, translations_by_bundle[bundle.bundle_id]) for bundle in bundles)
            )
            repaired = [item for repaired_list in repaired_lists for item in repaired_list]
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
        usage = provider.get_usage_summary() if provider is not None else ApiUsageSummary()
        reviewer_provider = self.reviewer_agent.provider
        if reviewer_provider is not None and reviewer_provider is not provider:
            # Review may run on a dedicated model; its tokens belong in the bill.
            usage.merge(reviewer_provider.get_usage_summary())
        brief_provider = self.brief_agent.provider if self.brief_agent is not None else None
        if brief_provider is not None and brief_provider is not provider and brief_provider is not reviewer_provider:
            usage.merge(brief_provider.get_usage_summary())
        result = PipelineResult(
            input_path=input_path,
            output_path=final_output_path if write_output else None,
            translated_text=output_text,
            segments=segments,
            translations=all_translations,
            validation=validation,
            api_usage=usage,
            context=context,
        )
        memory_stats = self.memory.stats()
        if memory_stats["hits"] or memory_stats["misses"]:
            logging.info("Memory: hits=%s misses=%s", memory_stats["hits"], memory_stats["misses"])
        result.report = self.report_builder.build(result)
        if self._sentinel_findings:
            result.report["sentinel_findings"] = [
                {"segment_id": finding.segment_id, "check": finding.check, "detail": finding.detail}
                for finding in self._sentinel_findings
            ]
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

    def memory_fingerprint_for(self, source_text: str) -> str:
        """Public wrapper so callers (e.g. --eval feedback) share the key."""
        return self._memory_fingerprint(source_text)

    def _style_fingerprint(self) -> str:
        return TranslationMemory.style_fingerprint(
            model=self.config.provider.model,
            tone=self.config.style.tone,
            audience=self.config.style.audience,
            instructions=self.config.style.instructions,
            preserve_terms=self.config.style.preserve_terms,
        )

    def _build_output_path(self, input_path: Path, target_lang: str) -> Path:
        normalized_lang = self._normalize_lang_for_filename(target_lang)
        file_name = self.config.output.file_suffix_template.format(stem=input_path.stem, lang=normalized_lang)
        return input_path.with_name(file_name)

    @staticmethod
    def _normalize_lang_for_filename(target_lang: str) -> str:
        return target_lang.split("-")[0].split("_")[0].lower()

    def _normalized_mode(self) -> str:
        return normalize_mode(self.config.pipeline.mode)

    def _review_min_severity(self) -> str:
        mode = self._normalized_mode()
        if mode == "quality":
            return "low"
        if mode == "fast":
            return "high"
        # medium catches cross-bundle terminology drift, the most common
        # coherence defect, while still ignoring cosmetic nits.
        return "medium"

    def _should_run_review(self, bundle, translations: list[TranslationResult]) -> bool:
        mode = self._normalized_mode()
        if mode == "fast":
            return False
        if self.config.pipeline.enable_review:
            return True
        if mode == "quality":
            return True

        bundle_tokens = sum(estimate_tokens(segment.source_text) for segment in bundle.segments)
        low_confidence = any(item.confidence < self.config.pipeline.review_confidence_threshold for item in translations)
        has_notes = any(item.notes for item in translations)
        return bundle_tokens >= self.config.pipeline.review_min_bundle_tokens or low_confidence or has_notes

    def _should_run_format_guard(self, validation) -> bool:
        if self.config.pipeline.enable_format_guard:
            return True
        return self._normalized_mode() in {"balanced", "quality"} and not validation.passed

    def _should_run_final_edit(self) -> bool:
        return (
            self.editor_agent is not None
            and self.config.pipeline.enable_final_edit
            and self._normalized_mode() == "quality"
        )

    def _render_and_validate(self, parsed, segments, translations):
        updated = self.mapper.apply(parsed, translations)
        spans = updated.metadata.pop("segment_spans", {})
        for segment in segments:
            span = spans.get(segment.segment_id)
            if span is not None:
                segment.metadata["output_start"], segment.metadata["output_end"] = span
            else:
                segment.metadata.pop("output_start", None)
                segment.metadata.pop("output_end", None)
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

    async def _build_brief(self, context, segments, target_lang: str, source_text: str = "") -> DocumentBrief:
        if self.brief_agent is None:
            return DocumentBrief()
        try:
            brief = await self.brief_agent.generate_async(
                context,
                segments,
                target_lang,
                mode=self._normalized_mode(),
                source_text=source_text,
            )
        except Exception as exc:
            logging.warning("Document brief failed (%s); using deterministic context", exc)
            return DocumentBrief()
        if not self.config.pipeline.enable_glossary:
            brief.glossary = {}
        return brief

    async def _build_glossary(self, context, segments, fingerprint: str, target_lang: str, resumed_bundles: dict) -> dict[str, str]:
        """Authoritative term -> rendering glossary shared by all bundles.

        Precedence: persisted user entries > preserve_terms (config) >
        persisted model entries > brief terms > legacy sampler terms.
        The Brief pass already read the whole document, so the legacy sampler
        only runs as a fallback (or when the brief produced no terms).
        """
        if not self.config.pipeline.enable_glossary:
            return {term: term for term in self.config.style.preserve_terms}

        brief = getattr(context, "brief", None)
        extracted: dict[str, str] = dict(brief.glossary) if brief is not None else {}
        if not extracted and self._normalized_mode() != "fast" and self.glossary_agent is not None:
            min_confidence = self.config.memory.reuse_min_confidence
            resumed_ids = {item.segment_id for items in resumed_bundles.values() for item in items}
            pending = [
                segment
                for segment in segments
                if segment.segment_id not in resumed_ids
                and self.memory.peek(segment.source_text, target_lang, fingerprint, min_confidence) is None
            ]
            if pending:
                sample_text = " ".join(segment.source_text for segment in pending[:8])
                try:
                    extracted = await self.glossary_agent.extract_async(context, sample_text, target_lang)
                except Exception as exc:
                    logging.warning("Glossary extraction failed (%s); continuing without it", exc)
                    extracted = {}

        if self.glossary_store is not None:
            for term, rendering in extracted.items():
                self.glossary_store.upsert(target_lang, term, rendering, origin="model")
        glossary: dict[str, str] = {}
        if self.glossary_store is not None:
            glossary.update(self.glossary_store.load(target_lang))
        glossary.update({term: term for term in self.config.style.preserve_terms})
        for term, rendering in extracted.items():
            glossary.setdefault(term, rendering)
        if glossary:
            logging.info("Glossary: %s term(s)%s", len(glossary), " (brief)" if brief and brief.glossary else "")
        return glossary

    async def _consistency_pass(
        self,
        bundles,
        translations: list[TranslationResult],
        context,
        target_lang: str,
        fingerprint: str,
        style_key: str,
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
                if segment is not None and not segment.metadata.get("split_parent"):
                    self.memory.store(segment.source_text, target_lang, item.translated_text, fingerprint, item.confidence, style_key)
        if self.glossary_store is not None:
            # Canonical renderings become the durable answer for next runs.
            for term, rendering in canonical.items():
                self.glossary_store.upsert(target_lang, term, rendering, origin="model")
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

    def _record_term_appearances(self, translations: list[TranslationResult], context, target_lang: str) -> None:
        """Count one document's occurrence of each term for the auto-glossary.

        A term "appears in a document" if the model reported it in
        ``applied_terms`` or it was in the document glossary. This drives the
        pending -> active promotion (>= ACTIVATE_AFTER_DOCS distinct docs).
        """
        if self.glossary_store is None:
            return
        terms: set[str] = set()
        for item in translations:
            for term in (item.applied_terms or {}):
                if term:
                    terms.add(str(term).strip())
        for term in getattr(context, "glossary", {}) or {}:
            if term:
                terms.add(str(term).strip())
        self.glossary_store.record_appearance(target_lang, terms)

    @staticmethod
    def _is_anchor_bundle(index: int, bundle: SegmentBundle, bundles: list[SegmentBundle]) -> bool:
        if index == 0:
            return True
        if not bundle.segments or bundle.segments[0].node_type != "heading":
            return False
        # A section that fits in one bundle needs no anchor: it already has the
        # whole section in front of the model. Only the first piece of a
        # section split across bundles anchors its continuation bundles.
        if index + 1 >= len(bundles):
            return False
        next_bundle = bundles[index + 1]
        return bool(next_bundle.segments and next_bundle.segments[0].node_type != "heading")

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
        style_key: str,
    ) -> list[TranslationResult]:
        if not bundles:
            return []

        limit = semaphore or asyncio.Semaphore(max(1, self.config.execution.max_parallel_translations))
        resumed_ids = set(resumed_bundles)
        results_by_bundle: dict[str, list[TranslationResult]] = {}

        def attach_anchor_context(bundle: SegmentBundle, anchor: SegmentBundle | None, anchor_results: dict) -> None:
            if anchor is None or anchor.bundle_id not in anchor_results or bundle.anchor_translations:
                return
            anchor_segments = anchor.segments
            anchor_items = anchor_results[anchor.bundle_id]
            bundle.anchor_translations = [
                {"source": segment.source_text[:240], "text": item.translated_text[:240]}
                for segment, item in list(zip(anchor_segments, anchor_items, strict=False))[:_ANCHOR_EXAMPLE_LIMIT]
            ]

        async def worker(bundle: SegmentBundle) -> list[TranslationResult]:
            async with limit:
                if bundle.bundle_id in resumed_ids:
                    translations = resumed_bundles[bundle.bundle_id]
                    if bundle_progress_callback is not None:
                        bundle_progress_callback(input_path, target_lang, bundle.bundle_id)
                    return translations
                translations = await self._process_bundle(bundle, context, target_lang, segment_lookup, mode, fingerprint, style_key)
                if self.checkpoint_store is not None:
                    self.checkpoint_store.save_bundle(input_path, target_lang, bundle.bundle_id, translations)
                if bundle_progress_callback is not None:
                    bundle_progress_callback(input_path, target_lang, bundle.bundle_id)
                return translations

        anchor_scheduling = self.config.pipeline.enable_anchor_scheduling and mode != "fast"
        anchor_results: dict[str, list[TranslationResult]] = {}
        anchor_of: dict[str, SegmentBundle | None] = {}
        current_anchor: SegmentBundle | None = None
        current_section: object = None
        for index, bundle in enumerate(bundles):
            section = bundle.segments[-1].metadata.get("section_id") if bundle.segments else None
            if self._is_anchor_bundle(index, bundle, bundles):
                current_anchor = bundle
                current_section = section
            elif section != current_section:
                current_anchor = None
            anchor_of[bundle.bundle_id] = current_anchor

        logging.info(
            "Translating %s bundles (concurrency=%s, anchors=%s)",
            len(bundles),
            getattr(limit, "_value", "?"),
            sum(1 for index, bundle in enumerate(bundles) if self._is_anchor_bundle(index, bundle, bundles)) if anchor_scheduling else "off",
        )
        if anchor_scheduling:
            # Phase 1: each section's anchor bundle runs sequentially in
            # document order, so its real translations exist as context.
            for index, bundle in enumerate(bundles):
                if self._is_anchor_bundle(index, bundle, bundles):
                    anchor_results[bundle.bundle_id] = await worker(bundle)
            # Phase 2: everything else runs in parallel carrying the anchor.
            others = [bundle for index, bundle in enumerate(bundles) if not self._is_anchor_bundle(index, bundle, bundles)]
            async with asyncio.TaskGroup() as task_group:
                futures = [
                    task_group.create_task(self._anchored_worker(worker, bundle, anchor_of.get(bundle.bundle_id), anchor_results, attach_anchor_context))
                    for bundle in others
                ]
            for bundle, future in zip(others, futures, strict=False):
                results_by_bundle[bundle.bundle_id] = future.result()
            for bundle_id, translations in anchor_results.items():
                results_by_bundle[bundle_id] = translations
        else:
            async with asyncio.TaskGroup() as task_group:
                futures = [task_group.create_task(worker(bundle)) for bundle in bundles]
            for bundle, future in zip(bundles, futures, strict=False):
                results_by_bundle[bundle.bundle_id] = future.result()
        return [item for bundle in bundles for item in results_by_bundle[bundle.bundle_id]]

    @staticmethod
    async def _anchored_worker(worker, bundle, anchor, anchor_results, attach_anchor_context) -> list[TranslationResult]:
        attach_anchor_context(bundle, anchor, anchor_results)
        return await worker(bundle)

    async def _process_bundle(
        self,
        bundle,
        context,
        target_lang: str,
        segment_lookup,
        mode: str,
        fingerprint: str,
        style_key: str,
    ) -> list[TranslationResult]:
        logging.info("Translating %s (%s segments)", bundle.bundle_id, len(bundle.segments))

        min_confidence = self.config.memory.reuse_min_confidence
        cached: dict[str, str] = {}
        for segment in bundle.segments:
            hit = self.memory.find(segment.source_text, target_lang, fingerprint, min_confidence)
            if hit is not None:
                cached[segment.segment_id] = hit

        pending_segments = [segment for segment in bundle.segments if segment.segment_id not in cached]

        # Fuzzy layer: near-identical sources are reused directly; close
        # matches become few-shot examples inside the prompt.
        fuzzy_reuse: dict[str, str] = {}
        similar_examples: dict[str, list[dict[str, str]]] = {}
        if self.config.memory.fuzzy_examples and pending_segments:
            for segment in pending_segments:
                candidates = self.memory.find_similar(
                    segment.source_text,
                    target_lang,
                    style_key,
                    limit=2,
                    min_score=self.config.memory.fuzzy_example_threshold,
                )
                if not candidates:
                    continue
                best_score, _best_source, best_translation = candidates[0]
                if best_score >= self.config.memory.fuzzy_reuse_threshold:
                    fuzzy_reuse[segment.segment_id] = best_translation
                else:
                    similar_examples[segment.segment_id] = [
                        {"source": source[:240], "translation": translated[:240]}
                        for score, source, translated in candidates
                        if score >= self.config.memory.fuzzy_example_threshold
                    ]
            pending_segments = [segment for segment in pending_segments if segment.segment_id not in fuzzy_reuse]

        if cached or fuzzy_reuse:
            logging.info(
                "Memory reuse: %s exact + %s fuzzy segments in %s",
                len(cached),
                len(fuzzy_reuse),
                bundle.bundle_id,
            )

        translations: list[TranslationResult] | None = None
        if pending_segments:
            pending_bundle = SegmentBundle(
                bundle_id=bundle.bundle_id,
                segments=pending_segments,
                summary_before=bundle.summary_before,
                summary_after=bundle.summary_after,
                style_instructions=bundle.style_instructions,
                similar_examples=similar_examples,
                anchor_translations=bundle.anchor_translations,
            )
            outcome = await self._translate_with_retry(pending_bundle, context, target_lang, mode)
            if outcome.context_requests and self.config.pipeline.enable_context_pull and mode != "fast":
                enriched = self._apply_context_requests(pending_bundle, outcome.context_requests, target_lang, style_key)
                if enriched is not None:
                    logging.info("Context pull: %s request(s) in %s; re-translating with deeper context", len(outcome.context_requests), bundle.bundle_id)
                    outcome = await self._translate_with_retry(enriched, context, target_lang, mode)
            translations = outcome.translations

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
            elif segment.segment_id in fuzzy_reuse:
                merged[segment.segment_id] = TranslationResult(
                    segment_id=segment.segment_id,
                    translated_text=fuzzy_reuse[segment.segment_id],
                    notes=["translation-memory-fuzzy"],
                    applied_terms={},
                    confidence=0.9,
                )
        ordered = [merged[segment.segment_id] for segment in bundle.segments]

        if not pending_segments:
            # Every segment came from memory and was already reviewed in a
            # previous run; skip reflection to make reuse free.
            return ordered

        sentinel_findings: list[SentinelFinding] = []
        if self.config.pipeline.enable_sentinels:
            sentinel_findings = run_sentinels(
                bundle.segments,
                ordered,
                min_ratio=self.config.pipeline.sentinel_min_length_ratio,
                max_ratio=self.config.pipeline.sentinel_max_length_ratio,
            )
            for finding in sentinel_findings:
                self._sentinel_findings.append(finding)
                item = merged.get(finding.segment_id)
                if item is not None:
                    note = f"sentinel:{finding.check}"
                    if note not in item.notes:
                        item.notes.append(note)

        if self._should_run_review(bundle, ordered) or (sentinel_findings and mode != "fast"):
            profile = profile_for(mode)
            scope_ids: set[str] | None = None
            if profile.review == "targeted":
                # Review the suspicious segments first; only a bundle that
                # crosses the token threshold without any specific finding
                # falls back to a whole-bundle review.
                suspicious = {finding.segment_id for finding in sentinel_findings}
                suspicious.update(
                    item.segment_id
                    for item in ordered
                    if item.confidence < self.config.pipeline.review_confidence_threshold or item.notes
                )
                if suspicious:
                    scope_ids = suspicious
            logging.info(
                "Reviewing %s (%s%s%s)",
                bundle.bundle_id,
                mode,
                f", {len(sentinel_findings)} sentinel finding(s)" if sentinel_findings else "",
                f", scope={len(scope_ids)}" if scope_ids else "",
            )
            ordered = await self.reviewer_agent.review_bundle_async(
                bundle,
                ordered,
                context,
                min_severity=self._review_min_severity(),
                max_rounds=self.config.pipeline.review_max_rounds,
                scope_ids=scope_ids,
            )

        for item in ordered:
            if item.notes in (["translation-memory"], ["translation-memory-fuzzy"]):
                continue
            segment = segment_lookup[item.segment_id]
            if segment.metadata.get("split_parent"):
                # Fragments are an implementation detail of line splitting;
                # remembering them would poison later runs with partial units.
                continue
            self.memory.store(
                segment.source_text,
                target_lang,
                item.translated_text,
                fingerprint,
                item.confidence,
                style_key,
            )

        return ordered

    def _apply_context_requests(self, bundle: SegmentBundle, requests: list[dict], target_lang: str, style_key: str) -> SegmentBundle | None:
        """Answer the model's pull-style context requests (one extra round).

        similar_translations triggers a deeper translation-memory search
        (lower threshold, more hits); neighbour_translations is already
        covered by anchor context when anchors are attached.
        """
        segments_by_id = {segment.segment_id: segment for segment in bundle.segments}
        enriched_similar = dict(bundle.similar_examples)
        changed = False
        for request in requests:
            segment = segments_by_id.get(str(request.get("segment_id", "")))
            if segment is None:
                continue
            need = str(request.get("need", ""))
            if need != "similar_translations":
                continue
            hits = self.memory.find_similar(segment.source_text, target_lang, style_key, limit=5, min_score=0.5)
            if not hits:
                continue
            enriched_similar[segment.segment_id] = [
                {"source": source[:240], "translation": translated[:240]}
                for _score, source, translated in hits
            ]
            changed = True
        if not changed:
            return None
        return SegmentBundle(
            bundle_id=bundle.bundle_id,
            segments=bundle.segments,
            summary_before=bundle.summary_before,
            summary_after=bundle.summary_after,
            style_instructions=bundle.style_instructions,
            similar_examples=enriched_similar,
            anchor_translations=bundle.anchor_translations,
        )

    async def _translate_with_retry(self, bundle, context, target_lang: str, mode: str = "balanced") -> TranslationOutcome:
        last_exc: Exception | None = None
        max_attempts = 5  # Retry budget for LLM output format issues.
        for attempt in range(1, max_attempts + 1):
            try:
                return await self.translator_agent.translate_bundle_async(
                    bundle=bundle,
                    context=context,
                    target_lang=target_lang,
                    mode=mode,
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
