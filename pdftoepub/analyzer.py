"""
Intelligent PDF Analyzer and OCR Decider.
Inspects each page for selectable text, Turkish character presence, font encoding corruption,
and image coverage to determine if OCR is required.
"""

import re
from enum import Enum
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


class PageType(Enum):
    DIGITAL_TEXT = "digital_text"              # Clean native text layer exists
    SCANNED_OCR_REQUIRED = "scanned_ocr"       # Pure image or scanned page (< 50 chars)
    CORRUPTED_OCR_REQUIRED = "corrupted_ocr"   # Text exists but has font/encoding errors
    BLANK = "blank"                            # Blank page


@dataclass
class PageAnalysis:
    page_number: int
    page_type: PageType
    char_count: int
    turkish_char_count: int
    image_count: int
    raw_text: str
    has_large_heading: bool
    largest_font_size: float


@dataclass
class DocumentAnalysis:
    total_pages: int
    digital_page_count: int
    ocr_required_page_count: int
    blank_page_count: int
    pages: List[PageAnalysis]
    needs_ocr: bool
    title: Optional[str] = None
    author: Optional[str] = None


def extract_geometric_page_text(page) -> str:
    """
    Extracts selectable text from a PDF page by clustering character/word bounding boxes.
    Prevents PyMuPDF's default text extraction from erroneously inserting spaces into
    tracked/kerning fonts (e.g. 'd a b i l i r i m' -> 'da bilirim', 'E sra'm' -> 'Esra'm').
    """
    words = page.get_text("words")
    if not words:
        return page.get_text("text", sort=True) or ""

    # Group words into lines by y-coordinate (tolerance ~3.5 pt)
    lines: List[List[Tuple]] = []
    current_line: List[Tuple] = []
    current_y: Optional[float] = None

    for w in sorted(words, key=lambda x: (x[1], x[0])):
        if current_y is None or abs(w[1] - current_y) <= 3.5:
            current_line.append(w)
            current_y = w[1]
        else:
            lines.append(sorted(current_line, key=lambda x: x[0]))
            current_line = [w]
            current_y = w[1]
    if current_line:
        lines.append(sorted(current_line, key=lambda x: x[0]))

    COMMON_SHORT_WORDS = {
        've', 'de', 'da', 'bu', 'şu', 'o', 'en', 'ne', 'ki', 'mi', 'mu', 'mü', 'mı',
        'ya', 'ile', 'bir', 'için', 'her', 'ama', 'ise', 'hem', 'pek', 'çok'
    }

    line_strings: List[str] = []
    for line_words in lines:
        if not line_words:
            continue
        reconstructed = []
        cur_token = line_words[0][4]
        for i in range(len(line_words) - 1):
            w_curr = line_words[i]
            w_next = line_words[i + 1]
            gap = w_next[0] - w_curr[2]

            # Inter-letter kerning gap is typically < 2.5 pt in book typesetting.
            is_punct = (
                w_next[4] in ('.', ',', '!', '?', ';', ':', "'", '"', '’', '”', '-', '—')
                or cur_token in ("'", '"', '‘', '“', '-', '—')
            )

            cur_is_short = cur_token.lower() in COMMON_SHORT_WORDS
            next_is_short = w_next[4].lower() in COMMON_SHORT_WORDS

            # Only genuine single-letter font fragments should be glued
            is_fragment = (not cur_is_short and len(cur_token) == 1) or (not next_is_short and len(w_next[4]) == 1)

            if gap < 2.5 and (is_fragment or is_punct) and not cur_is_short and not next_is_short:
                cur_token += w_next[4]
            else:
                reconstructed.append(cur_token)
                cur_token = w_next[4]
        reconstructed.append(cur_token)
        line_strings.append(" ".join(reconstructed))

    return "\n".join(line_strings)


class PDFAnalyzer:
    def __init__(self, min_char_threshold: int = 50, corruption_threshold: float = 0.08):
        self.min_char_threshold = min_char_threshold
        self.corruption_threshold = corruption_threshold

    def analyze_pdf(self, pdf_path: str) -> DocumentAnalysis:
        """Analyzes all pages in the PDF and determines OCR necessity page by page."""
        import fitz

        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        metadata = doc.metadata or {}
        extracted_title = metadata.get("title") or None
        extracted_author = metadata.get("author") or None

        pages_analysis: List[PageAnalysis] = []
        digital_count = 0
        ocr_count = 0
        blank_count = 0

        turkish_char_pattern = re.compile(r"[çğıöşüÇĞİÖŞÜ]")

        for page_num in range(total_pages):
            page = doc[page_num]
            text = extract_geometric_page_text(page)
            clean_text = text.strip()
            char_count = len(re.sub(r"\s+", "", clean_text))
            
            image_list = page.get_images()
            image_count = len(image_list)

            turkish_matches = len(turkish_char_pattern.findall(clean_text))

            # Inspect font sizes and heading candidates
            largest_font = 0.0
            has_heading = False
            
            try:
                page_dict = page.get_text("dict")
                for block in page_dict.get("blocks", []):
                    if block.get("type") == 0:  # text block
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                size = span.get("size", 0.0)
                                if size > largest_font:
                                    largest_font = size
                                if size >= 14.0 and len(span.get("text", "").strip()) > 3:
                                    has_heading = True
            except Exception:
                pass

            # Check unprintable / replacement characters
            unprintable_count = len(re.findall(r"[\ufffd\x00-\x08\x0b\x0c\x0e-\x1f]", text))
            unprintable_ratio = (unprintable_count / max(char_count, 1))

            # Check for corrupted embedded OCR patterns (e.g. 'başladıQı', 'DarOşşafaka', 'mOdür1üQü', 'Ot\'.\'2DU')
            corrupt_tokens = re.findall(
                r"[a-zçğıöşü]+[A-ZÇĞİÖŞÜ0-9][a-zçğıöşü]+|[a-zçğıöşü]+[qwxQWX][a-zçğıöşü]+|[A-Za-zçğıöşüÇĞİÖŞÜ]+['\.\^]+[0-9A-Za-zçğıöşüÇĞİÖŞÜ]+",
                text
            )
            corrupt_token_count = len(corrupt_tokens)

            # Classification
            if char_count == 0 and image_count == 0:
                p_type = PageType.BLANK
                blank_count += 1
            elif char_count < self.min_char_threshold:
                # Less than 50 chars, almost certainly a scanned page or illustration
                p_type = PageType.SCANNED_OCR_REQUIRED
                ocr_count += 1
            elif unprintable_ratio >= self.corruption_threshold or corrupt_token_count >= 3:
                # Text layer is corrupted (font cmap issue or degraded embedded OCR)
                p_type = PageType.CORRUPTED_OCR_REQUIRED
                ocr_count += 1
            else:
                # Clean digital text
                p_type = PageType.DIGITAL_TEXT
                digital_count += 1

            pages_analysis.append(PageAnalysis(
                page_number=page_num + 1,
                page_type=p_type,
                char_count=char_count,
                turkish_char_count=turkish_matches,
                image_count=image_count,
                raw_text=clean_text,
                has_large_heading=has_heading,
                largest_font_size=largest_font
            ))

        doc.close()

        needs_ocr = ocr_count > 0

        return DocumentAnalysis(
            total_pages=total_pages,
            digital_page_count=digital_count,
            ocr_required_page_count=ocr_count,
            blank_page_count=blank_count,
            pages=pages_analysis,
            needs_ocr=needs_ocr,
            title=extracted_title,
            author=extracted_author
        )
