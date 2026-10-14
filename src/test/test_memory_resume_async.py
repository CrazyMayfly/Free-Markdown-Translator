from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.cli.commands import _build_provider
from src.core.pipeline import TranslationPipeline
from src.core.types import TranslationResult
from src.infra.config import TranslatorConfig
from src.llm.client import AsyncOpenAIProvider, OpenAIProvider
from src.memory.checkpoint import JobCheckpointStore
from src.memory.translation_memory import NullMemory, TranslationMemory
from src.parser.markdown_parser import MarkdownParser
from src.parser.segment_extractor import SegmentExtractor
from src.test.test_ast_pipeline import SAMPLE_MARKDOWN, FakeProvider, FormatGuardAgent, ReviewerAgent, TranslatorAgent
from src.validators.markdown_validator import MarkdownValidator


def _pipeline(provider, config, memory=None, checkpoint_store=None) -> TranslationPipeline:
    return TranslationPipeline(
        config=config,
        parser=MarkdownParser(),
        extractor=SegmentExtractor(),
        translator_agent=TranslatorAgent(provider),
        reviewer_agent=ReviewerAgent(provider),
        format_guard_agent=FormatGuardAgent(provider),
        validator=MarkdownValidator(),
        memory=memory,
        checkpoint_store=checkpoint_store,
    )


def _config(**overrides) -> TranslatorConfig:
    config = TranslatorConfig()
    config.pipeline.mode = overrides.get("mode", "balanced")
    config.pipeline.enable_review = overrides.get("enable_review", False)
    config.pipeline.enable_format_guard = overrides.get("enable_format_guard", False)
    config.pipeline.fail_on_validation_error = True
    config.execution.max_parallel_translations = overrides.get("parallel", 4)
    return config


class MemoryTests(unittest.TestCase):
    def test_second_run_reuses_memory_without_llm(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = TranslationMemory(Path(temp_dir) / "memory.sqlite3")
            input_path = Path(temp_dir) / "README.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")

            first_provider = FakeProvider()
            _pipeline(first_provider, _config(), memory=memory).run(input_path, "zh-CN", write_output=False)
            self.assertEqual(first_provider.calls.count("translate"), 1)

            second_provider = FakeProvider()
            result = _pipeline(second_provider, _config(), memory=memory).run(input_path, "zh-CN", write_output=False)
            self.assertEqual(second_provider.calls.count("translate"), 0)
            self.assertEqual(result.translated_text.count("[ZH]"), result.translated_text.count("[ZH]"))
            memory_results = [item for item in result.translations if item.notes == ["translation-memory"]]
            self.assertTrue(memory_results)
            self.assertGreater(memory.stats()["hits"], 0)

    def test_memory_isolated_across_languages_and_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = TranslationMemory(Path(temp_dir) / "memory.sqlite3")
            zh_provider = FakeProvider()
            _pipeline(zh_provider, _config(), memory=memory).run(Path(self._write_sample(temp_dir)), "zh-CN", write_output=False)
            ja_provider = FakeProvider()
            _pipeline(ja_provider, _config(), memory=memory).run(Path(self._write_sample(temp_dir, "b.md")), "ja", write_output=False)
            self.assertEqual(ja_provider.calls.count("translate"), 1)

            # Different style fingerprint invalidates the memory.
            changed = _config()
            changed.style.tone = "casual"
            casual_provider = FakeProvider()
            _pipeline(casual_provider, changed, memory=memory).run(Path(self._write_sample(temp_dir, "c.md")), "zh-CN", write_output=False)
            self.assertEqual(casual_provider.calls.count("translate"), 1)

    @staticmethod
    def _write_sample(temp_dir: str, name: str = "README.md") -> str:
        path = Path(temp_dir) / name
        path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
        return str(path)

    def test_null_memory_always_misses(self) -> None:
        memory = NullMemory()
        self.assertIsNone(memory.find("x", "zh-CN", "fp"))
        memory.store("x", "zh-CN", "y", "fp")
        self.assertIsNone(memory.find("x", "zh-CN", "fp"))


class CheckpointTests(unittest.TestCase):
    def test_resume_skips_completed_bundles_and_clears_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "README.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            state_dir = Path(temp_dir) / "state"
            store = JobCheckpointStore(state_dir, fingerprint="fp1")

            # Simulate an interrupted run: bundle-0 was completed and saved.
            first_provider = FakeProvider()
            first_pipeline = _pipeline(first_provider, _config(), checkpoint_store=store)
            first_pipeline.checkpoint_store.save_bundle(
                input_path,
                "zh-CN",
                "bundle-0",
                [TranslationResult(segment_id=s.segment_id, translated_text=f"[ZH]{s.source_text}", notes=[], applied_terms={}, confidence=0.9) for s in _segments(input_path)],
            )

            resume_provider = FakeProvider()
            _pipeline(resume_provider, _config(), checkpoint_store=store).run(input_path, "zh-CN", write_output=False)
            self.assertEqual(resume_provider.calls.count("translate"), 0)
            # Successful completion clears the checkpoint.
            state_files = list(state_dir.glob("*.json"))
            self.assertEqual(state_files, [])

    def test_checkpoint_fingerprint_mismatch_discards_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "README.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            store = JobCheckpointStore(Path(temp_dir) / "state", fingerprint="old")
            store.save_bundle(input_path, "zh-CN", "bundle-0", [TranslationResult(segment_id="x", translated_text="y")])

            other = JobCheckpointStore(Path(temp_dir) / "state", fingerprint="new")
            self.assertEqual(other.load(input_path, "zh-CN"), {})


def _segments(path: Path):
    parser = MarkdownParser()
    extractor = SegmentExtractor()
    return extractor.extract(parser.parse(path.read_text(encoding="utf-8"), path, "zh-CN"))


class AsyncEquivalenceTests(unittest.TestCase):
    def test_async_and_sync_paths_produce_same_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_a = Path(temp_dir) / "a.md"
            input_b = Path(temp_dir) / "b.md"
            input_a.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            input_b.write_text(SAMPLE_MARKDOWN, encoding="utf-8")

            sync_result = _pipeline(FakeProvider(), _config()).run(input_a, "zh-CN", write_output=False)
            async_result = asyncio.run(_pipeline(FakeProvider(), _config()).run_async(input_b, "zh-CN", write_output=False))
            self.assertEqual(sync_result.translated_text, async_result.translated_text)
            self.assertEqual(sync_result.validation.passed, async_result.validation.passed)


class ProviderConfigTests(unittest.TestCase):
    def test_build_provider_returns_async_with_retry_config(self) -> None:
        config = TranslatorConfig()
        config.provider.max_retries = 5
        with patch("src.llm.client.AsyncOpenAI") as async_client:
            provider = _build_provider(config)
        self.assertIsInstance(provider, AsyncOpenAIProvider)
        self.assertEqual(async_client.call_args.kwargs["max_retries"], 5)

    def test_sync_provider_passes_max_retries(self) -> None:
        with patch("src.llm.client.OpenAI") as sync_client:
            OpenAIProvider(
                base_url="http://localhost:1",
                api_key="k",
                api_key_env="",
                model="m",
                temperature=0.1,
                max_tokens=8,
                max_retries=7,
            )
        self.assertEqual(sync_client.call_args.kwargs["max_retries"], 7)

    def test_cached_tokens_recorded_in_usage(self) -> None:
        with patch("src.llm.client.OpenAI"):
            provider = OpenAIProvider(
                base_url="http://localhost:1",
                api_key="k",
                api_key_env="",
                model="m",
                temperature=0.1,
                max_tokens=8,
            )
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok":true}'))],
            usage=SimpleNamespace(
                prompt_tokens=100,
                completion_tokens=10,
                total_tokens=110,
                prompt_tokens_details=SimpleNamespace(cached_tokens=64),
            ),
        )
        with patch.object(provider.client.chat.completions, "create", return_value=response):
            provider.chat_json("s", "{}")
        summary = provider.get_usage_summary()
        self.assertEqual(summary.total.cached_tokens, 64)


if __name__ == "__main__":
    unittest.main()
