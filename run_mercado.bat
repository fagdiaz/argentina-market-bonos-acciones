@echo off
echo Iniciando script de mercado...
echo Iniciando script de mercado... >> mercado_log.txt
echo Fecha y hora: %date% %time%
echo Fecha y hora: %date% %time% >> mercado_log.txt

:: Mostrar el directorio actual
echo Directorio actual: %CD%
echo Directorio actual: %CD% >> mercado_log.txt

:: Intentar cambiar al directorio del script
cd /d "%~dp0"
echo Nuevo directorio: %CD%
echo Nuevo directorio: %CD% >> mercado_log.txt

:: Verificar Python en el PATH
echo Verificando Python en el PATH...
echo Verificando Python en el PATH... >> mercado_log.txt
where python >> mercado_log.txt 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Python encontrado en el PATH
    echo Python encontrado en el PATH >> mercado_log.txt
    set PYTHON_FOUND=python
    goto :found_python
)

:not_found_python
echo ERROR: No se encontró Python en el PATH
echo ERROR: No se encontró Python en el PATH >> mercado_log.txt
echo Por favor, verifica que Python esté instalado correctamente
echo Por favor, verifica que Python esté instalado correctamente >> mercado_log.txt
echo y que la casilla "Add Python to PATH" esté marcada durante la instalación
echo y que la casilla "Add Python to PATH" esté marcada durante la instalación >> mercado_log.txt
pause
exit /b 1

:found_python
echo Python encontrado en: %PYTHON_FOUND%
echo Python encontrado en: %PYTHON_FOUND% >> mercado_log.txt

:: Mostrar la versión de Python
echo Mostrando versión de Python...
echo Mostrando versión de Python... >> mercado_log.txt
"%PYTHON_FOUND%" --version
"%PYTHON_FOUND%" --version >> mercado_log.txt 2>&1

:: Verificar dependencias
echo Verificando dependencias...
echo Verificando dependencias... >> mercado_log.txt
"%PYTHON_FOUND%" -c "import requests, pandas, gspread, gspread_dataframe, websocket, google.auth, dotenv" 2>> mercado_log.txt
if %ERRORLEVEL% NEQ 0 (
    echo Instalando dependencias...
    echo Instalando dependencias... >> mercado_log.txt
    "%PYTHON_FOUND%" -m pip install --upgrade pip >> mercado_log.txt 2>&1
    "%PYTHON_FOUND%" -m pip install -r requirements.txt >> mercado_log.txt 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: No se pudieron instalar las dependencias
        echo ERROR: No se pudieron instalar las dependencias >> mercado_log.txt
        pause
        exit /b 1
    )
    echo Dependencias instaladas correctamente
    echo Dependencias instaladas correctamente >> mercado_log.txt
)

:: Ejecutar el script
echo Ejecutando run_mercado.py...
echo Ejecutando run_mercado.py... >> mercado_log.txt
"%PYTHON_FOUND%" run_mercado.py
"%PYTHON_FOUND%" run_mercado.py >> mercado_log.txt 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: El script falló con código de error %ERRORLEVEL%
    echo ERROR: El script falló con código de error %ERRORLEVEL% >> mercado_log.txt
    pause
    exit /b 1
)

echo Script ejecutado correctamente
echo Script ejecutado correctamente >> mercado_log.txt
pause 
