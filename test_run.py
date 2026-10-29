"""
Direct conversion test script for Ayşe Kulin - Dört Gün Üç Gece
"""

import time
from pdftoepub.pipeline import ConversionPipeline


def main():
    start = time.time()
    print("[TEST] Starting conversion...")

    pipeline = ConversionPipeline(ocr_mode="auto")

    def on_prog(pct, msg):
        print(f"[{int(pct*100):>3}%] {msg}", flush=True)

    result = pipeline.convert(
        pdf_path="Ayşe Kulin Dört Gün Üç Gece Everest Yayınları.pdf",
        output_dir="converted_ebooks",
        title="Dört Gün Üç Gece",
        author="Ayşe Kulin",
        progress_callback=on_prog
    )

    elapsed = round(time.time() - start, 2)
    print(f"\n[TEST SUCCESS] Finished in {elapsed}s!")
    print(f"  Title: {result['title']}")
    print(f"  Author: {result['author']}")
    print(f"  Total Pages: {result['total_pages']}")
    print(f"  OCR Pages: {result['ocr_pages_count']}")
    print(f"  Chapters: {result['chapter_count']}")
    print(f"  EPUB: {result['epub_path']}")


if __name__ == "__main__":
    main()
