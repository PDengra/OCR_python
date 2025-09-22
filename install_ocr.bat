@echo off
title Instalador OCR como Servicio
echo ===== Instalador OCR Servicio =====

:: ----------------------------
:: 1. Comprobar Python
:: ----------------------------
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [⚠] Python no esta instalado. Descargalo e instalalo desde:
    echo     https://www.python.org/downloads/windows/
    pause
    exit /b
)

:: ----------------------------
:: 2. Añadir Python al PATH (temporal)
:: ----------------------------
set PYTHON_PATH=%LocalAppData%\Programs\Python\Python313
set SCRIPTS_PATH=%PYTHON_PATH%\Scripts
set PATH=%PATH%;%PYTHON_PATH%;%SCRIPTS_PATH%

:: ----------------------------
:: 3. Instalar librerías necesarias
:: ----------------------------
echo [✔] Instalando librerias de OCR...
python -m pip install --upgrade pip
python -m pip install opencv-python numpy easyocr watchdog pillow PyMuPDF pywin32

:: ----------------------------
:: 4. Crear carpetas OCR
:: ----------------------------
if not exist C:\OCR mkdir C:\OCR
if not exist C:\OCR\entrada mkdir C:\OCR\entrada
if not exist C:\OCR\salida mkdir C:\OCR\salida
if not exist C:\OCR\plantillas_adicionales mkdir C:\OCR\plantillas_adicionales

:: ----------------------------
:: 5. Copiar script OCR si no existe
:: ----------------------------
if not exist C:\OCR\ocr_service.py (
    copy "%~dp0ocr_service.py" "C:\OCR\ocr_service.py"
)

:: ----------------------------
:: 6. Instalar el servicio OCR
:: ----------------------------
echo [✔] Instalando servicio OCR...
python C:\OCR\ocr_service.py install

:: ----------------------------
:: 7. Iniciar el servicio OCR
:: ----------------------------
echo [✔] Iniciando servicio OCR...
python C:\OCR\ocr_service.py start

echo [✔] Servicio OCR instalado y en ejecucion.
pause

