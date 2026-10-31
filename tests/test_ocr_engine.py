import unittest
import os
import io
from PIL import Image, ImageDraw

from pdftoepub.ocr import (
    find_tesseract_binary,
    is_tesseract_available,
    get_tessdata_dir,
    OCREngine
)


class TestOCREngine(unittest.TestCase):
    def test_find_binary(self):
        binary = find_tesseract_binary()
        self.assertIsNotNone(binary, "Tesseract binary should be discoverable")
        self.assertTrue(os.path.isfile(binary), "Discovered binary file must exist")

    def test_tessdata_available(self):
        self.assertTrue(is_tesseract_available(), "Tesseract 5 with Turkish traineddata should be available")

    def test_auto_engine_resolution(self):
        engine = OCREngine(engine="auto")
        self.assertEqual(engine.active_engine, "tesseract")

    def test_explicit_easyocr_resolution(self):
        engine = OCREngine(engine="easyocr")
        self.assertEqual(engine.active_engine, "easyocr")

    def test_tesseract_image_ocr(self):
        # Create a simple synthetic image with Turkish text
        img = Image.new("RGB", (400, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 35), "Marmara Denizi", fill=(0, 0, 0))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        engine = OCREngine(engine="tesseract")
        text = engine.ocr_image_bytes(png_bytes)
        self.assertIn("Marmara", text)


if __name__ == "__main__":
    unittest.main()
