from __future__ import annotations

import hashlib
import json
import logging
import threading
from dataclasses import asdict
from pathlib import Path

from src.core.tokens import TOKEN_ESTIMATOR_VERSION
from src.core.types import TranslationResult


class JobCheckpointStore:
    """Per-(file, target-lang) checkpoint of completed bundle translations.

    Bundle results are persisted after each bundle finishes so an interrupted
    job can be resumed with --resume: completed bundles skip the LLM entirely.
    The store records a config fingerprint (model + style); a mismatch between
    runs discards the stale checkpoint.
    """

    def __init__(self, state_dir: str | Path, fingerprint: str = "") -> None:
        self._state_dir = Path(state_dir).expanduser()
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._fingerprint = fingerprint
        self._lock = threading.Lock()

    def _state_path(self, input_path: Path, target_lang: str) -> Path:
        raw = f"{Path(input_path).resolve()}\x00{target_lang}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
        return self._state_dir / f"{digest}.json"

    def load(self, input_path: Path, target_lang: str) -> dict[str, list[TranslationResult]]:
        state_path = self._state_path(input_path, target_lang)
        if not state_path.exists():
            return {}
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logging.warning("Ignoring unreadable checkpoint %s: %s", state_path, exc)
            return {}
        if data.get("fingerprint") != self._fingerprint:
            logging.info("Checkpoint %s was written under a different config; starting fresh", state_path.name)
            return {}
        bundles: dict[str, list[TranslationResult]] = {}
        for bundle_id, items in (data.get("bundles") or {}).items():
            bundles[bundle_id] = [
                TranslationResult(
                    segment_id=item["segment_id"],
                    translated_text=item["translated_text"],
                    notes=list(item.get("notes", [])),
                    applied_terms=dict(item.get("applied_terms", {})),
                    confidence=float(item.get("confidence", 0.0)),
                )
                for item in items
            ]
        return bundles

    def save_bundle(self, input_path: Path, target_lang: str, bundle_id: str, translations: list[TranslationResult]) -> None:
        with self._lock:
            state_path = self._state_path(input_path, target_lang)
            try:
                data = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
            except (OSError, json.JSONDecodeError):
                data = {}
            if data.get("fingerprint") != self._fingerprint:
                data = {"fingerprint": self._fingerprint, "bundles": {}}
            data.setdefault("bundles", {})[bundle_id] = [asdict(item) for item in translations]
            tmp_path = state_path.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            tmp_path.replace(state_path)

    def clear(self, input_path: Path, target_lang: str) -> None:
        with self._lock:
            state_path = self._state_path(input_path, target_lang)
            state_path.unlink(missing_ok=True)

    # Bump when segmentation itself changes (not just its parameters): bundle
    # boundaries and segment ids must never be resumed across versions.
    # structure-v3: budgets moved from characters to estimated tokens.
    SEGMENTATION_VERSION = "structure-v3"

    @classmethod
    def fingerprint(
        cls,
        model: str,
        tone: str,
        audience: str,
        mode: str,
        max_bundle_tokens: int | None = None,
        min_bundle_tokens: int | None = None,
    ) -> str:
        # Segmentation params are part of the key: they decide bundle
        # boundaries, so a checkpoint written under different boundaries must
        # not be resumed against newly built bundles. The estimator version is
        # included because the same budget maps to different text when the
        # estimator weights change.
        raw = f"{model}\x00{tone}\x00{audience}\x00{mode}"
        if max_bundle_tokens is not None:
            raw += (
                f"\x00seg\x00{cls.SEGMENTATION_VERSION}\x00{TOKEN_ESTIMATOR_VERSION}"
                f"\x00{max_bundle_tokens}\x00{min_bundle_tokens}"
            )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
