from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agents.format_guard_agent import FormatGuardAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.translator_agent import TranslatorAgent
from src.api.jobs import JobManager, JobParams
from src.core.pipeline import TranslationPipeline
from src.core.types import ApiUsageSummary
from src.infra.config import TranslatorConfig
from src.parser.markdown_parser import MarkdownParser
from src.parser.segment_extractor import SegmentExtractor
from src.test.test_ast_pipeline import FakeProvider
from src.validators.markdown_validator import MarkdownValidator

# Each section is well past section_align_min_chars (400), so every heading
# after the first starts a new bundle: N sections -> exactly N bundles, and
# each bundle stays under review_min_segments (6) so only "translate" fires.
_FILLER = (
    "This paragraph deliberately runs long enough to push the current bundle "
    "past the section alignment threshold, so the next heading is forced to "
    "start a fresh bundle of its own. "
)


def _sectioned_document(sections: int) -> str:
    parts = ["# Concurrency Fixture", ""]
    for index in range(sections):
        parts.append(f"## Section {index}")
        parts.append("")
        parts.extend([_FILLER] * 3)
        parts.append("")
    return "\n".join(parts)


class ConcurrencyTrackingProvider(FakeProvider):
    """FakeProvider that records the peak number of simultaneous LLM calls."""

    def __init__(self) -> None:
        super().__init__()
        self.in_flight = 0
        self.max_in_flight = 0

    async def chat_json_async(self, system_prompt: str, user_prompt: str, call_label: str = "llm", response_schema: dict | None = None):
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(0)  # yield so sibling bundles can interleave
            return self.chat_json(system_prompt, user_prompt, call_label, response_schema)
        finally:
            self.in_flight -= 1


class _SemaphoreTests(unittest.TestCase):
    def _pipeline(self, provider: ConcurrencyTrackingProvider, config: TranslatorConfig) -> TranslationPipeline:
        return TranslationPipeline(
            config=config,
            parser=MarkdownParser(),
            extractor=SegmentExtractor(),
            translator_agent=TranslatorAgent(provider),
            reviewer_agent=ReviewerAgent(provider),
            format_guard_agent=FormatGuardAgent(provider),
            validator=MarkdownValidator(),
        )

    def _config(self, parallel: int) -> TranslatorConfig:
        config = TranslatorConfig()
        config.pipeline.mode = "balanced"
        config.pipeline.enable_review = False
        config.pipeline.enable_format_guard = False
        config.pipeline.fail_on_validation_error = True
        config.execution.max_parallel_translations = parallel
        return config

    def test_semaphore_one_serializes_all_llm_calls(self) -> None:
        provider = ConcurrencyTrackingProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "doc.md"
            input_path.write_text(_sectioned_document(6), encoding="utf-8")
            result = asyncio.run(self._pipeline(provider, self._config(1)).run_async(input_path, "zh-CN", write_output=False))

        self.assertTrue(result.validation.passed)
        self.assertEqual(provider.calls.count("translate"), 6)  # sanity: 6 bundles ran
        self.assertEqual(provider.max_in_flight, 1)

    def test_semaphore_three_overlaps_but_never_exceeds_limit(self) -> None:
        provider = ConcurrencyTrackingProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "doc.md"
            input_path.write_text(_sectioned_document(6), encoding="utf-8")
            result = asyncio.run(self._pipeline(provider, self._config(3)).run_async(input_path, "zh-CN", write_output=False))

        self.assertTrue(result.validation.passed)
        self.assertEqual(provider.calls.count("translate"), 6)
        self.assertEqual(provider.max_in_flight, 3)


class GrowingUsageProvider:
    """Provider whose token totals grow per bundle, like the real ones."""

    def __init__(self, prompt_per_bundle: int, completion_per_bundle: int) -> None:
        self._prompt = prompt_per_bundle
        self._completion = completion_per_bundle
        self._bundles = 0

    def record_bundle(self) -> None:
        self._bundles += 1

    def get_usage_summary(self) -> ApiUsageSummary:
        summary = ApiUsageSummary()
        for _ in range(self._bundles):
            summary.add("translate", self._prompt, self._completion, self._prompt + self._completion, cached_tokens=8)
        return summary


class _UsagePipeline:
    """Minimal pipeline stand-in exposing translator_agent.provider to jobs.py."""

    def __init__(self, provider: GrowingUsageProvider, delay: float) -> None:
        self.translator_agent = SimpleNamespace(provider=provider)
        self._delay = delay

    def count_bundles(self, input_path, target_lang) -> int:
        return 2

    async def run_async(self, input_path, target_lang, write_output=True, output_path=None, semaphore=None, bundle_progress_callback=None):
        for index in range(2):
            await asyncio.sleep(self._delay)
            self.translator_agent.provider.record_bundle()
            if bundle_progress_callback is not None:
                bundle_progress_callback(input_path, target_lang, f"bundle-{index}")
        if write_output and output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(f"[{target_lang}] ok", encoding="utf-8")
        return SimpleNamespace(
            input_path=input_path,
            output_path=output_path if write_output else None,
            translated_text=f"[{target_lang}] ok",
            segments=[],
            translations=[],
            validation=SimpleNamespace(passed=True, errors=[], warnings=[]),
            api_usage=self.translator_agent.provider.get_usage_summary(),
            report={},
            context=None,
        )


class UsageAccountingTests(unittest.TestCase):
    def test_concurrent_pairs_accumulate_usage_incrementally(self) -> None:
        """Deltas, not snapshots: both pairs' tokens must survive interleaving.

        Pairs progress at different speeds and their usage grows between
        progress callbacks. Absolute snapshots would clobber each other, so
        the final job usage must equal the exact sum of both providers.
        """
        async def scenario():
            with tempfile.TemporaryDirectory() as temp_dir:
                sample = Path(temp_dir) / "doc.md"
                sample.write_text("# Hello\n\nWorld.\n", encoding="utf-8")
                output_dir = Path(temp_dir) / "out"
                config = TranslatorConfig()
                config.output.directory = str(output_dir)
                config.provider.api_key = None

                fast = GrowingUsageProvider(prompt_per_bundle=100, completion_per_bundle=10)
                slow = GrowingUsageProvider(prompt_per_bundle=250, completion_per_bundle=10)
                # 2 bundles each: fast pair (100/bundle) + slow pair (250/bundle).
                expected = {
                    "prompt": 2 * 100 + 2 * 250,
                    "completion": 2 * 10 + 2 * 10,
                    "total": 2 * 110 + 2 * 260,
                    "cached": 4 * 8,
                    "calls": 4,
                }

                fakes = [_UsagePipeline(fast, 0.03), _UsagePipeline(slow, 0.07)]
                manager = JobManager(config_loader=lambda: config)
                with patch("src.api.jobs.build_pipeline", side_effect=lambda *a, **kw: fakes.pop(0)):
                    job = manager.create(JobParams(paths=[str(sample)], target_langs=["zh-CN", "en"], output_dir=str(output_dir)))
                    assert job.task is not None
                    await job.task

                self.assertEqual(job.status, "completed")
                self.assertEqual(job.usage, expected)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
