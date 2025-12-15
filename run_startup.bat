@echo off
setlocal

REM Ruta base del repo (directorio donde está este .bat)
set "REPO_DIR=%~dp0"
pushd "%REPO_DIR%"

REM Activar entorno virtual
if exist ".venv\\Scripts\\activate.bat" (
    call ".venv\\Scripts\\activate.bat"
) else (
    echo [ERROR] No se encontró .venv\\Scripts\\activate.bat
    pause
    exit /b 1
)

REM Asegurar carpeta de logs
if not exist "logs" mkdir "logs"

REM Ejecutar scheduler con logs redirigidos
py run_mercado.py >> "logs\\startup.log" 2>&1

popd
endlocal
