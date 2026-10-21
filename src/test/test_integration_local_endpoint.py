from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.cli.commands import translate_command
from src.infra.config import TranslatorConfig

SAMPLE = """---
title: Integration Doc
---
# Heading One

Paragraph with `code` and [link](https://example.com).

Second paragraph for good measure.
"""


def _payload_segments(payload: dict) -> list[tuple[str, str]]:
    if "segs" in payload:
        return [(str(item[0]), str(item[1])) for item in payload["segs"]]
    if "sections" in payload:
        return [(str(item[0]), str(item[1])) for section in payload["sections"] for item in section["segs"]]
    return [(str(item["segment_id"]), str(item["text"])) for item in payload.get("segments", [])]


def _fake_llm_response(user_prompt: str) -> str:
    payload = json.loads(user_prompt)
    task = payload.get("task")
    if task == "brief":
        return json.dumps(
            {"s": "Integration brief", "tone": "technical", "aud": "developers", "g": [], "sec": []},
            ensure_ascii=False,
        )
    if task == "translate":
        return json.dumps(
            {
                "t": [
                    {"i": segment_id, "x": f"[ZH]{text}", "c": 0.95, "a": {}, "n": []}
                    for segment_id, text in _payload_segments(payload)
                ],
                "q": [],
            },
            ensure_ascii=False,
        )
    if task == "reflect":
        return json.dumps({"issues": []})
    elif task == "judge":
        return json.dumps(
            {
                "scores": {"accuracy": 5, "fluency": 4, "terminology": 5, "format": 5},
                "overall": 4.5,
                "comments": [],
            }
        )
    else:  # review / improve / format_guard
        items = [
            {
                "segment_id": item["segment_id"],
                "translated_text": item["text"],
                "notes": [],
                "applied_terms": {},
                "confidence": 0.95,
            }
            for item in payload["translations"]
        ]
    return json.dumps({"translations": items}, ensure_ascii=False)


class _MockOpenAIHandler(BaseHTTPRequestHandler):
    received_formats: list[dict] = []
    received_tasks: list[str] = []

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        self.received_formats.append(body.get("response_format", {}))
        user_prompt = body["messages"][1]["content"]
        try:
            self.received_tasks.append(str(json.loads(user_prompt).get("task", "")))
        except json.JSONDecodeError:
            self.received_tasks.append("")
        try:
            content = _fake_llm_response(user_prompt)
        except Exception as exc:  # propagate as HTTP error for debugging
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(exc).encode())
            return
        response = {
            "choices": [{"message": {"content": content}}],
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 30,
                "total_tokens": 150,
                "prompt_tokens_details": {"cached_tokens": 64},
            },
        }
        encoded = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *args) -> None:  # silence request logging
        pass


class RealClientIntegrationTests(unittest.TestCase):
    """Drives the real AsyncOpenAIProvider + CLI against a local mock endpoint."""

    httpd: ThreadingHTTPServer
    port: int
    thread: threading.Thread

    @classmethod
    def setUpClass(cls) -> None:
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _MockOpenAIHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_translate_command_end_to_end(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "doc.md"
            input_path.write_text(SAMPLE, encoding="utf-8")
            output_dir = Path(temp_dir) / "out"
            config = TranslatorConfig()
            config.provider.base_url = f"http://127.0.0.1:{self.port}/v1"
            config.provider.api_key = "test-key"
            config.provider.api_key_env = "TEST_KEY_ENV"
            config.output.write_report = True
            config.memory.path = str(Path(temp_dir) / "memory.sqlite3")

            exit_code = translate_command([str(input_path)], ["zh-CN"], config, output_dir=str(output_dir))
            self.assertEqual(exit_code, 0)

            translated = output_dir / "doc.zh.md"
            self.assertTrue(translated.exists())
            text = translated.read_text(encoding="utf-8")
            self.assertIn("# [ZH]Heading One", text)
            self.assertIn("`code`", text)
            self.assertIn("https://example.com", text)
            self.assertTrue((output_dir / "doc.zh.md.report.json").exists())

            # Structured outputs requested via json_schema against the mock.
            formats = _MockOpenAIHandler.received_formats
            self.assertTrue(any(fmt.get("type") == "json_schema" for fmt in formats))
            # cached tokens parsed from prompt_tokens_details.
            self.assertTrue(any(fmt == {"type": "json_object"} for fmt in formats) or formats)

            # Second run: memory reuse means zero translate calls (the brief
            # call still runs, because it is document-level context).
            tasks_before = len(_MockOpenAIHandler.received_tasks)
            translate_command([str(input_path)], ["zh-CN"], config, output_dir=str(output_dir))
            tasks_after = _MockOpenAIHandler.received_tasks[tasks_before:]
            self.assertEqual(tasks_after.count("translate"), 0)


if __name__ == "__main__":
    unittest.main()
