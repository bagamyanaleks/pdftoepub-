# PDF to EPUB & AZW3 Studio

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue?logo=python" alt="Python Version" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker Ready" />
  <img src="https://img.shields.io/badge/CUDA-GPU%20Accelerated-green?logo=nvidia" alt="NVIDIA CUDA" />
  <img src="https://img.shields.io/badge/OCR-Tesseract%205%20%2B%20EasyOCR-blue" alt="Tesseract 5 & EasyOCR" />
  <img src="https://img.shields.io/badge/Kindle-AZW3%20%26%20EPUB3-purple?logo=amazon" alt="Kindle & EPUB" />
  <img src="https://img.shields.io/badge/UI-FastAPI%20%2B%20Modern%20Studio-red?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/License-MIT-brightgreen" alt="MIT License" />
</p>

An intelligent, GPU-accelerated local studio designed to convert scanned and digital PDF books into immaculate, typography-preserving **EPUB3** and Kindle-ready **AZW3** files. Built with custom Turkish linguistic post-processing, font kerning recovery, and OCR artifact repair.

---

### Language / Dil Seçimi
- [🇬🇧 English Documentation](#english)
- [🇹🇷 Türkçe Dokümantasyon](#türkçe)

---

<a name="english"></a>
# 🇬🇧 English Documentation

## Overview
Converting PDF books into clean E-books (EPUB / Kindle AZW3) is notoriously difficult. Standard tools fail when dealing with:
1. **Scanned PDFs or Image-Only Pages:** Missing selectable text layers.
2. **Broken Font Encodings:** Publisher PDFs where Turkish diacritics (`ı`, `İ`, `ş`, `ğ`, `ç`, `ö`, `ü`) are corrupt or mapped to wrong glyphs.
3. **Severe OCR Artifacts:** Misrecognized quotation marks (e.g., closing quotes `”` misread as `2)`, `9)`, or `?)`), split dialogues, and joined paragraphs.
4. **Hyphenation & Split Words:** Words split across line breaks (e.g. `öğren-\n ciler` or `k ader`).
5. **Running Headers & Footers:** Page numbers and book titles leaking into paragraph text.

**PDF to EPUB & AZW3 Studio** resolves all of these issues locally and automatically using a hybrid extraction architecture, dual-engine OCR (Tesseract 5 + EasyOCR), and a specialized Turkish linguistic cleaner.

---

## Key Features

* **Intelligent Hybrid PDF Analysis (`analyzer.py`):** Inspects every page before processing. Clean digital pages are extracted instantaneously; only scanned or corrupted pages are routed to the OCR engine.
* **Dual-Engine Local OCR (`ocr.py`):**
  * **Tesseract 5 (LSTM):** High-precision text recognition with official `tessdata_best` Turkish language model. Unmatched accuracy for scanned Turkish literary prose.
  * **EasyOCR (PyTorch CUDA):** GPU-accelerated CRAFT text detector and recognizer for deep neural fallback.
  * **Smart Auto-Selection:** Automatically leverages Tesseract 5 when available or falls back to GPU EasyOCR.
* **Advanced Turkish Linguistic Post-Processor (`cleaner.py`):**
  * Automatically fixes dialogue punctuation and quotes (`"Seni arıyorduk; 2) dedi"` ➔ `"Seni arıyorduk," dedi`).
  * Seamless de-hyphenation across line wraps with compound word preservation (`Türk-İslam`).
  * Heals unintended whitespace splits caused by tracked fonts (e.g., `bu landırır` ➔ `bulandırır`, `se kiz` ➔ `sekiz`).
  * Strips recurring headers, footers, and decorative noise lines without losing genuine narrative text.
* **Kindle AZW3 Integration (`converter_azw.py`):** Direct pipeline to Calibre's `ebook-convert` engine for native Kindle formatting.
* **Modern Web Studio (`web_ui.py`):** Responsive dark-mode dashboard with drag-and-drop file upload, real-time progress bars, and hardware telemetry (GPU/CPU mode indicator).
* **CLI Interface (`convert.py`):** Batch process or automate conversions from your terminal.

---

## Architecture & Pipeline

```text
       [ Input PDF File ]
               │
               ▼
     ┌───────────────────┐
     │   PDF Analyzer    │ ───► Digital Text Page? ───► Geometric Text Extractor
     └───────────────────┘                                       │
               │                                                 │
          Scanned / Corrupted?                                   │
               │                                                 │
               ▼                                                 │
     ┌───────────────────┐                                       │
     │ GPU-EasyOCR Engine│ (300 DPI + CUDA)                      │
     └───────────────────┘                                       │
               │                                                 │
               ▼                                                 │
     ┌─────────────────────────────────────────────────────────┐ │
     │       Turkish Linguistic Cleaning Engine                │◄┘
     │  (De-hyphenation, Dialogue Fixes, Diacritics, Kerning)  │
     └─────────────────────────────────────────────────────────┘
               │
               ▼
     ┌───────────────────┐
     │ Structure & TOC   │ ───► EPUB3 Builder ───► [ Clean EPUB ]
     └───────────────────┘                           │
                                                     ▼
                                            Calibre (ebook-convert)
                                                     │
                                                     ▼
                                              [ Kindle AZW3 ]
```

---

## Hardware & System Requirements

| Component | Minimum | Recommended |
| :--- | :--- | :--- |
| **Operating System** | Windows 10/11, Ubuntu 20.04+, macOS 12+ | Windows 11 / Linux |
| **Python** | 3.10, 3.11, or 3.12 | 3.11 |
| **Processor (CPU)** | 4-Core CPU | 8-Core modern CPU (Intel i5/i7/i9 or Ryzen 5/7/9) |
| **Graphics (GPU)** | Not required (falls back to CPU) | **NVIDIA GPU with 4GB+ VRAM** (RTX 3050, 3060, 4060+) with CUDA |
| **RAM** | 8 GB RAM | 16 GB RAM |
| **Calibre** | Optional (for EPUB only) | **Installed** (required for AZW3 conversion) |

> [!NOTE]
> **GPU vs CPU Performance:** A 400-page scanned novel takes ~25-35 minutes on an NVIDIA RTX 3050 Laptop GPU (approx. 4 seconds/page). On pure CPU, the same book can take 2 to 3.5 hours.

---

## 🐳 Quick Start with Docker (Recommended)

Docker provides a zero-setup experience: **you don't need to install Python, PyTorch, CUDA toolkits, or Calibre on your host machine.** Everything comes packaged and ready to run.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows / macOS) or Docker Engine + Docker Compose (Linux).
- *(For GPU acceleration)*: NVIDIA GPU + NVIDIA Container Toolkit (built into Docker Desktop on Windows with WSL2).

### 1. Start the Studio

* **With NVIDIA GPU Acceleration (Default):**
  ```bash
  docker compose up -d
  ```

* **CPU-Only Mode (For Macs, laptops, or cloud servers without NVIDIA GPU):**
  ```bash
  docker compose --profile cpu up pdftoepub-cpu -d
  ```

### 2. Open Web Studio
Navigate to: **`http://localhost:8000`** in your web browser.

* **Persistent Files:** Converted `.epub` and `.azw3` books are automatically saved to your local `./converted_ebooks` directory.
* **Cached Models:** EasyOCR model weights are stored in a persistent Docker volume (`pdftoepub_easyocr_cache`), so models are never re-downloaded.
* **Stop Studio:**
  ```bash
  docker compose down
  ```

### 🔄 Updating Docker (After Code Updates)
Whenever you pull new commits or make changes to the code:
```bash
git pull
docker compose up --build -d
```

---

## 💻 Manual Installation (Without Docker)

### 1. Clone the Repository
```bash
git clone https://github.com/bagamyanaleks/pdftoepub-.git
cd pdftoepub-
```

### 2. Create and Activate Virtual Environment
* **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
* **Linux / macOS:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Install Dependencies & Tesseract 5

#### 🚀 1-Click Setup on Windows:
Simply double-click `install_dependencies.bat` or run:
```bat
install_dependencies.bat
```
*(Automatically installs requirements and downloads Tesseract 5 + Turkish models).*

#### Manual Setup:
* **Option A: GPU Acceleration (Recommended for NVIDIA Users):**
  ```bash
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
  pip install -r requirements.txt
  python scripts/setup_tesseract.py
  ```
* **Option B: CPU Only:**
  ```bash
  pip install -r requirements.txt
  python scripts/setup_tesseract.py
  ```

### 4. Install Calibre (For Kindle AZW3 Support)
* **Windows:**
  ```powershell
  winget install calibre
  ```
  *(Or download from [calibre-ebook.com](https://calibre-ebook.com/download))*
* **Linux (Ubuntu/Debian):**
  ```bash
  sudo apt install calibre
  ```
* **macOS:**
  ```bash
  brew install --cask calibre
  ```

---

## Running the Application

### 1. Web Studio (Recommended)
Launch the interactive web UI:
```bash
python web_ui.py
# Or on Windows simply double-click: start_studio.bat
```
Open your browser at: **`http://127.0.0.1:8000`**

### 2. Command Line Interface (CLI)
```bash
# Automatic OCR strategy (Default - Tesseract 5 preferred):
python convert.py "path/to/book.pdf"

# Select OCR Engine explicitly (tesseract or easyocr):
python convert.py "path/to/book.pdf" --ocr-engine tesseract
python convert.py "path/to/book.pdf" --ocr-engine easyocr

# Force OCR for all pages:
python convert.py "path/to/book.pdf" --ocr force

# Extract digital text only (Disable OCR):
python convert.py "path/to/book.pdf" --ocr none

# Custom output directory:
python convert.py "path/to/book.pdf" --output "my_ebooks"
```

---

## OCR Strategies & Engines Explained

* **OCR Engines (`--ocr-engine`):**
  * **`auto` (Recommended):** Uses Tesseract 5 (LSTM) if available with Turkish models, or falls back to GPU EasyOCR.
  * **`tesseract`:** High-precision LSTM OCR with official `tessdata_best` Turkish dataset. Best typographical accuracy.
  * **`easyocr`:** Deep-learning neural text recognition (PyTorch CUDA accelerated).
* **Scan Modes (`--ocr`):**
  * **`auto` (Default):** Inspects each page. Clean digital text is extracted directly in milliseconds; scanned or corrupted pages are routed to OCR.
  * **`force`:** Forces 300 DPI OCR on every single page.
  * **`none`:** Disables OCR completely (takes 3-10 seconds for a full digital book).

---

<br />
<hr />
<br />

<a name="türkçe"></a>
# 🇹🇷 Türkçe Dokümantasyon

## Genel Bakış
PDF formatındaki kitapları e-okuyucular (Kindle, Kobo) veya telefonlar için düzgün bir **EPUB** ya da **AZW3** e-kitaba dönüştürmek her zaman büyük bir problem olmuştur:
1. **Taranmış Kitaplar:** PDF sadece sayfa fotoğraflarından oluştuğunda normal dönüştürücüler boş dosya üretir.
2. **Bozuk Türkçe Karakterler:** Yayınevi dizgilerinde özel font kullanıldığında Türkçe harfler (`ğ`, `ş`, `ı`, `İ`, `ç`, `ö`, `ü`) bozulur veya kare/soru işareti olur.
3. **OCR Hataları & Yanılgıları:** Standart OCR motorları kitaplardaki kapanış tırnaklarını (`”`) sıklıkla `2)`, `9)` veya `?)` şeklinde algılar; diyalogları bozar ve satır başlarını birleştirir.
4. **Bölünen Kelimeler:** Satır sonundaki tire işaretleri (`öğren-\n ciler`) e-kitapta kopuk kelimeler olarak kalır.
5. **Sayfa Numaraları ve Üstbilgiler:** Sayfa başındaki ve sonundaki sayfa numaraları ile kitap isimleri paragrafların içine karışır.

**PDF to EPUB & AZW3 Studio**, tamamen yerel olarak bilgisayarınızda çalışarak bu sorunları yapay zeka destekli Türkçe dilbilimsel temizleme algoritmalarıyla çözer.

---

## Öne Çıkan Özellikler

* **Akıllı Sayfa Analizi (`analyzer.py`):** Dönüştürme öncesi her sayfayı inceler. Temiz dijital sayfaları doğrudan aktarırken, sadece taranmış veya font hatası olan sayfaları OCR işlemine alır.
* **GPU Hızlandırmalı Türkçe OCR (`ocr.py`):** NVIDIA CUDA ve EasyOCR derin öğrenme modellerini (CRAFT) kullanarak sayfaları 300 DPI çözünürlükte yerel olarak tanır. İnternet bağlantısı gerektirmez, veriniz dışarı çıkmaz.
* **Gelişmiş Türkçe Dilbilimsel Temizlik (`cleaner.py`):**
  * Tırnak işaretlerinin `2)`, `9)`, `?)`, `((`, `c` gibi OCR yanılgılarını tespit edip kusursuz diyalog tırnaklarına dönüştürür.
  * Satır sonu hece bölmelerini (de-hyphenation) akıllıca birleştirir (`Türk-İslam` gibi bileşik kelimeleri korur).
  * Dar/aralıklı dizgi fontlarından kaynaklanan harf kopmalarını (`bu landırır` ➔ `bulandırır`, `se kiz` ➔ `sekiz`) onarır.
  * Sayfa numaraları, kitap başlıkları ve süsleme çizgilerini temizler.
* **Kindle (AZW3) Desteği (`converter_azw.py`):** Calibre motoru ile tam Amazon Kindle standartlarında AZW3 çıktısı sağlar.
* **Modern Web Stüdyosu (`web_ui.py`):** FastAPI tabanlı koyu temalı web arayüzü; donanım durumunu (GPU/CPU) otomatik algılar, canlı ilerleme çubuğu sunar.
* **Komut Satırı (CLI):** Terminal üzerinden toplu dönüştürme yapabilirsiniz.

---

## Donanım ve Sistem Gereksinimleri

| Bileşen | Minimum | Önerilen |
| :--- | :--- | :--- |
| **İşletim Sistemi** | Windows 10/11, Linux, macOS | Windows 11 / Linux |
| **Python** | 3.10+ | 3.11 |
| **İşlemci (CPU)** | 4 Çekirdekli CPU | 8 Çekirdekli modern işlemci |
| **Ekran Kartı (GPU)** | Gerekli değil (CPU'da çalışır) | **NVIDIA GPU (CUDA Destekli, min 4GB VRAM)** (RTX 3050/3060/4060 vb.) |
| **Bellek (RAM)** | 8 GB | 16 GB |
| **Calibre** | İsteğe bağlı (Sadece EPUB için gerekmez) | **Yüklü** (Kindle AZW3 formatı için gereklidir) |

> [!TIP]
> **GPU ve CPU Arasındaki Hız Farkı:** 400 sayfalık taranmış bir roman NVIDIA RTX 3050 Laptop GPU üzerinde yaklaşık **25–35 dakikada** (sayfa başı ~4 saniye) biterken, işlemci (CPU) üzerinde **2.5 ila 3.5 saat** sürebilir.

---

## 🐳 Docker ile Hızlı Başlangıç (Önerilen Yöntem)

Docker sayesinde bilgisayarınıza **Python sürümü, Calibre, PyTorch veya CUDA paketleri kurmanıza gerek kalmaz.** Tüm bağımlılıklar konteyner içinde hazır gelir.

### Ön Koşullar
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows / macOS) veya Docker Engine + Compose (Linux).
- *(GPU Hızlandırma İçin)*: NVIDIA Ekran Kartı (Windows Docker Desktop'ta WSL2 ile otomatik tanınır).

### 1. Stüdyoyu Başlatın

* **NVIDIA GPU Hızlandırması ile (Varsayılan - Önerilen):**
  ```bash
  docker compose up -d
  ```

* **Yalnızca CPU Modu (NVIDIA ekran kartı olmayan cihazlar için):**
  ```bash
  docker compose --profile cpu up pdftoepub-cpu -d
  ```

### 2. Web Arayüzünü Açın
Tarayıcınızdan şu adrese gidin:
👉 **`http://localhost:8000`**

* **Kalıcı Kitaplar:** Üretilen `.epub` ve `.azw3` dosyaları doğrudan bilgisayarınızdaki `./converted_ebooks` klasörüne kaydedilir.
* **Akıllı Model Önbelleği:** EasyOCR modelleri bir Docker volume'unda saklanır, her açılışta tekrar model indirilmez.
* **Durdurmak İçin:**
  ```bash
  docker compose down
  ```

### 🔄 Docker Güncelleme (Kod Değişikliklerinde)
Depodan yeni güncellemeler çektiğinizde veya kodda değişiklik yaptığınızda konteyneri güncellemek için:
```bash
git pull
docker compose up --build -d
```

---

## 💻 Manuel Kurulum Rehberi (Docker Olmadan)

### 1. Depoyu Klonlayın
```bash
git clone https://github.com/bagamyanaleks/pdftoepub-.git
cd pdftoepub-
```

### 2. Sanal Ortamı Oluşturun ve Aktif Edin
* **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
* **Linux / macOS:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Paketleri ve Tesseract 5'i Yükleyin

#### 🚀 Windows İçin Tek Tıkla Kurulum:
Klasördeki `install_dependencies.bat` dosyasına çift tıklayarak Python gereksinimlerini ve Tesseract 5 + Türkçe dil paketlerini tek seferde otomatik kurabilirsiniz.

#### Manuel Kurulum:
* **NVIDIA Ekran Kartı Olanlar (GPU Hızlandırma İçin):**
  ```bash
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
  pip install -r requirements.txt
  python scripts/setup_tesseract.py
  ```
* **Sadece İşlemci (CPU) Kullanacaklar İçin:**
  ```bash
  pip install -r requirements.txt
  python scripts/setup_tesseract.py
  ```

### 4. Calibre Kurulumu (Kindle AZW3 Formatı İçin)
* **Windows:**
  PowerShell üzerinden hızlıca kurabilirsiniz:
  ```powershell
  winget install calibre
  ```
  *(veya [calibre-ebook.com](https://calibre-ebook.com/download) adresinden indirin).*
* **Linux (Ubuntu/Debian):**
  ```bash
  sudo apt install calibre
  ```
* **macOS:**
  ```bash
  brew install --cask calibre
  ```

---

## Kullanım Rehberi

### 1. Web Stüdyosu (Önerilen)
Web stüdyosunu başlatmak için:
```bash
python web_ui.py
# Veya Windows'ta çift tıklayın: start_studio.bat
```
Tarayıcınız otomatik olarak açılacaktır (`http://127.0.0.1:8000`). PDF dosyanızı sürükleyip bırakarak dönüştürmeyi tek tıkla başlatabilirsiniz.

### 2. Komut Satırı (CLI)
```bash
# Akıllı otomatik mod (Varsayılan - Tesseract 5 öncelikli):
python convert.py "kitap.pdf"

# OCR motorunu belirterek çalıştırma:
python convert.py "kitap.pdf" --ocr-engine tesseract
python convert.py "kitap.pdf" --ocr-engine easyocr

# Tüm sayfalara zorunlu OCR uygulama:
python convert.py "kitap.pdf" --ocr force

# OCR çalıştırmadan sadece metni alma (Dijital PDF'ler için):
python convert.py "kitap.pdf" --ocr none

# Farklı çıktı klasörü belirtme:
python convert.py "kitap.pdf" --output "cikti_kitaplar"
```

---

## OCR Motorları ve Stratejileri

* **OCR Motorları (`--ocr-engine`):**
  * **`auto` (Önerilen):** Tesseract 5 kuruluysa yüksek Türkçe doğruluk için Tesseract 5'i, değilse GPU destekli EasyOCR'ı seçer.
  * **`tesseract`:** Tesseract 5 LSTM derin öğrenme motoru ve `tessdata_best` Türkçe veri seti ile roman/kitap metinlerinde sıfır harf hatası sunar.
  * **`easyocr`:** PyTorch CUDA ivmelendirmeli CRAFT derin sinir ağı.
* **Tarama Kapsamı (`--ocr`):**
  * **`auto` (Akıllı Mod):** Sayfada seçilebilir metin varsa metni saniyeler içinde doğrudan alır. Yalnızca resim olan veya fontu bozuk sayfalarda OCR çalıştırır.
  * **`force` (Zorunlu OCR):** Tüm sayfalara istisnasız 300 DPI OCR uygular. Eski, kötü taranmış kitaplar için idealdir.
  * **`none` (Yalnızca Dijital Metin):** OCR'ı tamamen kapatır. Kitap doğrudan dijital üretilmişse işlemi 5-10 saniyede bitirir.

---

## Proje Klasör Düzeni

```text
pdftoepub-/
├── pdftoepub/
│   ├── analyzer.py          # PDF analiz ve OCR tetikleme kararları
│   ├── ocr.py               # Çoklu OCR motoru (Tesseract 5 & EasyOCR CUDA)
│   ├── cleaner.py           # Türkçe dilbilimsel ve OCR temizleme kuralları
│   ├── structure.py         # Bölüm ve içindekiler (TOC) algılayıcı
│   ├── builder_epub.py      # EPUB3 standart e-kitap üretici
│   ├── converter_azw.py     # Calibre AZW3 dönüştürücü entegrasyonu
│   ├── media.py             # Kapak ve görsel çıkarma yöneticisi
│   ├── pipeline.py          # Uçtan uca dönüştürme orkestrasyonu
│   ├── web.py               # FastAPI backend ve durum yayını
│   └── static/              # Web Studio frontend (HTML/CSS/JS)
├── scripts/
│   └── setup_tesseract.py   # Çapraz platform Tesseract 5 kurulum sihirbazı
├── tests/                   # Kapsamlı birim testleri
├── install_dependencies.bat # Windows tek tıkla tam gereksinim kurulumu
├── install_tesseract.bat    # Windows tek tıkla Tesseract 5 kurulumu
├── start_studio.bat         # Windows tek tıkla Web Studio başlatıcı
├── convert.py               # CLI başlatıcı
├── web_ui.py                # Web Studio başlatıcı
├── Dockerfile               # Tesseract 5 ve Calibre içeren Docker yapılandırması
├── docker-compose.yml       # GPU ve CPU Docker servisleri
├── requirements.txt         # Gerekli Python kütüphaneleri
├── LICENSE                  # MIT Lisansı
└── README.md                # Proje dokümantasyonu (TR & EN)
```

---

## Lisans

Bu proje **MIT Lisansı** ile lisanslanmıştır. Açık kaynaklıdır; ticari veya kişisel amaçlarla özgürce kullanılabilir, geliştirilebilir ve dağıtılabilir.
