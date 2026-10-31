@echo off
chcp 65001 > nul
title PDF to EPUB & AZW3 Studio
echo ============================================================
echo   PDF to EPUB & AZW3 Studio Başlatılıyor...
echo ============================================================
echo.
python web_ui.py
if %errorlevel% neq 0 (
    echo.
    echo [!] Web Studio durduruldu veya bir hata oluştu.
    pause
)
