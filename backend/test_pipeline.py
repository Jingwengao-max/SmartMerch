import tempfile
import unittest
from pathlib import Path

from PIL import Image

from layout_engine import extract_product_features, load_templates, make_candidate
from main import cutout, render
from poster_design_adapter import normalize_template
from poster_design_source import available, list_templates, load_template
from quality_evaluator import evaluate_document


class PosterPipelineTests(unittest.TestCase):
    def test_transparent_input_and_layout(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "product.png"
            output = Path(temporary) / "cutout.png"
            image = Image.new("RGBA", (300, 500), (0, 0, 0, 0))
            for x in range(60, 240):
                for y in range(30, 470):
                    image.putpixel((x, y), (245, 180, 195, 255))
            image.save(source)
            product = cutout(source, output)
            self.assertEqual(product.size, (180, 440))
            self.assertTrue(output.exists())

            templates = load_templates()
            self.assertEqual(len(templates), 3)
            features = extract_product_features(product)
            self.assertEqual(features["shape"], "vertical")
            options = [
                make_candidate(template, product, "粉色随行杯", "把喜欢的颜色带进每一天")
                for template in templates
            ]
            for option in options:
                self.assertEqual(option["score"], option["score"])  # 非 NaN
            poster = render(product, max(options, key=lambda item: item["score"]), "粉色随行杯", "把喜欢的颜色带进每一天", "产品展示")
            self.assertEqual(poster.size, (1080, 1350))

    def test_quality_evaluator_detects_overlap(self):
        document = {
            "canvas": {"width": 1080, "height": 1350},
            "elements": [
                {"type": "image", "role": "product", "x": 300, "y": 300, "width": 500, "height": 700},
                {"type": "text", "role": "title", "content": "测试标题", "x": 350, "y": 350,
                 "width": 300, "height": 100, "fontSize": 60},
            ],
        }
        result = evaluate_document(document)
        self.assertLess(result["scores"]["no_overlap"], 100)
        self.assertTrue(result["suggestions"])

    def test_poster_design_template_adapter(self):
        converted = normalize_template({
            "page": {"width": 1080, "height": 1350, "backgroundColor": "#ffffff"},
            "widgets": [{
                "uuid": "headline", "type": "w-text", "text": "新品上市",
                "left": 80, "top": 90, "width": 500, "height": 100,
                "fontSize": 72, "color": "#222222",
            }],
        })
        self.assertEqual(converted["canvas"]["width"], 1080)
        self.assertEqual(converted["elements"][0]["content"], "新品上市")
        self.assertEqual(converted["elements"][0]["id"], "headline")

    def test_poster_design_legacy_array(self):
        converted = normalize_template([{
            "global": {"width": 600, "height": 800, "backgroundColor": "#eeeeee"},
            "layers": [{"uuid": "photo", "type": "w-image", "imgUrl": "/generated/a.png",
                        "left": 10, "top": 20, "width": 300, "height": 500}],
        }])
        self.assertEqual(converted["canvas"]["height"], 800)
        self.assertEqual(converted["elements"][0]["src"], "/generated/a.png")

    def test_bundled_poster_design_template_can_be_loaded(self):
        if not available():
            self.skipTest("poster-design 源码尚未放入 vendor 目录")
        templates = list_templates()
        self.assertTrue(any(item["id"] == 1011 for item in templates))
        converted = normalize_template(load_template(1011))
        self.assertEqual(converted["canvas"]["width"], 750)
        self.assertTrue(converted["canvas"]["backgroundImage"].startswith("/poster-design-static/"))
        self.assertGreater(len(converted["elements"]), 10)


if __name__ == "__main__":
    unittest.main()
