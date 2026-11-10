import json
import unittest
from pathlib import Path

from template_compiler import compile_analysis
from template_instantiate import instantiate_template


ROOT = Path(__file__).resolve().parent


class TemplateInstantiateTests(unittest.TestCase):
    def setUp(self):
        analysis = json.loads(
            (ROOT / "training" / "template_analysis_sample.json").read_text(
                encoding="utf-8"
            )
        )
        self.template = compile_analysis(
            analysis, template_id="template_sample", name="秋日模板"
        )

    def test_instantiates_existing_poster_document(self):
        document = instantiate_template(
            self.template,
            {
                "title": "冬日新品",
                "feature": "层层酥脆 奶香浓郁",
                "footer": "WINTER COLLECTION",
            },
            product_url="/generated/product.png",
            background_url="/generated/background.jpg",
            product_size=(800, 800),
        )
        self.assertEqual(document["templateId"], "template_sample")
        self.assertEqual(document["canvas"]["backgroundImage"], "/generated/background.jpg")
        self.assertEqual(document["productName"], "冬日新品")
        self.assertEqual(len(document["elements"]), 4)

        title = next(item for item in document["elements"] if item["id"] == "title")
        self.assertEqual(title["content"], "冬日新品")
        self.assertEqual((title["x"], title["y"]), (86, 86))
        self.assertEqual(title["fontFamily"], "serif")
        self.assertEqual(title["textAlign"], "center")
        self.assertEqual(title["opacity"], 0.85)

    def test_replaces_product_and_keeps_aspect_ratio(self):
        document = instantiate_template(
            self.template,
            {"title": "新品", "feature": "卖点", "footer": "底部"},
            product_url="/generated/new_product.png",
            background_url="/generated/background.jpg",
            product_size=(400, 800),
        )
        product = next(item for item in document["elements"] if item["role"] == "product")
        self.assertEqual(product["src"], "/generated/new_product.png")
        self.assertEqual((product["width"], product["height"]), (331, 662))
        self.assertGreaterEqual(product["x"], round(0.24 * 1080))
        self.assertGreaterEqual(product["y"], round(0.28 * 1440))

    def test_background_color_fallback(self):
        document = instantiate_template(
            self.template,
            {"title": "新品", "feature": "卖点", "footer": "底部"},
            product_url="/generated/new_product.png",
        )
        self.assertEqual(document["canvas"]["backgroundColor"], "#f7f0df")
        self.assertNotIn("backgroundImage", document["canvas"])

    def test_skips_image_regions_without_extracted_assets(self):
        template = json.loads(json.dumps(self.template))
        template["layers"].append({
            "id": "decoration-placeholder",
            "type": "image",
            "role": "decoration",
            "bbox": [0.7, 0.1, 0.1, 0.1],
            "zIndex": 2,
            "assetId": None,
        })
        document = instantiate_template(
            template,
            {"title": "新品", "feature": "卖点", "footer": "底部"},
            product_url="/generated/new_product.png",
            background_url="/generated/background.jpg",
        )
        self.assertFalse(any(
            item["id"] == "decoration-placeholder" for item in document["elements"]
        ))


if __name__ == "__main__":
    unittest.main()
