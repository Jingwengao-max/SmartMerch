"""本地 .env 加载与"是否已配置"判定的测试，全部离线。"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from copywriting import config
from env_loader import load_env


def _write_env(text: str) -> Path:
    path = Path(tempfile.mkdtemp()) / ".env"
    path.write_text(text, encoding="utf-8")
    return path


class EnvLoaderTests(unittest.TestCase):
    def test_reads_file_without_overriding_existing_variables(self):
        path = _write_env('AI_MODEL="from-file"\nAI_API_URL=https://api.test/v1\n# 注释\n')
        with mock.patch.dict(os.environ, {"AI_MODEL": "from-shell"}, clear=True):
            self.assertTrue(load_env(path))
            self.assertEqual(os.environ["AI_MODEL"], "from-shell")
            self.assertEqual(os.environ["AI_API_URL"], "https://api.test/v1")

    def test_supports_export_prefix_quotes_and_extra_keys(self):
        path = _write_env("export AI_API_KEY='sk-local'\nexport AI_IMAGE_MAX_EDGE=2048\n")
        with mock.patch.dict(os.environ, {}, clear=True):
            load_env(path)
            self.assertEqual(os.environ["AI_API_KEY"], "sk-local")
            self.assertEqual(config.image_max_edge(), 2048)

    def test_missing_file_is_silent(self):
        self.assertFalse(load_env(Path(tempfile.mkdtemp()) / "missing.env"))

    def test_ignores_blank_lines_and_invalid_lines(self):
        path = _write_env("\n\n没有等号的一行\nAI_MODEL=qwen3-vl-plus\n")
        with mock.patch.dict(os.environ, {}, clear=True):
            load_env(path)
            self.assertEqual(os.environ["AI_MODEL"], "qwen3-vl-plus")
            self.assertNotIn("没有等号的一行", os.environ)


class ConfiguredGuardTests(unittest.TestCase):
    def test_placeholder_example_file_is_not_configured(self):
        with mock.patch.dict(
            os.environ,
            {"AI_API_URL": "https://example.com/v1", "AI_API_KEY": "replace-with-your-key"},
            clear=True,
        ):
            self.assertFalse(config.configured())

    def test_real_endpoint_with_key_is_configured(self):
        with mock.patch.dict(
            os.environ,
            {
                "AI_API_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "AI_API_KEY": "sk-abc",
            },
            clear=True,
        ):
            self.assertTrue(config.configured())

    def test_local_endpoint_without_key_is_configured(self):
        with mock.patch.dict(os.environ, {"AI_API_URL": "http://127.0.0.1:11434/v1"}, clear=True):
            self.assertTrue(config.configured())

    def test_missing_url_is_not_configured(self):
        with mock.patch.dict(os.environ, {"AI_API_KEY": "sk-abc"}, clear=True):
            self.assertFalse(config.configured())


if __name__ == "__main__":
    unittest.main()
