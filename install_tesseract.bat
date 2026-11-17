@echo off
setlocal
cd /d "%~dp0"

title PDF to EPUB Studio - Tesseract 5 Kurulumu

echo ============================================================
echo   PDF to EPUB Studio - Tesseract 5 ve Turkce Model Kurulumu
echo ============================================================
echo.
python scripts\setup_tesseract.py
echo.
pause
