"""
Unit tests for Turkish Text Cleaner, De-hyphenation, and Linguistic Normalization.
"""

import unittest
from pdftoepub.cleaner import TextCleaner


class TestTextCleaner(unittest.TestCase):
    def setUp(self):
        self.cleaner = TextCleaner()

    def test_unicode_normalization(self):
        # Combining cedilla s + ¸ should normalize to ş in NFC
        decomposed = "s\u0327emsiye"
        normalized = self.cleaner.normalize_unicode(decomposed)
        self.assertEqual(normalized, "şemsiye")

    def test_dehyphenation_normal_words(self):
        # Hyphenated word broken across line
        text = "kitapları oku-\n yan öğrenciler"
        cleaned = self.cleaner.dehyphenate(text)
        self.assertIn("okuyan", cleaned)

    def test_dehyphenation_compound_words_preserved(self):
        # Legitimate compound word should retain its hyphen
        text = "sosyo-\n ekonomik durum"
        cleaned = self.cleaner.dehyphenate(text)
        self.assertIn("sosyo-ekonomik", cleaned)

        text2 = "Türk-\n İslam düşüncesi"
        cleaned2 = self.cleaner.dehyphenate(text2)
        self.assertIn("Türk-İslam", cleaned2)

    def test_ocr_error_replacements(self):
        text = "clünya üzerinde b1r gün 1çinde yap1lan işler"
        cleaned = self.cleaner.clean_ocr_errors(text)
        self.assertIn("dünya", cleaned)
        self.assertIn("bir gün", cleaned)
        self.assertIn("içinde", cleaned)
        self.assertIn("yapılan", cleaned)

    def test_page_number_detection(self):
        self.assertTrue(self.cleaner.is_likely_page_number("42"))
        self.assertTrue(self.cleaner.is_likely_page_number("- 125 -"))
        self.assertTrue(self.cleaner.is_likely_page_number("[ 14 ]"))
        self.assertTrue(self.cleaner.is_likely_page_number("iv"))
        self.assertTrue(self.cleaner.is_likely_page_number("XII"))
        self.assertTrue(self.cleaner.is_likely_page_number("139_"))
        self.assertTrue(self.cleaner.is_likely_page_number("149 ="))
        self.assertTrue(self.cleaner.is_likely_page_number("153 _"))
        self.assertFalse(self.cleaner.is_likely_page_number("Bu bir paragraftır."))

    def test_header_footer_detection(self):
        title = "Tutsak Güneş"
        author = "Ayşe Kulin"
        self.assertTrue(self.cleaner.is_likely_header_footer("TUTSAK GÜNEŞ", book_title=title, author=author))
        self.assertTrue(self.cleaner.is_likely_header_footer("AYŞE KULİN", book_title=title, author=author))
        self.assertTrue(self.cleaner.is_likely_header_footer("128", book_title=title, author=author))
        self.assertFalse(self.cleaner.is_likely_header_footer("Güneş yavaşça batıyordu ve oda karardı.", book_title=title, author=author))

    def test_paragraph_reconstruction(self):
        lines = [
            "Birinci satır burada başlıyor",
            "ve ikinci satırla devam ediyor.",
            "",
            "- Sen kimsin? diye sordu adam.",
            "— Ben yolcuyum, dedi kadın."
        ]
        paragraphs = self.cleaner.reconstruct_paragraphs(lines)
        self.assertEqual(len(paragraphs), 3)
        self.assertEqual(paragraphs[0], "Birinci satır burada başlıyor ve ikinci satırla devam ediyor.")
        self.assertTrue(paragraphs[1].startswith("— "))
        self.assertTrue(paragraphs[2].startswith("— "))

    def test_heal_split_words(self):
        sample = "Sinek küçüktür ama mide bu landırır, kan görmeye daya namaz, yedi se kiz yaşlarında."
        healed = self.cleaner.heal_split_words(sample)
        self.assertIn("bulandırır", healed)
        self.assertIn("dayanamaz", healed)
        self.assertIn("sekiz", healed)

        sample2 = "yüzü nü görünce, Sesini yük seltti, hallede yim, maka sı, sey reltti, şaşı rarak, birleş tirdi"
        healed2 = self.cleaner.heal_split_words(sample2)
        self.assertIn("yüzünü", healed2)
        self.assertIn("yükseltti", healed2)
        self.assertIn("halledeyim", healed2)
        self.assertIn("makası", healed2)
        self.assertIn("seyreltti", healed2)
        self.assertIn("şaşırarak", healed2)
        self.assertIn("birleştirdi", healed2)

    def test_publisher_font_corruptions(self):
        # 'Đdı -> "Adı
        t1 = "'Đdı ne bu arkadaşın?\" diye sordu."
        c1 = self.cleaner.clean_ocr_errors(t1)
        self.assertIn('"Adı', c1)

        # O kadar ını? -> O kadar mı?
        t2 = "O kadar ını? Soyadı yok mu?"
        c2 = self.cleaner.clean_ocr_errors(t2)
        self.assertIn("O kadar mı?", c2)

        # M k; > a as. -> Makas?
        t3 = '"M k; >" a as.'
        c3 = self.cleaner.clean_ocr_errors(t3)
        self.assertIn('"Makas?"', c3)

        # k, , çı ar. -> çıkar.
        t4 = "belki içinden bir plaster k, , çı ar."
        c4 = self.cleaner.clean_ocr_errors(t4)
        self.assertIn("çıkar.", c4)


if __name__ == "__main__":
    unittest.main()
