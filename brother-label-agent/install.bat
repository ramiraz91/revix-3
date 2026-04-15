@echo off
chcp 65001 >nul
title Brother Label Agent - Instalador

echo ============================================================
echo   Brother Label Agent - Instalador
echo   Formato: DK-11204 (17mm x 54mm)
echo   Impresora: Brother QL-800
echo ============================================================
echo.

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado.
    echo Descargue Python 3.10+ desde https://www.python.org/downloads/
    echo Marque "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

echo [1/3] Creando entorno virtual...
if not exist "venv" (
    python -m venv venv
)

echo [2/3] Activando entorno e instalando dependencias...
call venv\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install flask flask-cors Pillow python-barcode requests pywin32

echo [3/3] Verificando instalacion...
python -c "import flask; import PIL; import barcode; import requests; import win32print; print('Todas las dependencias OK')"
if errorlevel 1 (
    echo [AVISO] Alguna dependencia fallo. Revise los errores anteriores.
) else (
    echo.
    echo ============================================================
    echo   Instalacion completada correctamente.
    echo.
    echo   Para iniciar el agente ejecute: start.bat
    echo   El agente escuchara en http://127.0.0.1:5555
    echo ============================================================
)

echo.
pause
