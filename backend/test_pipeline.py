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
        self.assertTrue(all(len(point) <= 10 for point in option["sellingPoints"]))
        self.assertEqual(option["launchText"], "新品上市")

    def test_style_models_are_registered_and_distinct(self):
        from learned_layout import MODEL_FILES, load_model_for

        self.assertIn("editorial", MODEL_FILES)
        self.assertIn("style2", MODEL_FILES)
        self.assertIn("retro", MODEL_FILES)
        self.assertNotIn("minimal", MODEL_FILES)
        editorial = load_model_for("editorial")
        retro = load_model_for("retro")
        self.assertEqual(editorial["style"]["name"], "bakery-editorial")
        self.assertEqual(retro["style"]["name"], "retro")
        self.assertNotEqual(editorial["regions"]["product"], retro["regions"]["product"])
        with self.assertRaises(ValueError):
            load_model_for("minimal")
        with self.assertRaises(ValueError):
            load_model_for("does-not-exist")
    def test_create_document_uses_style_regions(self):
        from learned_layout import create_document

        common = dict(mean_rgb=(200, 120, 140), product_size=(500, 700))
        editorial = create_document(
            "job-a", "/p.png", "/bg.jpg", **common,
            copy={"title": "Test Product", "subtitle": "测试商品",
                  "sellingPoints": ["卖点一", "卖点二"], "footer": "品牌口号"},
            style="editorial",
        )
        retro = create_document(
            "job-b", "/p.png", "/bg.jpg", **common,
            copy={"title": "TEST PRODUCT", "subtitle": "测试商品",
                  "slogan": "简洁口号", "feature": "清晰卖点"},
            style="retro",
        )
        product_a = next(item for item in editorial["elements"] if item["role"] == "product")
        product_b = next(item for item in retro["elements"] if item["role"] == "product")
        self.assertNotEqual((product_a["x"], product_a["y"]), (product_b["x"], product_b["y"]))

        magazine = create_document(
            "job-c", "/p.png", "/bg.jpg", **common,
            copy={"title": "TEST", "subtitle": "测试商品",
                  "sellingPoints": ["这是一条超过十个字的卖点文案"]}, style="editorial",
        )
        magazine_point = next(item for item in magazine["elements"] if item.get("role") == "sellingPoint")
        self.assertLessEqual(len(magazine_point["content"]), 10)
        self.assertNotIn("\n", magazine_point["content"])
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
            copy={
                "title": "Strawberry Danish",
                "subtitle": "草莓奶油丹麦",
                "sellingPoints": ["精选新鲜草莓", "层层起酥", "奶油香滑"],
            },
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

    def test_retro_style_has_adaptive_palette_and_copy(self):
        from learned_layout import build_style_background, create_document, load_model_for

        document = create_document(
            "retro-job", "/product.png", "/background.jpg",
            product_size=(600, 500), mean_rgb=(30, 150, 220),
            copy={
                "subtitle": "开心果可颂", "title": "A CROISSANT",
                "slogan": "层层起酥 奶香浓郁", "feature": "无添加、真材实料",
                "sellingPoints": ["金黄酥脆", "黄油醇香", "轻盈多层"],
                "year": "2026", "badgeText": "VOL.09",
                "footer": "QUALITY INGREDIENTS · MADE WITH CARE",
            },
            style="retro",
        )
        self.assertEqual(document["templateId"], "retro-food-poster-v1")
        self.assertNotEqual(document["palette"]["accent"], "#c64c22")
        warm_document = create_document(
            "retro-warm", "/product.png", "/background.jpg",
            product_size=(600, 500), mean_rgb=(220, 110, 35),
            copy={"subtitle": "暖色商品", "title": "WARM PRODUCT"}, style="retro",
        )
        self.assertNotEqual(document["palette"]["accent"], warm_document["palette"]["accent"])
        self.assertEqual(document["productName"], "开心果可颂")
        self.assertTrue(any(item.get("id") == "feature-panel" for item in document["elements"]))
        year = next(item for item in document["elements"] if item.get("id") == "year")
        self.assertEqual(year["content"], "2026")
        self.assertFalse(any(item.get("id") == "issue" for item in document["elements"]))
        self.assertFalse(any(item.get("role") == "sellingPoint" for item in document["elements"]))
        from style_specs import STYLE_SPECS
        self.assertEqual(
            [field["key"] for field in STYLE_SPECS["retro"]["fields"]],
            ["subtitle", "title", "slogan", "feature", "footer"],
        )
        product_layer = next(item for item in document["elements"] if item.get("role") == "product")
        product_box = (product_layer["x"], product_layer["y"],
                       product_layer["x"] + product_layer["width"],
                       product_layer["y"] + product_layer["height"])
        for item in (layer for layer in document["elements"] if layer.get("type") == "text"):
            text_box = (item["x"], item["y"], item["x"] + item["width"], item["y"] + item["height"])
            overlaps = not (
                text_box[2] <= product_box[0] or text_box[0] >= product_box[2]
                or text_box[3] <= product_box[1] or text_box[1] >= product_box[3]
            )
            self.assertFalse(overlaps, f"文案 {item['id']} 不应覆盖商品")

        with tempfile.TemporaryDirectory() as temporary:
            product = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
            product.paste((220, 140, 60, 255), (30, 30, 290, 150))
            background = Path(temporary) / "retro.jpg"
            build_style_background(
                background, document["palette"], product, load_model_for("retro"), style_key="retro",
            )
            self.assertTrue(background.is_file())
            rendered = Image.open(background)
            self.assertEqual(rendered.size, (1080, 1440))
            self.assertLess(rendered.getpixel((80, 100))[0], 160)
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
