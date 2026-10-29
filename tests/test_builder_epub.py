"""
Unit tests for EPUB Builder XML escaping and validation.
"""

import unittest
from pdftoepub.builder_epub import sanitize_xml_text, sanitize_xml_attr, EPUBBuilder
from pdftoepub.structure import Chapter, DocumentBlock
from lxml import etree
import tempfile
import os
import zipfile


class TestEPUBBuilder(unittest.TestCase):
    def test_sanitize_xml_text_escapes_entities(self):
        raw = "Bu bir <deneme> & test 'için' \"örnek\" metindir."
        sanitized = sanitize_xml_text(raw)
        self.assertIn("&lt;deneme&gt;", sanitized)
        self.assertIn("&amp;", sanitized)
        # Inside text, quotes do not need escaping, but < and > and & MUST be escaped
        self.assertNotIn("<", sanitized)
        self.assertNotIn(">", sanitized)

    def test_sanitize_xml_text_strips_illegal_control_chars(self):
        # 0x0c (form feed), 0x08 (backspace), 0x00 (null byte)
        raw = "Sayfa 1\x0cSayfa 2\x08devam\x00"
        sanitized = sanitize_xml_text(raw)
        self.assertEqual(sanitized, "Sayfa 1Sayfa 2devam")

    def test_epub_generation_with_corrupted_ocr_tags(self):
        # Problematic OCR snippet that triggered 'Qualified name is invalid: ilerliyordu:'
        problematic_text = "lunan ve ma and do g delerek <ilerliyordu: solberg halston mimari & Co."
        
        chap = Chapter(
            chapter_id="chap_001",
            title="BÖLÜM 1 & <GİRİŞ>",
            blocks=[
                DocumentBlock(text="BÖLÜM 1 & <GİRİŞ>", block_type="heading"),
                DocumentBlock(text=problematic_text, block_type="paragraph"),
                DocumentBlock(text="— Normal diyalog cümlesi.", block_type="paragraph"),
            ]
        )

        builder = EPUBBuilder(title="Test <Kitap> & Adı", author="Yazar & <Ortak>")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            epub_path = os.path.join(tmpdir, "test_out.epub")
            builder.create_epub(
                chapters=[chap],
                output_filepath=epub_path
            )

            self.assertTrue(os.path.exists(epub_path))

            # Inspect every XHTML file in the EPUB to ensure it is 100% valid XML
            with zipfile.ZipFile(epub_path, "r") as z:
                for name in z.namelist():
                    if name.endswith(".xhtml"):
                        raw_bytes = z.read(name)
                        # Strict XML parsing must succeed without throwing XMLSyntaxError
                        parser = etree.XMLParser(recover=False)
                        try:
                            etree.fromstring(raw_bytes, parser=parser)
                        except etree.XMLSyntaxError as e:
                            self.fail(f"EPUB XHTML file {name} failed XML validation: {e}")


if __name__ == "__main__":
    unittest.main()
