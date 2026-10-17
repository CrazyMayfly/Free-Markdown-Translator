from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


class MemoryStore(Protocol):
    """Translation memory interface shared by TranslationMemory and NullMemory."""

    def find(self, source_text: str, target_lang: str, fingerprint: str = "", min_confidence: float = 0.0) -> str | None: ...

    def peek(self, source_text: str, target_lang: str, fingerprint: str = "", min_confidence: float = 0.0) -> str | None: ...

    def store(
        self,
        source_text: str,
        target_lang: str,
        translated_text: str,
        fingerprint: str = "",
        confidence: float = 0.0,
        style_key: str = "",
    ) -> None: ...

    def find_similar(self, source_text: str, target_lang: str, style_key: str = "", limit: int = 2, min_score: float = 0.0) -> list[tuple[float, str, str]]: ...

    def downweight(self, source_text: str, target_lang: str, fingerprint: str, confidence: float = 0.0) -> bool: ...

    def stats(self) -> dict[str, int]: ...


@dataclass
class ApiTokenUsage:
    call_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0

    def add(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        call_count: int = 1,
        cached_tokens: int = 0,
    ) -> None:
        self.call_count += call_count
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += total_tokens
        self.cached_tokens += cached_tokens


@dataclass
class ApiUsageSummary:
    total: ApiTokenUsage = field(default_factory=ApiTokenUsage)
    by_call_label: dict[str, ApiTokenUsage] = field(default_factory=dict)

    def add(self, call_label: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, cached_tokens: int = 0) -> None:
        self.total.add(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cached_tokens=cached_tokens,
        )
        self.by_call_label.setdefault(call_label, ApiTokenUsage()).add(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cached_tokens=cached_tokens,
        )

    def merge(self, other: ApiUsageSummary) -> None:
        self.total.add(
            prompt_tokens=other.total.prompt_tokens,
            completion_tokens=other.total.completion_tokens,
            total_tokens=other.total.total_tokens,
            call_count=other.total.call_count,
            cached_tokens=other.total.cached_tokens,
        )
        for call_label, usage in other.by_call_label.items():
            self.by_call_label.setdefault(call_label, ApiTokenUsage()).add(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                call_count=usage.call_count,
                cached_tokens=usage.cached_tokens,
            )


@dataclass
class ProtectedSpan:
    placeholder: str
    original_text: str
    span_type: str


@dataclass
class Segment:
    segment_id: str
    node_type: str
    source_text: str
    context_path: list[str]
    line_start: int
    line_end: int
    metadata: dict[str, Any] = field(default_factory=dict)
    protected_spans: list[ProtectedSpan] = field(default_factory=list)


@dataclass
class SegmentBundle:
    bundle_id: str
    segments: list[Segment]
    summary_before: str
    summary_after: str
    style_instructions: list[str]
    # Fuzzy translation-memory neighbours: segment_id -> [{source, translation}]
    # prior renderings of similar source text, injected as few-shot examples.
    similar_examples: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    # Already-translated segments that open this bundle's section (from the
    # section's anchor bundle): real target-language context for continuity.
    anchor_translations: list[dict[str, str]] = field(default_factory=list)


@dataclass
class TranslationResult:
    segment_id: str
    translated_text: str
    notes: list[str] = field(default_factory=list)
    applied_terms: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class TranslationOutcome:
    """Translator output plus optional pull-style context requests.

    context_requests is the model asking for more context it could not see
    (e.g. deeper translation-memory search for a specific segment); the
    pipeline answers the request and translates once more.
    """

    translations: list[TranslationResult] = field(default_factory=list)
    context_requests: list[dict] = field(default_factory=list)


@dataclass
class ValidationReport:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentContext:
    title: str
    abstract: str
    section_summaries: dict[str, str]
    style_guide: list[str]
    audience: str
    # Document map shared by every bundle: all headings in document order and
    # the authoritative term -> rendering glossary for this run.
    heading_outline: list[str] = field(default_factory=list)
    glossary: dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    source_path: Path
    source_text: str
    body_text: str
    target_lang: str
    ast: list[Any]
    metadata: dict[str, Any]
    lines: list[str]
    body_line_offset: int = 0


@dataclass
class PipelineResult:
    input_path: Path
    output_path: Path | None
    translated_text: str
    segments: list[Segment]
    translations: list[TranslationResult]
    validation: ValidationReport
    api_usage: ApiUsageSummary = field(default_factory=ApiUsageSummary)
    report: dict[str, Any] = field(default_factory=dict)
    context: DocumentContext | None = None
