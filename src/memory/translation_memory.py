from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS translation_entries (
    entry_key TEXT PRIMARY KEY,
    source_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    target_lang TEXT NOT NULL,
    model TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class TranslationMemory:
    """SQLite-backed exact-match translation memory.

    An entry is keyed by (source_text, target_lang, model, style-config hash):
    a hit means the exact same segment was already translated under the exact
    same conditions, so the stored translation can be reused without an LLM
    call. Source texts contain protected placeholders, which keeps the key
    stable across runs of the same document.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def style_fingerprint(
        model: str,
        tone: str,
        audience: str,
        instructions: list[str],
        preserve_terms: list[str],
        document_id: str = "",
    ) -> str:
        # document_id is omitted from the payload when empty so "global" scope
        # keeps producing the same keys as libraries written by older versions.
        payload = json.dumps(
            {
                "model": model,
                "tone": tone,
                "audience": audience,
                "instructions": list(instructions),
                "preserve_terms": list(preserve_terms),
                **({"document": document_id} if document_id else {}),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def build_key(cls, source_text: str, target_lang: str, fingerprint: str) -> str:
        raw = "\x00".join([source_text, target_lang, fingerprint])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def find(self, source_text: str, target_lang: str, fingerprint: str = "") -> str | None:
        row = self.peek(source_text, target_lang, fingerprint)
        if row is None:
            self.misses += 1
            return None
        self.hits += 1
        return row

    def peek(self, source_text: str, target_lang: str, fingerprint: str = "") -> str | None:
        """Lookup without touching the hit/miss counters (used for planning)."""
        key = self.build_key(source_text, target_lang, fingerprint)
        with self._lock:
            row = self._conn.execute(
                "SELECT translated_text FROM translation_entries WHERE entry_key = ?",
                (key,),
            ).fetchone()
        return str(row[0]) if row is not None else None

    def store(self, source_text: str, target_lang: str, translated_text: str, fingerprint: str = "", confidence: float = 0.0) -> None:
        key = self.build_key(source_text, target_lang, fingerprint)
        with self._lock:
            self._conn.execute(
                "INSERT INTO translation_entries (entry_key, source_text, translated_text, target_lang, model, confidence) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(entry_key) DO UPDATE SET translated_text=excluded.translated_text, confidence=excluded.confidence",
                (key, source_text, translated_text, target_lang, fingerprint, float(confidence)),
            )
            self._conn.commit()

    def stats(self) -> dict[str, int]:
        return {"hits": self.hits, "misses": self.misses}

    def entry_count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM translation_entries").fetchone()
        return int(row[0])

    def clear_all(self) -> int:
        with self._lock:
            removed = self._conn.execute("SELECT COUNT(*) FROM translation_entries").fetchone()[0]
            self._conn.execute("DELETE FROM translation_entries")
            self._conn.commit()
        self.hits = 0
        self.misses = 0
        return int(removed)


class NullMemory:
    """Drop-in replacement used when memory is disabled."""

    def find(self, source_text: str, target_lang: str, fingerprint: str = "") -> str | None:
        return None

    def peek(self, source_text: str, target_lang: str, fingerprint: str = "") -> str | None:
        return None

    def store(self, source_text: str, target_lang: str, translated_text: str, fingerprint: str = "", confidence: float = 0.0) -> None:
        return None

    def stats(self) -> dict[str, int]:
        return {"hits": 0, "misses": 0}

    def entry_count(self) -> int:
        return 0

    def clear_all(self) -> int:
        return 0


def build_memory(config) -> object:
    from src.infra.config import TranslatorConfig

    if not isinstance(config, TranslatorConfig) or not config.memory.enabled:
        return NullMemory()
    try:
        return TranslationMemory(config.memory.path)
    except Exception as exc:  # pragma: no cover - unreadable path etc.
        logging.warning("Translation memory unavailable (%s); continuing without it", exc)
        return NullMemory()
