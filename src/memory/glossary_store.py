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
    status TEXT NOT NULL DEFAULT 'pending',
    doc_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (lang, term)
);
"""

# Migrate a store created before the status/doc_count columns existed.
_MIGRATION_COLUMNS = {"status": "TEXT NOT NULL DEFAULT 'pending'", "doc_count": "INTEGER NOT NULL DEFAULT 0"}

# Terms become active (injected into prompts) after appearing in this many
# distinct documents. A "document" is one translated source file regardless of
# how often the term occurs inside it.
ACTIVATE_AFTER_DOCS = 4


class GlossaryStore:
    """Persistent term -> rendering glossary accumulated across runs.

    One row per (lang, term). Entries written by the user (origin='user')
    always win: model-side upserts never overwrite them, and at merge time
    persisted renderings shadow freshly extracted ones.

    Each term tracks a lifecycle: it starts ``pending`` and counts how many
    distinct documents it has appeared in. Once it has appeared in
    ``ACTIVATE_AFTER_DOCS`` documents it becomes ``active`` and is injected into
    prompts like a hand-written entry. A user may mark any term ``excluded`` to
    keep it out of prompts forever (and stop counting it).
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self._migrate()

    def _migrate(self) -> None:
        with self._lock:
            columns = {row[1] for row in self._conn.execute("PRAGMA table_info(glossary_entries)")}
            for column, decl in _MIGRATION_COLUMNS.items():
                if column in columns:
                    continue
                try:
                    self._conn.execute(f"ALTER TABLE glossary_entries ADD COLUMN {column} {decl}")
                    self._conn.commit()
                except sqlite3.OperationalError as exc:
                    logging.warning("Glossary migration skipped (%s): %s", column, exc)
            # Pre-existing entries were user-authored and should stay active.
            if "status" not in columns:
                self._conn.execute(
                    "UPDATE glossary_entries SET status='active' WHERE origin='user'"
                )
                self._conn.commit()

    def load(self, lang: str) -> dict[str, str]:
        """Active + user terms that actually get injected into prompts."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT term, rendering FROM glossary_entries "
                "WHERE lang = ? AND (status = 'active' OR origin = 'user')",
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
                    "INSERT INTO glossary_entries (lang, term, rendering, origin, status) "
                    "VALUES (?, ?, ?, 'user', 'active') "
                    "ON CONFLICT(lang, term) DO UPDATE SET rendering=excluded.rendering, "
                    "origin='user', status='active', updated_at=datetime('now')",
                    (lang, term, rendering),
                )
            else:
                self._conn.execute(
                    "INSERT INTO glossary_entries (lang, term, rendering, origin, status) "
                    "VALUES (?, ?, ?, 'model', 'pending') "
                    "ON CONFLICT(lang, term) DO UPDATE SET rendering=excluded.rendering, "
                    "updated_at=datetime('now') WHERE glossary_entries.origin != 'user'",
                    (lang, term, rendering),
                )
            self._conn.commit()

    def record_appearance(self, lang: str, terms: set[str]) -> None:
        """Count one document's occurrence of each term; promote to active once
        the term has appeared in ACTIVATE_AFTER_DOCS distinct documents.

        Terms not yet in the store are inserted as pending placeholders
        (rendering = term) so their doc_count can start accumulating.
        """
        if not terms:
            return
        with self._lock:
            for term in terms:
                term = term.strip()
                if not term:
                    continue
                self._conn.execute(
                    "INSERT INTO glossary_entries (lang, term, rendering, origin, status, doc_count) "
                    "VALUES (?, ?, ?, 'model', 'pending', 0) "
                    "ON CONFLICT(lang, term) DO NOTHING",
                    (lang, term, term),
                )
                self._conn.execute(
                    "UPDATE glossary_entries SET doc_count = doc_count + 1, "
                    "status = CASE WHEN doc_count + 1 >= ? AND origin != 'user' "
                    "  THEN 'active' ELSE status END, updated_at = datetime('now') "
                    "WHERE lang = ? AND term = ? AND status != 'excluded'",
                    (ACTIVATE_AFTER_DOCS, lang, term),
                )
            self._conn.commit()

    def set_status(self, lang: str, term: str, status: str) -> bool:
        if status not in {"pending", "active", "excluded"}:
            return False
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE glossary_entries SET status = ?, updated_at = datetime('now') "
                "WHERE lang = ? AND term = ?",
                (status, lang, term),
            )
            self._conn.commit()
        return cursor.rowcount > 0

    def delete(self, lang: str, term: str) -> bool:
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM glossary_entries WHERE lang = ? AND term = ?",
                (lang, term),
            )
            self._conn.commit()
        return cursor.rowcount > 0

    def entries(self, lang: str) -> list[dict[str, object]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT term, rendering, origin, status, doc_count, updated_at "
                "FROM glossary_entries WHERE lang = ? ORDER BY doc_count DESC, term",
                (lang,),
            ).fetchall()
        return [
            {
                "term": str(term),
                "rendering": str(rendering),
                "origin": str(origin),
                "status": str(status),
                "doc_count": int(doc_count),
                "updated_at": str(updated_at),
            }
            for term, rendering, origin, status, doc_count, updated_at in rows
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

    def record_appearance(self, lang: str, terms: set[str]) -> None:
        return None

    def set_status(self, lang: str, term: str, status: str) -> bool:
        return False

    def delete(self, lang: str, term: str) -> bool:
        return False

    def entries(self, lang: str) -> list[dict[str, object]]:
        return []

    def languages(self) -> list[str]:
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
