"""
Command Line Interface (CLI) for PDF to EPUB & AZW3 Converter.
Features rich interactive progress, GPU status reporting, and batch conversion.
"""

import os
import sys
import argparse
import glob
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table
from rich.panel import Panel

from pdftoepub.pipeline import ConversionPipeline


# Ensure Windows console handles UTF-8 smoothly without charmap crashes
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(safe_box=True, highlight=False)


def process_single_pdf(pdf_path: str, args) -> bool:
    console.print(Panel(f"[bold cyan]Dönüştürülüyor:[/bold cyan] {os.path.basename(pdf_path)}", expand=False))
    
    pipeline = ConversionPipeline(
        ocr_mode=args.ocr,
        ocr_engine=args.ocr_engine,
        use_gpu=None if args.gpu is None else args.gpu,
        calibre_path=args.calibre_path,
        ai_repair=args.ai_repair,
        ai_backend=args.ai_backend,
        ai_model=args.ai_model,
        ai_api_base=args.ai_api_base
    )

    with Progress(
        TextColumn("[bold blue]•[/bold blue]"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Başlatılıyor...", total=100)

        def on_progress(fraction: float, message: str):
            progress.update(task, completed=int(fraction * 100), description=message)

        try:
            result = pipeline.convert(
                pdf_path=pdf_path,
                output_dir=args.output,
                title=args.title,
                author=args.author,
                progress_callback=on_progress
            )

            # Summary Table
            table = Table(title="[bold green]✓ Dönüştürme Başarılı[/bold green]", show_header=True, header_style="bold magenta")
            table.add_column("Özellik", style="dim", width=20)
            table.add_column("Değer")

            table.add_row("Kitap Adı", result["title"])
            table.add_row("Yazar", result["author"])
            table.add_row("Toplam Sayfa", str(result["total_pages"]))
            table.add_row("OCR Yapılan Sayfa", str(result["ocr_pages_count"]))
            if result.get("ai_repairs_count", 0) > 0:
                table.add_row("AI Onarım (Qwen)", f"[bold green]{result['ai_repairs_count']} hasarlı paragraf tamamlandı[/bold green]")
            table.add_row("Bölüm Sayısı", str(result["chapter_count"]))
            table.add_row("EPUB Çıktısı", f"[cyan]{result['epub_path']}[/cyan]")
            
            if result["azw3_path"]:
                table.add_row("AZW3 Çıktısı", f"[green]{result['azw3_path']}[/green]")
            else:
                table.add_row("AZW3 Durumu", f"[yellow]{result['azw3_message']}[/yellow]")

            console.print(table)
            return True

        except Exception as e:
            console.print(f"[bold red]HATA:[/bold red] {str(e)}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Yerel GPU Destekli Türkçe PDF -> EPUB / AZW3 Dönüştürücü"
    )
    parser.add_argument("input", nargs="?", help="Dönüştürülecek PDF dosyası veya klasör yolu")
    parser.add_argument("--batch", "-b", help="Klasördeki tüm PDF'leri toplu dönüştür", default=None)
    parser.add_argument("--output", "-o", help="Çıktı klasörü (Varsayılan: PDF ile aynı dizin)", default=None)
    parser.add_argument("--ocr", choices=["auto", "force", "none"], default="force", help="OCR Modu (auto: yalnızca gerektiğinde, force: tüm sayfalara en yüksek kalite, none: sadece vektörel)")
    parser.add_argument("--ocr-engine", choices=["auto", "tesseract", "easyocr"], default="tesseract", help="OCR Motoru (auto: Tesseract 5 öncelikli, tesseract: Tesseract 5 LSTM, easyocr: EasyOCR GPU)")
    parser.add_argument("--gpu", action="store_true", default=None, help="GPU ivmelendirmeyi zorla aç")
    parser.add_argument("--no-gpu", dest="gpu", action="store_false", help="GPU kullanma, CPU ile çalıştır")
    parser.add_argument("--title", "-t", help="Kitap başlığını manuel belirle", default=None)
    parser.add_argument("--author", "-a", help="Yazar adını manuel belirle", default=None)
    parser.add_argument("--calibre-path", help="Calibre ebook-convert.exe dosya yolu", default=None)
    parser.add_argument("--ai-repair", action="store_true", default=True, help="Hasarlı/kopuk paragrafları yerel Qwen yapay zeka modeliyle onar (Varsayılan: Açık)")
    parser.add_argument("--no-ai-repair", dest="ai_repair", action="store_false", help="AI metin onarımını devre dışı bırak")
    parser.add_argument("--ai-backend", choices=["transformers", "openai_compatible", "ollama"], default="transformers", help="Yapay zeka motoru")
    parser.add_argument("--ai-model", default="Qwen/Qwen2.5-1.5B-Instruct", help="Yapay zeka model adı")
    parser.add_argument("--ai-api-base", default="http://localhost:11434/v1", help="Ollama veya yerel API adresi")

    args = parser.parse_args()

    # If no argument passed, look for PDFs in current directory
    if not args.input and not args.batch:
        pdfs = glob.glob("*.pdf")
        if pdfs:
            console.print("[bold yellow]PDF parametresi belirtilmedi. Mevcut dizindeki PDF'ler listeleniyor:[/bold yellow]")
            for idx, p in enumerate(pdfs):
                console.print(f" [{idx + 1}] {p}")
            choice = input("\nDönüştürmek istediğiniz numara (veya hepsi için 'all'): ").strip()
            if choice.lower() == "all":
                args.batch = "."
            elif choice.isdigit() and 1 <= int(choice) <= len(pdfs):
                args.input = pdfs[int(choice) - 1]
            else:
                console.print("[red]İptal edildi.[/red]")
                sys.exit(0)
        else:
            parser.print_help()
            sys.exit(1)

    if args.batch:
        search_path = os.path.join(args.batch, "*.pdf") if os.path.isdir(args.batch) else args.batch
        found_pdfs = glob.glob(search_path)
        if not found_pdfs:
            console.print(f"[red]Belirtilen yolda PDF bulunamadı: {args.batch}[/red]")
            sys.exit(1)

        console.print(f"[bold green]{len(found_pdfs)} adet PDF bulundu, toplu dönüştürme başlatılıyor...[/bold green]\n")
        success_count = 0
        for pdf_file in found_pdfs:
            if process_single_pdf(pdf_file, args):
                success_count += 1
            console.print()

        console.print(Panel(f"[bold green]Toplu işlem bitti: {success_count}/{len(found_pdfs)} kitap dönüştürüldü.[/bold green]"))

    elif args.input:
        if not os.path.exists(args.input):
            console.print(f"[red]Dosya bulunamadı: {args.input}[/red]")
            sys.exit(1)
        process_single_pdf(args.input, args)


if __name__ == "__main__":
    main()
