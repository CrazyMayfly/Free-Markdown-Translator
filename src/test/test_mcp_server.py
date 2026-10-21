from __future__ import annotations

import asyncio
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

MCP_AVAILABLE = importlib.util.find_spec("mcp") is not None


@unittest.skipUnless(MCP_AVAILABLE, "mcp SDK not installed (pip install mdtx[mcp])")
class McpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        from src.mcp_server import server as mcp_server_module

        self.module = mcp_server_module

    def test_tools_registered(self) -> None:
        # Direct call proves the decorator preserved a callable function.
        self.assertTrue(callable(self.module.translate_markdown))
        self.assertTrue(callable(self.module.evaluate_translation))

    def test_translate_markdown_returns_per_language_results(self) -> None:
        from src.core.types import ApiUsageSummary

        class FakePipeline:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def count_bundles(self, input_path, target_lang) -> int:
                return 1

            async def run_async(self, input_path, target_lang, write_output=True, semaphore=None, bundle_progress_callback=None, stage_callback=None):
                self.calls.append(target_lang)
                if bundle_progress_callback is not None:
                    bundle_progress_callback(input_path, target_lang, "bundle-0")
                return SimpleNamespace(
                    output_path=Path(f"{input_path}.{target_lang}.md") if write_output else None,
                    translated_text=f"[{target_lang}] translated",
                    segments=[object()],
                    validation=SimpleNamespace(passed=True, errors=[]),
                    api_usage=ApiUsageSummary(),
                )

        fake = FakePipeline()
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "doc.md"
            input_path.write_text("# Hello\n", encoding="utf-8")
            with patch.object(self.module, "build_pipeline", return_value=fake), patch.object(
                self.module, "build_memory", return_value=None
            ), patch.object(self.module, "_prepare_config", return_value=SimpleNamespace(
                execution=SimpleNamespace(max_parallel_translations=2),
                output=SimpleNamespace(directory=temp_dir),
            )):
                result = asyncio.run(
                    self.module.translate_markdown(str(input_path), ["zh-CN", "ja"], write=False)
                )

        self.assertEqual(sorted(result.keys()), ["ja", "zh-CN"])
        self.assertTrue(result["zh-CN"]["validation_passed"])
        self.assertIn("translated_markdown", result["zh-CN"])
        self.assertEqual(fake.calls, ["zh-CN", "ja"])

    def test_translate_markdown_rejects_missing_file(self) -> None:
        with patch.object(self.module, "_prepare_config", return_value=SimpleNamespace(
            execution=SimpleNamespace(max_parallel_translations=2),
        )):
            with self.assertRaises(FileNotFoundError):
                asyncio.run(self.module.translate_markdown("/nonexistent/doc.md", ["zh-CN"]))


if __name__ == "__main__":
    unittest.main()
