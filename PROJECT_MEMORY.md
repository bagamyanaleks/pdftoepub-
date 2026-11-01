# 🧠 PROJE HAFIZA VE DEVAMLILIK DOSYASI (PROJECT MEMORY)
**Proje Adı:** PDF to EPUB & AZW3 Studio (Yerel Türkçe E-Kitap Dönüştürücü)  
**Telif & Geliştirici:** Aleks Bayamyan  
**Git Deposu:** `https://github.com/bagamyanaleks/pdftoepub-.git`  
**Ana Dal (Branch):** `main`  
**Son Güncelleme Tarihi:** 1 Kasım 2026  

---

## 📌 1. PROJENİN AMACI VE GENEL MİMARİSİ
Bu proje; taranmış, vektörel veya fiziksel kusurları (yırtık, katlanma, sensör gürültüsü) olan Türkçe PDF kitapları, edebi dil kurallarını ve tipografik düzeni koruyarak modern e-okuyucular (Kindle Paperwhite, Kobo, Apple Books) için **EPUB** ve **AZW3** formatlarına dönüştüren yerel bir stüdyodur.

### Temel Prensipler:
1. **%100 Yerel ve Gizli:** Hiçbir veri dışarıya veya buluta gitmez. Tüm işlemler (OCR ve Qwen AI dahil) bilgisayarda (GPU veya CPU) yerel çalışır.
2. **Kayıpsız Türkçe Tipografisi:** Türkçe karakterler (`ç, ğ, ı, ö, ş, ü, İ`), tırnak işaretleri, tire birleştirmeleri ve diyalog çizgileri edebi akışa uygun olarak temizlenir.
3. **Hibrit & Yedekli Altyapı:** Tesseract 5 LSTM + EasyOCR (CUDA GPU) hibrit çalışır; hasarlı paragraflar için Qwen 2.5 yapay zekası devreye girer.

---

## 🏗️ 2. MODÜLLER VE DOSYA YAPISI

| Dosya | Görevi ve Sorumluluğu |
| :--- | :--- |
| **`pdftoepub/analyzer.py`** | PDF'i sayfa sayfa analiz eder. Sayfanın vektörel mi yoksa taranmış/resim mi olduğunu anlar. Sayfadaki gömülü bozuk OCR katmanlarını tespit eder, kısa Türkçe kelimelerin yanlış yapışmasını engeller. |
| **`pdftoepub/ocr.py`** | Çift motorlu OCR yönetim modülü. **Tesseract 5 LSTM** (300 DPI, `tur+eng`) ve **EasyOCR** (PyTorch CUDA GPU hızlandırma) motorlarını otomatik algılar ve yönetir. |
| **`pdftoepub/cleaner.py`** | Kapsamlı Türkçe dil temizliği. Satır sonu tire birleştirmeleri, OCR gürültü sembolleri, hatalı boşluklar, tırnak işaretleri (`« »`, `“ ”`) ve noktalama düzeltmeleri yapar. |
| **`pdftoepub/ai_repair.py`** | **Qwen 2.5 In-Painting Motoru.** Ağır hasarlı, kenarları yırtık veya harfleri kopuk paragrafları edebi bağlamdan koparmadan lokal LLM ile onarır. Anomali puanlama algoritması içerir. |
| **`pdftoepub/structure.py`** | Başlıkları, alt başlıkları, bölüm sınırlarını ve içindekiler (TOC) yapısını otomatik tespit eden hiyerarşik yapı çıkarıcı. |
| **`pdftoepub/media.py`** | PDF içindeki kapak görselini ve bölüm içi illüstrasyonları orijinal kalitede çıkarıp optimize eden modül. |
| **`pdftoepub/builder_epub.py`** | EbookLib kullanarak modern, Kindle uyumlu CSS stilleriyle temiz EPUB3 dosyası oluşturan modül. |
| **`pdftoepub/converter_azw.py`** | Calibre `ebook-convert` aracını kullanarak Kindle USB kablo yüklemeleri için kayıpsız AZW3 üreten modül. |
| **`pdftoepub/pipeline.py`** | Tüm bu alt sistemleri birleştiren ana dönüştürme orkestratörü (`ConversionPipeline`). |
| **`pdftoepub/web.py`** | FastAPI arka ucu. Dosya yükleme, klasördeki PDF'leri listeleme, gerçek zamanlı durum takibi ve dosya indirme API'leri. |
| **`pdftoepub/static/`** | Web arayüzü dosyaları (`index.html`, `style.css`, `app.js`). Sürükle-bırak destekli koyu tema modern arayüz. |
| **`web_ui.py`** | Web Studio'yu başlatan ana başlatıcı (Uvicorn + tarayıcıyı otomatik açma). |
| **`convert.py`** | Terminalden komut satırıyla dönüştürme ve toplu (`--batch`) işlem CLI aracı. |
| **`Dockerfile` & `docker-compose.yml`** | Kuruluma gerek kalmadan Tesseract 5, Calibre, PyTorch CUDA ve Qwen modellerini izole çalıştıran Docker altyapısı. |

---

## ⚡ 3. EN SON YAPILAN KRİTİK GÜNCELLEMELER

### A. Varsayılan Ayarlar (Default Profile):
Kullanıcının her açılışta ayar seçmek zorunda kalmaması için **En Yüksek Kalite** profili varsayılan yapıldı:
1. **OCR Motoru:** `tesseract` (Tesseract 5 LSTM) varsayılan seçildi.
2. **Tarama Kapsamı:** `force` ("Tüm Sayfaları OCR'dan Geçir - En Yüksek Kalite") varsayılan seçildi. Tüm sayfalar 300 DPI'da Tesseract motorundan geçirilir.
3. **Qwen AI Onarımı:** `checked` (Aktif) ve model olarak `Qwen 2.5 (1.5B)` varsayılan seçildi.
4. Bu ayarlar `index.html`, `web.py`, `pipeline.py` ve `convert.py` genelinde senkronize edildi.

### B. Qwen 2.5 Edebi Metin Onarımı (Selective In-Painting):
* `pdftoepub/ai_repair.py` modülü geliştirildi.
* Yalnızca anomali skoru yüksek (`score >= 0.20`) olan hasarlı paragraflar için lazy-loading ile HuggingFace'ten `Qwen/Qwen2.5-1.5B-Instruct` modelini belleğe yükler; sağlam paragrafları doğrudan korur.
* Ollama / OpenAI uyumlu API veya yerel PyTorch/transformers üzerinden çalışır.

### C. Docker ve Kalıcı Önbellek (Caching):
* `Dockerfile` Debian 12 slim üzerinde `calibre`, `tesseract-ocr`, `tesseract-ocr-tur` paketlerini içerir.
* `docker-compose.yml` üzerinde `easyocr_cache` ve `hf_cache` adında kalıcı volume'lar oluşturuldu. Bu sayede Qwen veya EasyOCR modelleri konteyner silinse bile ana bilgisayarda saklanır, tekrar indirilmez.

### D. Linter ve Tip Güvenliği:
* Pyrefly ve Pylance linter uyarıları (`torch` için `# type: ignore`, `file.filename` null kontrolü, kullanılmayan import temizlikleri) yapıldı. IDE dosya ağacındaki hata bayrakları (kırmızı "1") tamamen sıfırlandı.

---

## 🚀 4. BAŞKA BİR BİLGİSAYARDA (İŞ YERİNDE) ÇALIŞMA REHBERİ

İş yerindeki bilgisayardan projeye devam etmek istediğinizde adımlar:

### Adım 1: Projeyi Klonlayın veya Çekin
```bash
git clone https://github.com/bagamyanaleks/pdftoepub-.git
cd pdftoepub-
git pull origin main
```

### Adım 2: Çalıştırma Yöntemi Seçin

#### Seçenek A — Docker ile (Önerilen - Sıfır Kurulum):
İş yeri bilgisayarında Docker varsa başka hiçbir şey kurmanıza gerek yoktur:
```bash
# NVIDIA GPU varsa:
docker compose up -d

# GPU yoksa (Normal ofis bilgisayarı / CPU):
docker compose --profile cpu up pdftoepub-cpu -d
```
Tarayıcıdan `http://localhost:8000` adresine girmeniz yeterlidir.

#### Seçenek B — Doğrudan Python ile (Manuel):
1. Sanal ortam oluşturup aktif edin:
   ```bash
   python -m venv .venv
   # Windows için:
   .venv\Scripts\activate
   ```
2. Bağımlılıkları kurun:
   ```bash
   pip install -r requirements.txt
   # PyTorch için (GPU varsa cu121, yoksa normal CPU):
   pip install torch torchvision
   ```
3. Web Stüdyoyu başlatın:
   ```bash
   python web_ui.py
   # veya
   start_studio.bat
   ```

---

## 📝 5. YOL HARİTASI VE PLANLANAN SONRAKİ ADIMLAR (ROADMAP)
Gelecek oturumlarda üzerine eklenebilecek fikirler:
1. **Web UI Toplu İşlem:** Web arayüzünde birden fazla PDF'i aynı anda sıraya ekleyip dönüştürme listesi oluşturma.
2. **Sayfa Aralığı Seçici:** Büyük kitaplarda sadece belirli sayfaları dönüştürebilmek için Web UI'a "Sayfa Aralığı (Örn: 10-50)" alanı ekleme.
3. **Ollama Entegrasyonu Seçeneği:** Web UI ayarlarında Hugging Face doğrudan model indirme yerine, ofis ağında çalışan yerel bir `http://localhost:11434` Ollama adresini tek tıkla seçebilme.

---
*Bu dosya, projede nerede kalındığını ve sistemin nasıl işlediğini yeni bir çalışma oturumuna anında aktarmak için tasarlanmıştır.*
