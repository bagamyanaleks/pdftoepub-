"""
Unit tests for OCR garbage line detection and spaced-out word healing.
"""

import unittest
import re
from pdftoepub.cleaner import TextCleaner


class TestGarbageFilterAndWordHealing(unittest.TestCase):
    def setUp(self):
        self.cleaner = TextCleaner()

    def test_garbage_lines_from_illustrations_filtered(self):
        raw_lines = [
            "Z V R İ H 'TE",
            "-",
            "------ ZAMAN",
            ")).·",
            "•",
            ".",
            ",,;:",
            ">",
            "c .",
            "l'",
            "; ·J/",
            ",, -",
            ".",
            "Ò -",
            "/.;__-",
            "Gerhard haftalardır karısı ve çocuklarıyla kayınpederinin evinde yaşıyordu."
        ]
        paragraphs = self.cleaner.reconstruct_paragraphs(raw_lines)
        joined = " ".join(paragraphs)
        
        # None of the garbage OCR noise should be present
        self.assertNotIn(")).·", joined)
        self.assertNotIn(",,;:", joined)
        self.assertNotIn("; ·J/", joined)
        self.assertNotIn("/.;__-", joined)
        self.assertIn("Gerhard haftalardır", joined)

    def test_garbage_lines_on_elveda_page(self):
        raw_lines = [
            "E LVE DA",
            "VATAN I M",
            "--ı",
            "____",
            "_",
            "I ;:",
            r"QR\S. ,.;-",
            '"" -.:3',
            "l -",
            "'",
            "-.",
            "-Ó",
            "--..:CĈ",
            "İsviçre sınırından pasaport kontrolünü olaysız atlattıktan sonra,"
        ]
        paragraphs = self.cleaner.reconstruct_paragraphs(raw_lines)
        joined = " ".join(paragraphs)
        self.assertNotIn("QR\\S", joined)
        self.assertNotIn("--..:CĈ", joined)
        self.assertNotIn("____", joined)
        self.assertIn("İsviçre sınırından", joined)

    def test_heal_spaced_out_letters(self):
        samples = [
            ("da b i l i r i m .", "da bilirim."),
            ("Ama ne çare ki", "Ama ne çare ki"),
            ("b i z i m", "bizim"),
            ("bundan son - raki faslına", "bundan sonraki faslına"),
            ("HAS R ET", "HASRET"),
            ("E LVE DA", "ELVEDA"),
            ("VATAN I M", "VATANIM"),
            ("AYR I LI K", "AYRILIK"),
            ("Y İ N E", "YİNE"),
            ("Z V R İ H 'TE", "ZÜRİH'TE"),
            ("ZAMAN 1", "ZAMANI"),
            ("Esra'm inan bana", "Esra'm inan bana"),
            ("açmamalıydı m.", "açmamalıydım."),
        ]
        for raw, expected in samples:
            healed = self.cleaner.heal_split_words(raw)
            healed = self.cleaner.clean_ocr_errors(healed)
            self.assertEqual(healed.strip(), expected.strip(), f"Failed for: {raw}")


if __name__ == "__main__":
    unittest.main()
