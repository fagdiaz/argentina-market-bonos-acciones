@echo off
setlocal enabledelayedexpansion

chcp 65001 >nul
cd /d "%~dp0"

set LOGDIR=%cd%\logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

set VENV_PY=%cd%\.venv\Scripts\python.exe
set VENV_PIP=%VENV_PY% -m pip

REM Log header
echo ================================================== >> "%LOGDIR%\startup.log"
echo [%DATE% %TIME%] START run_startup.bat en %cd% >> "%LOGDIR%\startup.log"

REM Validar venv (sin pause: esto corre en Task Scheduler)
if not exist "%VENV_PY%" (
  echo [%DATE% %TIME%] ERROR: No existe el venv en %cd%\.venv >> "%LOGDIR%\startup.log"
  echo [%DATE% %TIME%] Crear con: py -m venv .venv >> "%LOGDIR%\startup.log"
  exit /b 1
)

REM (Opcional) instalar deps SOLO si falta algo clave
"%VENV_PY%" -c "import gspread" >nul 2>&1
if errorlevel 1 (
  echo [%DATE% %TIME%] Dependencias faltantes. Instalando requirements.txt... >> "%LOGDIR%\startup.log"
  "%VENV_PIP%" install -r requirements.txt --disable-pip-version-check >> "%LOGDIR%\startup.log" 2>&1
  if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: pip install fallo. >> "%LOGDIR%\startup.log"
    exit /b 1
  )
) else (
  echo [%DATE% %TIME%] Dependencias OK. >> "%LOGDIR%\startup.log"
)

REM Ejecutar scheduler (deja logs dentro del mismo archivo)
echo [%DATE% %TIME%] Ejecutando run_mercado.py... >> "%LOGDIR%\startup.log"
"%VENV_PY%" run_mercado.py >> "%LOGDIR%\startup.log" 2>&1

REM Si termina (no deberia, salvo error), lo registramos
echo [%DATE% %TIME%] FIN run_mercado.py (salio del loop o fallo). >> "%LOGDIR%\startup.log"
exit /b 0
