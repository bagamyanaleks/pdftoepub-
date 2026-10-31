@echo off
chcp 65001 > nul
title PDF to EPUB Studio - Gereksinim Kurulumu
echo ============================================================
echo   PDF to EPUB & AZW3 Studio - Tam Kurulum Sihirbazı
echo ============================================================
echo.
echo [1/2] Python paketleri yükleniyor (requirements.txt)...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [!] Python paketleri yüklenirken hata oluştu!
    pause
    exit /b %errorlevel%
)
echo.
echo [2/2] Tesseract 5 ve Türkçe dil modelleri kuruluyor...
python scripts\setup_tesseract.py
echo.
echo ============================================================
echo   [OK] Tüm kurulumlar tamamlandı!
echo   Web Studio'yu başlatmak için start_studio.bat dosyasını çalıştırabilirsiniz.
echo ============================================================
echo.
pause
