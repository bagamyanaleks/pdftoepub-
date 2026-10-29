"""
GPU-Accelerated Local Turkish OCR Engine.
Utilizes EasyOCR with PyTorch CUDA to recognize Turkish text with high fidelity.
"""

import numpy as np
from typing import List, Tuple, Optional


class OCREngine:
    def __init__(self, languages: Optional[List[str]] = None, use_gpu: Optional[bool] = None):
        self.languages = languages or ["tr", "en"]
        self._use_gpu = use_gpu
        self._reader = None
        self._cuda_available = None

    @property
    def is_cuda_available(self) -> bool:
        if self._cuda_available is None:
            try:
                import torch
                self._cuda_available = torch.cuda.is_available()
            except ImportError:
                self._cuda_available = False
        return self._cuda_available

    def _get_reader(self):
        if self._reader is None:
            import easyocr
            import torch

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
        # Render page to high-res pixmap
        pix = page.get_pixmap(dpi=dpi)
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        
        # If alpha channel present, convert RGBA to RGB
        if pix.n == 4:
            img_np = img_np[:, :, :3]

        reader = self._get_reader()
        # Read with paragraph=True to group nearby lines into logical blocks
        results = reader.readtext(img_np, paragraph=True)

        # Sort blocks vertically (top to bottom)
        # result format: ([[x1,y1], [x2,y2], [x3,y3], [x4,y4]], "text")
        sorted_results = sorted(results, key=lambda item: item[0][0][1])
        
        extracted_paragraphs = [text.strip() for _, text in sorted_results if text.strip()]
        return "\n\n".join(extracted_paragraphs)

    def ocr_image_bytes(self, image_bytes: bytes) -> str:
        """Runs OCR directly on raw image bytes."""
        import io
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        img_np = np.array(img)
        if len(img_np.shape) == 3 and img_np.shape[2] == 4:
            img_np = img_np[:, :, :3]

        reader = self._get_reader()
        results = reader.readtext(img_np, paragraph=True)
        sorted_results = sorted(results, key=lambda item: item[0][0][1])
        return "\n\n".join([text.strip() for _, text in sorted_results if text.strip()])
