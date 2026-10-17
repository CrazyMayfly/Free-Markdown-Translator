from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
from pathlib import Path

from src.core.types import MemoryStore

_SCHEMA = """
CREATE TABLE IF NOT EXISTS translation_entries (
    entry_key TEXT PRIMARY KEY,
    source_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    target_lang TEXT NOT NULL,
    model TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.0,
    style_key TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_entries_lang_style
    ON translation_entries(target_lang, style_key);
"""


def _trigrams(text: str) -> set[str]:
    if len(text) < 3:
        return {text} if text else set()
    return {text[i : i + 3] for i in range(len(text) - 2)}


def similarity(left: str, right: str) -> float:
    """Character-trigram Dice similarity with a coarse length guard.

    Deliberately lexical (no embeddings): deterministic, offline, and good
    enough to catch reworded or near-duplicate segments. Dice (2|A∩B| /
    (|A|+|B|)) is used instead of Jaccard because it stays forgiving for
    natural rewording of short sentences while still hitting ~1.0 for
    near-identical text.
    """
    if not left or not right:
        return 0.0
    longer, shorter = (left, right) if len(left) >= len(right) else (right, left)
    if len(shorter) * 2 < len(longer):
        return 0.0
    left_set, right_set = _trigrams(left), _trigrams(right)
    if not left_set or not right_set:
        return 0.0
    return 2 * len(left_set & right_set) / (len(left_set) + len(right_set))


class TranslationMemory:
    """SQLite-backed translation memory: exact reuse plus fuzzy neighbours.

    An entry is keyed by (source_text, target_lang, model, style-config hash):
    a hit means the exact same segment was already translated under the exact
    same conditions, so the stored translation can be reused without an LLM
    call. Source texts contain protected placeholders, which keeps the key
    stable across runs of the same document.

    Fuzzy matching works on a separate style_key (the fingerprint without the
    document id) so similar segments can be found across documents of the same
    style, powering direct reuse of near-identical sources and few-shot
    examples for close matches.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._ensure_style_key_column()
        self._conn.commit()
        self.hits = 0
        self.misses = 0

    def _ensure_style_key_column(self) -> None:
        columns = {row[1] for row in self._conn.execute("PRAGMA table_info(translation_entries)")}
        if "style_key" not in columns:
            self._conn.execute("ALTER TABLE translation_entries ADD COLUMN style_key TEXT NOT NULL DEFAULT ''")

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

    def find(self, source_text: str, target_lang: str, fingerprint: str = "", min_confidence: float = 0.0) -> str | None:
        row = self._lookup(source_text, target_lang, fingerprint, min_confidence)
        if row is None:
            self.misses += 1
            return None
        self.hits += 1
        return row

    def peek(self, source_text: str, target_lang: str, fingerprint: str = "", min_confidence: float = 0.0) -> str | None:
        """Lookup without touching the hit/miss counters (used for planning)."""
        return self._lookup(source_text, target_lang, fingerprint, min_confidence)

    def _lookup(self, source_text: str, target_lang: str, fingerprint: str, min_confidence: float) -> str | None:
        key = self.build_key(source_text, target_lang, fingerprint)
        with self._lock:
            row = self._conn.execute(
                "SELECT translated_text, confidence FROM translation_entries WHERE entry_key = ?",
                (key,),
            ).fetchone()
        if row is None or float(row[1]) < min_confidence:
            return None
        return str(row[0])

    def store(
        self,
        source_text: str,
        target_lang: str,
        translated_text: str,
        fingerprint: str = "",
        confidence: float = 0.0,
        style_key: str = "",
    ) -> None:
        key = self.build_key(source_text, target_lang, fingerprint)
        with self._lock:
            self._conn.execute(
                "INSERT INTO translation_entries (entry_key, source_text, translated_text, target_lang, model, confidence, style_key) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(entry_key) DO UPDATE SET translated_text=excluded.translated_text, "
                "confidence=excluded.confidence, style_key=excluded.style_key",
                (key, source_text, translated_text, target_lang, fingerprint, float(confidence), style_key),
            )
            self._conn.commit()

    def find_similar(
        self,
        source_text: str,
        target_lang: str,
        style_key: str = "",
        limit: int = 2,
        min_score: float = 0.0,
    ) -> list[tuple[float, str, str]]:
        """Best fuzzy matches as (score, source_text, translated_text).

        Scans entries of the same language and style across documents; the
        exact-match row itself is excluded.
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT source_text, translated_text FROM translation_entries "
                "WHERE target_lang = ? AND style_key = ? AND source_text <> ?",
                (target_lang, style_key, source_text),
            ).fetchall()
        scored: list[tuple[float, str, str]] = []
        for source, translated in rows:
            score = similarity(source_text, str(source))
            if score >= min_score:
                scored.append((score, str(source), str(translated)))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[:limit]

    def downweight(self, source_text: str, target_lang: str, fingerprint: str, confidence: float = 0.0) -> bool:
        """Lower an entry's confidence (judge feedback); returns True if it existed."""
        key = self.build_key(source_text, target_lang, fingerprint)
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE translation_entries SET confidence = ? WHERE entry_key = ?",
                (float(confidence), key),
            )
            self._conn.commit()
        return cursor.rowcount > 0

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

    def find(self, source_text: str, target_lang: str, fingerprint: str = "", min_confidence: float = 0.0) -> str | None:
        return None

    def peek(self, source_text: str, target_lang: str, fingerprint: str = "", min_confidence: float = 0.0) -> str | None:
        return None

    def store(
        self,
        source_text: str,
        target_lang: str,
        translated_text: str,
        fingerprint: str = "",
        confidence: float = 0.0,
        style_key: str = "",
    ) -> None:
        return None

    def find_similar(
        self,
        source_text: str,
        target_lang: str,
        style_key: str = "",
        limit: int = 2,
        min_score: float = 0.0,
    ) -> list[tuple[float, str, str]]:
        return []

    def downweight(self, source_text: str, target_lang: str, fingerprint: str, confidence: float = 0.0) -> bool:
        return False

    def stats(self) -> dict[str, int]:
        return {"hits": 0, "misses": 0}

    def entry_count(self) -> int:
        return 0

    def clear_all(self) -> int:
        return 0


def build_memory(config) -> MemoryStore:
    from src.infra.config import TranslatorConfig

    if not isinstance(config, TranslatorConfig) or not config.memory.enabled:
        return NullMemory()
    try:
        return TranslationMemory(config.memory.path)
    except Exception as exc:  # pragma: no cover - unreadable path etc.
        logging.warning("Translation memory unavailable (%s); continuing without it", exc)
        return NullMemory()
