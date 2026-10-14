from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ApiTokenUsage:
    call_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, prompt_tokens: int, completion_tokens: int, total_tokens: int, call_count: int = 1) -> None:
        self.call_count += call_count
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += total_tokens


@dataclass
class ApiUsageSummary:
    total: ApiTokenUsage = field(default_factory=ApiTokenUsage)
    by_call_label: dict[str, ApiTokenUsage] = field(default_factory=dict)

    def add(self, call_label: str, prompt_tokens: int, completion_tokens: int, total_tokens: int) -> None:
        self.total.add(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
        self.by_call_label.setdefault(call_label, ApiTokenUsage()).add(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    def merge(self, other: "ApiUsageSummary") -> None:
        self.total.add(
            prompt_tokens=other.total.prompt_tokens,
            completion_tokens=other.total.completion_tokens,
            total_tokens=other.total.total_tokens,
            call_count=other.total.call_count,
        )
        for call_label, usage in other.by_call_label.items():
            self.by_call_label.setdefault(call_label, ApiTokenUsage()).add(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                call_count=usage.call_count,
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


@dataclass
class TranslationResult:
    segment_id: str
    translated_text: str
    notes: list[str] = field(default_factory=list)
    applied_terms: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0


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
