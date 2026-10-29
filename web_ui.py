"""
Web UI Launcher for PDF to EPUB & AZW3 Studio.
Runs FastAPI with Uvicorn and provides a safe, GPU-optimized local web studio.
"""

import sys
import webbrowser
import threading
import time
import argparse
import uvicorn


def open_browser_safely(url: str, delay: float = 2.0):
    time.sleep(delay)
    try:
        print(f"\n[Web UI] Tarayıcı açılıyor: {url}")
        webbrowser.open_new_tab(url)
    except Exception as e:
        print(f"[Web UI] Tarayıcı otomatik açılamadı, lütfen elle açın ({url}): {e}")


def main():
    parser = argparse.ArgumentParser(description="PDF to EPUB & AZW3 Web Studio")
    parser.add_argument("--host", default="127.0.0.1", help="Sunucu adresi (Varsayılan: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Sunucu portu (Varsayılan: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Tarayıcıyı otomatik açma")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"

    print("=" * 65)
    print("  PDF to EPUB & AZW3 Studio - Yerel Türkçe E-Kitap Dönüştürücü")
    print("=" * 65)
    print(f"\n[+] Yerel Web Sunucusu Hazır:")
    print(f"    --> {url}")
    print(f"\nTarayıcınızdan yukarıdaki adresi açarak kullanabilirsiniz.")
    print("Durdurmak için: CTRL + C\n")

    if not args.no_browser:
        threading.Thread(target=open_browser_safely, args=(url,), daemon=True).start()

    # Start FastAPI server with clean logging (silence repetitive polling access logs)
    uvicorn.run(
        "pdftoepub.web:app",
        host=args.host,
        port=args.port,
        log_level="warning",
        access_log=False
    )


if __name__ == "__main__":
    main()
