import os
from pathlib import Path
import datetime as _dt

from dotenv import load_dotenv

# Load local .env if present to help during development.
load_dotenv()


def _get_env_var(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_file_path(name: str) -> str:
    path = _get_env_var(name)
    if not Path(path).expanduser().exists():
        raise FileNotFoundError(f"Configured path for {name} does not exist: {path}")
    return path


def _get_env_var_optional(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


def _parse_time(value: str) -> _dt.time:
    try:
        hours, minutes = value.split(":")
        return _dt.time(int(hours), int(minutes))
    except Exception:
        raise RuntimeError(f"Invalid time format for {value}, expected HH:MM")


IOL_USER = _get_env_var("IOL_USER")
IOL_PASS = _get_env_var("IOL_PASS")

ENABLE_ROFEX = _get_env_var_optional("ENABLE_ROFEX", "false").strip().lower() in ("1", "true", "yes", "y")

ROFEX_USER = os.getenv("ROFEX_USER", "")
ROFEX_PASS = os.getenv("ROFEX_PASS", "")

if ENABLE_ROFEX and (not ROFEX_USER or not ROFEX_PASS):
    raise RuntimeError("ENABLE_ROFEX=true but ROFEX_USER/ROFEX_PASS are missing")


# Path to the Google service account JSON file (kept outside the repo).
GOOGLE_SERVICE_ACCOUNT_JSON = _get_file_path("GOOGLE_SERVICE_ACCOUNT_JSON")

# Scheduler parameters (optional with defaults)
MERCADO_START = _parse_time(_get_env_var_optional("MERCADO_START", "11:00"))
MERCADO_END = _parse_time(_get_env_var_optional("MERCADO_END", "17:00"))
MERCADO_EVERY_MIN = int(_get_env_var_optional("MERCADO_EVERY_MIN", "15"))

# Google Sheets (bonos)
SHEET_BONOS_ID = _get_env_var("SHEET_BONOS_ID")
SHEET_BONOS_TAB = _get_env_var_optional("SHEET_BONOS_TAB", "BONOS")
SHEET_CLEAR = _get_env_var_optional("SHEET_CLEAR", "false").lower() in ("1", "true", "yes", "y")


SHEET_BONOS_ID = _get_env_var("SHEET_BONOS_ID")
SHEET_BONOS_TAB = _get_env_var_optional("SHEET_BONOS_TAB", "BONOS")
SHEET_CLEAR = _get_env_var_optional("SHEET_CLEAR", "false").strip().lower() in ("1","true","yes","y")
