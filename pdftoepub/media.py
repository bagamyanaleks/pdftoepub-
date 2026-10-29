"""
Media and Cover Image Extractor for PDF to EPUB/AZW3 conversion.
Extracts, optimizes, and prepares book cover and internal illustrations.
"""

import os
import io
from typing import Optional, List, Dict, Tuple
from PIL import Image


class MediaManager:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.images_dir = os.path.join(output_dir, "images")
        os.makedirs(self.images_dir, exist_ok=True)
        self.cover_path: Optional[str] = None
        self.extracted_images: List[str] = []

    def save_optimized_image(self, image_bytes: bytes, filename: str, max_dimension: int = 1600, quality: int = 85) -> Optional[str]:
        """Saves and optimizes an image for e-readers (JPEG or PNG, resized if too huge)."""
        try:
            img = Image.open(io.BytesIO(image_bytes))
            
            # Skip tiny icons / lines / artifacts (< 25px in both dimensions)
            if img.width < 25 and img.height < 25:
                return None

            # Convert RGBA to RGB for JPEG if no transparent channel needed
            target_ext = os.path.splitext(filename)[1].lower()
            if target_ext in [".jpg", ".jpeg"] and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Resize if exceeding max dimensions while maintaining aspect ratio
            if img.width > max_dimension or img.height > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

            dest_path = os.path.join(self.images_dir, filename)
            
            if target_ext in [".jpg", ".jpeg"]:
                img.save(dest_path, "JPEG", quality=quality, optimize=True)
            else:
                img.save(dest_path, "PNG", optimize=True)

            self.extracted_images.append(dest_path)
            return dest_path
        except Exception as e:
            print(f"[MediaManager] Error saving image {filename}: {e}")
            return None

    def render_page_as_cover(self, page, dpi: int = 200) -> Optional[str]:
        """Renders the first page of the PDF as a high-quality JPEG cover image."""
        try:
            import fitz
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = pix.tobytes("jpeg")
            dest = self.save_optimized_image(img_bytes, "cover.jpg", quality=90)
            self.cover_path = dest
            return dest
        except Exception as e:
            print(f"[MediaManager] Error rendering cover: {e}")
            return None
