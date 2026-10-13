"""视觉文案模块的离线测试：不需要 API Key，也不发网络请求。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

import copywriting
from copywriting.compose import FABRICATION_NOTE, compose
from copywriting.legacy import to_legacy
from copywriting.providers import local_fallback
from copywriting.schema import CopyRequest, normalize_identification, normalize_variants


def _make_image(directory: Path, color: tuple[int, int, int]) -> Path:
    path = directory / "product_cutout.png"
    image = Image.new("RGBA", (64, 96), (*color, 255))
    image.save(path)
    return path


class StubProvider:
    name = "stub"

    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        self.last_request = request
        return self.payload

    def generate_refine(self, request, current, feedback):
        self.calls += 1
        self.last_request = request
        self.last_current = current
        self.last_feedback = feedback
        return self.payload


class SchemaTests(unittest.TestCase):
    def test_normalize_variants_caps_count_and_truncates(self):
        raw = [{"title": f"{'标' * 20}{index}", "subtitle": "副标题"} for index in range(5)]
        variants = normalize_variants(raw)
        self.assertEqual(len(variants), 3)
        self.assertLessEqual(len(variants[0]["title"]), 24)

    def test_variants_without_title_or_subtitle_are_dropped(self):
        self.assertEqual(normalize_variants([{"title": "", "subtitle": ""}]), [])
        self.assertEqual(normalize_variants("不是列表"), [])

    def test_selling_points_are_split_deduped_and_capped(self):
        variant = normalize_variants([{
            "title": "杯子",
            "selling_points": "手工拉坯、手工拉坯，耐高温；易清洗\n第五个卖点",
        }])[0]
        self.assertEqual(variant["selling_points"], ["手工拉坯", "耐高温", "易清洗", "第五个卖点"])

    def test_identification_defaults(self):
        data = normalize_identification({})
        self.assertEqual(data["category"], "待确认商品")
        self.assertEqual(data["confidence"], 0.0)
        self.assertEqual(data["visible_features"], [])

    def test_known_facts_include_selling_points(self):
        request = CopyRequest(name="陶瓷杯", selling_points=["耐高温", "  ", "易清洗"])
        self.assertEqual(request.known_facts["用户提供的卖点"], "耐高温、易清洗")
        self.assertEqual(request.known_facts["商品名称"], "陶瓷杯")


class ComposeTests(unittest.TestCase):
    MODEL_OUTPUT = {
        "category": "陶瓷马克杯",
        "color": "米白",
        "visible_features": ["圆柱杯身", "带把手"],
        "scene": ["办公桌"],
        "confidence": 0.82,
        "warning": "",
        "variants": [
            {
                "title": "手作陶瓷杯",
                "subtitle": "每一只都独一无二",
                "selling_points": ["手工拉坯"],
                "price_text": "限时特价 9.9 元",
                "promo_text": "买一送一",
            },
        ],
    }

    def test_invented_promo_is_stripped_and_price_becomes_estimate(self):
        result = compose(dict(self.MODEL_OUTPUT), CopyRequest())
        variant = result["variants"][0]
        # 价格允许推测，但会被标注为参考价；折扣/活动仍然一律清空。
        self.assertEqual(variant["price_text"], "限时特价 9.9 元")
        self.assertTrue(variant["price_estimated"])
        self.assertEqual(variant["promo_text"], "")
        self.assertIn(FABRICATION_NOTE, result["identification"]["warning"])
        self.assertEqual(result["source"], "ai")

    def test_user_facts_are_kept_and_fill_empty_fields(self):
        request = CopyRequest(price="￥39", promo="第二件半价")
        payload = {
            "category": "陶瓷马克杯",
            "variants": [{"title": "手作陶瓷杯", "subtitle": "每一只都独一无二"}],
        }
        variant = compose(payload, request)["variants"][0]
        self.assertEqual(variant["price_text"], "￥39")
        self.assertEqual(variant["promo_text"], "第二件半价")

    def test_missing_variants_raise(self):
        with self.assertRaises(ValueError):
            compose({"category": "杯子"}, CopyRequest())


class GenerateCopyTests(unittest.TestCase):
    def test_falls_back_to_local_without_ai(self):
        with tempfile.TemporaryDirectory() as folder:
            path = _make_image(Path(folder), (230, 180, 190))
            with mock.patch.dict("os.environ", {"AI_API_URL": "", "AI_API_KEY": ""}, clear=False):
                result = copywriting.generate_copy(CopyRequest(images=[path]))
        self.assertEqual(result["source"], "local_fallback")
        self.assertEqual(result["variants"][0]["title"], "质感新选")
        self.assertEqual(result["identification"]["category"], "待人工确认的商品")
        self.assertEqual(result["identification"]["color"], "暖色")

    def test_require_ai_raises_without_configuration(self):
        with mock.patch.dict("os.environ", {"AI_API_URL": "", "AI_API_KEY": ""}, clear=False):
            with self.assertRaises(RuntimeError):
                copywriting.generate_copy(CopyRequest(), require_ai=True)

    def test_uses_provider_when_configured(self):
        stub = StubProvider(ComposeTests.MODEL_OUTPUT)
        request = CopyRequest(name="陶瓷杯", price="￥39", promo="第二件半价")
        with tempfile.TemporaryDirectory() as folder:
            request.images = [_make_image(Path(folder), (240, 240, 240))]
            with mock.patch.object(copywriting, "get_provider", return_value=stub):
                result = copywriting.generate_copy(request)
        self.assertEqual(stub.calls, 1)
        self.assertEqual(result["source"], "ai")
        self.assertEqual(result["suggested"]["name"], "陶瓷马克杯")
        self.assertEqual(result["variants"][0]["price_text"], "￥39")

    def test_local_fallback_reuses_user_input_and_splits_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            request = CopyRequest(
                images=[_make_image(Path(folder), (200, 200, 200))],
                name="陶瓷马克杯",
                feature="手工拉坯成型",
                selling_points=["耐高温", "易清洗", "不烫手"],
                price="￥39",
                promo="第二件半价",
            )
            with mock.patch.dict("os.environ", {"AI_API_URL": "", "AI_API_KEY": ""}, clear=False):
                result = copywriting.generate_copy(request)
        variant = result["variants"][0]
        self.assertEqual(result["source"], "local_fallback")
        self.assertEqual(variant["title"], "陶瓷马克杯")
        self.assertEqual(variant["subtitle"], "手工拉坯成型")
        self.assertEqual(variant["selling_points"], ["耐高温", "易清洗", "不烫手"])
        self.assertEqual(variant["price_text"], "￥39")
        self.assertEqual(variant["promo_text"], "第二件半价")


class LegacyContractTests(unittest.TestCase):
    def test_to_legacy_keeps_old_field_names(self):
        with tempfile.TemporaryDirectory() as folder:
            path = _make_image(Path(folder), (200, 200, 200))
            legacy = to_legacy(local_fallback.generate(CopyRequest(images=[path])))
        self.assertEqual(
            sorted(legacy.keys()),
            sorted(["category", "color", "visible_features", "scene",
                    "confidence", "warning", "copywriting", "source"]),
        )
        self.assertEqual(sorted(legacy["copywriting"][0].keys()), ["subtitle", "title"])
        self.assertEqual(legacy["source"], "local_fallback")


if __name__ == "__main__":
    unittest.main()
