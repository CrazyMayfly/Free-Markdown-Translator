from __future__ import annotations

import json
import logging
from concurrent.futures import Executor, Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from src.agents.format_guard_agent import FormatGuardAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.translator_agent import TranslatorAgent
from src.core.errors import TranslationPipelineError
from src.core.orchestrator import Orchestrator
from src.core.types import PipelineResult, TranslationResult
from src.infra.config import TranslatorConfig
from src.infra.logging import log_success
from src.memory.document_context import DocumentContextBuilder
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
    ) -> None:
        self.config = config
        self.parser = parser
        self.extractor = extractor
        self.translator_agent = translator_agent
        self.reviewer_agent = reviewer_agent
        self.format_guard_agent = format_guard_agent
        self.validator = validator
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
        bundle_executor: Executor | None = None,
        bundle_progress_callback: Callable[[Path, str, str], None] | None = None,
    ) -> PipelineResult:
        logging.info("Pipeline: %s -> %s", input_path.name, target_lang)
        source_text = input_path.read_text(encoding="utf-8")
        parsed = self.parser.parse(source_text, input_path, target_lang)
        segments = self.extractor.extract(parsed)
        parsed.segments = segments  # type: ignore[attr-defined]

        context = self.context_builder.build(parsed, segments, self.config)
        bundles = self.orchestrator.build_bundles(segments, context, self.config)
        logging.info("Prepared %s segments in %s bundles", len(segments), len(bundles))

        segment_lookup = {segment.segment_id: segment for segment in segments}
        mode = self._normalized_mode()
        all_translations = self._translate_bundles(
            bundles=bundles,
            context=context,
            target_lang=target_lang,
            segment_lookup=segment_lookup,
            mode=mode,
            input_path=input_path,
            bundle_executor=bundle_executor,
            bundle_progress_callback=bundle_progress_callback,
        )

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
                repaired.extend(self.format_guard_agent.repair_bundle(bundle, bundle_translations))
            for item in repaired:
                item.translated_text = self.protected_span_processor.restore(item.translated_text, segment_lookup[item.segment_id])
            output_text, validation, all_translations = self._render_and_validate(
                parsed=parsed,
                segments=segments,
                translations=repaired,
            )

        if self.config.pipeline.fail_on_validation_error and not validation.passed:
            raise TranslationPipelineError("; ".join(validation.errors))

        final_output_path = output_path or self._build_output_path(input_path, target_lang)
        if write_output:
            final_output_path.parent.mkdir(parents=True, exist_ok=True)
            final_output_path.write_text(output_text, encoding="utf-8")
            log_success("Saved markdown: %s", final_output_path)

        result = PipelineResult(
            input_path=input_path,
            output_path=final_output_path if write_output else None,
            translated_text=output_text,
            segments=segments,
            translations=all_translations,
            validation=validation,
            api_usage=self.translator_agent.provider.get_usage_summary(),
            context=context,
        )
        result.report = self.report_builder.build(result)
        return result

    def count_bundles(self, input_path: Path, target_lang: str) -> int:
        source_text = input_path.read_text(encoding="utf-8")
        parsed = self.parser.parse(source_text, input_path, target_lang)
        segments = self.extractor.extract(parsed)
        context = self.context_builder.build(parsed, segments, self.config)
        bundles = self.orchestrator.build_bundles(segments, context, self.config)
        return len(bundles)

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
        return "low" if self._normalized_mode() == "strict" else "high"

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
        validation = self.validator.validate(parsed, output_text)
        if validation.passed:
            logging.info("Validation passed")
        else:
            logging.warning("Validation: %s errors, %s warnings", len(validation.errors), len(validation.warnings))
        return output_text, validation, translations

    def _translate_bundles(
        self,
        bundles,
        context,
        target_lang: str,
        segment_lookup,
        mode: str,
        input_path: Path,
        bundle_executor: Executor | None,
        bundle_progress_callback: Callable[[Path, str, str], None] | None,
    ) -> list[TranslationResult]:
        if not bundles:
            return []

        configured_workers = max(1, self.config.execution.max_parallel_translations)
        if configured_workers == 1 and bundle_executor is None:
            all_translations: list[TranslationResult] = []
            for index, bundle in enumerate(bundles, start=1):
                logging.info("Bundle %s/%s: translating %s (%s segments)", index, len(bundles), bundle.bundle_id, len(bundle.segments))
                translations = self._process_bundle(bundle, context, target_lang, segment_lookup, mode)
                all_translations.extend(translations)
                if bundle_progress_callback is not None:
                    bundle_progress_callback(input_path, target_lang, bundle.bundle_id)
            return all_translations

        owns_executor = bundle_executor is None
        executor = bundle_executor or ThreadPoolExecutor(
            max_workers=min(configured_workers, len(bundles)),
            thread_name_prefix="mdtx-bundle",
        )
        try:
            future_to_bundle: dict[Future[list[TranslationResult]], tuple[int, object]] = {}
            for index, bundle in enumerate(bundles, start=1):
                logging.info("Bundle %s/%s: queued %s (%s segments)", index, len(bundles), bundle.bundle_id, len(bundle.segments))
                future = executor.submit(
                    self._process_bundle,
                    bundle,
                    context,
                    target_lang,
                    segment_lookup,
                    mode,
                )
                future_to_bundle[future] = (index, bundle)

            ordered_results: dict[int, list[TranslationResult]] = {}
            try:
                for future in as_completed(future_to_bundle):
                    index, bundle = future_to_bundle[future]
                    ordered_results[index] = future.result()
                    if bundle_progress_callback is not None:
                        bundle_progress_callback(input_path, target_lang, bundle.bundle_id)
            except Exception:
                for pending_future in future_to_bundle:
                    if not pending_future.done():
                        pending_future.cancel()
                raise

            all_translations: list[TranslationResult] = []
            for index in range(1, len(bundles) + 1):
                all_translations.extend(ordered_results[index])
            return all_translations
        finally:
            if owns_executor:
                executor.shutdown(wait=True)

    def _process_bundle(
        self,
        bundle,
        context,
        target_lang: str,
        segment_lookup,
        mode: str,
    ) -> list[TranslationResult]:
        logging.info("Translating %s (%s segments)", bundle.bundle_id, len(bundle.segments))

        translations: list[TranslationResult] | None = None
        last_exc: Exception | None = None
        max_attempts = 5  # Retry budget for LLM output format issues.
        for attempt in range(1, max_attempts + 1):
            try:
                translations = self.translator_agent.translate_bundle(
                    bundle=bundle,
                    context=context,
                    target_lang=target_lang,
                )
                break
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

        if translations is None and last_exc is not None:
            raise last_exc
        assert translations is not None

        if self._should_run_review(bundle, translations):
            logging.info("Reviewing %s (%s)", bundle.bundle_id, mode)
            translations = self.reviewer_agent.review_bundle(
                bundle,
                translations,
                context,
                min_severity=self._review_min_severity(),
            )
        for item in translations:
            item.translated_text = self.protected_span_processor.restore(item.translated_text, segment_lookup[item.segment_id])
        return translations

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
