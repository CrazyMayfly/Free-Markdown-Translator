"""Persistent job history so finished translations survive app restarts.

Live jobs live in JobManager memory; once a job reaches a terminal state its
summary plus full results (segments, translated markdown, validation, usage)
are upserted into a small SQLite database under ``~/.mdtx/history.sqlite3``.
The UI merges the two sources, which also enables re-opening a result to fix
a single segment without re-running the model.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

DEFAULT_HISTORY_PATH = Path.home() / ".mdtx" / "history.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    created_at REAL,
    finished_at REAL,
    summary_json TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    updated_at REAL NOT NULL
)
"""


def rerender_markdown(markdown: str, segments: list[dict[str, Any]], edits: dict[str, str]) -> str:
    """Rebuild the translated document after in-place segment edits.

    Segments are in document order, so each one's stored ``translated`` text
    is located monotonically forward through the markdown; that keeps duplicate
    segment texts unambiguous. Segments listed in ``edits`` (by segment_id) are
    spliced out in favor of their new text; the caller persists the new text
    onto the segment itself afterwards.
    """
    parts: list[str] = []
    cursor = 0
    for segment in segments:
        current = segment.get("translated") or ""
        if not current:
            continue
        idx = markdown.find(current, cursor)
        if idx < 0:
            idx = markdown.find(current)
            if idx < 0:
                continue  # already replaced by an earlier edit; keep going
        parts.append(markdown[cursor:idx])
        segment_id = segment.get("segment_id")
        if isinstance(segment_id, str) and segment_id in edits:
            parts.append(edits[segment_id])
        else:
            parts.append(current)
        cursor = idx + len(current)
    parts.append(markdown[cursor:])
    return "".join(parts)


class JobHistory:
    def __init__(self, path: Path | str = DEFAULT_HISTORY_PATH) -> None:
        self._path = Path(path).expanduser()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def save(self, summary: dict[str, Any], results: list[dict[str, Any]]) -> None:
        self._conn.execute(
            "INSERT INTO jobs (id, status, created_at, finished_at, summary_json, detail_json, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET status=excluded.status, finished_at=excluded.finished_at, "
            "summary_json=excluded.summary_json, detail_json=excluded.detail_json, updated_at=excluded.updated_at",
            (
                summary["id"],
                summary["status"],
                summary.get("created_at"),
                summary.get("finished_at"),
                json.dumps(summary, ensure_ascii=False),
                json.dumps({"results": results}, ensure_ascii=False),
                time.time(),
            ),
        )
        self._conn.commit()

    def list(self, limit: int = 200) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT summary_json FROM jobs ORDER BY COALESCE(finished_at, created_at, updated_at) DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def get(self, job_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT summary_json, detail_json FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        summary = json.loads(row[0])
        detail = json.loads(row[1])
        return {**summary, "results": detail.get("results", [])}

    def delete(self, job_id: str) -> bool:
        cursor = self._conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def get_result(self, job_id: str, result_index: int) -> dict[str, Any] | None:
        job = self.get(job_id)
        if job is None or not (0 <= result_index < len(job["results"])):
            return None
        return job["results"][result_index]

    def update_segment(self, job_id: str, result_index: int, segment_id: str, text: str) -> dict[str, Any]:
        """Edit one segment's translation in place and re-render the markdown."""
        job = self.get(job_id)
        if job is None:
            raise KeyError(job_id)
        results = job["results"]
        if not (0 <= result_index < len(results)):
            raise IndexError(result_index)
        result = results[result_index]
        target = next((seg for seg in result["segments"] if seg["segment_id"] == segment_id), None)
        if target is None:
            raise KeyError(segment_id)
        result["translated_markdown"] = rerender_markdown(
            result.get("translated_markdown") or "", result["segments"], {segment_id: text}
        )
        target["translated"] = text
        self.save({key: value for key, value in job.items() if key != "results"}, results)
        return result

    def write_result_markdown(self, job_id: str, result_index: int, path: Path | None = None) -> Path:
        result = self.get_result(job_id, result_index)
        if result is None:
            raise KeyError(job_id)
        markdown = result.get("translated_markdown") or ""
        if not markdown:
            raise ValueError("Result has no translated markdown to save")
        target = path or (Path(result["output_path"]) if result.get("output_path") else _fallback_path(result))
        target = target.expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")
        logging.info("Saved result markdown: %s", target)
        return target

    def close(self) -> None:
        self._conn.close()


def _fallback_path(result: dict[str, Any]) -> Path:
    """Mirror the pipeline's default naming when it never wrote the file."""
    input_path = Path(result.get("input_path", "document.md"))
    return Path.home() / "output" / "{stem}.{lang}.md".format(
        stem=input_path.stem,
        lang=result.get("target_lang", "translated").lower(),
    )
