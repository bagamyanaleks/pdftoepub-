"""
Chapter and Document Structure Detector for PDF to EPUB/AZW3 conversion.
Identifies chapters, headers, and builds the Table of Contents (TOC).
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


CHAPTER_PATTERNS = [
    # BÖLÜM 1, 1. BÖLÜM, BİRİNCİ BÖLÜM
    r"^(?:(?:bölüm|kısım|fasıl)\s+\d+|(?:bölüm|kısım)\s+[ivxlcdm]+|\d+\.\s*(?:bölüm|kısım)|(?:birinci|ikinci|üçüncü|dördüncü|beşinci|altıncı|yedinci|sekizinci|dokuzuncu|onuncu)\s+(?:bölüm|kısım))$",
    # Roman numeral on its own line: I, II, III, IV, V...
    r"^[IVXLCDM]{1,6}$",
    # Common Turkish book structural sections
    r"^(?:giriş|önsöz|sonsöz|epilog|prolog|ithaf|teşekkür|başlangıç|sonuç|kaynakça|içindekiler)$",
    # Numbered chapter heading like "1. Yolculuk" or "1 - Başlangıç"
    r"^\d{1,3}\s*[\.\-–—]\s*[A-ZÇĞİÖŞÜa-zçğıöşü\s]{3,40}$",
]

COMPILED_CHAPTER_REGEX = [re.compile(p, re.IGNORECASE) for p in CHAPTER_PATTERNS]


@dataclass
class DocumentBlock:
    text: str
    block_type: str = "paragraph"  # "heading", "paragraph", "image", "break"
    image_path: Optional[str] = None
    level: int = 1  # heading level (1 for h1, 2 for h2)


@dataclass
class Chapter:
    title: str
    chapter_id: str
    blocks: List[DocumentBlock] = field(default_factory=list)


BOILERPLATE_WORDS = {
    "isbn", "yayın", "yayınları", "yayıncılık", "baskı", "cilt", "basım",
    "matbaa", "sertifika", "tel", "faks", "eserleri", "eserler", "editör",
    "düzeltmen", "kapak", "tasarımı", "sayfa", "everest", "yayınevi"
}


class StructureDetector:
    def __init__(self):
        pass

    def is_chapter_heading(
        self,
        line: str,
        is_large_font: bool = False,
        book_title: Optional[str] = None,
        author: Optional[str] = None
    ) -> bool:
        """Determines if a given text line represents a legitimate chapter heading."""
        cleaned = line.strip()
        if not cleaned or len(cleaned) < 2 or len(cleaned) > 60:
            return False

        # Headings NEVER start with dialogue dashes or quotes
        if re.match(r'^[\-–—"\'‘“„]', cleaned):
            return False

        # Headings NEVER end with conversational terminal punctuation or quotes enclosing them
        if re.search(r'[\.!\?,;:]["\'”’]?$', cleaned) and not re.match(r'^\d+\.', cleaned):
            return False

        lower = cleaned.lower()
        lower_compact = re.sub(r"\s+", "", lower)

        # Reject if matches author name or book title
        if author:
            auth_compact = re.sub(r"\s+", "", author.lower())
            if auth_compact and auth_compact in lower_compact:
                return False
        if book_title:
            title_compact = re.sub(r"\s+", "", book_title.lower())
            if title_compact and title_compact in lower_compact:
                return False

        # Reject publisher boilerplate
        words = set(re.findall(r"\b\w+\b", lower))
        if words & BOILERPLATE_WORDS:
            return False
        for bp in BOILERPLATE_WORDS:
            if bp in lower_compact:
                return False

        # Check regex patterns (Bölüm 1, Birinci Kısım, etc.)
        for regex in COMPILED_CHAPTER_REGEX:
            if regex.match(cleaned):
                return True

        # Pure uppercase titles without terminal punctuation (allowing internal apostrophes like ZÜRİH'TE, SUZAN'IN)
        no_apos = re.sub(r"(?<=[a-zA-ZçğıöşüA-ZÇĞİÖŞÜ])['’](?=[a-zA-ZçğıöşüA-ZÇĞİÖŞÜ])", "", cleaned)
        if no_apos.isupper() and 3 <= len(cleaned) <= 45:
            if not re.search(r'[\.!\?,;:\"”]', no_apos) and not cleaned.startswith(('"', "'", "“", "—", "-")):
                return True

        return False

    def extract_printed_toc(self, doc) -> Dict[int, str]:
        """
        Scans the early pages of the PDF for a printed Table of Contents (İÇİNDEKİLER / TOC).
        Returns a mapping of {page_number (1-indexed): clean_chapter_title}.
        """
        toc: Dict[int, str] = {}
        toc_pages: List[int] = []
        for p in range(min(15, len(doc))):
            text = doc[p].get_text("text")
            if re.search(r"NDEK.*LER|İÇİNDEKİLER|ICINDEKILER", text, re.IGNORECASE):
                toc_pages.append(p)
                for next_p in range(p + 1, min(p + 4, len(doc))):
                    nt = doc[next_p].get_text("text")
                    if re.search(r"[\.·\s]{3,}\s*\d", nt):
                        toc_pages.append(next_p)
                    else:
                        break
                break

        if not toc_pages:
            return toc

        pending_title = ""
        for p in toc_pages:
            text = doc[p].get_text("text")
            for line in text.splitlines():
                line = line.strip()
                if not line or re.search(r"NDEK.*LER|İÇİNDEKİLER|ICINDEKILER", line, re.IGNORECASE):
                    continue
                # Match title ... page_number (allowing space in page number like '1 15' -> 115)
                m = re.search(r"^(.*?)\s*[\.·_\-\s]{3,}\s*(\d[\s\d]*\d|\d+)\s*$", line)
                if m:
                    part = m.group(1).strip()
                    full_title = f"{pending_title} {part}".strip() if pending_title else part
                    pg_str = re.sub(r"\s+", "", m.group(2))
                    page_num = int(pg_str)
                    if 1 <= page_num <= len(doc) and len(full_title) >= 2:
                        toc[page_num] = full_title
                    pending_title = ""
                else:
                    if not re.match(r"^(?:[Iİ1-9ivxlcdm]+[\-\s]+[A-ZÇĞİÖŞÜa-zçğıöşü\s]+)$", line) and len(line) > 3 and not line.isdigit():
                        pending_title = line
                    else:
                        pending_title = ""

        return toc

    def build_chapters(self, blocks: List[DocumentBlock], default_title: str = "Bölüm") -> List[Chapter]:
        """
        Groups sequential document blocks into logical chapters.
        Cleans up empty headings and merges front matter cleanly.
        """
        raw_chapters: List[Chapter] = []
        current_chapter: Optional[Chapter] = None
        chapter_counter = 0

        for block in blocks:
            if block.block_type == "heading":
                chapter_counter += 1
                title = block.text.strip()
                chap_id = f"chapter_{chapter_counter:03d}"
                current_chapter = Chapter(title=title, chapter_id=chap_id)
                raw_chapters.append(current_chapter)
                current_chapter.blocks.append(block)
            else:
                if current_chapter is None:
                    chapter_counter += 1
                    current_chapter = Chapter(title="Giriş", chapter_id=f"chapter_{chapter_counter:03d}")
                    raw_chapters.append(current_chapter)
                current_chapter.blocks.append(block)

        # Filter out empty chapters (chapters with no paragraphs or images)
        meaningful_chapters: List[Chapter] = []
        for chap in raw_chapters:
            content_blocks = [b for b in chap.blocks if b.block_type in ("paragraph", "image")]
            if content_blocks:
                meaningful_chapters.append(chap)
            elif meaningful_chapters:
                # Merge orphan heading as sub-element of previous chapter
                meaningful_chapters[-1].blocks.extend(chap.blocks)

        # If after filtering no chapters remain or only 1 huge chapter
        if not meaningful_chapters:
            return [Chapter(title="Kitap", chapter_id="chapter_001", blocks=blocks)]

        # Re-index chapter IDs
        for idx, chap in enumerate(meaningful_chapters):
            chap.chapter_id = f"chapter_{idx + 1:03d}"

        return meaningful_chapters

        # Fallback: if all text was dumped into a single huge chapter with > 100 blocks
        # and no headings, partition into sensible reading chunks of ~50 paragraphs each
        if len(chapters) == 1 and len(chapters[0].blocks) > 80:
            single = chapters[0]
            chunk_size = 50
            new_chapters: List[Chapter] = []
            for i in range(0, len(single.blocks), chunk_size):
                num = (i // chunk_size) + 1
                c = Chapter(
                    title=f"{default_title} {num}",
                    chapter_id=f"chapter_{num:03d}",
                    blocks=single.blocks[i:i + chunk_size]
                )
                new_chapters.append(c)
            return new_chapters

        return chapters if chapters else [Chapter(title="İçerik", chapter_id="chapter_001", blocks=blocks)]
