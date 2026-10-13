"""按意见修改与价格推测规则的离线测试。"""

from __future__ import annotations

import unittest
from unittest import mock

import copywriting
from copywriting.compose import PRICE_ESTIMATE_NOTE, compose
from copywriting.feedback import has_feedback, normalize_feedback
from copywriting.prompts import build_refine_text
from copywriting.schema import CopyRequest
from test_copywriting import StubProvider


class PriceEstimateTests(unittest.TestCase):
    MODEL_OUTPUT = {
        "category": "陶瓷马克杯",
        "warning": "",
        "variants": [{
            "title": "手作陶瓷杯",
            "subtitle": "每一只都独一无二",
            "price_text": "￥129-159",
            "promo_text": "买一送一",
        }],
    }

    def test_model_price_is_kept_but_flagged_as_estimate(self):
        result = compose(dict(self.MODEL_OUTPUT), CopyRequest())
        variant = result["variants"][0]
        self.assertEqual(variant["price_text"], "￥129-159")
        self.assertTrue(variant["price_estimated"])
        self.assertIn(PRICE_ESTIMATE_NOTE, result["identification"]["warning"])

    def test_invented_promo_is_still_stripped(self):
        result = compose(dict(self.MODEL_OUTPUT), CopyRequest())
        self.assertEqual(result["variants"][0]["promo_text"], "")

    def test_user_price_wins_and_is_not_an_estimate(self):
        result = compose(dict(self.MODEL_OUTPUT), CopyRequest(price="￥39"))
        variant = result["variants"][0]
        self.assertEqual(variant["price_text"], "￥39")
        self.assertFalse(variant["price_estimated"])
        self.assertNotIn(PRICE_ESTIMATE_NOTE, result["identification"]["warning"])


class FeedbackTests(unittest.TestCase):
    def test_normalize_feedback_aligns_with_selling_points(self):
        feedback = normalize_feedback({"selling_points": ["太长", "", "换个说法"]}, 3)
        self.assertEqual(feedback["selling_points"], ["太长", "", "换个说法"])

    def test_normalize_feedback_pads_missing_points(self):
        feedback = normalize_feedback({"title": "更活泼"}, 2)
        self.assertEqual(feedback["selling_points"], ["", ""])
        self.assertTrue(has_feedback(feedback))
        self.assertFalse(has_feedback(normalize_feedback({}, 2)))

    def test_refine_text_lists_only_given_comments(self):
        current = {"title": "旧标题", "subtitle": "旧副标题", "selling_points": ["卖点一"],
                   "price_text": "￥39", "promo_text": ""}
        feedback = normalize_feedback({"selling_points": ["太长"], "title": "更活泼"}, 1)
        text = build_refine_text(current, feedback)
        self.assertIn("旧标题", text)
        self.assertIn("- 主标题：更活泼", text)
        self.assertIn("- 卖点 1：太长", text)
        self.assertNotIn("- 副标题：", text)


class RefineCopyTests(unittest.TestCase):
    REFINED = {
        "category": "陶瓷马克杯",
        "warning": "",
        "variants": [
            {"title": "把温暖捧在手心", "subtitle": "每一只都独一无二",
             "selling_points": ["手工拉坯"], "price_text": "￥129", "promo_text": ""},
            {"title": "不该出现的第二组", "subtitle": "应被裁掉", "selling_points": []},
        ],
    }

    SOURCE = {
        "title": "手作陶瓷杯", "subtitle": "每一只都独一无二",
        "selling_points": ["手工拉坯"], "price_text": "￥129-159",
        "promo_text": "", "price_estimated": True,
    }

    def test_refine_can_revise_an_estimated_price(self):
        stub = StubProvider(self.REFINED)
        feedback = normalize_feedback({"title": "更活泼"}, 1)
        with mock.patch.object(copywriting, "get_provider", return_value=stub):
            result = copywriting.refine_copy(CopyRequest(), self.SOURCE, feedback)
        self.assertEqual(len(result["variants"]), 1)
        self.assertEqual(result["variants"][0]["title"], "把温暖捧在手心")
        self.assertEqual(result["variants"][0]["price_text"], "￥129")
        self.assertTrue(result["variants"][0]["price_estimated"])
        self.assertEqual(result["refinedFrom"]["title"], "手作陶瓷杯")

    def test_refine_user_price_cannot_be_overridden(self):
        stub = StubProvider(self.REFINED)
        with mock.patch.object(copywriting, "get_provider", return_value=stub):
            result = copywriting.refine_copy(
                CopyRequest(price="￥39"), self.SOURCE, normalize_feedback({"price_text": "太贵"}, 1)
            )
        self.assertEqual(result["variants"][0]["price_text"], "￥39")
        self.assertFalse(result["variants"][0]["price_estimated"])

    def test_refine_keeps_previous_price_when_model_omits_it(self):
        payload = {"category": "杯子", "warning": "",
                   "variants": [{"title": "新标题", "subtitle": "新副标题", "selling_points": []}]}
        stub = StubProvider(payload)
        with mock.patch.object(copywriting, "get_provider", return_value=stub):
            result = copywriting.refine_copy(CopyRequest(), self.SOURCE, normalize_feedback({"title": "换"}, 0))
        self.assertEqual(result["variants"][0]["price_text"], "￥129-159")
        self.assertTrue(result["variants"][0]["price_estimated"])

    def test_refine_requires_a_model(self):
        with mock.patch.object(copywriting, "get_provider", return_value=None):
            with self.assertRaises(RuntimeError):
                copywriting.refine_copy(CopyRequest(), {"title": "旧"}, normalize_feedback({}, 0))


if __name__ == "__main__":
    unittest.main()
