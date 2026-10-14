from __future__ import annotations

import copy
import json
import logging
import threading
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path

from src.agents.format_guard_agent import FormatGuardAgent
from src.agents.judge_agent import JudgeAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.translator_agent import TranslatorAgent
from src.core.pipeline import TranslationPipeline
from src.core.orchestrator import Orchestrator
from src.core.types import ApiUsageSummary
from src.infra.config import TranslatorConfig
from src.infra.logging import log_success, log_task_context
from src.llm.client import OpenAIProvider
from src.memory.document_context import DocumentContextBuilder
from src.parser.markdown_parser import MarkdownParser
from src.parser.segment_extractor import SegmentExtractor
from src.validators.markdown_validator import MarkdownValidator
from tqdm import tqdm


def _build_provider(config: TranslatorConfig):
    if config.provider.name == "openai":
        return OpenAIProvider(
            base_url=config.provider.base_url,
            api_key=config.provider.api_key,
            api_key_env=config.provider.api_key_env,
            model=config.provider.model,
            temperature=config.provider.temperature,
            max_tokens=config.provider.max_tokens,
            structured_outputs=config.provider.structured_outputs,
        )
    raise ValueError(f"Provider {config.provider.name} is not implemented.")


def build_pipeline(config: TranslatorConfig) -> TranslationPipeline:
    provider = _build_provider(config)
    return TranslationPipeline(
        config=config,
        parser=MarkdownParser(),
        extractor=SegmentExtractor(),
        translator_agent=TranslatorAgent(provider),
        reviewer_agent=ReviewerAgent(provider if config.pipeline.enable_review else None),
        format_guard_agent=FormatGuardAgent(provider if config.pipeline.enable_format_guard else None),
        validator=MarkdownValidator(),
    )


def _looks_like_output_path(value: str) -> bool:
    return value.endswith(".md") or "\\" in value or "/" in value


@dataclass(frozen=True)
class TranslationSource:
    input_path: Path
    relative_output_path: Path


@dataclass(frozen=True)
class TranslationTask:
    index: int
    total: int
    source: TranslationSource
    target_lang: str
    output_path: Path | None

    @property
    def label(self) -> str:
        return f"{self.index}/{self.total} {self.source.relative_output_path} -> {self.target_lang}"


def _resolve_parallel_workers(config: TranslatorConfig, task_count: int) -> int:
    configured = max(1, config.execution.max_parallel_translations)
    return min(configured, max(1, task_count))


def _resolve_bundle_workers(config: TranslatorConfig) -> int:
    return max(1, config.execution.max_parallel_translations)


class BundleProgressTracker:
    def __init__(self, total_bundles: int) -> None:
        self._lock = threading.Lock()
        self._bar = tqdm(
            total=total_bundles,
            desc="Translating bundles",
            unit="bundle",
            dynamic_ncols=True,
        )

    def update(self, input_path: Path, target_lang: str, bundle_id: str) -> None:
        with self._lock:
            self._bar.set_postfix_str(f"{input_path.name} -> {target_lang} [{bundle_id}]")
            self._bar.update(1)

    def close(self) -> None:
        with self._lock:
            self._bar.close()


def _resolve_relative_output_path(input_path: Path, source_root: Path | None = None) -> Path:
    resolved_input = input_path.resolve()
    cwd = Path.cwd().resolve()
    try:
        return resolved_input.relative_to(cwd)
    except ValueError:
        pass

    if source_root is not None:
        resolved_root = source_root.resolve()
        try:
            return Path(source_root.name) / resolved_input.relative_to(resolved_root)
        except ValueError:
            pass

    return Path(input_path.name)


def _collect_translation_sources(paths: list[str], match_pattern: str) -> list[TranslationSource]:
    sources: list[TranslationSource] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            raise FileNotFoundError(f"Input path does not exist: {path}")
        if path.is_file():
            sources.append(
                TranslationSource(
                    input_path=path,
                    relative_output_path=_resolve_relative_output_path(path),
                )
            )
            continue

        matched_files = sorted(candidate for candidate in path.rglob(match_pattern) if candidate.is_file())
        for candidate in matched_files:
            sources.append(
                TranslationSource(
                    input_path=candidate,
                    relative_output_path=_resolve_relative_output_path(candidate, source_root=path),
                )
            )
    if not sources:
        raise ValueError(f"No input files matched pattern: {match_pattern}")
    return sources


def _build_task_output_path(source: TranslationSource, target_lang: str, output_dir: Path, config: TranslatorConfig) -> Path:
    normalized_lang = TranslationPipeline._normalize_lang_for_filename(target_lang)
    file_name = config.output.file_suffix_template.format(stem=source.relative_output_path.stem, lang=normalized_lang)
    return output_dir / source.relative_output_path.parent / file_name


def _build_translation_tasks(
    sources: list[TranslationSource],
    target_langs: list[str],
    output_dir: Path,
    config: TranslatorConfig,
) -> list[TranslationTask]:
    total = len(sources) * len(target_langs)
    tasks: list[TranslationTask] = []
    index = 1
    for source in sources:
        for target_lang in target_langs:
            tasks.append(
                TranslationTask(
                    index=index,
                    total=total,
                    source=source,
                    target_lang=target_lang,
                    output_path=_build_task_output_path(source, target_lang, output_dir, config),
                )
            )
            index += 1
    return tasks


def _run_translation_task(task: TranslationTask, config: TranslatorConfig):
    with log_task_context(task.label):
        pipeline = build_pipeline(copy.deepcopy(config))
        logging.info("Task start: %s -> %s", task.source.input_path, task.target_lang)
        result = pipeline.run(task.source.input_path, task.target_lang, write_output=True, output_path=task.output_path)
        log_success("Task done: %s", result.output_path)
        return task, result


def _count_task_bundles(task: TranslationTask, config: TranslatorConfig, cache: dict[Path, int] | None = None) -> int:
    # Bundle count depends only on the source file, not the target language,
    # so repeated file x language tasks can share one parse.
    if cache is not None:
        key = task.source.input_path.resolve()
        if key in cache:
            return cache[key]

    parser = MarkdownParser()
    extractor = SegmentExtractor()
    context_builder = DocumentContextBuilder()
    orchestrator = Orchestrator()

    source_text = task.source.input_path.read_text(encoding="utf-8")
    parsed = parser.parse(source_text, task.source.input_path, task.target_lang)
    segments = extractor.extract(parsed)
    context = context_builder.build(parsed, segments, config)
    bundles = orchestrator.build_bundles(segments, context, config)
    count = len(bundles)
    if cache is not None:
        cache[key] = count
    return count


def _log_task_token_usage(task: TranslationTask, usage: ApiUsageSummary) -> None:
    logging.info(
        "Tokens %s -> %s: prompt=%s completion=%s total=%s calls=%s",
        task.source.input_path.name,
        task.target_lang,
        usage.total.prompt_tokens,
        usage.total.completion_tokens,
        usage.total.total_tokens,
        usage.total.call_count,
    )
    if usage.by_call_label:
        parts = []
        for call_label in sorted(usage.by_call_label):
            item = usage.by_call_label[call_label]
            parts.append(
                f"{call_label}(c={item.call_count}, p={item.prompt_tokens}, o={item.completion_tokens}, t={item.total_tokens})"
            )
        logging.info(
            "Token stages %s -> %s: %s",
            task.source.input_path.name,
            task.target_lang,
            "; ".join(parts),
        )


def _log_total_token_usage(usage: ApiUsageSummary, task_count: int) -> None:
    logging.info(
        "Job tokens: tasks=%s prompt=%s completion=%s total=%s calls=%s",
        task_count,
        usage.total.prompt_tokens,
        usage.total.completion_tokens,
        usage.total.total_tokens,
        usage.total.call_count,
    )
    if usage.by_call_label:
        parts = []
        for call_label in sorted(usage.by_call_label):
            item = usage.by_call_label[call_label]
            parts.append(
                f"{call_label}(c={item.call_count}, p={item.prompt_tokens}, o={item.completion_tokens}, t={item.total_tokens})"
            )
        logging.info("Job token stages: %s", "; ".join(parts))


def _run_translation_task_with_shared_bundle_executor(
    task: TranslationTask,
    config: TranslatorConfig,
    bundle_executor: ThreadPoolExecutor,
    progress_tracker: BundleProgressTracker | None,
):
    with log_task_context(task.label):
        pipeline = build_pipeline(copy.deepcopy(config))
        logging.info("Task start: %s -> %s", task.source.input_path, task.target_lang)
        result = pipeline.run(
            task.source.input_path,
            task.target_lang,
            write_output=True,
            output_path=task.output_path,
            bundle_executor=bundle_executor,
            bundle_progress_callback=progress_tracker.update if progress_tracker is not None else None,
        )
        log_success("Task done: %s", result.output_path)
        return task, result


def translate_command(
    paths: list[str],
    target_langs: list[str],
    config: TranslatorConfig,
    output_dir: str | None = None,
    match_pattern: str | None = None,
) -> int:
    if any(_looks_like_output_path(lang) for lang in target_langs):
        raise ValueError("`--to` expects language codes, not file paths. Use `--output` to specify an output directory.")

    resolved_match_pattern = match_pattern or config.input.file_pattern
    resolved_output_dir = Path(output_dir or config.output.directory)
    sources = _collect_translation_sources(paths, resolved_match_pattern)
    tasks = _build_translation_tasks(sources, target_langs, resolved_output_dir, config)
    task_workers = _resolve_parallel_workers(config, len(tasks))
    bundle_workers = _resolve_bundle_workers(config)
    bundle_count_cache: dict[Path, int] = {}
    total_bundles = sum(_count_task_bundles(task, config, bundle_count_cache) for task in tasks)
    logging.info(
        "Job start: files=%s targets=%s tasks=%s bundles=%s workers=%s/%s",
        len(sources),
        ", ".join(target_langs),
        len(tasks),
        total_bundles,
        task_workers,
        bundle_workers,
    )
    total_usage = ApiUsageSummary()

    if task_workers == 1 and bundle_workers == 1:
        progress_tracker = BundleProgressTracker(total_bundles)
        try:
            for task in tasks:
                pipeline = build_pipeline(copy.deepcopy(config))
                _, result = task, pipeline.run(
                    task.source.input_path,
                    task.target_lang,
                    write_output=True,
                    output_path=task.output_path,
                    bundle_progress_callback=progress_tracker.update,
                )
                total_usage.merge(result.api_usage)
                _log_task_token_usage(task, result.api_usage)
                if config.output.write_report and result.output_path is not None:
                    report_path = result.output_path.with_suffix(result.output_path.suffix + ".report.json")
                    report_path.write_text(json.dumps(result.report, ensure_ascii=False, indent=2), encoding="utf-8")
                    log_success("Saved report: %s", report_path)
        finally:
            progress_tracker.close()
        _log_total_token_usage(total_usage, len(tasks))
        return 0

    completed = 0
    future_to_task = {}
    progress_tracker = BundleProgressTracker(total_bundles)
    try:
        with ThreadPoolExecutor(max_workers=task_workers, thread_name_prefix="mdtx-translate") as executor:
            with ThreadPoolExecutor(max_workers=bundle_workers, thread_name_prefix="mdtx-bundle") as bundle_executor:
                for task in tasks:
                    future_to_task[
                        executor.submit(
                            _run_translation_task_with_shared_bundle_executor,
                            task,
                            config,
                            bundle_executor,
                            progress_tracker,
                        )
                    ] = task

                pending = set(future_to_task)
                while pending:
                    done, pending = wait(pending, return_when=FIRST_EXCEPTION)
                    for future in done:
                        task = future_to_task[future]
                        try:
                            _, result = future.result()
                        except Exception:
                            for pending_future in pending:
                                pending_future.cancel()
                            logging.error(
                                "Translation task failed: source=%s target=%s",
                                task.source.input_path,
                                task.target_lang,
                            )
                            raise

                        completed += 1
                        total_usage.merge(result.api_usage)
                        _log_task_token_usage(task, result.api_usage)
                        if config.output.write_report and result.output_path is not None:
                            report_path = result.output_path.with_suffix(result.output_path.suffix + ".report.json")
                            report_path.write_text(json.dumps(result.report, ensure_ascii=False, indent=2), encoding="utf-8")
                            log_success(
                                "[%s/%s] Saved report: %s",
                                completed,
                                len(tasks),
                                report_path,
                            )
                        log_success(
                            "[%s/%s] Completed: %s -> %s",
                            completed,
                            len(tasks),
                            task.source.input_path,
                            result.output_path,
                        )
    finally:
        progress_tracker.close()
    _log_total_token_usage(total_usage, len(tasks))
    return 0


def validate_command(path: str, config: TranslatorConfig) -> int:
    parser = MarkdownParser()
    validator = MarkdownValidator()
    input_path = Path(path)
    source_text = input_path.read_text(encoding="utf-8")
    parsed = parser.parse(source_text, input_path, config.target_languages[0])
    report = validator.validate(parsed, source_text)
    output = {
        "input_path": str(input_path),
        "validation_passed": report.passed,
        "errors": report.errors,
        "warnings": report.warnings,
        "metrics": report.metrics,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if report.passed else 1


def report_command(path: str, target_lang: str, config: TranslatorConfig) -> int:
    pipeline = build_pipeline(config)
    result = pipeline.run(Path(path), target_lang, write_output=False)
    print(json.dumps(result.report, ensure_ascii=False, indent=2))
    return 0


def evaluate_command(path: str, target_lang: str, config: TranslatorConfig) -> int:
    """Translate one file and print an LLM-as-judge quality report."""
    pipeline = build_pipeline(config)
    result = pipeline.run(Path(path), target_lang, write_output=False)
    judge = JudgeAgent(_build_provider(config))
    judge_report = judge.evaluate(result.segments, result.translations, result.context, target_lang)
    judge_report["input_path"] = str(path)
    judge_report["validation_passed"] = result.validation.passed
    judge_report["api_usage"] = {
        "prompt_tokens": result.api_usage.total.prompt_tokens,
        "completion_tokens": result.api_usage.total.completion_tokens,
        "total_tokens": result.api_usage.total.total_tokens,
        "calls": result.api_usage.total.call_count,
    }
    print(json.dumps(judge_report, ensure_ascii=False, indent=2))
    return 0 if judge_report["overall"] >= 3.0 else 1
