"""
Master Conversion Pipeline.
Orchestrates PDF analysis, intelligent OCR, Turkish linguistic cleaning,
image/media extraction, chapter segmentation, and EPUB/AZW3 generation.
"""

import os
import shutil
import tempfile
from typing import Optional, Callable, Dict, Any, List
import re
import pymupdf as fitz

from .analyzer import PDFAnalyzer, PageType
from .ocr import OCREngine
from .cleaner import TextCleaner
from .ai_repair import AIRepairEngine
from .structure import StructureDetector, DocumentBlock
from .media import MediaManager
from .builder_epub import EPUBBuilder
from .converter_azw import AZW3Converter


def _normalize_fuzzy_title(s: str) -> str:
    table = str.maketrans({
        'ç': 'c', 'Ç': 'c',
        'ğ': 'g', 'Ğ': 'g',
        'ı': 'i', 'I': 'i', 'İ': 'i', 'i': 'i',
        'ö': 'o', 'Ö': 'o',
        'ş': 's', 'Ş': 's',
        'ü': 'u', 'Ü': 'u'
    })
    s = s.translate(table).lower()
    return re.sub(r'[^a-z0-9]', '', s)


_MONTHS_PATTERN = r'(?:ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık|januar|februar|märz|april|mai|juni|juli|august|september|oktober|november|dezember)'


def _is_date_or_place_subtitle(text: str) -> bool:
    t = text.lower()
    has_year = bool(re.search(r'\b(19\d\d|20\d\d)\b', t))
    has_month = bool(re.search(_MONTHS_PATTERN, t))
    return (has_year or has_month) and len(text) <= 60


def _is_chapter_header_or_noise(p: str, title: str) -> bool:
    p_stripped = p.strip()
    if not p_stripped or len(p_stripped) <= 3:
        return True
    uppers = sum(1 for c in p_stripped if c.isupper())
    lowers = sum(1 for c in p_stripped if c.islower())
    total_letters = uppers + lowers

    if _is_date_or_place_subtitle(p_stripped):
        return False

    norm_p = _normalize_fuzzy_title(p_stripped)
    title_words = [_normalize_fuzzy_title(w) for w in title.split() if len(_normalize_fuzzy_title(w)) >= 4]
    if any(tw in norm_p for tw in title_words) and len(p_stripped) <= 80:
        return True

    if (uppers >= 3 and lowers <= 3 and len(p_stripped) <= 70) or (total_letters > 0 and uppers / total_letters > 0.60 and len(p_stripped) <= 70):
        return True
    if len(p_stripped) <= 25 and not re.search(r'[\.!\?…]$', p_stripped):
        return True
    return False


class ConversionPipeline:
    def __init__(
        self,
        ocr_mode: str = "force",  # "auto", "force", "none"
        ocr_engine: str = "tesseract",  # "auto", "tesseract", "easyocr"
        use_gpu: Optional[bool] = None,
        calibre_path: Optional[str] = None,
        ai_repair: bool = True,
        ai_backend: str = "transformers",
        ai_model: str = "Qwen/Qwen2.5-1.5B-Instruct",
        ai_api_base: str = "http://localhost:11434/v1"
    ):
        self.ocr_mode = ocr_mode
        self.ocr_engine = ocr_engine
        self.use_gpu = use_gpu
        self.ai_repair = ai_repair
        self.analyzer = PDFAnalyzer()
        self.cleaner = TextCleaner()
        self.ai_repair_engine = AIRepairEngine(
            enabled=ai_repair,
            backend=ai_backend,
            model_name=ai_model,
            api_base=ai_api_base
        )
        self.structure_detector = StructureDetector()
        self.azw_converter = AZW3Converter(custom_calibre_path=calibre_path)
        self._ocr_engine: Optional[OCREngine] = None

    def _get_ocr_engine(self) -> OCREngine:
        if self._ocr_engine is None:
            self._ocr_engine = OCREngine(engine=self.ocr_engine, use_gpu=self.use_gpu)
        return self._ocr_engine

    def convert(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes the end-to-end conversion process.
        Returns a summary dictionary with generated file paths and metrics.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF bulunamadı: {pdf_path}")

        filename = os.path.basename(pdf_path)
        base_name, _ = os.path.splitext(filename)
        # Strip UUID prefix if uploaded via Web UI
        base_name = re.sub(r"^[0-9a-fA-F\-]{32,38}_", "", base_name)

        if not output_dir:
            output_dir = os.path.dirname(os.path.abspath(pdf_path))

        def update_progress(percent: float, message: str):
            if progress_callback:
                progress_callback(percent, message)
            else:
                print(f"[{int(percent * 100)}%] {message}")

        update_progress(0.05, f"PDF analiz ediliyor: {filename}")

        # Step 1: Analyze Document
        analysis = self.analyzer.analyze_pdf(pdf_path)

        # Smart title & author fallback from filename
        clean_basename = re.sub(
            r"\s*(?:Everest|Can|İletişim|Doğan|Yapı\s+Kredi|İş\s+Bankası)\s+Yayınları\s*(?:\(\d+\))?",
            "",
            base_name,
            flags=re.IGNORECASE
        ).strip()
        guessed_author = None
        guessed_title = clean_basename
        if " - " in clean_basename:
            guessed_author, guessed_title = clean_basename.split(" - ", 1)
        else:
            # Common two-word or three-word author detection at start of filename
            words = clean_basename.split()
            if len(words) >= 4 and words[0].isalpha() and words[1].isalpha():
                first_two = f"{words[0]} {words[1]}"
                if first_two.lower() in ("ayşe kulin", "jojo moyes", "orhan pamuk", "ahmet ümit", "sabahattin ali", "yaşar kemal", "elif şafak", "zülfü livaneli"):
                    guessed_author = first_two
                    guessed_title = " ".join(words[2:]).strip()

        book_title = title or analysis.title or guessed_title or base_name
        book_author = author or analysis.author or guessed_author or "Bilinmeyen Yazar"

        total_pages = analysis.total_pages
        update_progress(
            0.15,
            f"Analiz tamamlandı ({total_pages} sayfa, {analysis.digital_page_count} dijital, {analysis.ocr_required_page_count} OCR gerektiren sayfa)"
        )

        temp_workspace = tempfile.mkdtemp(prefix="pdftoepub_")
        media_mgr = MediaManager(temp_workspace)

        doc = fitz.open(pdf_path)
        total_ai_repairs = 0
        document_blocks: List[DocumentBlock] = []
        pending_footnotes: List[str] = []

        def flush_footnotes():
            nonlocal pending_footnotes
            if pending_footnotes:
                for fn in pending_footnotes:
                    document_blocks.append(DocumentBlock(text=fn, block_type="footnote"))
                pending_footnotes = []

        # Extract printed TOC if present in book (e.g. pages 4-7)
        printed_toc = self.structure_detector.extract_printed_toc(doc)
        if printed_toc:
            print(f"Basılı İçindekiler tablosundan {len(printed_toc)} bölüm algılandı.")

        try:
            # Step 2: Extract Cover Image from Page 1
            if total_pages > 0:
                first_page = doc[0]
                first_images = first_page.get_images()
                if first_images and len(first_images) == 1:
                    # Full page cover image
                    xref = first_images[0][0]
                    base_image = doc.extract_image(xref)
                    media_mgr.save_optimized_image(
                        base_image["image"],
                        f"cover.{base_image['ext']}",
                        quality=92
                    )
                    media_mgr.cover_path = os.path.join(media_mgr.images_dir, f"cover.{base_image['ext']}")
                else:
                    # Render first page as cover
                    media_mgr.render_page_as_cover(first_page, dpi=200)

            # Step 3: Process Pages (Extract text or OCR)
            for i, p_info in enumerate(analysis.pages):
                page_idx = p_info.page_number - 1
                page = doc[page_idx]

                progress_val = 0.20 + (0.50 * (i / max(total_pages, 1)))

                # Determine if OCR should run for this page
                do_ocr = False
                if self.ocr_mode == "force":
                    do_ocr = True
                elif self.ocr_mode == "none":
                    do_ocr = False
                else:  # auto
                    do_ocr = p_info.page_type in (PageType.SCANNED_OCR_REQUIRED, PageType.CORRUPTED_OCR_REQUIRED)

                page_raw_text = ""
                if do_ocr:
                    ocr_engine = self._get_ocr_engine()
                    eng_label = "Tesseract 5" if ocr_engine.active_engine == "tesseract" else "GPU EasyOCR"
                    update_progress(progress_val, f"Sayfa {p_info.page_number}/{total_pages} {eng_label} ile taranıyor...")
                    page_raw_text = ocr_engine.ocr_page(page, dpi=300)
                else:
                    update_progress(progress_val, f"Sayfa {p_info.page_number}/{total_pages} metin ayrıştırılıyor...")
                    page_raw_text = p_info.raw_text

                # Step 4: Extract embedded illustrations (for pages after cover)
                page_image_blocks = []
                if i > 0 and not do_ocr:
                    page_w = page.rect.width
                    page_h = page.rect.height
                    for img_idx, img_item in enumerate(page.get_images()):
                        xref = img_item[0]
                        try:
                            base_img = doc.extract_image(xref)
                            img_w = base_img.get("width", 0)
                            img_h = base_img.get("height", 0)

                            # Skip if image covers virtually the entire page and page has plenty of digital text (background scan/watermark)
                            rects = page.get_image_rects(xref)
                            if rects:
                                box = rects[0]
                                if p_info.char_count > 150 and box.width >= page_w * 0.92 and box.height >= page_h * 0.92:
                                    continue
                            else:
                                if p_info.char_count > 150 and img_w >= page_w * 2.5 and img_h >= page_h * 2.5:
                                    continue

                            # Only include substantial figures (not tiny tracking lines/spacers)
                            if img_w > 80 and img_h > 80:
                                img_name = f"fig_p{p_info.page_number}_{img_idx}.{base_img['ext']}"
                                saved_img = media_mgr.save_optimized_image(
                                    base_img["image"],
                                    img_name,
                                    quality=85
                                )
                                if saved_img:
                                    page_image_blocks.append(
                                        DocumentBlock(text="", block_type="image", image_path=saved_img)
                                    )
                        except Exception:
                            pass

                # If this page starts a chapter according to the printed TOC
                page_num = p_info.page_number
                is_toc_chapter_start = page_num in printed_toc
                chapter_title = printed_toc.get(page_num, "")

                if is_toc_chapter_start:
                    flush_footnotes()
                    document_blocks.append(
                        DocumentBlock(text=chapter_title, block_type="heading", level=1)
                    )
                    if page_image_blocks:
                        document_blocks.extend(page_image_blocks)
                        page_image_blocks = []

                # Step 5: Extract footnotes & clean page text and split into blocks
                if page_raw_text.strip():
                    page_body_raw, page_fns = self.cleaner.extract_page_footnotes(page_raw_text)
                    if page_fns:
                        pending_footnotes.extend(page_fns)

                    cleaned_page_text = self.cleaner.process_full_text(
                        page_body_raw,
                        book_title=book_title,
                        author=book_author
                    )

                    # Step 5b: Selective AI Repair on heavily damaged paragraphs
                    if self.ai_repair and self.ai_repair_engine:
                        cleaned_page_text, rep_count = self.ai_repair_engine.repair_full_text(cleaned_page_text)
                        total_ai_repairs += rep_count

                    paragraphs = cleaned_page_text.split("\n\n")
                    first_p = True
                    past_header = not is_toc_chapter_start

                    for p in paragraphs:
                        p_stripped = p.strip()
                        if not p_stripped:
                            continue

                        # If this page started from printed TOC, skip redundant raw heading lines at top
                        if not past_header:
                            if _is_date_or_place_subtitle(p_stripped):
                                past_header = True
                                document_blocks.append(DocumentBlock(text=p_stripped, block_type="paragraph"))
                                continue

                            if _is_chapter_header_or_noise(p_stripped, chapter_title):
                                continue
                            else:
                                past_header = True

                        # Check if this paragraph is a chapter heading (for non-TOC pages or sub-sections)
                        if not is_toc_chapter_start:
                            is_heading = self.structure_detector.is_chapter_heading(
                                p_stripped,
                                is_large_font=p_info.has_large_heading,
                                book_title=book_title,
                                author=book_author
                            )

                            if is_heading:
                                flush_footnotes()
                                document_blocks.append(
                                    DocumentBlock(text=p_stripped, block_type="heading", level=1)
                                )
                                # Place any illustration right below the heading
                                if page_image_blocks:
                                    document_blocks.extend(page_image_blocks)
                                    page_image_blocks = []
                                first_p = False
                                continue

                        # Cross-page paragraph continuation
                        # If this is the first paragraph of the page, find the most recent paragraph block
                        prev_p_idx = None
                        if first_p and document_blocks:
                            for b_i in range(len(document_blocks) - 1, -1, -1):
                                if document_blocks[b_i].block_type == "paragraph":
                                    prev_p_idx = b_i
                                    break
                                elif document_blocks[b_i].block_type in ("heading", "footnote"):
                                    break

                        if prev_p_idx is not None:
                            prev_text = document_blocks[prev_p_idx].text.strip()
                            ends_with_terminal = bool(re.search(r'[\.!\?…\"”\']$', prev_text))
                            ends_with_hyphen = bool(re.search(r'[-–—\xad·•]$', prev_text))
                            is_dialogue = p_stripped.startswith("—") or p_stripped.startswith("- ") or p_stripped.startswith('"')

                            # Merge into previous paragraph if not a dialogue and either ends with hyphen or lacks terminal punctuation
                            if not is_dialogue and (ends_with_hyphen or not ends_with_terminal):
                                if ends_with_hyphen:
                                    merged = self.cleaner.dehyphenate(prev_text + "\n" + p_stripped)
                                else:
                                    merged = prev_text + " " + p_stripped
                                document_blocks[prev_p_idx].text = self.cleaner.heal_split_words(merged)
                                first_p = False
                                continue

                        first_p = False
                        document_blocks.append(
                            DocumentBlock(text=p_stripped, block_type="paragraph")
                        )

                # Any remaining illustrations on the page (not placed after a heading)
                if page_image_blocks:
                    document_blocks.extend(page_image_blocks)

            flush_footnotes()
            # Clean trailing hyphen on final paragraph if present
            for b in reversed(document_blocks):
                if b.block_type == "paragraph":
                    b.text = re.sub(r"[-–—\xad·•]+$", ".", b.text)
                    break
            doc.close()

            # Step 6: Build Book Chapters & TOC
            update_progress(0.75, "Bölümler ve içindekiler tablosu (TOC) oluşturuluyor...")
            chapters = self.structure_detector.build_chapters(document_blocks, default_title="Bölüm")

            # Step 7: Build EPUB 3
            update_progress(0.85, "EPUB 3 dosyası derleniyor...")
            epub_path = os.path.join(output_dir, f"{base_name}.epub")
            builder = EPUBBuilder(title=book_title, author=book_author, language="tr")
            builder.create_epub(
                chapters=chapters,
                output_filepath=epub_path,
                cover_image_path=media_mgr.cover_path,
                embedded_images=media_mgr.extracted_images
            )

            # Step 8: Build AZW3 (Calibre conversion)
            update_progress(0.92, "AZW3 formatına dönüştürülüyor...")
            azw3_path = os.path.join(output_dir, f"{base_name}.azw3")
            azw3_success, azw3_msg = self.azw_converter.convert_epub_to_azw3(epub_path, azw3_path)

            update_progress(1.0, "Dönüştürme başarıyla tamamlandı!")

            return {
                "success": True,
                "title": book_title,
                "author": book_author,
                "total_pages": total_pages,
                "ocr_pages_count": analysis.ocr_required_page_count,
                "ai_repairs_count": total_ai_repairs,
                "chapter_count": len(chapters),
                "epub_path": epub_path,
                "azw3_path": azw3_path if azw3_success else None,
                "azw3_message": azw3_msg,
                "cover_path": media_mgr.cover_path
            }

        finally:
            try:
                shutil.rmtree(temp_workspace, ignore_errors=True)
            except Exception:
                pass
