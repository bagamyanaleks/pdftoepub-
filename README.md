# PDF to EPUB & AZW3 Studio

GPU hızlandırmalı yerel Türkçe OCR ve Kindle / E-Kitap dönüştürücü stüdyosu.

Taranmış veya dijital PDF belgelerini Türkçe dil yapısına ve tipografisine uygun olarak kayıpsız bir şekilde **EPUB** ve **AZW3** (Kindle) formatlarına dönüştürür.

---

## 🚀 Özellikler

* **Akıllı PDF Analizi:** Belgenin sayfalarını tek tek analiz ederek dijital metin katmanı olan sayfaları anında kayıpsız aktarır; taranmış veya font bozulması olan sayfaları tespit ederek yalnızca gerektiğinde OCR çalıştırır.
* **GPU Hızlandırmalı Türkçe OCR:** NVIDIA GPU (CUDA) ve EasyOCR derin öğrenme modelleri (CRAFT) ile yüksek çözünürlükte (300 DPI) yerel ve çevrimdışı Türkçe metin tanıma.
* **Gelişmiş Türkçe Dilbilimsel Temizlik (`cleaner.py`):**
  * OCR kaynaklı tırnak ve noktalama yanılgılarını (`2)`, `9)`, `?)`, `((`, `c` vb.) otomatik temizleme.
  * Satır sonu hece bölmelerini (de-hyphenation) Türkçe kurallarına uygun birleştirme.
  * İnce font ve kerning kaynaklı harf ayrışmalarını ve Türkçe ekleri onarma.
  * Başlık, altbilgi (header/footer) ve sayfa numaralarını gövde metninden ayıklama.
* **Kindle (AZW3) Entegrasyonu:** Calibre motoru ile Kindle cihazlar için tam uyumlu AZW3 formatı üretimi.
* **Modern Web Stüdyosu:** FastAPI ve yerel HTML5/CSS arayüzü ile tarayıcı üzerinden sürükle-bırak kullanım, gerçek zamanlı GPU/CPU donanım durumu ve dönüştürme ilerleme takibi.

---

## 🛠️ Kurulum

1. Depoyu klonlayın:
   ```bash
   git clone https://github.com/bagamyanaleks/pdftoepub.git
   cd pdftoepub
   ```

2. Sanal ortamı oluşturun ve aktif edin:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   ```

3. Bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
   *(GPU desteği için sisteminizdeki CUDA sürümüne uygun PyTorch paketinin kurulu olduğundan emin olun).*

4. *(İsteğe Bağlı)* AZW3 (Kindle) çıktısı için [Calibre](https://calibre-ebook.com/download) kurulumunu yapın.

---

## 🖥️ Kullanım

### Web Arayüzü (Önerilen)
Web stüdyosunu başlatmak için:
```bash
python web_ui.py
```
Tarayıcınız otomatik olarak `http://127.0.0.1:8000` adresinde açılacaktır.

### Komut Satırı (CLI)
Doğrudan terminal üzerinden dönüştürmek için:
```bash
python convert.py "ornek_kitap.pdf" --ocr-mode auto
```

---

## 📂 Proje Yapısı

```text
pdftoepub/
├── pdftoepub/
│   ├── analyzer.py          # PDF sayfa analizi ve OCR karar motoru
│   ├── ocr.py               # GPU destekli EasyOCR motoru
│   ├── cleaner.py           # Türkçe dilbilimsel temizleme ve OCR hata giderici
│   ├── structure.py         # Bölüm ve içindekiler (TOC) tespit motoru
│   ├── builder_epub.py      # EPUB3 standartlarına uygun e-kitap derleyici
│   ├── converter_azw.py     # Calibre AZW3 dönüştürücü
│   ├── pipeline.py          # Uçtan uca dönüştürme orkestrasyonu
│   ├── web.py               # FastAPI backend ve SSE durum yayını
│   └── static/              # Web Studio frontend (HTML/CSS/JS)
├── tests/                   # Birim testleri
├── convert.py               # CLI başlatıcı
├── web_ui.py                # Web UI başlatıcı
└── requirements.txt         # Python bağımlılıkları
```

---

## 📄 Lisans
MIT License.
