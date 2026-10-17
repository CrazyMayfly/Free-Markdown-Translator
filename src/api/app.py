"""FastAPI application powering the mdtx UI.

Development: run `mdtx --ui-port 8000` (or uvicorn directly) and open the
Vue dev server; production (Tauri): the sidecar binary runs this app on a
port chosen by the shell and only listens on 127.0.0.1.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.api.history import JobHistory, rerender_markdown
from src.api.jobs import TERMINAL_STATUSES, JobManager, JobParams
from src.core.types import MemoryStore
from src.infra.config import (
    TranslatorConfig,
    default_user_config_path,
    load_config,
    resolve_config_path,
)
from src.memory.translation_memory import build_memory

API_KEY_MASK = "********"

_CONFIG_WRITABLE_SECTIONS = {
    "target_languages",
    "provider",
    "pipeline",
    "segmentation",
    "input",
    "style",
    "output",
    "execution",
    "memory",
}


def _mask_config(config: TranslatorConfig) -> dict[str, Any]:
    data = {
        "target_languages": list(config.target_languages),
        "provider": {
            "name": config.provider.name,
            "base_url": config.provider.base_url,
            "api_key": API_KEY_MASK if config.provider.api_key else "",
            "api_key_env": config.provider.api_key_env,
            "model": config.provider.model,
            "temperature": config.provider.temperature,
            "max_tokens": config.provider.max_tokens,
            "structured_outputs": config.provider.structured_outputs,
            "max_retries": config.provider.max_retries,
        },
        "pipeline": {
            "mode": config.pipeline.mode,
            "enable_review": config.pipeline.enable_review,
            "enable_format_guard": config.pipeline.enable_format_guard,
            "fail_on_validation_error": config.pipeline.fail_on_validation_error,
        },
        "segmentation": {
            "max_bundle_chars": config.segmentation.max_bundle_chars,
            "max_bundle_segments": config.segmentation.max_bundle_segments,
        },
        "input": {"file_pattern": config.input.file_pattern},
        "style": {
            "tone": config.style.tone,
            "audience": config.style.audience,
            "preserve_terms": list(config.style.preserve_terms),
            "instructions": list(config.style.instructions),
        },
        "output": {
            "directory": config.output.directory,
            "file_suffix_template": config.output.file_suffix_template,
            "write_report": config.output.write_report,
        },
        "execution": {"max_parallel_translations": config.execution.max_parallel_translations},
        "memory": {"enabled": config.memory.enabled, "path": config.memory.path},
    }
    return data


def _strip_mask(patch: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
    """Drop masked/empty api_key values so saving the form never clobbers a stored key."""
    cleaned = json.loads(json.dumps(patch))  # deep copy
    provider = cleaned.get("provider")
    if isinstance(provider, dict) and "api_key" in provider:
        incoming = provider.pop("api_key")
        if incoming and incoming != API_KEY_MASK:
            provider["api_key"] = incoming
        else:
            existing_key = (existing.get("provider") or {}).get("api_key")
            if existing_key and incoming == API_KEY_MASK:
                provider["api_key"] = existing_key
    return cleaned


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def _config_file_path() -> Path:
    resolved = resolve_config_path()
    return resolved if resolved is not None else default_user_config_path()


class SegmentEditBody(BaseModel):
    text: str


class SaveResultBody(BaseModel):
    path: str | None = None


class ConfigTestBody(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None


class RevealBody(BaseModel):
    path: str


def create_app(memory: MemoryStore | None = None, config_loader=None, history: JobHistory | None = None) -> FastAPI:
    app = FastAPI(title="mdtx", version="3.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "tauri://localhost"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.memory = memory
    app.state.history = history
    app.state.jobs = JobManager(memory=memory, config_loader=config_loader, history=history)

    config_router = APIRouter(prefix="/api")

    @config_router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}
    jobs_router = APIRouter(prefix="/api/jobs")
    misc_router = APIRouter(prefix="/api")

    @config_router.get("/config")
    def get_config() -> dict[str, Any]:
        config = (config_loader or load_config)()
        return {"config": _mask_config(config), "config_path": str(_config_file_path())}

    @config_router.patch("/config")
    def update_config(patch: dict[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(patch) - _CONFIG_WRITABLE_SECTIONS)
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unsupported config keys: {', '.join(unknown)}")
        path = _config_file_path()
        existing: dict[str, Any] = {}
        if path.exists():
            try:
                existing = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as exc:
                raise HTTPException(status_code=409, detail=f"Existing config is not valid YAML: {exc}") from exc
        cleaned = _strip_mask(patch, existing)
        merged = _merge_dict(existing, cleaned)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(merged, allow_unicode=True, sort_keys=False), encoding="utf-8")
        config = (config_loader or load_config)()
        return {"config": _mask_config(config), "config_path": str(path)}

    @config_router.get("/fs")
    def list_dir(path: str = "") -> dict[str, Any]:
        target = Path(path).expanduser().resolve() if path else Path.home()
        if not target.is_dir():
            raise HTTPException(status_code=400, detail=f"Not a directory: {target}")
        entries = []
        try:
            children = sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        except PermissionError:
            children = []
        for child in children[:500]:
            if child.name.startswith("."):
                continue
            entries.append(
                {
                    "name": child.name,
                    "path": str(child),
                    "is_dir": child.is_dir(),
                    "is_markdown": child.is_file() and child.suffix.lower() == ".md",
                }
            )
        return {"path": str(target), "parent": str(target.parent) if target.parent != target else None, "entries": entries}

    @jobs_router.post("")
    async def create_job(params: JobParams) -> dict[str, Any]:
        try:
            job = app.state.jobs.create(params)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return job.summary()

    @jobs_router.get("")
    def list_jobs() -> list[dict[str, Any]]:
        return app.state.jobs.list_jobs()

    @jobs_router.get("/{job_id}")
    def get_job(job_id: str) -> dict[str, Any]:
        job = app.state.jobs.get(job_id)
        if job is not None:
            return {**job.summary(), "params": job.params.model_dump(), "results": job.results}
        if app.state.history is not None:
            record = app.state.history.get(job_id)
            if record is not None:
                return record
        raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")

    @jobs_router.put("/{job_id}/results/{result_index}/segments/{segment_id}")
    def edit_segment(job_id: str, result_index: int, segment_id: str, body: SegmentEditBody) -> dict[str, Any]:
        job = app.state.jobs.get(job_id)
        if job is not None and 0 <= result_index < len(job.results):
            result = job.results[result_index]
            target = next((seg for seg in result.get("segments", []) if seg.get("segment_id") == segment_id), None)
            if target is None:
                raise HTTPException(status_code=404, detail=f"Unknown segment: {segment_id}")
            result["translated_markdown"] = rerender_markdown(
                result.get("translated_markdown") or "", result["segments"], {segment_id: body.text}
            )
            target["translated"] = body.text
            if app.state.history is not None:
                try:
                    app.state.history.save({**job.summary(), "params": job.params.model_dump()}, job.results)
                except Exception:
                    logging.exception("Failed to persist edited job %s", job_id)
            return {"result": result}
        if app.state.history is not None:
            try:
                result = app.state.history.update_segment(job_id, result_index, segment_id, body.text)
            except KeyError:
                pass
            except IndexError:
                raise HTTPException(status_code=404, detail=f"Result index out of range: {result_index}") from None
            else:
                return {"result": result}
        raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")

    @jobs_router.post("/{job_id}/results/{result_index}/save")
    def save_result(job_id: str, result_index: int, body: SaveResultBody) -> dict[str, Any]:
        def fallback_path(result: dict[str, Any]) -> Path:
            input_path = Path(result.get("input_path", "document.md"))
            return Path.home() / "output" / f"{input_path.stem}.{result.get('target_lang', 'translated').lower()}.md"

        def write_markdown(result: dict[str, Any]) -> Path:
            markdown = result.get("translated_markdown") or ""
            if not markdown:
                raise HTTPException(status_code=409, detail="Result has no translated markdown to save")
            target = Path(body.path).expanduser() if body.path else (
                Path(result["output_path"]).expanduser() if result.get("output_path") else fallback_path(result)
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(markdown, encoding="utf-8")
            return target

        job = app.state.jobs.get(job_id)
        if job is not None:
            if not (0 <= result_index < len(job.results)):
                raise HTTPException(status_code=404, detail=f"Result index out of range: {result_index}")
            path = write_markdown(job.results[result_index])
            return {"path": str(path)}
        if app.state.history is not None:
            record = app.state.history.get(job_id)
            if record is not None:
                if not (0 <= result_index < len(record["results"])):
                    raise HTTPException(status_code=404, detail=f"Result index out of range: {result_index}")
                path = write_markdown(record["results"][result_index])
                return {"path": str(path)}
        raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")

    @jobs_router.post("/{job_id}/cancel")
    async def cancel_job(job_id: str) -> dict[str, Any]:
        if app.state.jobs.get(job_id) is None:
            raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")
        cancelled = app.state.jobs.cancel(job_id)
        return {"id": job_id, "cancel_requested": cancelled}

    @jobs_router.get("/{job_id}/events")
    async def job_events(job_id: str, last: int = Query(default=0, ge=0)) -> StreamingResponse:
        job = app.state.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")

        async def stream():
            index = last
            while True:
                while index < len(job.events):
                    event = job.events[index]
                    payload = json.dumps(event, ensure_ascii=False)
                    yield f"event: {event['type']}\ndata: {payload}\n\n"
                    index += 1
                if job.status in TERMINAL_STATUSES:
                    yield f"event: end\ndata: {json.dumps({'status': job.status})}\n\n"
                    return
                await asyncio.sleep(0.15)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @misc_router.get("/history")
    def history_list() -> list[dict[str, Any]]:
        if app.state.history is None:
            return []
        return app.state.history.list()

    @misc_router.delete("/history/{job_id}")
    def history_delete(job_id: str) -> dict[str, Any]:
        if app.state.history is None or not app.state.history.delete(job_id):
            raise HTTPException(status_code=404, detail=f"Unknown history job: {job_id}")
        return {"id": job_id, "deleted": True}

    @config_router.post("/config/test")
    def test_config(body: ConfigTestBody) -> dict[str, Any]:
        import time as _time

        import httpx

        config = (config_loader or load_config)()
        base_url = (body.base_url or config.provider.base_url or "").rstrip("/")
        api_key = body.api_key
        if api_key in (None, "", API_KEY_MASK):
            api_key = config.provider.api_key
        model = body.model or config.provider.model
        if not base_url:
            raise HTTPException(status_code=400, detail="base_url is not configured")

        started = _time.monotonic()
        try:
            response = httpx.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
                timeout=8.0,
            )
        except httpx.HTTPError as exc:
            return {"ok": False, "base_url": base_url, "latency_ms": None, "error": f"连接失败: {exc}"}
        latency_ms = int((_time.monotonic() - started) * 1000)
        if response.status_code != 200:
            return {
                "ok": False,
                "base_url": base_url,
                "latency_ms": latency_ms,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
            }
        try:
            model_ids = [item.get("id") for item in response.json().get("data", [])]
        except ValueError:
            model_ids = []
        # Some gateways serve virtual aliases (e.g. "fast") that /models does
        # not list but chat completions accept — a missing model is a warning,
        # not a failed connection.
        model_warning = model and model_ids and model not in model_ids
        return {
            "ok": True,
            "base_url": base_url,
            "latency_ms": latency_ms,
            "models": model_ids,
            "model_warning": f"模型 {model} 不在网关模型列表中，请确认名称是否正确" if model_warning else None,
            "error": None,
        }

    @misc_router.post("/fs/reveal")
    def reveal_path(body: RevealBody) -> dict[str, Any]:
        import subprocess
        import sys

        target = Path(body.path).expanduser()
        if not target.exists():
            raise HTTPException(status_code=404, detail=f"Path does not exist: {target}")
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target.parent if target.is_file() else target)])
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"无法打开访达: {exc}") from exc
        return {"revealed": str(target)}

    @misc_router.get("/memory/stats")
    def memory_stats() -> dict[str, Any]:
        memory = _get_memory(app)
        stats = dict(memory.stats())
        if hasattr(memory, "entry_count"):
            stats["entries"] = memory.entry_count()
        return stats

    @misc_router.delete("/memory")
    def memory_clear() -> dict[str, Any]:
        removed = _get_memory(app).clear_all()
        return {"removed": removed}

    @misc_router.get("/checkpoints")
    def list_checkpoints() -> list[dict[str, Any]]:
        config = (config_loader or load_config)()
        state_dir = Path(config.output.directory).expanduser() / ".mdtx-state"
        if not state_dir.is_dir():
            return []
        items = []
        for state_file in sorted(state_dir.glob("*.json")):
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            items.append(
                {
                    "file": state_file.name,
                    "fingerprint": data.get("fingerprint", ""),
                    "bundles": len(data.get("bundles") or {}),
                }
            )
        return items

    app.include_router(config_router)
    app.include_router(jobs_router)
    app.include_router(misc_router)
    return app


def _get_memory(app: FastAPI):
    if app.state.memory is None:
        app.state.memory = build_memory(load_config())
    return app.state.memory


def run_server(port: int, open_browser: bool = True) -> None:
    import uvicorn

    if open_browser:
        import webbrowser

        url = f"http://127.0.0.1:{port}"
        logging.info("mdtx UI listening on %s", url)
        try:
            webbrowser.open(url)
        except Exception:  # pragma: no cover - best effort
            pass
    uvicorn.run(create_app(history=JobHistory()), host="127.0.0.1", port=port, log_level="warning")
