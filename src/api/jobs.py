"""Job management for the UI/API layer.

A job is one UI submission: N input paths x M target languages. Execution
reuses the exact CLI pipeline (run_async + TaskGroup); bundle-level progress
is bridged into a per-job event log that the SSE endpoint streams to the
browser. Nothing here touches pipeline internals.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel

from src.cli.commands import TranslationSource, _build_provider, _build_task_output_path, _resolve_relative_output_path, build_pipeline
from src.core.errors import OutputWriteError
from src.core.types import ApiUsageSummary
from src.infra.config import TranslatorConfig, load_config
from src.memory.checkpoint import JobCheckpointStore

TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
_MAX_EVENTS = 5000


class JobParams(BaseModel):
    paths: list[str]
    target_langs: list[str]
    output_dir: str | None = None
    mode: str | None = None
    tone: str | None = None
    model: str | None = None
    evaluate: bool = False
    resume: bool = False


@dataclass
class Job:
    id: str
    params: JobParams
    config: TranslatorConfig
    pairs: list[tuple[Path, str]]
    status: str = "queued"
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    error: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=lambda: {"prompt": 0, "completion": 0, "total": 0, "cached": 0, "calls": 0})
    task: asyncio.Task | None = None

    def emit(self, event_type: str, **data: Any) -> None:
        self.events.append({"seq": len(self.events), "type": event_type, "ts": time.time(), **data})
        if len(self.events) > _MAX_EVENTS:
            del self.events[: len(self.events) - _MAX_EVENTS]

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "error": self.error,
            "pairs": [f"{path.name} -> {lang}" for path, lang in self.pairs],
            "usage": dict(self.usage),
            "result_count": len(self.results),
        }


class JobManager:
    def __init__(
        self,
        memory: object | None = None,
        config_loader: Callable[[], TranslatorConfig] | None = None,
        history: object | None = None,
    ) -> None:
        self._jobs: dict[str, Job] = {}
        self._memory = memory
        self._config_loader = config_loader or load_config
        self._history = history

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[dict[str, Any]]:
        return [job.summary() for job in self._jobs.values()]

    def create(self, params: JobParams) -> Job:
        if not params.paths or not params.target_langs:
            raise ValueError("paths and target_langs must not be empty")
        config = self._config_loader()
        if params.mode:
            config.pipeline.mode = params.mode
        if params.tone:
            config.style.tone = params.tone
        if params.model:
            config.provider.model = params.model
        # Absolute so result paths stay meaningful regardless of the API
        # process cwd (the desktop sidecar runs from the user's home).
        output_dir = Path(params.output_dir or config.output.directory).expanduser().resolve()
        pairs: list[tuple[Path, str]] = []
        for raw_path in params.paths:
            input_path = Path(raw_path).expanduser()
            if input_path.is_dir():
                matched = sorted(
                    candidate
                    for candidate in input_path.rglob(config.input.file_pattern)
                    if candidate.is_file()
                )
                if not matched:
                    raise ValueError(f"No files matched {config.input.file_pattern} under {input_path}")
                files: list[Path] = matched
            elif input_path.is_file():
                files = [input_path]
            else:
                raise FileNotFoundError(f"Input path does not exist: {input_path}")
            for file_path in files:
                for lang in params.target_langs:
                    pairs.append((file_path, lang))
        job = Job(id=uuid.uuid4().hex[:12], params=params, config=config, pairs=pairs)
        self._jobs[job.id] = job
        job.task = asyncio.create_task(self._execute(job, config, output_dir), name=f"mdtx-job-{job.id}")
        return job

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None or job.task is None or job.task.done():
            return False
        job.task.cancel()
        return True

    async def _execute(self, job: Job, config: TranslatorConfig, output_dir: Path) -> None:
        job.status = "running"
        job.emit("status", status="running", total_pairs=len(job.pairs))
        checkpoint_store = None
        if job.params.resume:
            checkpoint_store = JobCheckpointStore(
                output_dir / ".mdtx-state",
                JobCheckpointStore.fingerprint(
                    model=config.provider.model,
                    tone=config.style.tone,
                    audience=config.style.audience,
                    mode=config.pipeline.mode,
                ),
            )
        try:
            # Pairs run concurrently; one shared semaphore caps global LLM
            # concurrency at max_parallel_translations (same semantics as the
            # CLI's _translate_pairs).
            semaphore = asyncio.Semaphore(max(1, config.execution.max_parallel_translations))
            async with asyncio.TaskGroup() as task_group:
                for index, (input_path, target_lang) in enumerate(job.pairs, start=1):
                    task_group.create_task(
                        self._run_pair(job, config, output_dir, checkpoint_store, semaphore, input_path, target_lang, index)
                    )
            job.status = "completed"
            job.emit("status", status="completed", results=job.results)
        except asyncio.CancelledError:
            job.status = "cancelled"
            job.emit("status", status="cancelled")
        except BaseExceptionGroup as exc:
            # TaskGroup wraps child failures; surface the first real error.
            first = next((item for item in exc.exceptions if not isinstance(item, asyncio.CancelledError)), None)
            logging.exception("Job %s failed", job.id)
            job.status = "failed"
            job.error = str(first or exc)
            job.emit("status", status="failed", error=str(first or exc))
        finally:
            job.finished_at = time.time()
            if self._history is not None:
                try:
                    summary = {**job.summary(), "params": job.params.model_dump()}
                    self._history.save(summary, job.results)
                except Exception:
                    logging.exception("Failed to persist job %s to history", job.id)

    async def _run_pair(
        self,
        job: Job,
        config: TranslatorConfig,
        output_dir: Path,
        checkpoint_store: JobCheckpointStore | None,
        semaphore: asyncio.Semaphore,
        input_path: Path,
        target_lang: str,
        index: int,
    ) -> None:
        from src.agents.judge_agent import JudgeAgent

        pipeline = build_pipeline(config, memory=self._memory, checkpoint_store=checkpoint_store)
        total_bundles = pipeline.count_bundles(input_path, target_lang)
        done = {"count": 0}
        last_totals = {"prompt": 0, "completion": 0, "total": 0, "cached": 0, "calls": 0}

        def _absorb_pair_usage() -> None:
            """Fold new provider tokens into job totals as deltas.

            Several pairs run concurrently, so absolute snapshots would clobber
            each other; deltas computed in one event-loop turn are safe.
            """
            provider = getattr(getattr(pipeline, "translator_agent", None), "provider", None)
            if provider is None:
                return
            totals = provider.get_usage_summary().total
            deltas = {
                "prompt": totals.prompt_tokens - last_totals["prompt"],
                "completion": totals.completion_tokens - last_totals["completion"],
                "total": totals.total_tokens - last_totals["total"],
                "cached": totals.cached_tokens - last_totals["cached"],
                "calls": totals.call_count - last_totals["calls"],
            }
            for key, delta in deltas.items():
                if delta > 0:
                    job.usage[key] += delta
            last_totals.update(
                prompt=totals.prompt_tokens,
                completion=totals.completion_tokens,
                total=totals.total_tokens,
                cached=totals.cached_tokens,
                calls=totals.call_count,
            )

        def on_bundle(path: Path, lang: str, bundle_id: str) -> None:
            done["count"] += 1
            _absorb_pair_usage()  # track tokens even if a later step fails
            job.emit(
                "progress",
                input=str(input_path),
                lang=target_lang,
                bundle_id=bundle_id,
                done=done["count"],
                total=total_bundles,
                usage=dict(job.usage),
            )

        source = TranslationSource(input_path=input_path, relative_output_path=_resolve_relative_output_path(input_path))
        output_path = _build_task_output_path(source, target_lang, output_dir, config)
        job.emit("pair_start", input=str(input_path), lang=target_lang, index=index, bundles=total_bundles)
        write_error: str | None = None
        try:
            result = await pipeline.run_async(
                input_path,
                target_lang,
                write_output=True,
                output_path=output_path,
                semaphore=semaphore,
                bundle_progress_callback=on_bundle,
            )
        except OutputWriteError as exc:
            # Translation succeeded; only the file write failed. Surface the
            # text instead of losing the run.
            _absorb_pair_usage()
            logging.warning("Output write failed for %s: %s", input_path.name, exc)
            write_error = str(exc)
            provider = getattr(getattr(pipeline, "translator_agent", None), "provider", None)
            result = SimpleNamespace(
                input_path=input_path,
                output_path=None,
                translated_text=exc.output_text,
                segments=exc.segments,
                translations=exc.translations,
                validation=exc.validation,
                api_usage=provider.get_usage_summary() if provider is not None else ApiUsageSummary(),
                report={},
                context=None,
            )

        _absorb_pair_usage()

        judge_report = None
        if job.params.evaluate:
            try:
                judge = JudgeAgent(_build_provider(config))
                judge_report = await judge.evaluate_async(result.segments, result.translations, result.context, target_lang)
            except Exception as exc:
                logging.warning("Judge evaluation failed for %s: %s", input_path.name, exc)
                judge_report = {"error": str(exc)}

        serialized = _serialize_result(result, target_lang, judge_report)
        serialized["write_error"] = write_error
        job.results.append(serialized)
        job.emit(
            "pair_done",
            input=str(input_path),
            lang=target_lang,
            index=index,
            usage=dict(job.usage),
            write_error=write_error,
        )


def _serialize_result(result, target_lang: str, judge_report: dict | None) -> dict[str, Any]:
    translations_by_id = {item.segment_id: item for item in result.translations}
    segments = []
    for segment in result.segments:
        translation = translations_by_id.get(segment.segment_id)
        segments.append(
            {
                "segment_id": segment.segment_id,
                "context_path": segment.context_path,
                "source": segment.source_text,
                "translated": translation.translated_text if translation else "",
                "confidence": translation.confidence if translation else 0.0,
            }
        )
    return {
        "input_path": str(result.input_path),
        "output_path": str(result.output_path) if result.output_path else None,
        "target_lang": target_lang,
        "translated_markdown": result.translated_text,
        "validation": {
            "passed": result.validation.passed,
            "errors": result.validation.errors,
            "warnings": result.validation.warnings,
        },
        "usage": {
            "prompt": result.api_usage.total.prompt_tokens,
            "completion": result.api_usage.total.completion_tokens,
            "total": result.api_usage.total.total_tokens,
            "cached": result.api_usage.total.cached_tokens,
            "calls": result.api_usage.total.call_count,
        },
        "segments": segments,
        "judge": judge_report,
    }
