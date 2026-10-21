from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.api.app import API_KEY_MASK, create_app
from src.core.types import ApiUsageSummary
from src.infra.config import TranslatorConfig
from src.memory.translation_memory import TranslationMemory
from src.parser.markdown_parser import MarkdownParser
from src.parser.segment_extractor import SegmentExtractor
from src.test.test_ast_pipeline import SAMPLE_MARKDOWN


def _fake_result(input_path: Path, target_lang: str, output_path: Path | None):
    segments = SegmentExtractor().extract(MarkdownParser().parse(SAMPLE_MARKDOWN, input_path, target_lang))
    usage = ApiUsageSummary()
    usage.add("translate", 100, 20, 120, cached_tokens=64)
    return SimpleNamespace(
        input_path=input_path,
        output_path=output_path,
        translated_text=f"[{target_lang}] done",
        segments=segments,
        translations=[
            SimpleNamespace(segment_id=s.segment_id, translated_text=f"[{target_lang}]{s.source_text}", confidence=0.9)
            for s in segments
        ],
        validation=SimpleNamespace(passed=True, errors=[], warnings=[]),
        api_usage=usage,
        report={},
        context=None,
    )


class FakeUiPipeline:
    def __init__(self, delay: float = 0.0) -> None:
        self.delay = delay
        self.calls: list[tuple[Path, str]] = []

    def count_bundles(self, input_path, target_lang) -> int:
        return 2

    async def run_async(self, input_path, target_lang, write_output=True, output_path=None, semaphore=None, bundle_progress_callback=None, stage_callback=None):
        self.calls.append((input_path, target_lang))
        for index in range(2):
            if self.delay:
                await asyncio.sleep(self.delay)
            if bundle_progress_callback is not None:
                bundle_progress_callback(input_path, target_lang, f"bundle-{index}")
        if write_output and output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(f"[{target_lang}] done", encoding="utf-8")
        return _fake_result(input_path, target_lang, output_path if write_output else None)


def _test_config(output_dir: str) -> TranslatorConfig:
    config = TranslatorConfig()
    config.output.directory = output_dir
    config.provider.api_key = None
    return config


def _make_app(pipeline: FakeUiPipeline, output_dir: str, memory=None):
    config = _test_config(output_dir)
    return create_app(memory=memory, config_loader=lambda: config), config


def _write_sample(temp_dir: str) -> Path:
    path = Path(temp_dir) / "doc.md"
    path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
    return path


async def _post_json(client, url, payload):
    response = await client.post(url, json=payload)
    return response


class JobLifecycleTests(unittest.TestCase):
    def _run(self, coroutine):
        return asyncio.run(coroutine)

    def test_submit_progress_and_result(self) -> None:
        async def scenario():
            with tempfile.TemporaryDirectory() as temp_dir:
                sample = _write_sample(temp_dir)
                output_dir = Path(temp_dir) / "out"
                pipeline = FakeUiPipeline()
                app, config = _make_app(pipeline, str(output_dir))
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    with patch("src.api.jobs.build_pipeline", return_value=pipeline):
                        response = await client.post(
                            "/api/jobs",
                            json={"paths": [str(sample)], "target_langs": ["zh-CN"], "output_dir": str(output_dir)},
                        )
                        self.assertEqual(response.status_code, 200, response.text)
                        job_id = response.json()["id"]

                        detail = (await client.get(f"/api/jobs/{job_id}")).json()
                        for _ in range(100):
                            if detail["status"] in {"completed", "failed", "cancelled"}:
                                break
                            await asyncio.sleep(0.05)
                            detail = (await client.get(f"/api/jobs/{job_id}")).json()

                    self.assertEqual(detail["status"], "completed")
                    self.assertEqual(len(detail["results"]), 1)
                    result = detail["results"][0]
                    self.assertEqual(result["target_lang"], "zh-CN")
                    self.assertTrue(result["validation"]["passed"])
                    self.assertEqual(result["usage"]["cached"], 64)
                    self.assertTrue(result["segments"])
                    self.assertEqual(pipeline.calls, [(sample, "zh-CN")])
                    # Translated file written under output dir.
                    self.assertTrue((output_dir / "doc.zh.md").exists())

                    # SSE replay contains the full event sequence and terminates.
                    events = []
                    async with client.stream("GET", f"/api/jobs/{job_id}/events") as stream_response:
                        async for line in stream_response.aiter_lines():
                            if line.startswith("event: "):
                                events.append(line[len("event: "):])
                    self.assertEqual(events[0], "status")
                    self.assertIn("pair_start", events)
                    self.assertEqual(events.count("progress"), 2)
                    self.assertIn("pair_done", events)
                    self.assertEqual(events[-1], "end")

        self._run(scenario())

    def test_pairs_run_in_parallel(self) -> None:
        """Both pairs must start before either finishes (TaskGroup, not a for-loop)."""
        async def scenario():
            with tempfile.TemporaryDirectory() as temp_dir:
                sample = _write_sample(temp_dir)
                output_dir = Path(temp_dir) / "out"
                pipeline = FakeUiPipeline(delay=0.3)
                app, _ = _make_app(pipeline, str(output_dir))
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    with patch("src.api.jobs.build_pipeline", return_value=pipeline):
                        response = await client.post(
                            "/api/jobs",
                            json={"paths": [str(sample)], "target_langs": ["zh-CN", "en"], "output_dir": str(output_dir)},
                        )
                        job_id = response.json()["id"]
                        for _ in range(200):
                            detail = (await client.get(f"/api/jobs/{job_id}")).json()
                            if detail["status"] in {"completed", "failed", "cancelled"}:
                                break
                            await asyncio.sleep(0.05)
                        self.assertEqual(detail["status"], "completed")
                        self.assertEqual(len(detail["results"]), 2)

                        events = []
                        async with client.stream("GET", f"/api/jobs/{job_id}/events") as stream_response:
                            current_type = None
                            async for line in stream_response.aiter_lines():
                                if line.startswith("event: "):
                                    current_type = line[len("event: "):]
                                elif line.startswith("data: ") and current_type not in (None, "end"):
                                    events.append({"type": current_type, **json.loads(line[len("data: "):])})
                        starts = [i for i, event in enumerate(events) if event["type"] == "pair_start"]
                        dones = [i for i, event in enumerate(events) if event["type"] == "pair_done"]
                        self.assertEqual(len(starts), 2)
                        self.assertEqual(len(dones), 2)
                        self.assertLess(max(starts), min(dones), f"pairs did not interleave: {events}")

        self._run(scenario())

    def test_cancel_running_job(self) -> None:
        async def scenario():
            with tempfile.TemporaryDirectory() as temp_dir:
                sample = _write_sample(temp_dir)
                pipeline = FakeUiPipeline(delay=30.0)
                app, _ = _make_app(pipeline, str(Path(temp_dir) / "out"))
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    with patch("src.api.jobs.build_pipeline", return_value=pipeline):
                        response = await client.post(
                            "/api/jobs",
                            json={"paths": [str(sample)], "target_langs": ["zh-CN"]},
                        )
                        job_id = response.json()["id"]
                        await asyncio.sleep(0.2)  # let the job start
                        cancel_response = await client.post(f"/api/jobs/{job_id}/cancel")
                    self.assertTrue(cancel_response.json()["cancel_requested"])

                    for _ in range(100):
                        detail = (await client.get(f"/api/jobs/{job_id}")).json()
                        if detail["status"] == "cancelled":
                            break
                        await asyncio.sleep(0.05)
                    self.assertEqual(detail["status"], "cancelled")

        self._run(scenario())

    def test_memory_routes_report_and_clear(self) -> None:
        async def scenario():
            with tempfile.TemporaryDirectory() as temp_dir:
                memory = TranslationMemory(Path(temp_dir) / "memory.sqlite3")
                memory.store("hello", "zh-CN", "你好", "fp", 0.9)
                memory.store("world", "zh-CN", "世界", "fp", 0.9)
                app, _ = _make_app(FakeUiPipeline(), temp_dir, memory=memory)
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    stats = (await client.get("/api/memory/stats")).json()
                    self.assertEqual(stats["entries"], 2)

                    cleared = await client.delete("/api/memory")
                    self.assertEqual(cleared.json()["removed"], 2)
                    stats_after = (await client.get("/api/memory/stats")).json()
                    self.assertEqual(stats_after["entries"], 0)

        self._run(scenario())

    def test_submit_rejects_missing_file(self) -> None:
        async def scenario():
            app, _ = _make_app(FakeUiPipeline(), "/tmp")
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/api/jobs", json={"paths": ["/no/such/file.md"], "target_langs": ["zh-CN"]})
                self.assertEqual(response.status_code, 400)

        self._run(scenario())

    def test_unknown_job_404(self) -> None:
        async def scenario():
            app, _ = _make_app(FakeUiPipeline(), "/tmp")
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                self.assertEqual((await client.get("/api/jobs/nope")).status_code, 404)
                self.assertEqual((await client.get("/api/jobs/nope/events")).status_code, 404)

        self._run(scenario())


class ConfigRouteTests(unittest.TestCase):
    def _run(self, coroutine):
        return asyncio.run(coroutine)

    def test_get_config_masks_api_key(self) -> None:
        async def scenario():
            config = TranslatorConfig()
            config.provider.api_key = "sk-secret-value"
            app = create_app(config_loader=lambda: config)
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                data = (await client.get("/api/config")).json()
            self.assertEqual(data["config"]["provider"]["api_key"], API_KEY_MASK)
            self.assertNotIn("sk-secret-value", json.dumps(data))
            # Every PipelineConfig toggle the ConfigView renders must be
            # present, or the form silently shows unchecked boxes.
            pipeline = data["config"]["pipeline"]
            for key in (
                "enable_glossary",
                "enable_sentinels",
                "enable_anchor_scheduling",
                "enable_context_pull",
                "enable_final_edit",
            ):
                self.assertIn(key, pipeline)
                self.assertTrue(pipeline[key])
            self.assertIn("reviewer_model", pipeline)
            self.assertIn("judge_model", pipeline)
            self.assertIn("max_bundle_tokens", data["config"]["segmentation"])
            self.assertIn("min_bundle_tokens", data["config"]["segmentation"])
            self.assertIn("scope", data["config"]["memory"])

        self._run(scenario())

    def test_patch_config_preserves_masked_key(self) -> None:
        async def scenario():
            with tempfile.TemporaryDirectory() as temp_dir:
                config_path = Path(temp_dir) / "config.yaml"
                config_path.write_text("provider:\n  api_key: sk-keep-me\n  model: m1\n", encoding="utf-8")
                config = TranslatorConfig()
                config.provider.api_key = "sk-keep-me"
                app = create_app(config_loader=lambda: config)
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    with patch("src.api.app._config_file_path", return_value=config_path):
                        response = await client.patch(
                            "/api/config",
                            json={"provider": {"model": "m2", "api_key": API_KEY_MASK}},
                        )
                    self.assertEqual(response.status_code, 200, response.text)
                on_disk = config_path.read_text(encoding="utf-8")
                self.assertIn("sk-keep-me", on_disk)
                self.assertIn("m2", on_disk)

        self._run(scenario())

    def test_patch_rejects_unknown_keys(self) -> None:
        async def scenario():
            app = create_app(config_loader=TranslatorConfig)
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.patch("/api/config", json={"bogus_key": 1})
                self.assertEqual(response.status_code, 400)

        self._run(scenario())


class FsRouteTests(unittest.TestCase):
    def test_list_dir_returns_markdown_flag(self) -> None:
        async def scenario():
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir) / "docs"
                root.mkdir()
                (root / "readme.md").write_text("# x", encoding="utf-8")
                (root / "notes.txt").write_text("x", encoding="utf-8")
                (root / "subdir").mkdir()
                app = create_app(config_loader=TranslatorConfig)
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    data = (await client.get("/api/fs", params={"path": str(root)})).json()
                entries = {item["name"]: item for item in data["entries"]}
                self.assertTrue(entries["subdir"]["is_dir"])
                self.assertTrue(entries["readme.md"]["is_markdown"])
                self.assertFalse(entries["notes.txt"]["is_markdown"])
                self.assertEqual(Path(data["parent"]).resolve(), root.parent.resolve())

        asyncio.run(scenario())

    def test_list_dir_rejects_file(self) -> None:
        async def scenario():
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = Path(temp_dir) / "x.md"
                file_path.write_text("x", encoding="utf-8")
                app = create_app(config_loader=TranslatorConfig)
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get("/api/fs", params={"path": str(file_path)})
                    self.assertEqual(response.status_code, 400)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
