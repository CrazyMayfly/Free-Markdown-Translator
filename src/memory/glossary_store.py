from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS glossary_entries (
    lang TEXT NOT NULL,
    term TEXT NOT NULL,
    rendering TEXT NOT NULL,
    origin TEXT NOT NULL DEFAULT 'model',
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (lang, term)
);
"""


class GlossaryStore:
    """Persistent term -> rendering glossary accumulated across runs.

    One row per (lang, term). Entries written by the user (origin='user')
    always win: model-side upserts never overwrite them, and at merge time
    persisted renderings shadow freshly extracted ones.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def load(self, lang: str) -> dict[str, str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT term, rendering FROM glossary_entries WHERE lang = ?",
                (lang,),
            ).fetchall()
        return {str(term): str(rendering) for term, rendering in rows}

    def upsert(self, lang: str, term: str, rendering: str, origin: str = "model") -> None:
        term, rendering = term.strip(), rendering.strip()
        if not term or not rendering:
            return
        with self._lock:
            if origin == "user":
                self._conn.execute(
                    "INSERT INTO glossary_entries (lang, term, rendering, origin) VALUES (?, ?, ?, 'user') "
                    "ON CONFLICT(lang, term) DO UPDATE SET rendering=excluded.rendering, origin='user', "
                    "updated_at=datetime('now')",
                    (lang, term, rendering),
                )
            else:
                self._conn.execute(
                    "INSERT INTO glossary_entries (lang, term, rendering, origin) VALUES (?, ?, ?, 'model') "
                    "ON CONFLICT(lang, term) DO UPDATE SET rendering=excluded.rendering, "
                    "updated_at=datetime('now') WHERE glossary_entries.origin != 'user'",
                    (lang, term, rendering),
                )
            self._conn.commit()

    def delete(self, lang: str, term: str) -> bool:
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM glossary_entries WHERE lang = ? AND term = ?",
                (lang, term),
            )
            self._conn.commit()
        return cursor.rowcount > 0

    def entries(self, lang: str) -> list[dict[str, str]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT term, rendering, origin, updated_at FROM glossary_entries WHERE lang = ? ORDER BY term",
                (lang,),
            ).fetchall()
        return [
            {"term": str(term), "rendering": str(rendering), "origin": str(origin), "updated_at": str(updated_at)}
            for term, rendering, origin, updated_at in rows
        ]

    def languages(self) -> list[str]:
        with self._lock:
            rows = self._conn.execute("SELECT DISTINCT lang FROM glossary_entries ORDER BY lang").fetchall()
        return [str(row[0]) for row in rows]


class NullGlossaryStore:
    """Drop-in replacement used when glossary persistence is disabled."""

    def load(self, lang: str) -> dict[str, str]:
        return {}

    def upsert(self, lang: str, term: str, rendering: str, origin: str = "model") -> None:
        return None

    def delete(self, lang: str, term: str) -> bool:
        return False

    def entries(self, lang: str) -> list[dict[str, str]]:
        return []


def build_glossary_store(config):
    from src.infra.config import TranslatorConfig

    if not isinstance(config, TranslatorConfig) or not config.memory.glossary_persist:
        return NullGlossaryStore()
    try:
        return GlossaryStore(config.memory.glossary_path)
    except Exception as exc:  # pragma: no cover - unreadable path etc.
        logging.warning("Glossary store unavailable (%s); continuing without it", exc)
        return NullGlossaryStore()
