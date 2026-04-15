@echo off
chcp 65001 >nul
title Brother Label Agent - Instalar Servicio

echo ============================================================
echo   Instalacion como Servicio de Windows
echo   (Requiere ejecutar como Administrador)
echo ============================================================
echo.

:: Verificar admin
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Ejecute este script como Administrador.
    echo   Clic derecho en install-service.bat -^> Ejecutar como administrador
    pause
    exit /b 1
)

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo [1/3] Instalando servicio...
python service.py install

echo [2/3] Configurando inicio automatico...
sc config BrotherLabelAgent start= auto >nul 2>&1

echo [3/3] Configurando reinicio automatico tras fallos...
sc failure BrotherLabelAgent reset= 60 actions= restart/5000/restart/10000/restart/30000 >nul 2>&1

echo.
echo ============================================================
echo   Servicio instalado correctamente.
echo.
echo   Para iniciarlo ahora:
echo     python service.py start
echo   O reinicie Windows.
echo.
echo   El servicio se reiniciara automaticamente si falla.
echo ============================================================
echo.
pause
