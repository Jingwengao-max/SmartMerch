"""Fast, isolated tests for style2 title layout."""

import unittest

from PIL import Image, ImageDraw

from ai_copywriter import _validate
from learned_layout import _semantic_tokens, _split_fixed_title, layout_fixed_title, load_models_for
from layout_engine import load_font
from style_specs import get_style_spec


class TitleLayoutTests(unittest.TestCase):
    def test_fixed_distribution(self):
        expected = {
            1: [1],
            2: [2],
            3: [3],
            4: [2, 2],
            5: [3, 2],
            6: [3, 3],
            7: [4, 3],
            8: [4, 4],
            9: [3, 3, 3],
        }
        source = "桌面式智能摄像设备"
        for length, counts in expected.items():
            with self.subTest(length=length):
                title = source[:length]
                lines = _split_fixed_title(title)
                self.assertEqual([len(line) for line in lines], counts)
                self.assertEqual("".join(lines), title)

    def test_layout_keeps_font_size_and_fills_json_frame(self):
        frame_width = 830
        for title in (
            "云台", "高清云台", "智能高清云", "智能高清云台",
            "桌面式智能摄像", "桌面式智能摄像设备",
        ):
            with self.subTest(title=title):
                layout = layout_fixed_title(title, frame_width)
                self.assertGreaterEqual(layout["fontSize"], 100)
                self.assertEqual(len(layout["lineSpacings"]), len(layout["lines"]))
                self.assertEqual(len(layout["lineAlignments"]), len(layout["lines"]))
                block_height = (
                    (len(layout["lines"]) - 1) * layout["lineHeight"]
                    + layout["fontSize"]
                )
                self.assertLessEqual(block_height, 752)
                probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
                font = load_font(layout["fontSize"], 900, "hei")
                for line, spacing, alignment in zip(
                    layout["lines"], layout["lineSpacings"], layout["lineAlignments"],
                ):
                    if len(line) <= 1:
                        continue
                    if alignment == "left":
                        self.assertEqual(spacing, 0)
                        continue
                    span = probe.textlength(line, font=font) + spacing * (len(line) - 1)
                    self.assertAlmostEqual(span, frame_width, delta=2)
                if len(layout["lines"]) == 2:
                    self.assertGreaterEqual(layout["lineHeight"] / layout["fontSize"], 1.17)
                if len(title) in {5, 7}:
                    self.assertEqual(layout["lineAlignments"], ["justify", "left"])
                else:
                    self.assertTrue(all(item == "justify" for item in layout["lineAlignments"]))
                if title == "桌面式智能摄像设备":
                    self.assertGreaterEqual(layout["fontSize"], 225)
                    block_height = (
                        (len(layout["lines"]) - 1) * layout["lineHeight"]
                        + layout["fontSize"]
                    )
                    self.assertGreaterEqual(block_height, 730)

    def test_nine_character_limit_on_input_and_ai(self):
        title = "桌面式智能超高清摄像设备"
        layout = layout_fixed_title(title, 830)
        self.assertEqual(layout["content"].replace("\n", ""), title[:9])

        result = _validate({
            "copywriting": [{
                "name": title,
                "slogan": "清晰稳定",
                "intro": "商品介绍",
                "sellingPoints": ["广角", "智能", "稳定"],
            }],
        }, style="style2")
        self.assertEqual(result["copywriting"][0]["name"], title[:9])
        name_field = next(
            field for field in get_style_spec("style2")["fields"] if field["key"] == "name"
        )
        self.assertEqual(name_field["maxChars"], 9)

    def test_semantic_tokenizer_is_unchanged(self):
        self.assertEqual(
            _semantic_tokens("桌面式智能摄像设备"),
            (["桌面式", "智能", "摄像", "设备"], ""),
        )

    def test_preview_uses_original_vertical_canvas_and_title_frame(self):
        model = load_models_for("style2")[0]
        x, y, width, height = model["regions"]["name"]
        self.assertEqual((round(x * 1080), round(y * 1440)), (40, 35))
        self.assertEqual((round(width * 1080), round(height * 1440)), (830, 752))
        self.assertEqual(model["canvas"], [1080, 1440])


if __name__ == "__main__":
    unittest.main()
