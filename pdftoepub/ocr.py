"""
Multi-Engine Turkish OCR Module for PDF to EPUB/AZW3 Studio.
Supports Tesseract 5 (high-accuracy LSTM with Turkish traineddata)
and EasyOCR (PyTorch GPU CUDA acceleration) with automatic detection and fallback.
"""

import os
import shutil
from typing import List, Optional
import numpy as np


def find_tesseract_binary() -> Optional[str]:
    """
    Finds the Tesseract OCR executable on the system.
    Searches custom environment variables, PATH, and standard Windows installation paths.
    """
    # 1. Direct environment variable override
    env_cmd = os.environ.get("TESSERACT_CMD") or os.environ.get("TESSERACT_PATH")
    if env_cmd and os.path.isfile(env_cmd):
        return env_cmd

    # 2. System PATH
    which_tess = shutil.which("tesseract")
    if which_tess:
        return which_tess

    # 3. Standard Windows locations
    user_home = os.path.expanduser("~")
    candidates = [
        # User local installation (zero-admin portable layout)
        os.path.join(user_home, "AppData", "Local", "Programs", "Tesseract-OCR", "bin", "tesseract.exe"),
        os.path.join(user_home, "AppData", "Local", "Programs", "Tesseract-OCR", "tesseract.exe"),
        # System-wide installations
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(user_home, "AppData", "Local", "Tesseract-OCR", "tesseract.exe"),
    ]

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    return None


def get_tessdata_dir(tesseract_binary: Optional[str] = None) -> Optional[str]:
    """Locates the tessdata language models directory."""
    if os.environ.get("TESSDATA_PREFIX") and os.path.isdir(os.environ["TESSDATA_PREFIX"]):
        return os.environ["TESSDATA_PREFIX"]

    candidates = [
        # Linux standard distribution paths (Ubuntu, Debian, Docker)
        "/usr/share/tesseract-ocr/5/tessdata",
        "/usr/share/tesseract-ocr/4.00/tessdata",
        "/usr/share/tesseract-ocr/tessdata",
        "/usr/share/tessdata",
        # macOS Homebrew paths
        "/opt/homebrew/share/tessdata",
        "/usr/local/share/tessdata",
    ]

    if tesseract_binary:
        bin_dir = os.path.dirname(os.path.abspath(tesseract_binary))
        candidates = [
            os.path.join(bin_dir, "tessdata"),
            os.path.join(bin_dir, "..", "tessdata"),
            os.path.join(bin_dir, "..", "share", "tessdata"),
        ] + candidates

    for c in candidates:
        norm = os.path.abspath(c)
        if os.path.isdir(norm):
            return norm

    return None


def is_tesseract_available() -> bool:
    """Returns True if Tesseract OCR executable and Turkish traineddata are ready."""
    binary = find_tesseract_binary()
    if not binary:
        return False
    tessdata = get_tessdata_dir(binary)
    if tessdata:
        tur_path = os.path.join(tessdata, "tur.traineddata")
        if os.path.isfile(tur_path):
            return True
    return False


class OCREngine:
    def __init__(
        self,
        engine: str = "auto",  # "auto", "tesseract", "easyocr"
        languages: Optional[List[str]] = None,
        use_gpu: Optional[bool] = None,
        tesseract_cmd: Optional[str] = None
    ):
        self.requested_engine = engine.lower()
        self.languages = languages or ["tr", "en"]
        self._use_gpu = use_gpu
        self._custom_tess_cmd = tesseract_cmd
        self._reader = None
        self._cuda_available = None
        self._active_engine = None
        self._tesseract_bin: Optional[str] = None
        self._tess_lang: Optional[str] = None

        self._resolve_engine()

    def _resolve_engine(self):
        tess_bin = self._custom_tess_cmd or find_tesseract_binary()

        if self.requested_engine == "tesseract":
            if not tess_bin:
                raise RuntimeError("Tesseract OCR bulunamadı. Lütfen Tesseract 5 kurun veya 'easyocr' modunu seçin.")
            self._active_engine = "tesseract"
        elif self.requested_engine == "easyocr":
            self._active_engine = "easyocr"
        else:  # "auto"
            # Prefer Tesseract 5 for printed books due to superior Turkish diacritics & grammar fidelity
            if tess_bin and is_tesseract_available():
                self._active_engine = "tesseract"
            else:
                self._active_engine = "easyocr"

        # Initialize Tesseract config if selected
        if self._active_engine == "tesseract":
            import pytesseract
            self._tesseract_bin = tess_bin
            pytesseract.pytesseract.tesseract_cmd = tess_bin
            tessdata = get_tessdata_dir(tess_bin)
            if tessdata:
                os.environ["TESSDATA_PREFIX"] = tessdata

            # Build language string (map 'tr' -> 'tur', 'en' -> 'eng')
            tess_langs = []
            for lang in self.languages:
                if lang in ("tr", "tur"):
                    tess_langs.append("tur")
                elif lang in ("en", "eng"):
                    tess_langs.append("eng")
                else:
                    tess_langs.append(lang)
            self._tess_lang = "+".join(tess_langs) if tess_langs else "tur"
            print(f"[OCREngine] Active Engine: Tesseract 5 (Binary: {self._tesseract_bin}, Lang: {self._tess_lang})")
        else:
            print(f"[OCREngine] Active Engine: EasyOCR (Languages: {self.languages})")

    @property
    def active_engine(self) -> str:
        return self._active_engine

    @property
    def is_cuda_available(self) -> bool:
        if self._cuda_available is None:
            try:
                import torch  # type: ignore
                self._cuda_available = torch.cuda.is_available()
            except ImportError:
                self._cuda_available = False
        return self._cuda_available

    def _get_easyocr_reader(self):
        if self._reader is None:
            import easyocr  # type: ignore
            import torch  # type: ignore

            gpu_flag = self.is_cuda_available if self._use_gpu is None else self._use_gpu
            device_name = torch.cuda.get_device_name(0) if (gpu_flag and torch.cuda.is_available()) else "CPU"
            print(f"[OCREngine] Initializing EasyOCR (Languages: {self.languages}, Device: {device_name})")
            
            self._reader = easyocr.Reader(self.languages, gpu=gpu_flag)
        return self._reader

    def ocr_page(self, page, dpi: int = 300) -> str:
        """
        Renders a PyMuPDF page at high DPI (default 300) and extracts Turkish text.
        Preserves reading order and paragraphs.
        """
        pix = page.get_pixmap(dpi=dpi)

        if self._active_engine == "tesseract":
            return self._ocr_pixmap_tesseract(pix)
        else:
            return self._ocr_pixmap_easyocr(pix)

    def _ocr_pixmap_tesseract(self, pix) -> str:
        import pytesseract
        from PIL import Image

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        # PSM 3: Fully automatic page segmentation without OSD (fast & accurate for books)
        raw_text = pytesseract.image_to_string(img, lang=self._tess_lang, config="--psm 3")
        
        # Clean lines and normalize paragraphs
        paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
        return "\n\n".join(paragraphs)

    def _ocr_pixmap_easyocr(self, pix) -> str:
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        if pix.n == 4:
            img_np = img_np[:, :, :3]

        reader = self._get_easyocr_reader()
        results = reader.readtext(img_np, paragraph=True)
        sorted_results = sorted(results, key=lambda item: item[0][0][1])
        extracted_paragraphs = [text.strip() for _, text in sorted_results if text.strip()]
        return "\n\n".join(extracted_paragraphs)

    def ocr_image_bytes(self, image_bytes: bytes) -> str:
        """Runs OCR directly on raw image bytes."""
        import io
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))

        if self._active_engine == "tesseract":
            import pytesseract
            if img.mode != "RGB":
                img = img.convert("RGB")
            raw_text = pytesseract.image_to_string(img, lang=self._tess_lang, config="--psm 3")
            paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
            return "\n\n".join(paragraphs)
        else:
            img_np = np.array(img)
            if len(img_np.shape) == 3 and img_np.shape[2] == 4:
                img_np = img_np[:, :, :3]

            reader = self._get_easyocr_reader()
            results = reader.readtext(img_np, paragraph=True)
            sorted_results = sorted(results, key=lambda item: item[0][0][1])
            return "\n\n".join([text.strip() for _, text in sorted_results if text.strip()])

