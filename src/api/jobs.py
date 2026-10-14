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
from typing import Any

from pydantic import BaseModel

from src.cli.commands import TranslationSource, _build_provider, _build_task_output_path, _resolve_relative_output_path, build_pipeline
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
    def __init__(self, memory: object | None = None, config_loader: Callable[[], TranslatorConfig] | None = None) -> None:
        self._jobs: dict[str, Job] = {}
        self._memory = memory
        self._config_loader = config_loader or load_config

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
        output_dir = Path(params.output_dir or config.output.directory).expanduser()
        pairs: list[tuple[Path, str]] = []
        for raw_path in params.paths:
            input_path = Path(raw_path).expanduser()
            if not input_path.is_file():
                raise FileNotFoundError(f"Input file does not exist: {input_path}")
            for lang in params.target_langs:
                pairs.append((input_path, lang))
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
            for index, (input_path, target_lang) in enumerate(job.pairs, start=1):
                await self._run_pair(job, config, output_dir, checkpoint_store, input_path, target_lang, index)
            job.status = "completed"
            job.emit("status", status="completed", results=job.results)
        except asyncio.CancelledError:
            job.status = "cancelled"
            job.emit("status", status="cancelled")
        except Exception as exc:
            logging.exception("Job %s failed", job.id)
            job.status = "failed"
            job.error = str(exc)
            job.emit("status", status="failed", error=str(exc))
        finally:
            job.finished_at = time.time()

    async def _run_pair(
        self,
        job: Job,
        config: TranslatorConfig,
        output_dir: Path,
        checkpoint_store: JobCheckpointStore | None,
        input_path: Path,
        target_lang: str,
        index: int,
    ) -> None:
        from src.agents.judge_agent import JudgeAgent

        pipeline = build_pipeline(config, memory=self._memory, checkpoint_store=checkpoint_store)
        total_bundles = pipeline.count_bundles(input_path, target_lang)
        done = {"count": 0}

        def on_bundle(path: Path, lang: str, bundle_id: str) -> None:
            done["count"] += 1
            job.emit(
                "progress",
                input=str(input_path),
                lang=target_lang,
                bundle_id=bundle_id,
                done=done["count"],
                total=total_bundles,
            )

        source = TranslationSource(input_path=input_path, relative_output_path=_resolve_relative_output_path(input_path))
        output_path = _build_task_output_path(source, target_lang, output_dir, config)
        job.emit("pair_start", input=str(input_path), lang=target_lang, index=index, bundles=total_bundles)
        result = await pipeline.run_async(
            input_path,
            target_lang,
            write_output=True,
            output_path=output_path,
            bundle_progress_callback=on_bundle,
        )

        pair_usage = result.api_usage.total
        job.usage["prompt"] += pair_usage.prompt_tokens
        job.usage["completion"] += pair_usage.completion_tokens
        job.usage["total"] += pair_usage.total_tokens
        job.usage["cached"] += pair_usage.cached_tokens
        job.usage["calls"] += pair_usage.call_count

        judge_report = None
        if job.params.evaluate:
            try:
                judge = JudgeAgent(_build_provider(config))
                judge_report = await judge.evaluate_async(result.segments, result.translations, result.context, target_lang)
            except Exception as exc:
                logging.warning("Judge evaluation failed for %s: %s", input_path.name, exc)
                judge_report = {"error": str(exc)}

        serialized = _serialize_result(result, target_lang, judge_report)
        job.results.append(serialized)
        job.emit("pair_done", input=str(input_path), lang=target_lang, index=index, usage=serialized["usage"])


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
