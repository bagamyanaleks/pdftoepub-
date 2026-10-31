"""
EPUB 3 Builder module.
Generates fully compliant, beautifully styled EPUB 3 books with Turkish metadata,
cover art, responsive typography, and navigation documents.
"""

import os
import re
import html
import uuid
from typing import List, Optional
from ebooklib import epub

from .structure import Chapter, DocumentBlock


def sanitize_xml_text(text: str) -> str:
    """
    Strips illegal XML 1.0 control characters and escapes XML special characters (&, <, >).
    Preserves quotes within element text.
    """
    if not text:
        return ""
    # Strip XML 1.0 illegal control characters: 0x00-0x08, 0x0B-0x0C, 0x0E-0x1F, 0x7F-0x84, 0x86-0x9F
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]", "", text)
    return html.escape(cleaned, quote=False)


def sanitize_xml_attr(attr: str) -> str:
    """
    Escapes XML attribute values including double and single quotes.
    """
    if not attr:
        return ""
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]", "", attr)
    return html.escape(cleaned, quote=True)


DEFAULT_EPUB_CSS = """
@charset "utf-8";

body {
    margin: 5% 5%;
    padding: 0;
    font-family: "Georgia", "Merriweather", "Times New Roman", serif;
    font-size: 1.05em;
    line-height: 1.6;
    text-align: justify;
    -webkit-hyphens: auto;
    hyphens: auto;
    color: #1a1a1a;
    background-color: transparent;
}

h1.chapter-title {
    font-size: 1.8em;
    font-weight: bold;
    text-align: center;
    margin-top: 2em;
    margin-bottom: 1.5em;
    line-height: 1.25;
    letter-spacing: 0.03em;
    page-break-before: always;
}

h2.section-title {
    font-size: 1.3em;
    font-weight: bold;
    text-align: left;
    margin-top: 1.5em;
    margin-bottom: 0.8em;
}

p {
    margin-top: 0;
    margin-bottom: 0;
    text-indent: 1.5em;
}

p.first-para {
    text-indent: 0;
}

p.dialogue {
    text-indent: 1em;
}

figure.book-figure {
    margin: 1.5em auto;
    text-align: center;
    display: block;
    max-width: 100%;
}

figure.book-figure img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0 auto;
    border-radius: 4px;
}

figcaption {
    font-size: 0.85em;
    color: #555;
    margin-top: 0.5em;
    font-style: italic;
    text-align: center;
}

hr.scene-break {
    border: none;
    border-top: 1px solid #ccc;
    width: 25%;
    margin: 2em auto;
}

aside.footnote-block {
    margin-top: 1.2em;
    margin-bottom: 0.8em;
    padding: 0.5em 1em;
    font-size: 0.85em;
    color: #4a5568;
    background-color: rgba(0, 0, 0, 0.02);
    border-left: 3px solid #718096;
    border-radius: 2px;
    text-indent: 0;
}

aside.footnote-block p.footnote-text {
    text-indent: 0;
    margin: 0;
    line-height: 1.45;
}
"""


class EPUBBuilder:
    def __init__(self, title: str, author: Optional[str] = None, language: str = "tr"):
        self.title = title or "İsimsiz Kitap"
        self.author = author or "Bilinmeyen Yazar"
        self.language = language
        self.book_id = str(uuid.uuid4())

    def create_epub(
        self,
        chapters: List[Chapter],
        output_filepath: str,
        cover_image_path: Optional[str] = None,
        embedded_images: Optional[List[str]] = None
    ) -> str:
        """Assembles and writes a standard EPUB 3 book."""
        book = epub.EpubBook()

        # Metadata
        book.set_identifier(self.book_id)
        book.set_title(self.title)
        book.set_language(self.language)
        book.add_author(self.author)

        # Add CSS stylesheet
        style_item = epub.EpubItem(
            uid="style_nav",
            file_name="style/style.css",
            media_type="text/css",
            content=DEFAULT_EPUB_CSS.encode("utf-8")
        )
        book.add_item(style_item)

        # Add cover image if provided
        if cover_image_path and os.path.exists(cover_image_path):
            with open(cover_image_path, "rb") as f:
                cover_data = f.read()
            cover_ext = os.path.splitext(cover_image_path)[1].lower()
            cover_fname = f"cover{cover_ext}"
            book.set_cover(cover_fname, cover_data)

        # Add embedded images
        image_manifest = {}
        if embedded_images:
            for img_path in embedded_images:
                if os.path.exists(img_path):
                    bname = os.path.basename(img_path)
                    ext = os.path.splitext(bname)[1].lower()
                    media_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
                    with open(img_path, "rb") as f:
                        img_bytes = f.read()
                    
                    epub_img = epub.EpubItem(
                        uid=f"img_{bname.replace('.', '_')}",
                        file_name=f"images/{bname}",
                        media_type=media_type,
                        content=img_bytes
                    )
                    book.add_item(epub_img)
                    image_manifest[bname] = f"images/{bname}"

        epub_chapters = []
        for i, chap in enumerate(chapters):
            safe_title = sanitize_xml_text(chap.title)
            c_item = epub.EpubHtml(
                title=chap.title,
                file_name=f"{chap.chapter_id}.xhtml",
                lang=self.language
            )
            c_item.add_item(style_item)

            # Build HTML content
            html_parts = [
                '<?xml version="1.0" encoding="utf-8"?>',
                '<!DOCTYPE html>',
                f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{self.language}" lang="{self.language}">',
                '<head>',
                '  <meta charset="utf-8"/>',
                f'  <title>{safe_title}</title>',
                '  <link rel="stylesheet" href="style/style.css" type="text/css"/>',
                '</head>',
                '<body>',
                '  <section class="chapter">',
                f'    <h1 class="chapter-title">{safe_title}</h1>',
            ]

            is_first_p = True
            for block in chap.blocks:
                if block.block_type == "heading" and block.text.strip() != chap.title.strip():
                    heading_text = sanitize_xml_text(block.text.strip())
                    html_parts.append(f'    <h2 class="section-title">{heading_text}</h2>')
                elif block.block_type == "image" and block.image_path:
                    bname = os.path.basename(block.image_path)
                    rel_src = image_manifest.get(bname, f"images/{bname}")
                    safe_src = sanitize_xml_attr(rel_src)
                    html_parts.append(
                        f'    <figure class="book-figure"><img src="{safe_src}" alt="Görsel"/></figure>'
                    )
                elif block.block_type == "paragraph":
                    text = block.text.strip()
                    if text:
                        p_class = "first-para" if is_first_p else "dialogue" if text.startswith("—") else ""
                        class_attr = f' class="{p_class}"' if p_class else ""
                        escaped_text = sanitize_xml_text(text)
                        html_parts.append(f'    <p{class_attr}>{escaped_text}</p>')
                        is_first_p = False
                elif block.block_type == "footnote":
                    fn_text = sanitize_xml_text(block.text.strip())
                    if fn_text:
                        html_parts.append(
                            f'    <aside epub:type="footnote" class="footnote-block"><p class="footnote-text">{fn_text}</p></aside>'
                        )

            html_parts.extend([
                '  </section>',
                '</body>',
                '</html>'
            ])

            c_item.set_content("\n".join(html_parts).encode("utf-8"))
            book.add_item(c_item)
            epub_chapters.append(c_item)

        # Table of Contents
        book.toc = tuple(epub_chapters)

        # Add default NCX and Nav
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Define spine
        book.spine = ["nav"] + epub_chapters

        # Ensure destination directory exists
        dest_dir = os.path.dirname(os.path.abspath(output_filepath))
        os.makedirs(dest_dir, exist_ok=True)

        # Write to system temp directory first, then atomically replace to avoid OneDrive sync file locks
        import tempfile
        import shutil
        temp_file = os.path.join(tempfile.gettempdir(), f"epub_build_{uuid.uuid4().hex}.epub")
        try:
            epub.write_epub(temp_file, book, {})
            # Atomic move / replace
            shutil.move(temp_file, output_filepath)
        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

        return output_filepath
