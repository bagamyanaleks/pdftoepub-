# 🧠 PROJE HAFIZA VE DEVAMLILIK DOSYASI (PROJECT MEMORY)

**Proje Adı:** PDF to EPUB & AZW3 Studio (Yerel Türkçe E-Kitap Dönüştürücü)  
**Geliştirici:** Aleks Bayamyan  
**GitHub Deposu:** `https://github.com/bagamyanaleks/pdftoepub-.git`  
**Ana Dal (Branch):** `main`  
**Son Güncelleme:** 1 Kasım 2026  
**Son Commit:** `aae74c3` — feat(defaults): set Tesseract 5, force OCR, and Qwen AI as defaults; resolve linter warnings

---

## 📌 1. PROJENİN AMACI VE MİMARİSİ

Taranmış veya fiziksel kusurları (yırtık, katlanma, sensör gürültüsü) olan Türkçe PDF kitapları; edebi dil kurallarını, tipografik düzeni ve bölüm yapısını koruyarak Kindle/Kobo/Apple Books için **EPUB** ve **AZW3** formatlarına dönüştüren **%100 yerel (çevrimdışı)** stüdyo uygulamasıdır.

### Temel Prensipler
1. **%100 Yerel & Özel:** Hiçbir veri dışarıya veya buluta gitmez. OCR ve Qwen AI dahil her şey bilgisayarda çalışır.
2. **Kayıpsız Türkçe Tipografisi:** `ç, ğ, ı, ö, ş, ü, İ`, tırnak, diyalog çizgileri edebi akışa göre korunur.
3. **Hibrit & Yedekli Altyapı:** Tesseract 5 LSTM + EasyOCR (CUDA GPU) hibrit; hasarlı paragraflar için Qwen 2.5 AI devreye girer.

---

## 🏗️ 2. MODÜLLER VE DOSYA YAPISI

```
pdftoepub/
├── pdftoepub/
│   ├── analyzer.py        → Sayfanın taranmış/vektörel/bozuk olup olmadığını tespit eder
│   ├── ocr.py             → Tesseract 5 LSTM + EasyOCR GPU hibrit OCR motoru
│   ├── cleaner.py         → Kapsamlı Türkçe dil ve OCR gürültü temizleyici
│   ├── ai_repair.py       → Qwen 2.5 ile hasarlı paragraf onarımı (In-Painting)
│   ├── structure.py       → Bölüm/başlık/TOC yapısını otomatik çıkarır
│   ├── media.py           → Kapak ve illüstrasyon görsellerini çıkarır
│   ├── builder_epub.py    → EPUB3 üretici (ebooklib + Kindle uyumlu CSS)
│   ├── converter_azw.py   → Calibre ile AZW3 üretici
│   ├── pipeline.py        → Tüm modülleri yöneten ana orkestratör
│   ├── web.py             → FastAPI arka ucu (upload, durum, indirme API'leri)
│   └── static/
│       ├── index.html     → Sürükle-bırak destekli koyu tema Web UI
│       ├── style.css      → UI stilleri
│       └── app.js         → UI JavaScript mantığı
├── web_ui.py              → Uvicorn başlatıcı (tarayıcıyı otomatik açar)
├── convert.py             → CLI aracı (terminal / toplu batch işlem)
├── Dockerfile             → Docker imaj tanımı (Tesseract + Calibre + Python)
├── docker-compose.yml     → GPU ve CPU servis tanımları (kalıcı volume'larla)
├── requirements.txt       → Python bağımlılık listesi
├── install_tesseract.bat  → Windows için Tesseract 5 kurulum betiği
├── install_dependencies.bat → Python bağımlılıklarını kuran Windows betiği
├── start_studio.bat       → Web Studio'yu başlatan Windows kısayolu
└── PROJECT_MEMORY.md      → Bu dosya — proje hafızası
```

---

## ⚡ 3. TÜM YAPILAN KRİTİK GELİŞTİRMELER (Kronolojik)

### [Commit 4974709] — İlk Sürüm
- Temel PDF → EPUB dönüştürme pipeline'ı
- EasyOCR entegrasyonu
- Web UI ilk sürümü

### [Commit b62db77] — Docker Desteği
- `Dockerfile` ve `docker-compose.yml` oluşturuldu
- GPU (cu121) ve CPU profilleri ayrı servisler olarak tanımlandı

### [Commit 1cc48e5] — Tesseract 5 Entegrasyonu
- `pdftoepub/ocr.py`: Tesseract 5 LSTM motoru eklendi
- Türkçe `tur+eng` traineddata desteği
- Web UI'a "OCR Motoru" seçici (Tesseract / EasyOCR / Otomatik) eklendi
- `300 DPI` ile tüm sayfaları OCR yapma modu (`force`) eklendi

### [Commit a6baf77] — Qwen 2.5 AI Metin Onarımı
- `pdftoepub/ai_repair.py` sıfırdan yazıldı
- **Anomali Puanlama:** `score_paragraph_anomaly()` fonksiyonu ile OCR gürültüsü ölçülür
- **Lazy-Loading:** Yalnızca `score >= 0.20` hasarlı paragraflar için model yüklenir
- **Seçici Onarım:** Sağlam paragraflar dokunulmadan geçer, sadece bozuklar LLM'e gider
- **Desteklenen Backend'ler:** `transformers` (HuggingFace yerel), `openai_compatible`, `ollama`
- **Varsayılan Model:** `Qwen/Qwen2.5-1.5B-Instruct` (1.5B parametre, ~1.5-2 GB)
- Web UI'a "Qwen AI Onarımı" checkbox ve model seçici eklendi

### [Commit dde306a] — Docker & HuggingFace Cache Güncellemesi
- `docker-compose.yml`: `hf_cache` (HuggingFace Qwen modelleri) ve `easyocr_cache` kalıcı volume'ları eklendi
- Bu sayede konteyner yeniden başlatılsa bile modeller tekrar indirilmez

### [Commit 3a26cfc] — Analyzer Hata Düzeltmeleri
- Kısa Türkçe kelimelerin yanlış yapışması engellendi
- Bozuk gömülü OCR katmanları tespit edilip yok sayılıyor

### [Commit aae74c3] — Varsayılan Ayarlar + Linter Temizliği (SON COMMIT)

#### Varsayılan Profil "En Yüksek Kalite" olarak ayarlandı:
| Ayar | Eski Varsayılan | Yeni Varsayılan |
|:---|:---|:---|
| OCR Motoru | `auto` (Akıllı Otomatik) | `tesseract` (Tesseract 5 LSTM) |
| Tarama Kapsamı | `auto` (Sadece Gerektiğinde) | `force` (Tüm Sayfalara - En Yüksek Kalite) |
| Qwen AI Onarımı | `False` (Kapalı) | `True` (Aktif) |
| Qwen Modeli | `0.5B` | `1.5B` |

Bu değişiklikler 4 dosyada senkronize edildi:
- `pdftoepub/static/index.html` → HTML `selected` attributeleri güncellendi, checkbox `checked` yapıldı
- `pdftoepub/web.py` → API Form default'ları ve Pydantic model default'ları güncellendi
- `pdftoepub/pipeline.py` → `ConversionPipeline.__init__()` parametreleri güncellendi
- `convert.py` → CLI argparse default'ları güncellendi, `--no-ai-repair` flag'i eklendi

#### Linter / Pyrefly Hata Temizliği:
- `pdftoepub/web.py`: `import torch # type: ignore` eklendi (torch yüklü olmayan ortamlarda kırmızı bayrak kaldırıldı)
- `pdftoepub/web.py`: Kullanılmayan `glob`, `asyncio`, `JSONResponse` import'ları silindi
- `pdftoepub/web.py`: `file.filename` için `None` kontrolü eklendi (tip güvenliği)
- `pdftoepub/ocr.py`: `import torch # type: ignore` ve `import easyocr # type: ignore` eklendi
- `web_ui.py`: Kullanılmayan `import sys` silindi
- Pyrefly check sonucu: **0 error** (2 suppressed)

---

## 🐳 4. DOCKER NASIL ÇALIŞIR?

### Kullanıcı Bakış Açısından
```
Kullanıcı → docker compose up -d → Tarayıcıdan http://localhost:8000
```
Kullanıcının bilgisayarına **Tesseract, Calibre, Python, PyTorch kurulmaz.**

### İzole Konteyner İçi Kurulumlar (Dockerfile)
```dockerfile
apt-get install -y calibre tesseract-ocr tesseract-ocr-tur tesseract-ocr-eng
pip install torch torchvision  # CUDA 12.1 veya CPU
pip install -r requirements.txt  # Tüm Python bağımlılıkları
```

### Kalıcı Hafıza (Volume'lar)
```yaml
volumes:
  - hf_cache:/root/.cache/huggingface   # Qwen 2.5 modeli (~1.5 GB)
  - easyocr_cache:/root/.EasyOCR        # EasyOCR model ağırlıkları
  - ./converted_ebooks:/app/converted_ebooks  # Çıktı kitaplar
```

Qwen modeli **ilk kullanımda bir kez** HuggingFace'ten indirilir, sonraki çalıştırmalarda volume'dan kullanılır.

---

## 💻 5. YEREL (DOCKER'SIZ) KURULUM

### Windows'ta Gereksinimler
1. **Python 3.11+** — python.org'dan
2. **Tesseract 5** — `install_tesseract.bat` ile veya:
   - https://github.com/UB-Mannheim/tesseract/wiki → Windows installer
   - Kurulumda Türkçe dil paketi seçilmeli (`tur`)
3. **Calibre** (AZW3 için opsiyonel) — calibre-ebook.com
4. **PyTorch** (GPU varsa):
   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   ```

### Kurulum ve Başlatma
```bash
git clone https://github.com/bagamyanaleks/pdftoepub-.git
cd pdftoepub-
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python web_ui.py
# veya
start_studio.bat
```

---

## 🚀 6. İŞ YERİ BİLGİSAYARINDA DEVAM ETME REHBERİ

### Adım 1: Kodu çek
```bash
git clone https://github.com/bagamyanaleks/pdftoepub-.git
cd pdftoepub-
git pull origin main
```

### Adım 2: Çalıştırma seçeneği

#### Docker ile (Önerilen - Sıfır Kurulum):
```bash
# NVIDIA GPU varsa:
docker compose up -d

# GPU yoksa (ofis bilgisayarı):
docker compose --profile cpu up pdftoepub-cpu -d
```
→ `http://localhost:8000` — Hazır!

#### Python ile (Manuel):
```bash
.venv\Scripts\activate
python web_ui.py
```

### Adım 3: AI Ajanına Bağlam Ver
Bu `PROJECT_MEMORY.md` dosyasını AI asistanına vererek şunu söyle:
> "Bu proje hafıza dosyasını oku ve kaldığımız yerden devam et."

---

## 🤖 7. OCR & AI AKIŞI — Nasıl Çalışıyor?

```
PDF Sayfası
    ↓
[analyzer.py] → Sayfa Türü Tespiti
    ├── Vektörel metin var → doğrudan al
    └── Taranmış / bozuk → OCR'a gönder
         ↓
    [ocr.py] → Motor Seçimi
         ├── tesseract → Tesseract 5 LSTM (300 DPI, tur+eng)
         └── easyocr  → EasyOCR + PyTorch GPU
              ↓
    [cleaner.py] → Türkçe Dil Temizliği
         ├── Tire birleştirme, boşluk düzeltme
         ├── OCR gürültü sembolleri temizleme
         └── Tırnak, noktalama normalizasyonu
              ↓
    [ai_repair.py] → Anomali Tespiti (score_paragraph_anomaly)
         ├── score < 0.20 → Paragraf sağlam, dokunma
         └── score ≥ 0.20 → Qwen 2.5 ile onar
              ↓
    [structure.py] → Bölüm / Başlık Yapısı
              ↓
    [builder_epub.py] → EPUB3 Üretim
    [converter_azw.py] → AZW3 Üretim (Calibre)
```

---

## 📝 8. ROADMAP — Sonraki Oturumlarda Yapılacaklar

1. **Web UI Toplu İşlem:** Birden fazla PDF'i sıraya ekleyip sırayla dönüştürme
2. **Sayfa Aralığı Seçici:** Web UI'dan "Yalnızca 10-50. sayfalar" gibi seçim
3. **Ollama Entegrasyonu:** Hugging Face yerine yerel `http://localhost:11434` Ollama adresini tek tıkla seçme
4. **İlerleme Webhook:** Dönüştürme tamamlandığında bildirim (tarayıcı notification veya e-posta)
5. **Çoklu Dil Desteği:** Türkçe dışında Arapça, Farsça, Rusça gibi diller için OCR profili

---

*Bu dosya, AI asistanına projenin tüm bağlamını anında aktarmak ve farklı bilgisayarlarda kaldığınız yerden devam etmek için tasarlanmıştır.*
