import json
import unittest
from pathlib import Path

from template_compiler import compile_analysis


ROOT = Path(__file__).resolve().parent


class TemplateCompilerTests(unittest.TestCase):
    def setUp(self):
        self.analysis = json.loads(
            (ROOT / "training" / "template_analysis_sample.json").read_text(
                encoding="utf-8"
            )
        )

    def test_compiles_analysis_into_template(self):
        template = compile_analysis(
            self.analysis, template_id="template_sample", name="秋日模板"
        )
        self.assertEqual(template["schemaVersion"], 1)
        self.assertEqual(template["templateId"], "template_sample")
        self.assertEqual(template["canvas"], {"width": 1080, "height": 1440})
        self.assertEqual(len(template["layers"]), 4)
        self.assertEqual(template["source"]["analysisId"], "analysis_sample_001")
        self.assertIn("复古食品海报", template["generationPrompt"])

    def test_creates_dynamic_fields_and_bindings(self):
        template = compile_analysis(self.analysis)
        fields = {field["key"]: field for field in template["fields"]}
        self.assertEqual(set(fields), {"product", "title", "feature", "footer"})
        title = next(layer for layer in template["layers"] if layer["id"] == "title")
        self.assertEqual(title["bindTo"], "title")
        self.assertEqual(title["opacity"], 0.85)
        self.assertEqual(fields["title"]["maxChars"], 12)
        self.assertTrue(fields["product"]["required"])

    def test_preserves_background_cleanup_and_review_flags(self):
        template = compile_analysis(self.analysis)
        self.assertEqual(
            template["background"]["cleanupMasks"],
            [
                [0.08, 0.06, 0.7, 0.14],
                [0.16, 0.8, 0.6, 0.065],
                [0.12, 0.92, 0.76, 0.05],
            ],
        )
        feature = next(layer for layer in template["layers"] if layer["id"] == "feature")
        self.assertTrue(feature["reviewRequired"])
        feature_constraint = next(
            item for item in template["constraints"] if item["target"] == "feature"
        )
        self.assertEqual(feature_constraint["safeBBox"], feature["bbox"])

    def test_rejects_invalid_normalized_bbox(self):
        broken = json.loads(json.dumps(self.analysis))
        broken["observations"][0]["bbox"] = [20, 40, 200, 100]
        with self.assertRaises(ValueError):
            compile_analysis(broken)


if __name__ == "__main__":
    unittest.main()
