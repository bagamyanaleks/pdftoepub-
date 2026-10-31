# Multi-purpose Dockerfile for PDF to EPUB & AZW3 Studio
# Supports NVIDIA GPU (CUDA) acceleration and CPU fallback
FROM python:3.11-slim

# Prevent interactive debian prompts and python buffering
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    NO_BROWSER=true

# Install system dependencies:
# - calibre: for ebook-convert CLI tool (AZW3 conversion)
# - tesseract-ocr & language data: for high-accuracy local Turkish and English OCR
# - libgl1, libglib2.0-0, libgomp1: required by OpenCV, EasyOCR, and PyMuPDF
# - curl: for container healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    calibre \
    tesseract-ocr \
    tesseract-ocr-tur \
    tesseract-ocr-eng \
    tesseract-ocr-osd \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install PyTorch
# Default: PyTorch with CUDA 12.1 for NVIDIA GPU acceleration
# For CPU-only builds: pass --build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url ${TORCH_INDEX_URL}

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose FastAPI Web UI port
EXPOSE 8000

# Declare persistent volumes for output ebooks, EasyOCR, and Hugging Face (Qwen AI) cache
VOLUME ["/app/converted_ebooks", "/root/.EasyOCR", "/root/.cache/huggingface"]

# Healthcheck to verify the web service is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8000/api/system-status || exit 1

# Start Web UI
CMD ["python", "web_ui.py", "--host", "0.0.0.0", "--port", "8000", "--no-browser"]

