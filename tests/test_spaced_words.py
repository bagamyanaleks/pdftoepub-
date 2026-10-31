import unittest
import os
import fitz
from pdftoepub.analyzer import extract_geometric_page_text
from pdftoepub.structure import StructureDetector
from pdftoepub.cleaner import TextCleaner

class TestGeometricExtractionAndTOC(unittest.TestCase):
    def setUp(self):
        pdf_name = "Ayşe Kulin Kanadı Kırık Kuşlar Everest Yayınları (2).pdf"
        if not os.path.exists(pdf_name):
            self.skipTest(f"Test PDF not present: {pdf_name}")
        self.doc = fitz.open(pdf_name)
        self.detector = StructureDetector()
        self.cleaner = TextCleaner()

    def tearDown(self):
        self.doc.close()

    def test_page_9_email_geometric_extraction(self):
        """Page 9 contains typewriter email with spaced letters: 'da b i li ri m', 'k ader imiz'."""
        text = extract_geometric_page_text(self.doc[8])
        self.assertIn("Sevgili Esra'm, biricik torunum,", text)
        self.assertIn("da bilirim.", text)
        self.assertIn("bizim kaderimizde", text)

    def test_page_374_sms_geometric_extraction(self):
        """Page 374 contains SMS with spaced characters."""
        text = extract_geometric_page_text(self.doc[373])
        self.assertIn("Esra'm nerdesin?", text)
        self.assertIn("ilk buluş", text)
        self.assertIn("tuğumuz yere gel aynı saatte.", text)
        self.assertIn("Tarık!", text)
        self.assertIn("asla o ilk buluştuğumuz yere, aynı saatte yetişemezdim. Benim", text)

    def test_printed_toc_extraction(self):
        """Tests automatic extraction of all chapters from the printed Table of Contents."""
        toc = self.detector.extract_printed_toc(self.doc)
        self.assertGreaterEqual(len(toc), 35)
        # Verify key chapters and their start pages
        self.assertIn(15, toc)
        self.assertEqual(toc[15], "Bize Yine Hasret Düştü")
        self.assertIn(36, toc)
        self.assertEqual(toc[36], "Elveda Vatanım")
        self.assertIn(45, toc)
        self.assertEqual(toc[45], "Zürih'te Zaman")
        self.assertIn(58, toc)
        self.assertEqual(toc[58], "Ortasından Deniz Geçen Şehirde")
        self.assertIn(66, toc)
        self.assertEqual(toc[66], "Yoktan Var Edilmiş Şehirde")
        self.assertIn(340, toc)
        self.assertEqual(toc[340], "Kanadı Kırık Kuşlar")

if __name__ == "__main__":
    unittest.main()
