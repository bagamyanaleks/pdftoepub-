#!/usr/bin/env python3
"""
Automated Tesseract 5 & Turkish Language Pack Installer.
Cross-platform: Windows (zero-admin portable layout), Linux (apt), and macOS (brew).
"""

import os
import sys
import platform
import shutil
import tarfile
import urllib.request
import subprocess

TESSERACT_PORTABLE_URL = "https://github.com/mikhailgarber/tesseract-portable/releases/download/v5.5.3_4/tesseract-5.5.3_4-x64-windows-static.tar.gz"

TRAINEDDATA_URLS = {
    "tur.traineddata": "https://github.com/tesseract-ocr/tessdata_best/raw/main/tur.traineddata",
    "eng.traineddata": "https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata",
    "osd.traineddata": "https://github.com/tesseract-ocr/tessdata_fast/raw/main/osd.traineddata",
}


def print_step(msg: str):
    print(f"\n[+] {msg}")


def print_success(msg: str):
    print(f"[OK] {msg}")


def print_warn(msg: str):
    print(f"[!] {msg}")


def setup_windows():
    local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
    target_dir = os.path.join(local_app_data, "Programs", "Tesseract-OCR")
    bin_dir = os.path.join(target_dir, "bin")
    tess_exe = os.path.join(bin_dir, "tesseract.exe")
    tessdata_dir = os.path.join(bin_dir, "tessdata")

    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(bin_dir, exist_ok=True)
    os.makedirs(tessdata_dir, exist_ok=True)

    # 1. Download & Extract Tesseract 5 if not already present
    if not os.path.isfile(tess_exe):
        print_step("Tesseract 5.5 taşınabilir Windows sürümü indiriliyor...")
        archive_path = os.path.join(target_dir, "tesseract-portable.tar.gz")
        try:
            urllib.request.urlretrieve(TESSERACT_PORTABLE_URL, archive_path)
            print_success(f"İndirildi: {os.path.getsize(archive_path) / (1024*1024):.2f} MB")
            
            print_step("Arşiv açılıyor...")
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(target_dir)
            
            if os.path.exists(archive_path):
                os.remove(archive_path)
            print_success("Tesseract ikilileri başarıyla çıkartıldı.")
        except Exception as e:
            print_warn(f"Tesseract indirme/açma hatası: {e}")
            return False
    else:
        print_success(f"Tesseract 5 ikilisi mevcut: {tess_exe}")

    # 2. Download Turkish & English traineddata
    print_step("Türkçe yüksek doğruluklu dil modeli (tessdata_best) kontrol ediliyor...")
    for filename, url in TRAINEDDATA_URLS.items():
        dst = os.path.join(tessdata_dir, filename)
        if not os.path.isfile(dst) or os.path.getsize(dst) < 1000:
            print(f"    --> {filename} indiriliyor...")
            try:
                urllib.request.urlretrieve(url, dst)
                print_success(f"    {filename} tamamlandı ({os.path.getsize(dst) / (1024*1024):.2f} MB)")
            except Exception as e:
                print_warn(f"    {filename} indirilemedi: {e}")
        else:
            print_success(f"    {filename} hazır ({os.path.getsize(dst) / (1024*1024):.2f} MB)")

    # 3. Verify
    print_step("Kurulum test ediliyor...")
    try:
        res = subprocess.run([tess_exe, "--list-langs"], capture_output=True, text=True, check=True)
        langs = [l.strip() for l in res.stdout.splitlines() if l.strip() and not l.startswith("List")]
        print_success(f"Tesseract 5 hazır! Tanınan diller: {', '.join(langs)}")
        return True
    except Exception as e:
        print_warn(f"Doğrulama başarısız oldu: {e}")
        return False


def setup_linux():
    print_step("Linux Debian/Ubuntu için Tesseract 5 kurulumu...")
    if shutil.which("tesseract"):
        print_success("Tesseract zaten sistemde kurulu.")
    else:
        print("Sistem paketleri kuruluyor (sudo gerekebilir)...")
        cmd = ["sudo", "apt-get", "update", "&&", "sudo", "apt-get", "install", "-y", "tesseract-ocr", "tesseract-ocr-tur", "tesseract-ocr-eng"]
        subprocess.run(" ".join(cmd), shell=True)


def setup_darwin():
    print_step("macOS için Tesseract kurulumu...")
    if shutil.which("tesseract"):
        print_success("Tesseract zaten sistemde kurulu.")
    else:
        print("Homebrew ile Tesseract kuruluyor...")
        subprocess.run(["brew", "install", "tesseract", "tesseract-lang"])


def main():
    print("=" * 60)
    print("  PDF to EPUB & AZW3 Studio - Tesseract 5 Kurulum Sihirbazı")
    print("=" * 60)

    sys_os = platform.system().lower()
    if sys_os == "windows":
        success = setup_windows()
    elif sys_os == "linux":
        setup_linux()
        success = True
    elif sys_os == "darwin":
        setup_darwin()
        success = True
    else:
        print_warn(f"Desteklenmeyen işletim sistemi: {sys_os}")
        success = False

    if success:
        print("\n" + "=" * 60)
        print("  [OK] Kurulum basariyla tamamlandi!")
        print("  Web Studio'yu baslatmak icin: python web_ui.py")
        print("=" * 60 + "\n")
    else:
        print("\n[!] Kurulum tamamlanamadı. Lütfen internet bağlantınızı kontrol edin.\n")


if __name__ == "__main__":
    main()
