@echo off
setlocal
cd /d "%~dp0"

title PDF to EPUB and AZW3 Studio

echo ============================================================
echo   PDF to EPUB and AZW3 Studio Baslatiliyor...
echo ============================================================
echo.

set "PY_CMD="
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0.venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_CMD=python"
    )
)

if "%PY_CMD%"=="" (
    echo [HATA] Python veya .venv ortami bulunamadi!
    echo Lutfen Python 3.10 veya 3.11 kurun veya 'install_dependencies.bat' dosyasini calistirin.
    echo.
    pause
    exit /b 1
)

"%PY_CMD%" -c "import uvicorn, fastapi, fitz" >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Bazi Python kutuphaneleri eksik gorunuyor.
    echo [+] Gerekli paketler yukleniyor...
    echo.
    "%PY_CMD%" -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo [HATA] Kutuphaneler yuklenemedi.
        echo Lutfen 'install_dependencies.bat' dosyasini calistirin.
        echo.
        pause
        exit /b 1
    )
)

echo [+] Web Studio baslatiliyor...
"%PY_CMD%" web_ui.py
if %errorlevel% neq 0 (
    echo.
    echo [!] Web Studio durduruldu veya bir hata olustu.
    pause
)
