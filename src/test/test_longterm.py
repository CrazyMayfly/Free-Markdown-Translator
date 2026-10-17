from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agents.editor_agent import EditorAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.translator_agent import TranslatorAgent
from src.core.pipeline import TranslationPipeline
from src.infra.config import TranslatorConfig
from src.memory.translation_memory import TranslationMemory
from src.parser.markdown_parser import MarkdownParser
from src.parser.segment_extractor import SegmentExtractor
from src.test.test_ast_pipeline import SAMPLE_MARKDOWN, FakeProvider, FormatGuardAgent
from src.validators.markdown_validator import MarkdownValidator

_STORED_PARAGRAPH = "Rotate the signing keys for the staging cluster every 30 days."
_NEW_PARAGRAPH = "Rotate the signing keys for the production fleet every 90 days."


def _config(**overrides) -> TranslatorConfig:
    config = TranslatorConfig()
    config.pipeline.mode = overrides.get("mode", "balanced")
    config.pipeline.enable_review = False
    config.pipeline.enable_format_guard = False
    config.pipeline.enable_glossary = False
    config.pipeline.enable_sentinels = False
    config.pipeline.enable_anchor_scheduling = overrides.get("enable_anchor_scheduling", True)
    config.pipeline.enable_context_pull = overrides.get("enable_context_pull", True)
    config.pipeline.enable_final_edit = overrides.get("enable_final_edit", True)
    config.memory.fuzzy_examples = True
    return config


def _pipeline(provider, config, memory=None, editor: EditorAgent | None = None) -> TranslationPipeline:
    return TranslationPipeline(
        config=config,
        parser=MarkdownParser(),
        extractor=SegmentExtractor(),
        translator_agent=TranslatorAgent(provider),
        reviewer_agent=ReviewerAgent(provider),
        format_guard_agent=FormatGuardAgent(provider),
        validator=MarkdownValidator(),
        memory=memory,
        editor_agent=editor,
    )


class ContextPullProvider(FakeProvider):
    """First translate call asks for deeper TM context; second is answered."""

    def __init__(self) -> None:
        super().__init__()
        self.requested = False
        self.payloads: list[dict] = []

    def chat_json(self, system_prompt, user_prompt, call_label="llm", response_schema=None):
        payload = json.loads(user_prompt)
        if payload.get("task") == "translate":
            self.schemas.append(response_schema)
            self.calls.append(call_label)
            self.payloads.append(payload)
            translations = [
                {
                    "segment_id": segment["segment_id"],
                    "translated_text": f"[ZH]{segment['text']}",
                    "notes": [],
                    "applied_terms": {},
                    "confidence": 0.99,
                }
                for segment in payload["segments"]
            ]
            if not self.requested:
                self.requested = True
                paragraph = next(segment for segment in payload["segments"] if segment["segment_id"].startswith("body-") and "Rotate" in segment["text"])
                return {
                    "translations": translations,
                    "context_requests": [
                        {"segment_id": paragraph["segment_id"], "need": "similar_translations", "reason": "unsure how this operation was rendered before"}
                    ],
                }
            return {"translations": translations, "context_requests": []}
        return super().chat_json(system_prompt, user_prompt, call_label, response_schema)


class ContextPullTests(unittest.TestCase):
    def test_request_triggers_deeper_search_and_second_round(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = TranslationMemory(Path(temp_dir) / "memory.sqlite3")
            seed = Path(temp_dir) / "seed.md"
            seed.write_text(f"# Ops\n\n{_STORED_PARAGRAPH}\n", encoding="utf-8")
            _pipeline(FakeProvider(), _config(), memory=memory).run(seed, "zh-CN", write_output=False)

            provider = ContextPullProvider()
            target = Path(temp_dir) / "target.md"
            target.write_text(f"# Ops\n\n{_NEW_PARAGRAPH}\n", encoding="utf-8")
            _pipeline(provider, _config(), memory=memory).run(target, "zh-CN", write_output=False)

        self.assertEqual(provider.calls.count("translate"), 2)
        first_paragraph = next(segment for segment in provider.payloads[0]["segments"] if "Rotate" in segment["text"])
        second_paragraph = next(segment for segment in provider.payloads[1]["segments"] if segment["segment_id"] == first_paragraph["segment_id"])
        # 0.65 similarity is below the auto example threshold: round 1 had no
        # example, the pull round got the deep-search hit.
        self.assertNotIn("similar", first_paragraph)
        self.assertIn("similar", second_paragraph)
        self.assertIn("staging cluster", second_paragraph["similar"][0]["source"])

    def test_pull_disabled_sticks_to_one_round(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = TranslationMemory(Path(temp_dir) / "memory.sqlite3")
            seed = Path(temp_dir) / "seed.md"
            seed.write_text(f"# Ops\n\n{_STORED_PARAGRAPH}\n", encoding="utf-8")
            _pipeline(FakeProvider(), _config(), memory=memory).run(seed, "zh-CN", write_output=False)

            provider = ContextPullProvider()
            target = Path(temp_dir) / "target.md"
            target.write_text(f"# Ops\n\n{_NEW_PARAGRAPH}\n", encoding="utf-8")
            _pipeline(provider, _config(enable_context_pull=False), memory=memory).run(target, "zh-CN", write_output=False)

        self.assertEqual(provider.calls.count("translate"), 1)

    def test_fast_mode_ignores_context_requests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = TranslationMemory(Path(temp_dir) / "memory.sqlite3")
            seed = Path(temp_dir) / "seed.md"
            seed.write_text(f"# Ops\n\n{_STORED_PARAGRAPH}\n", encoding="utf-8")
            _pipeline(FakeProvider(), _config(), memory=memory).run(seed, "zh-CN", write_output=False)

            provider = ContextPullProvider()
            target = Path(temp_dir) / "target.md"
            target.write_text(f"# Ops\n\n{_NEW_PARAGRAPH}\n", encoding="utf-8")
            _pipeline(provider, _config(mode="fast"), memory=memory).run(target, "zh-CN", write_output=False)

        self.assertEqual(provider.calls.count("translate"), 1)


class FinalEditProvider(FakeProvider):
    """Flags one document-level issue and echoes the improved text."""

    def __init__(self) -> None:
        super().__init__()
        self.final_edit_payloads: list[dict] = []
        self.improve_payloads: list[dict] = []

    def chat_json(self, system_prompt, user_prompt, call_label="llm", response_schema=None):
        if call_label == "final_edit":
            self.calls.append(call_label)
            self.schemas.append(response_schema)
            payload = json.loads(user_prompt)
            self.final_edit_payloads.append(payload)
            last = payload["translations"][-1]["segment_id"]
            return {
                "issues": [
                    {"segment_id": last, "type": "style", "severity": "high", "comment": "tone drifts from the opening section"}
                ]
            }
        if call_label == "final_edit_improve":
            self.calls.append(call_label)
            self.schemas.append(response_schema)
            payload = json.loads(user_prompt)
            self.improve_payloads.append(payload)
            return {
                "translations": [
                    {
                        "segment_id": item["segment_id"],
                        "translated_text": f"[EDITED]{item['text']}",
                        "notes": [],
                        "applied_terms": {},
                        "confidence": 0.99,
                    }
                    for item in payload["translations"]
                ],
                "context_requests": [],
            }
        return super().chat_json(system_prompt, user_prompt, call_label, response_schema)


class FinalEditTests(unittest.TestCase):
    def test_strict_mode_runs_document_level_final_edit(self) -> None:
        provider = FinalEditProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "doc.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            result = _pipeline(provider, _config(mode="strict"), editor=EditorAgent(provider)).run(input_path, "zh-CN", write_output=False)

        self.assertEqual(provider.calls.count("final_edit"), 1)
        self.assertEqual(provider.calls.count("final_edit_improve"), 1)
        # The document-level review sees every segment, not one bundle.
        self.assertEqual(len(provider.final_edit_payloads[0]["translations"]), 4)
        # Improve carried the flagged segment plus neighbour context.
        improved_ids = [item["segment_id"] for item in provider.improve_payloads[0]["translations"]]
        self.assertEqual(improved_ids, ["body-1"])
        self.assertIn("[EDITED]", result.translated_text)
        edited = [item for item in result.translations if any(note.startswith("final-edit:") for note in item.notes)]
        self.assertEqual(len(edited), 1)

    def test_balanced_mode_skips_final_edit(self) -> None:
        provider = FinalEditProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "doc.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            _pipeline(provider, _config(mode="balanced"), editor=EditorAgent(provider)).run(input_path, "zh-CN", write_output=False)

        self.assertEqual(provider.calls.count("final_edit"), 0)
        self.assertEqual(provider.calls.count("final_edit_improve"), 0)

    def test_final_edit_disabled_by_config(self) -> None:
        provider = FinalEditProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "doc.md"
            input_path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            _pipeline(provider, _config(mode="strict", enable_final_edit=False), editor=EditorAgent(provider)).run(input_path, "zh-CN", write_output=False)

        self.assertEqual(provider.calls.count("final_edit"), 0)


if __name__ == "__main__":
    unittest.main()
