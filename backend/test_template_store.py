import json
import tempfile
import unittest
from pathlib import Path

from template_compiler import compile_analysis
from template_store import list_templates, load_template, save_template


ROOT = Path(__file__).resolve().parent


class TemplateStoreTests(unittest.TestCase):
    def setUp(self):
        analysis = json.loads(
            (ROOT / "training" / "template_analysis_sample.json").read_text(
                encoding="utf-8"
            )
        )
        analysis["sourceUrl"] = "/generated/analysis/sample/source.jpg"
        self.template = compile_analysis(analysis, "template_sample", "秋日模板")

    def test_save_and_load_template(self):
        with tempfile.TemporaryDirectory() as temporary:
            base_dir = Path(temporary)
            saved = save_template(self.template, base_dir)
            self.assertEqual(saved["templateId"], "template_sample")
            loaded = load_template("template_sample", base_dir)
            self.assertEqual(loaded["name"], "秋日模板")
            self.assertEqual(
                loaded["background"]["sourceUrl"],
                "/generated/analysis/sample/source.jpg",
            )

    def test_list_templates_returns_summary(self):
        with tempfile.TemporaryDirectory() as temporary:
            base_dir = Path(temporary)
            save_template(self.template, base_dir)
            summaries = list_templates(base_dir)
            self.assertEqual(len(summaries), 1)
            self.assertEqual(summaries[0]["fieldCount"], 4)
            self.assertEqual(summaries[0]["layerCount"], 4)
            self.assertEqual(
                summaries[0]["previewUrl"], "/generated/analysis/sample/source.jpg"
            )

    def test_rejects_unsafe_template_id(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                save_template(self.template, Path(temporary), "../outside")


if __name__ == "__main__":
    unittest.main()
