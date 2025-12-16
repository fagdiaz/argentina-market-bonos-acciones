import datetime as dt
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List

import gspread
import pandas as pd
import requests
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
from config import (
    GOOGLE_SERVICE_ACCOUNT_JSON,
    IOL_PASS,
    IOL_USER,
    SHEET_BONOS_ID,
    SHEET_BONOS_TAB,
    SHEET_CLEAR,
)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "mercado.log"
CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_ACC_PANEL = CACHE_DIR / "panel_acciones.json"


def _setup_logging() -> logging.Logger:
    logger = logging.getLogger(__name__)
    if logger.handlers:
        return logger

    logger.setLevel(LOG_LEVEL)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    return logger


logger = _setup_logging()


# --------------------
# IOL Auth / Token
# --------------------
def pedirtoken() -> dict:
    url = "https://api.invertironline.com/token"
    data = {"username": IOL_USER, "password": IOL_PASS, "grant_type": "password"}
    response = requests.post(url=url, data=data, timeout=10)
    if not response.ok:
        logger.error("IOL token error %s: %s", response.status_code, response.text[:300])
    response.raise_for_status()
    token_data = response.json()
    logger.info("Token de InvertirOnline obtenido correctamente")
    return token_data


def _expires_in_seconds(token: dict) -> float:
    exp = dt.datetime.strptime(token[".expires"], "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=dt.UTC)
    ahora = dt.datetime.now(dt.UTC)
    return (exp - ahora).total_seconds()


def actualizartoken(token: dict) -> dict:
    if _expires_in_seconds(token) < 120:
        return pedirtoken()
    return token


def get_iol_token() -> dict:
    """Obtiene y renueva token IOL si es necesario."""
    tk = pedirtoken()
    return actualizartoken(tk)


# --------------------
# Cache de paneles
# --------------------
def _load_panel_cache(ttl_hours: int = 24) -> str:
    """Devuelve panel de acciones cacheado si no esta vencido."""
    try:
        if not CACHE_ACC_PANEL.exists():
            return ""
        age_seconds = (dt.datetime.now() - dt.datetime.fromtimestamp(CACHE_ACC_PANEL.stat().st_mtime)).total_seconds()
        if age_seconds > ttl_hours * 3600:
            return ""
        with CACHE_ACC_PANEL.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("panel", "")
    except Exception as e:
        logger.debug("No se pudo leer cache de paneles: %s", e)
        return ""


def _save_panel_cache(panel: str) -> None:
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        with CACHE_ACC_PANEL.open("w", encoding="utf-8") as f:
            json.dump({"panel": panel, "saved_at": dt.datetime.now().isoformat()}, f)
    except Exception as e:
        logger.debug("No se pudo guardar cache de paneles: %s", e)


# --------------------
# IOL Data
# --------------------
def listar_paneles(pais: str, instrumento: str, access_token: str) -> List[str]:
    """Lista paneles disponibles para un instrumento."""
    url = f"https://api.invertironline.com/api/v2/{pais}/Titulos/Cotizacion/Paneles/{instrumento}"
    headers = {"Authorization": f"Bearer {access_token}"}

    r = requests.get(url, headers=headers, timeout=10)
    logger.info("IOL GET %s -> %s", url, r.status_code)

    if not r.ok:
        logger.error("Error listando paneles: %s", r.text[:300])
        return []

    data = r.json()

    if isinstance(data, list):
        if data and isinstance(data[0], str):
            return data
        if data and isinstance(data[0], dict):
            for key in ("panel", "nombre", "name", "descripcion"):
                if key in data[0]:
                    return [x.get(key) for x in data if isinstance(x, dict) and x.get(key)]

    logger.warning("Formato inesperado al listar paneles: %s", str(data)[:300])
    return []


def panel(instrumento: str, panel_name: str, pais: str, access_token: str) -> pd.DataFrame:
    url_base = "https://api.invertironline.com/api/v2/"
    endpoint = f"Cotizaciones/{instrumento}/{panel_name}/{pais}"
    url = url_base + endpoint

    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url=url, headers=headers, timeout=10)

    logger.info("IOL GET %s -> %s", endpoint, response.status_code)

    if response.status_code == 404:
        logger.warning("Endpoint no encontrado (404): %s", endpoint)
        return pd.DataFrame()

    if not response.ok:
        logger.error(
            "IOL error %s en %s. Body (primeros 300 chars): %s",
            response.status_code,
            endpoint,
            response.text[:300],
        )
        return pd.DataFrame()

    try:
        data = response.json()
    except Exception as e:
        logger.error("ERROR: No se pudo decodificar la respuesta como JSON en %s: %s", endpoint, e)
        logger.debug("Body (primeros 300 chars): %s", response.text[:300])
        return pd.DataFrame()

    if isinstance(data, dict) and "titulos" in data:
        return pd.DataFrame(data["titulos"])

    logger.error("ERROR: Respuesta inesperada (sin 'titulos') en %s: %s", endpoint, data)
    return pd.DataFrame()


def fetch_bonos(access_token: str) -> pd.DataFrame:
    """Obtiene DataFrame de Bonos BYMA."""
    return panel("Bonos", "BYMA", "argentina", access_token)


def fetch_acciones(access_token: str, panel_name: str) -> pd.DataFrame:
    """Obtiene DataFrame de Acciones para el panel dado."""
    return panel("Acciones", panel_name, "argentina", access_token)


# --------------------
# Google Sheets
# --------------------
def export_to_sheets_simple(
    clear: bool,
    df: pd.DataFrame,
    sheet_id: str,
    sheet_name: str,
    columna: int,
    fila: int
) -> None:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    if isinstance(df, dict):
        df = pd.DataFrame([df])
    elif isinstance(df, pd.Series):
        df = df.to_frame().T
    elif df is None:
        df = pd.DataFrame()

    if df.empty:
        logger.warning("DataFrame vacio para exportar en sheet '%s'. No se exporta.", sheet_name)
        return

    credentials = Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_JSON, scopes=scopes)
    gc = gspread.authorize(credentials)

    sh = gc.open_by_key(sheet_id)

    try:
        worksheet = sh.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        logger.warning("Worksheet '%s' no existe. Creandola...", sheet_name)
        worksheet = sh.add_worksheet(title=sheet_name, rows=1000, cols=50)

    if clear:
        worksheet.clear()
        logger.info("Hoja '%s' limpiada antes de exportar", sheet_name)

    set_with_dataframe(
        worksheet,
        df,
        col=columna,
        row=fila,
        include_index=False,
        include_column_header=True,
    )

    logger.info(
        "Datos exportados a Google Sheets (%s / %s). Filas=%s, Cols=%s",
        sheet_id,
        sheet_name,
        df.shape[0],
        df.shape[1],
    )


def export_df_to_sheet(df: pd.DataFrame, tab_name: str) -> None:
    """Exporta un DataFrame a la hoja indicada usando SHEET_BONOS_ID."""
    export_to_sheets_simple(SHEET_CLEAR, df, SHEET_BONOS_ID, tab_name, 1, 1)


# --------------------
# Transformaciones
# --------------------
def transform_bonos(bonos_df: pd.DataFrame) -> pd.DataFrame:
    """Aplica las transformaciones actuales sobre Bonos."""
    if bonos_df.empty:
        return bonos_df

    columnas_a_eliminar = [
        "puntas",
        "puntas_col1",
        "puntas_col2",
        "puntas_col3",
        "puntas_col4",
        "puntas_col1_part1",
        "precioEjercicio",
        "tipoOpcion",
        "fechaVencimiento",
        "mercado",
        "puntas_col2_part1",
        "puntas_col3_part1",
        "puntas_col4_part1",
    ]

    if "puntas" in bonos_df.columns:
        bonos_df["puntas"] = bonos_df["puntas"].astype(str)
        split_columns = bonos_df["puntas"].str.split(",", expand=True)

        for idx, col in enumerate(["puntas_col1", "puntas_col2", "puntas_col3", "puntas_col4"]):
            if idx in split_columns.columns:
                bonos_df[col] = split_columns[idx]

        if "puntas_col4" in bonos_df.columns:
            bonos_df["puntas_col4"] = bonos_df["puntas_col4"].str.replace("}", "", regex=False)

        for i in range(1, 5):
            col_name = f"puntas_col{i}"
            if col_name in bonos_df.columns:
                split_again = bonos_df[col_name].str.split(": ", expand=True)
                if len(split_again.columns) >= 2:
                    bonos_df[f"{col_name}_part1"] = split_again[0]
                    bonos_df[f"{col_name}_part2"] = split_again[1]
    else:
        logger.warning("No 'puntas' column found in bonos_df")

    def convert_to_number(x):
        if pd.isna(x) or x == "":
            return None
        try:
            x = str(x).strip().replace(",", ".")
            return float(x)
        except Exception:
            return None

    for i in range(1, 5):
        for j in range(1, 3):
            col_name = f"puntas_col{i}_part{j}"
            if col_name in bonos_df.columns:
                bonos_df[col_name] = bonos_df[col_name].apply(convert_to_number)

    columnas_existentes = [col for col in columnas_a_eliminar if col in bonos_df.columns]
    if columnas_existentes:
        bonos_df = bonos_df.drop(columns=columnas_existentes)

    return bonos_df


# --------------------
# Main flow
# --------------------
def main() -> None:
    tk = get_iol_token()
    access_token = tk["access_token"]

    # --- BONOS ---
    bonos_raw = fetch_bonos(access_token)
    if bonos_raw.empty:
        logger.error("No llegaron datos de Bonos (result vacio). No se exporta.")
        return
    bonos_df = transform_bonos(bonos_raw)
    export_df_to_sheet(bonos_df, SHEET_BONOS_TAB)

    # --- ACCIONES ---
    acciones_tab = os.getenv("SHEET_ACCIONES_TAB", "ACCIONES")
    acciones_panel_env = os.getenv("ACCIONES_PANEL", "").strip()

    if acciones_panel_env:
        acciones_panel = acciones_panel_env
        logger.info("Usando ACCIONES_PANEL desde env: %s", acciones_panel)
    else:
        cached_panel = _load_panel_cache()
        if cached_panel:
            acciones_panel = cached_panel
            logger.info("Usando panel cacheado: %s", acciones_panel)
        else:
            paneles_acc = listar_paneles("argentina", "Acciones", access_token)
            if not paneles_acc:
                logger.warning("No hay paneles disponibles para Acciones. No se exporta.")
                return
            if "Merval" in paneles_acc:
                acciones_panel = "Merval"
            else:
                acciones_panel = paneles_acc[0]
            _save_panel_cache(acciones_panel)
            logger.info("Panel de acciones seleccionado: %s", acciones_panel)

    acciones_df = fetch_acciones(access_token, acciones_panel)
    logger.info("Acciones con panel '%s': filas=%s cols=%s", acciones_panel, acciones_df.shape[0], acciones_df.shape[1])

    if acciones_df.empty:
        logger.warning("Acciones vacio. No se exporta.")
    else:
        export_df_to_sheet(acciones_df, acciones_tab)


if __name__ == "__main__":
    main()
