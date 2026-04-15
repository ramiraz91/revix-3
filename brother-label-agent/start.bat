@echo off
chcp 65001 >nul
title Brother Label Agent v2.1.0 — Produccion

echo ============================================================
echo   Brother Label Agent v2.1.0 — Produccion
echo   Servidor: Waitress (produccion)
echo   Formato:  DK-11204 (17mm x 54mm)
echo ============================================================
echo.
echo   El agente se reiniciara automaticamente si falla.
echo   Pulse Ctrl+C para detener definitivamente.
echo ============================================================
echo.

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:loop
echo [%date% %time%] Iniciando agente...
python agent.py

echo.
echo [%date% %time%] El agente se detuvo. Reiniciando en 5 segundos...
echo   (Pulse Ctrl+C ahora para detener definitivamente)
timeout /t 5 /nobreak >nul
goto loop
