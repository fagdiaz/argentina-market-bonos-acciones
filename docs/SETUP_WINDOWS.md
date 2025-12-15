# Puesta en marcha en Windows

Este repo corre el scheduler `run_mercado.py` (Bonos/Acciones) en un entorno virtual `.venv`. A continuación los pasos para dejarlo arrancando al iniciar Windows.

## Prerrequisitos
- Python instalado (3.6+). Verifica que `py` o `python` estén en PATH.
- Crear venv en el root del repo: `python -m venv .venv`
- Activar venv y instalar dependencias:
  ```
  .venv\Scripts\activate
  pip install -r requirements.txt
  ```

## Variables de entorno (.env no se versiona)
Crear un archivo `.env` en el root (no subirlo a git) con placeholders, por ejemplo:
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
- Comparte la hoja (`SHEET_BONOS_ID`) con el correo del Service Account definido en tu JSON (`client_email`).
- El JSON debe estar fuera del repo; apunta `GOOGLE_SERVICE_ACCOUNT_JSON` a esa ruta segura.

## Script de arranque
- Archivo: `run_startup.bat` (en el root).
- Hace `cd` al repo, activa `.venv\Scripts\activate.bat`, crea `logs/` si falta y ejecuta `py run_mercado.py >> logs/startup.log 2>&1`.

## Registrar tarea en Task Scheduler
1. Abrir "Task Scheduler" → "Create Task…".
2. General: marcar "Run whether user is logged on or not" y "Run with highest privileges" si aplica.
3. Triggers: "At startup" (o al iniciar sesión si prefieres).
4. Actions: "Start a program" → `run_startup.bat` (ruta completa en el repo).
5. Settings: habilitar "Restart on failure" y configurar reintentos.
6. Condiciones: desactiva "Start the task only if the computer is on AC power" si quieres que corra siempre.

## Logs
- El scheduler original escribe en `mercado_scheduler.log`; el startup redirige stdout/stderr a `logs/startup.log`.
- `logs/` está ignorado en git; revisa esos archivos para diagnosticar.

## Troubleshooting
- Permisos: si Task Scheduler falla, habilita "Run with highest privileges".
- PATH/py vs python: el .bat usa `py`; si no existe, edítalo a `python`.
- Venv: asegúrate de que `.venv\Scripts\activate.bat` existe; si cambiaste la ruta del repo, ajusta el .bat.
- Credenciales: verifica `.env` y que la hoja esté compartida con el service account.
