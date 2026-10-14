import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from layout_engine import extract_product_features, load_templates, make_candidate
from main import cutout, render
from poster_design_adapter import normalize_template
from poster_design_source import available, list_templates, load_template
from quality_evaluator import evaluate_document


class PosterPipelineTests(unittest.TestCase):
    def test_translation_reuses_unified_ai_configuration(self):
        from ai_copywriter import translate_with_ai

        response = Mock()
        response.status_code = 200
        response.ok = True
        response.json.return_value = {
            "choices": [{"message": {"content": '{"translation":"Strawberry Danish"}'}}],
        }
        with patch.dict(os.environ, {
            "AI_API_URL": "https://example.test/v1",
            "AI_API_KEY": "unified-secret",
            "AI_MODEL": "vision-model",
        }, clear=True), patch("requests.post", return_value=response) as post:
            translated = translate_with_ai("草莓丹麦")

        self.assertEqual(translated, "Strawberry Danish")
        self.assertEqual(post.call_args.args[0], "https://example.test/v1/chat/completions")
        self.assertEqual(post.call_args.kwargs["json"]["model"], "vision-model")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer unified-secret")

    def test_visual_copy_contract_matches_current_poster(self):
        from ai_copywriter import _validate

        result = _validate({
            "category": "丹麦酥",
            "copywriting": [{
                "english_name": "Strawberry Danish",
                "chinese_name": "草莓奶油丹麦",
                "selling_points": ["新鲜草莓", "层层起酥", "奶油香滑", "不会进入海报"],
                "footer": "现烤现卖",
                "launch_text": "新品上市",
                "badge_text": "NEW!",
            }],
        })
        option = result["copywriting"][0]
        self.assertNotIn("title", option)
        self.assertEqual(option["subtitle"], "草莓奶油丹麦")
        self.assertEqual(len(option["sellingPoints"]), 3)
        self.assertEqual(option["launchText"], "新品上市")

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
            self.assertEqual(poster.size, (1080, 1440))

    def test_learned_layout_model(self):
        from learned_layout import adaptive_palette, create_document, load_model

        model = load_model()
        self.assertEqual(model["trainedSamples"], 4)
        self.assertEqual(len(model["regions"]), 9)
        document = create_document(
            job_id="test",
            product_url="/generated/test/product.png",
            background_url="/generated/test/background.jpg",
            product_size=(600, 500),
            mean_rgb=(215, 95, 110),
            title="Strawberry Danish",
            feature="草莓奶油丹麦",
            selling_points=["精选新鲜草莓", "层层起酥", "奶油香滑"],
        )
        self.assertEqual(document["templateId"], "learned-bakery-editorial-v1")
        self.assertEqual(document["canvas"], {
            "width": 1080,
            "height": 1440,
            "backgroundImage": "/generated/test/background.jpg",
        })
        selling_points = [item for item in document["elements"] if item.get("role") == "sellingPoint"]
        self.assertEqual(len(selling_points), 3)
        self.assertNotIn("footer-values", {item["id"] for item in document["elements"]})
        self.assertIn("accent", adaptive_palette((215, 95, 110)))

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
