from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from src.infra.config import (
    TranslatorConfig,
    _default_config_dict,
    default_user_config_path,
    initialize_config,
    load_config,
    render_default_config_yaml,
    resolve_config_path,
)


class ConfigPathTests(unittest.TestCase):
    def test_resolve_config_prefers_user_home_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            home_dir = Path(tmp_dir)
            config_dir = home_dir / ".mdtx"
            config_dir.mkdir(parents=True, exist_ok=True)
            expected = config_dir / "config.yaml"
            expected.write_text("target_languages:\n  - zh-CN\n", encoding="utf-8")

            with patch("src.infra.config.Path.home", return_value=home_dir), patch(
                "src.infra.config._workspace_root", return_value=home_dir / "workspace"
            ):
                self.assertEqual(resolve_config_path(), expected)

    def test_initialize_config_creates_default_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            home_dir = Path(tmp_dir)
            with patch("src.infra.config.Path.home", return_value=home_dir):
                created = initialize_config()
                self.assertEqual(created, default_user_config_path())
                self.assertTrue(created.exists())
                self.assertIn("target_languages:", created.read_text(encoding="utf-8"))

    def test_initialize_config_preserves_existing_file_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            destination = Path(tmp_dir) / "config.yaml"
            destination.write_text("provider:\n  model: custom-model\n", encoding="utf-8")

            created = initialize_config(str(destination), force=False)

            self.assertEqual(created, destination)
            self.assertEqual(destination.read_text(encoding="utf-8"), "provider:\n  model: custom-model\n")

    def test_load_config_creates_user_config_when_nothing_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            home_dir = Path(tmp_dir)
            with patch("src.infra.config.Path.home", return_value=home_dir), patch(
                "src.infra.config._workspace_root", return_value=home_dir / "workspace"
            ):
                load_config()
                created = home_dir / ".mdtx" / "config.yaml"
                self.assertTrue(created.exists())

    def test_rendered_template_matches_default_dict(self) -> None:
        rendered = yaml.safe_load(render_default_config_yaml())
        self.assertEqual(rendered, _default_config_dict())

    def test_dataclass_defaults_match_default_dict(self) -> None:
        config = TranslatorConfig()
        self.assertEqual(config.target_languages, _default_config_dict()["target_languages"])
        self.assertEqual(config.provider.model, _default_config_dict()["provider"]["model"])
        self.assertEqual(config.segmentation.max_bundle_segments, _default_config_dict()["segmentation"]["max_bundle_segments"])
        self.assertEqual(config.segmentation.max_bundle_chars, _default_config_dict()["segmentation"]["max_bundle_chars"])
        self.assertEqual(config.output.write_report, _default_config_dict()["output"]["write_report"])
        self.assertEqual(config.execution.max_parallel_translations, _default_config_dict()["execution"]["max_parallel_translations"])
        self.assertEqual(config.style.instructions, _default_config_dict()["style"]["instructions"])
        self.assertEqual(config.style.preserve_terms, _default_config_dict()["style"]["preserve_terms"])
        self.assertEqual(config.pipeline.mode, _default_config_dict()["pipeline"]["mode"])
        self.assertEqual(config.provider.temperature, _default_config_dict()["provider"]["temperature"])
        self.assertEqual(config.provider.max_tokens, _default_config_dict()["provider"]["max_tokens"])


if __name__ == "__main__":
    unittest.main()
