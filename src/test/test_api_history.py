"""Tests for persistent job history, segment editing, salvage and config probe."""

from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.api.app import create_app
from src.api.history import JobHistory, rerender_markdown
from src.core.errors import OutputWriteError
from src.infra.config import TranslatorConfig
from src.parser.markdown_parser import MarkdownParser
from src.parser.segment_extractor import SegmentExtractor
from src.test.test_ast_pipeline import SAMPLE_MARKDOWN

_SUMMARY = {
    "id": "hist0001",
    "status": "completed",
    "created_at": 1.0,
    "finished_at": 2.0,
    "error": None,
    "pairs": ["a.md -> en"],
    "usage": {"prompt": 10, "completion": 5, "total": 15, "cached": 0, "calls": 1},
    "result_count": 1,
}


def _seed_result(markdown: str = "# T\n\nalpha\n\nalpha\n") -> dict:
    return {
        "input_path": "/tmp/a.md",
        "output_path": None,
        "target_lang": "en",
        "translated_markdown": markdown,
        "validation": {"passed": True, "errors": [], "warnings": []},
        "usage": {"prompt": 10, "completion": 5, "total": 15, "cached": 0, "calls": 1},
        "segments": [
            {"segment_id": "s1", "context_path": "", "source": "A", "translated": "alpha", "confidence": 0.9},
            {"segment_id": "s2", "context_path": "", "source": "A", "translated": "alpha", "confidence": 0.9},
        ],
        "judge": None,
    }


def _history_with(path: Path, result: dict | None = None) -> JobHistory:
    history = JobHistory(path)
    history.save(dict(_SUMMARY), [result or _seed_result()])
    return history


def _app_with_history(history: JobHistory | None, output_dir: str):
    config = TranslatorConfig()
    config.output.directory = output_dir
    config.provider.api_key = None
    return create_app(history=history, config_loader=lambda: config)


def _write_sample(temp_dir: str) -> Path:
    path = Path(temp_dir) / "doc.md"
    path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
    return path


class RerenderTests(unittest.TestCase):
    def test_edits_apply_in_document_order_with_duplicates(self) -> None:
        markdown = "# T\n\nalpha\n\nalpha\n"
        segments = [
            {"segment_id": "s1", "translated": "alpha"},
            {"segment_id": "s2", "translated": "alpha"},
        ]
        edited = rerender_markdown(markdown, segments, {"s1": "alpha-1", "s2": "beta-2"})
        self.assertEqual(edited, "# T\n\nalpha-1\n\nbeta-2\n")

    def test_unedited_segments_pass_through(self) -> None:
        segments = [{"segment_id": "s1", "translated": "missing"}]
        self.assertEqual(rerender_markdown("# T\n\nkeep\n", segments, {}), "# T\n\nkeep\n")


class HistoryPersistenceTests(unittest.TestCase):
    def test_job_survives_new_app_instance(self) -> None:
        async def scenario():
            with tempfile.TemporaryDirectory() as temp_dir:
                sample = _write_sample(temp_dir)
                output_dir = Path(temp_dir) / "out"
                history_path = Path(temp_dir) / "history.sqlite3"
                from src.test.test_api_layer import FakeUiPipeline

                pipeline = FakeUiPipeline()
                history = JobHistory(history_path)
                app = create_app(history=history, config_loader=lambda: _config(str(output_dir)))
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    with patch("src.api.jobs.build_pipeline", return_value=pipeline):
                        response = await client.post(
                            "/api/jobs",
                            json={"paths": [str(sample)], "target_langs": ["zh-CN"], "output_dir": str(output_dir)},
                        )
                        job_id = response.json()["id"]
                        for _ in range(100):
                            detail = (await client.get(f"/api/jobs/{job_id}")).json()
                            if detail["status"] in {"completed", "failed", "cancelled"}:
                                break
                            await asyncio.sleep(0.05)
                    self.assertEqual(detail["status"], "completed")

                # Fresh app over the same history file: live job is gone, the
                # record must come back from SQLite.
                fresh_app = _app_with_history(JobHistory(history_path), str(output_dir))
                fresh_transport = httpx.ASGITransport(app=fresh_app)
                async with httpx.AsyncClient(transport=fresh_transport, base_url="http://test") as client:
                    record = (await client.get(f"/api/jobs/{job_id}")).json()
                    self.assertEqual(record["status"], "completed")
                    self.assertEqual(len(record["results"]), 1)
                    self.assertTrue(record["results"][0]["translated_markdown"])

                    listed = (await client.get("/api/history")).json()
                    self.assertIn(job_id, [item["id"] for item in listed])

                    deleted = await client.delete(f"/api/history/{job_id}")
                    self.assertEqual(deleted.status_code, 200)
                    missing = await client.get(f"/api/jobs/{job_id}")
                    self.assertEqual(missing.status_code, 404)

        asyncio.run(scenario())

    def test_live_edit_resave_keeps_params_in_history(self) -> None:
        """Re-saving history from the live-job edit path must not drop params."""
        async def scenario():
            with tempfile.TemporaryDirectory() as temp_dir:
                sample = _write_sample(temp_dir)
                output_dir = Path(temp_dir) / "out"
                history_path = Path(temp_dir) / "history.sqlite3"
                from src.test.test_api_layer import FakeUiPipeline

                pipeline = FakeUiPipeline()
                app = create_app(history=JobHistory(history_path), config_loader=lambda: _config(str(output_dir)))
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    with patch("src.api.jobs.build_pipeline", return_value=pipeline):
                        response = await client.post(
                            "/api/jobs",
                            json={"paths": [str(sample)], "target_langs": ["zh-CN"], "output_dir": str(output_dir)},
                        )
                        job_id = response.json()["id"]
                        for _ in range(100):
                            detail = (await client.get(f"/api/jobs/{job_id}")).json()
                            if detail["status"] in {"completed", "failed", "cancelled"}:
                                break
                            await asyncio.sleep(0.05)

                        edited = await client.put(
                            f"/api/jobs/{job_id}/results/0/segments/body-0",
                            json={"text": "改"},
                        )
                        self.assertEqual(edited.status_code, 200, edited.text)

                        record = JobHistory(history_path).get(job_id)
                        assert record is not None
                        self.assertIsNotNone(record.get("params"))
                        self.assertEqual(record["params"]["target_langs"], ["zh-CN"])

        asyncio.run(scenario())

    def test_segment_edit_and_save_from_history(self) -> None:
        async def scenario():
            with tempfile.TemporaryDirectory() as temp_dir:
                history_path = Path(temp_dir) / "history.sqlite3"
                app = _app_with_history(_history_with(path=history_path), temp_dir)
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    edited = await client.put(
                        "/api/jobs/hist0001/results/0/segments/s2",
                        json={"text": "beta"},
                    )
                    self.assertEqual(edited.status_code, 200, edited.text)
                    result = edited.json()["result"]
                    self.assertEqual(result["segments"][0]["translated"], "alpha")
                    self.assertEqual(result["segments"][1]["translated"], "beta")
                    # Only the second occurrence was replaced.
                    self.assertEqual(result["translated_markdown"], "# T\n\nalpha\n\nbeta\n")

                    saved = await client.post(
                        "/api/jobs/hist0001/results/0/save",
                        json={"path": str(Path(temp_dir) / "fixed.md")},
                    )
                    self.assertEqual(saved.status_code, 200, saved.text)
                    self.assertEqual(Path(saved.json()["path"]).read_text(encoding="utf-8"), "# T\n\nalpha\n\nbeta\n")

                    # Editing a second time works (edited text is now in the doc).
                    again = await client.put(
                        "/api/jobs/hist0001/results/0/segments/s2",
                        json={"text": "gamma"},
                    )
                    self.assertEqual(again.json()["result"]["translated_markdown"], "# T\n\nalpha\n\ngamma\n")

        asyncio.run(scenario())


class SalvageTests(unittest.TestCase):
    def test_write_failure_keeps_translation_and_history(self) -> None:
        async def scenario():
            with tempfile.TemporaryDirectory() as temp_dir:
                sample = _write_sample(temp_dir)
                output_dir = Path(temp_dir) / "out"
                history_path = Path(temp_dir) / "history.sqlite3"

                segments = SegmentExtractor().extract(
                    MarkdownParser().parse(SAMPLE_MARKDOWN, sample, "zh-CN")
                )
                translations = [
                    SimpleNamespace(segment_id=s.segment_id, translated_text="[zh]译文", confidence=0.9)
                    for s in segments
                ]

                class BrokenWritePipeline:
                    def count_bundles(self, input_path, target_lang) -> int:
                        return 1

                    async def run_async(self, input_path, target_lang, write_output=True, output_path=None, semaphore=None, bundle_progress_callback=None):
                        raise OutputWriteError(
                            "写入输出文件失败: [Errno 30] Read-only file system",
                            output_text="[zh]完整译文",
                            output_path=output_path,
                            validation=SimpleNamespace(passed=True, errors=[], warnings=[]),
                            segments=segments,
                            translations=translations,
                        )

                pipeline = BrokenWritePipeline()
                app = create_app(history=JobHistory(history_path), config_loader=lambda: _config(str(output_dir)))
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    with patch("src.api.jobs.build_pipeline", return_value=pipeline):
                        response = await client.post(
                            "/api/jobs",
                            json={"paths": [str(sample)], "target_langs": ["zh-CN"], "output_dir": str(output_dir)},
                        )
                        job_id = response.json()["id"]
                        for _ in range(100):
                            detail = (await client.get(f"/api/jobs/{job_id}")).json()
                            if detail["status"] in {"completed", "failed", "cancelled"}:
                                break
                            await asyncio.sleep(0.05)

                    self.assertEqual(detail["status"], "completed")
                    result = detail["results"][0]
                    self.assertTrue(result["write_error"])
                    self.assertEqual(result["translated_markdown"], "[zh]完整译文")
                    self.assertTrue(result["segments"])

                    record = _app_with_history(JobHistory(history_path), str(output_dir)).state.history.get(job_id)
                    self.assertIsNotNone(record)
                    self.assertEqual(record["results"][0]["translated_markdown"], "[zh]完整译文")

        asyncio.run(scenario())


class ConfigTestRouteTests(unittest.TestCase):
    def test_probe_success_reports_models_and_latency(self) -> None:
        async def scenario():
            app = _app_with_history(None, tempfile.gettempdir())
            transport = httpx.ASGITransport(app=app)
            fake_response = SimpleNamespace(
                status_code=200,
                text="",
                json=lambda: {"data": [{"id": "fast"}, {"id": "big"}]},
            )
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                with patch("httpx.get", return_value=fake_response) as mock_get:
                    body = await client.post(
                        "/api/config/test",
                        json={"base_url": "http://mini:8010/v1", "api_key": "sk-x", "model": "fast"},
                    )
                    self.assertEqual(body.status_code, 200, body.text)
                    data = body.json()
                    self.assertTrue(data["ok"])
                    self.assertIsNone(data["model_warning"])
                    self.assertEqual(data["models"], ["fast", "big"])
                    self.assertIsInstance(data["latency_ms"], int)
                    called_url = mock_get.call_args.args[0]
                    self.assertEqual(called_url, "http://mini:8010/v1/models")

        asyncio.run(scenario())

    def test_probe_unknown_model_warns_but_stays_ok(self) -> None:
        async def scenario():
            app = _app_with_history(None, tempfile.gettempdir())
            transport = httpx.ASGITransport(app=app)
            fake_response = SimpleNamespace(
                status_code=200,
                text="",
                json=lambda: {"data": [{"id": "glm-5.3"}]},
            )
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                with patch("httpx.get", return_value=fake_response):
                    body = await client.post(
                        "/api/config/test",
                        json={"base_url": "http://mini:8010/v1", "model": "fast"},
                    )
                    data = body.json()
                    # Virtual aliases work on many gateways despite /models.
                    self.assertTrue(data["ok"])
                    self.assertIn("fast", data["model_warning"])

        asyncio.run(scenario())

    def test_probe_connection_failure(self) -> None:
        async def scenario():
            app = _app_with_history(None, tempfile.gettempdir())
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
                    body = await client.post(
                        "/api/config/test",
                        json={"base_url": "http://mini:8010/v1"},
                    )
                    self.assertEqual(body.status_code, 200, body.text)
                    data = body.json()
                    self.assertFalse(data["ok"])
                    self.assertIn("连接失败", data["error"])

        asyncio.run(scenario())


def _config(output_dir: str) -> TranslatorConfig:
    config = TranslatorConfig()
    config.output.directory = output_dir
    config.provider.api_key = None
    return config


if __name__ == "__main__":
    unittest.main()
