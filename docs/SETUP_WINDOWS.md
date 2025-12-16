# Puesta en marcha en Windows

Flujo recomendado: Task Scheduler llama a `run_startup.bat`, que usa el venv `.venv` y ejecuta el scheduler `run_mercado.py` (core en `mercado.py`).

## Prerrequisitos
- Python 3.6+ instalado (usa `python` o `py` solo para crear el venv).
- Crear venv en el root: `python -m venv .venv`
- Instalar dependencias dentro del venv:
  .venv\Scripts\activate
  pip install -r requirements.txt

## Variables de entorno (.env no se versiona)
Crea `.env` en el root (no subirlo a git), por ejemplo:
```
IOL_USER=tu_usuario_iol
IOL_PASS=tu_password_iol
ROFEX_USER=tu_usuario_rofex
ROFEX_PASS=tu_password_rofex
GOOGLE_SERVICE_ACCOUNT_JSON=C:\ruta\segura\service_account.json
SHEET_BONOS_ID=tu_sheet_id
SHEET_BONOS_TAB=BONOS
SHEET_CLEAR=false
SHEET_ACCIONES_TAB=ACCIONES
ACCIONES_PANEL=Merval           # opcional; si no, usa cache/descubrimiento
MERCADO_START=11:00
MERCADO_END=17:00
MERCADO_EVERY_MIN=15
LOG_LEVEL=INFO
```

## Google Sheets
- Comparte la hoja (`SHEET_BONOS_ID`) con el `client_email` del Service Account (JSON).
- El JSON debe estar fuera del repo; apunta `GOOGLE_SERVICE_ACCOUNT_JSON` a esa ruta segura.

## Script de arranque (unico entrypoint)
- Usa solo `run_startup.bat` en el root.
- Hace `cd` al repo, crea `logs/`, verifica `.venv\Scripts\python.exe`, instala deps si falta gspread y ejecuta `run_mercado.py` con ese Python. Todo loguea en `logs/startup.log`.

## Registrar tarea en Task Scheduler
1. Task Scheduler -> Create Task.
2. General: "Run whether user is logged on or not"; "Run with highest privileges" si aplica.
3. Trigger: "At startup" (o al iniciar sesion).
4. Action: "Start a program".
   - Program/script: ruta completa a `run_startup.bat`.
   - Start in (opcional pero recomendado): ruta del repo (sin comillas internas, solo el path).
5. Settings: habilita "Restart on failure" y reintentos.
6. Condiciones: desactiva "Start the task only if the computer is on AC power" si quieres que corra siempre.

## Logs
- `run_mercado.py` escribe en `mercado_scheduler.log`.
- `run_startup.bat` redirige stdout/stderr a `logs/startup.log`.
- `logs/` esta ignorado en git; revisa esos archivos para diagnosticar.

## Troubleshooting
- Permisos: si Task Scheduler falla, habilita "Run with highest privileges".
- Venv: confirma que `.venv\Scripts\python.exe` existe; si mueves el repo, ajusta el .bat.
- Dependencias: si faltan, `run_startup.bat` las instala (revisa `logs/startup.log`).
- Credenciales: revisa `.env` y que la hoja este compartida con el service account.
