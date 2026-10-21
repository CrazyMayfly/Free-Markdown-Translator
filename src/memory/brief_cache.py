from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class BriefCache:
    """Persistent document-brief cache keyed by content/model/language/version."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False, timeout=10)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS briefs (
                key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    @staticmethod
    def make_key(
        document_text: str,
        model: str,
        target_lang: str,
        mode: str,
        prompt_version: str,
    ) -> str:
        raw = "\x00".join([document_text, model, target_lang, mode, prompt_version])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT payload FROM briefs WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        try:
            payload = json.loads(row[0])
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def put(self, key: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO briefs (key, payload, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at",
                (key, json.dumps(payload, ensure_ascii=False), time.time()),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def build_brief_cache(config) -> BriefCache | None:
    path = (config.memory.brief_path or "").strip()
    if not path:
        return None
    try:
        return BriefCache(Path(path))
    except (OSError, sqlite3.Error):
        # A read-only home or unwritable path must not break translation.
        return None
