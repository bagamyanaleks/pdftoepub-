@echo off
setlocal
cd /d "%~dp0"

title PDF to EPUB Studio - Gereksinim Kurulumu

echo ============================================================
echo   PDF to EPUB and AZW3 Studio - Tam Kurulum Sihirbazi
echo ============================================================
echo.
echo [1/2] Python paketleri yukleniyor (requirements.txt)...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [!] Python paketleri yuklenirken hata olustu!
    pause
    exit /b %errorlevel%
)
echo.
echo [2/2] Tesseract 5 ve Turkce dil modelleri kuruluyor...
python scripts\setup_tesseract.py
echo.
echo ============================================================
echo   [OK] Tum kurulumlar tamamlandi!
echo   Web Studio'yu baslatmak icin start_studio.bat calistirabilirsiniz.
echo ============================================================
echo.
pause
