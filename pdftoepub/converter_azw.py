"""
AZW3 (Amazon Kindle KF8) Converter module.
Detects local Calibre installation and converts EPUB to AZW3.
Provides clear fallback instructions if Calibre is not present.
"""

import os
import shutil
import subprocess
from typing import Optional, Tuple


CALIBRE_SEARCH_PATHS = [
    r"C:\Program Files\Calibre2\ebook-convert.exe",
    r"C:\Program Files (x86)\Calibre2\ebook-convert.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\calibre-ebook\ebook-convert.exe"),
    r"C:\Calibre\ebook-convert.exe",
    r"C:\Calibre-Portable\Calibre\ebook-convert.exe",
]


class AZW3Converter:
    def __init__(self, custom_calibre_path: Optional[str] = None):
        self.calibre_exe = self._find_ebook_convert(custom_calibre_path)

    def _find_ebook_convert(self, custom_path: Optional[str] = None) -> Optional[str]:
        """Locates the ebook-convert executable from PATH or standard directories."""
        if custom_path and os.path.exists(custom_path):
            return custom_path

        # 1. Check system PATH
        path_in_env = shutil.which("ebook-convert")
        if path_in_env:
            return path_in_env

        # 2. Check standard Windows locations
        for p in CALIBRE_SEARCH_PATHS:
            if os.path.exists(p):
                return p

        return None

    @property
    def is_available(self) -> bool:
        return self.calibre_exe is not None

    def convert_epub_to_azw3(self, epub_path: str, output_azw3_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Converts an EPUB file to AZW3 format using Calibre's ebook-convert.
        Returns (success: bool, message_or_path: str).
        """
        if not os.path.exists(epub_path):
            return False, f"EPUB dosyası bulunamadı: {epub_path}"

        if not output_azw3_path:
            base, _ = os.path.splitext(epub_path)
            output_azw3_path = f"{base}.azw3"

        if not self.is_available:
            msg = (
                "Calibre (ebook-convert) sistemde bulunamadı.\n"
                "• EPUB dosyanız başarıyla oluşturuldu ve Amazon'un resmi 'Send to Kindle' servisiyle doğrudan Kindle'a gönderilebilir.\n"
                "• USB kablosuyla doğrudan cihaza yüklemek için AZW3 formatı istiyorsanız, "
                "Calibre'yi resmi sitesinden (calibre-ebook.com) veya PowerShell ile 'winget install calibre' komutunu kullanarak kurabilirsiniz."
            )
            return False, msg

        cmd = [
            self.calibre_exe,
            epub_path,
            output_azw3_path,
            "--output-profile", "kindle",
            "--share-not-sync"
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False
            )
            if result.returncode == 0 and os.path.exists(output_azw3_path):
                return True, output_azw3_path
            else:
                return False, f"Calibre dönüştürme hatası:\n{result.stderr or result.stdout}"
        except Exception as e:
            return False, f"AZW3 dönüştürme işlemi sırasında hata oluştu: {str(e)}"
