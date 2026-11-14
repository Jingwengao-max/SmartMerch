import unittest
import tempfile
from pathlib import Path

from PIL import Image

from poster_analyzer import _normalize_bbox, _normalize_text_style, _prepare_vision_image


class PosterAnalyzerTests(unittest.TestCase):
    def test_explicit_corner_object(self):
        self.assertEqual(
            _normalize_bbox({"left": 0.2, "top": 0.1, "right": 0.8, "bottom": 0.5}),
            [0.2, 0.1, 0.6, 0.4],
        )

    def test_explicit_xywh_object(self):
        self.assertEqual(
            _normalize_bbox({"x": 0.2, "y": 0.1, "width": 0.6, "height": 0.4}),
            [0.2, 0.1, 0.6, 0.4],
        )

    def test_legacy_xywh_array(self):
        self.assertEqual(_normalize_bbox([0.1, 0.2, 0.3, 0.4]), [0.1, 0.2, 0.3, 0.4])

    def test_vision_corner_array_is_recognized(self):
        self.assertEqual(
            _normalize_bbox([0.205, 0.035, 0.825, 0.08]),
            [0.205, 0.035, 0.62, 0.045],
        )

    def test_invalid_or_empty_box(self):
        self.assertIsNone(_normalize_bbox([0.4, 0.4, 0.4, 0.7]))
        self.assertIsNone(_normalize_bbox("bad"))

    def test_text_style_is_normalized_for_editor(self):
        style = _normalize_text_style({
            "style": {
                "fontCategory": "宋体",
                "fontSize": 72,
                "fontWeight": 900,
                "color": "#c64c22",
                "textAlign": "center",
            },
        }, [0.1, 0.2, 0.5, 0.1], 1440)
        self.assertEqual(style["fontId"], "serif")
        self.assertEqual(style["fontSize"], 72)
        self.assertEqual(style["fontWeight"], 900)
        self.assertEqual(style["color"], "#c64c22")
        self.assertEqual(style["textAlign"], "center")

    def test_prepares_downscaled_vision_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "poster.png"
            Image.new("RGBA", (2400, 3200), (250, 240, 220, 255)).save(source)
            vision_path, size = _prepare_vision_image(source, 1280)
            try:
                self.assertEqual(size, (960, 1280))
                self.assertTrue(vision_path.is_file())
                with Image.open(vision_path) as copied:
                    self.assertEqual(copied.size, (960, 1280))
            finally:
                vision_path.unlink(missing_ok=True)
            self.assertTrue(source.is_file())


if __name__ == "__main__":
    unittest.main()
