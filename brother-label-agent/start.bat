@echo off
chcp 65001 >nul
title Brother Label Agent v1.0.0

echo ============================================================
echo   Brother Label Agent v1.0.0
echo   Formato: DK-11204 (17mm x 54mm)
echo   Puerto:  http://127.0.0.1:5555
echo ============================================================
echo.
echo   Endpoints disponibles:
echo     GET  /health      - Estado del agente
echo     GET  /printers    - Listar impresoras
echo     POST /print       - Imprimir etiqueta
echo     POST /test-print  - Imprimir etiqueta de prueba
echo.
echo   Pulse Ctrl+C para detener el agente.
echo ============================================================
echo.

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python agent.py

if errorlevel 1 (
    echo.
    echo [ERROR] El agente se detuvo con errores.
    echo Revise agent.log para mas informacion.
    pause
)
