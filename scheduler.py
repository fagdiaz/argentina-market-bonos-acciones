# -*- coding: utf-8 -*-

import datetime as dt
import logging
import os
import subprocess
import sys
import time

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None

from config import MERCADO_EVERY_MIN, MERCADO_END, MERCADO_START

AR_TZ = ZoneInfo("America/Argentina/Buenos_Aires") if ZoneInfo else None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("mercado_scheduler.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def is_market_hours(now: dt.datetime | None = None) -> bool:
    if now is None:
        now = dt.datetime.now(AR_TZ) if AR_TZ else dt.datetime.now()

    if AR_TZ is not None and now.tzinfo is None:
        now = now.replace(tzinfo=AR_TZ)

    # Lunes=0 .. Domingo=6
    if now.weekday() >= 5:
        return False

    return MERCADO_START <= now.time() <= MERCADO_END


def run_mercado() -> None:
    try:
        logger.info("Ejecutando mercado.py...")
        subprocess.run([sys.executable, "mercado.py"], check=True)
        logger.info("mercado.py ejecutado exitosamente")
    except subprocess.CalledProcessError as e:
        logger.error("Error al ejecutar mercado.py: %s", str(e))
    except Exception as e:
        logger.error("Error inesperado: %s", str(e))


def _is_interactive() -> bool:
    # Si hay consola/tty para preguntar
    return sys.stdin.isatty() and sys.stdout.isatty()


def _ask_yes_no(prompt: str) -> bool:
    while True:
        ans = input(prompt).strip().lower()
        if ans in ("s", "si", "sí", "y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Respuesta inválida. Escribí S o N.")


def run_test() -> int:
    if AR_TZ is None:
        logger.error("ZoneInfo no disponible; no puedo fijar TZ Argentina en este Python.")
        return 2

    cases = [
        ("Sábado 12:00", dt.datetime(2025, 12, 13, 12, 0, tzinfo=AR_TZ)),
        ("Domingo 12:00", dt.datetime(2025, 12, 14, 12, 0, tzinfo=AR_TZ)),
        ("Lunes 10:59", dt.datetime(2025, 12, 15, 10, 59, tzinfo=AR_TZ)),
        ("Lunes 11:00", dt.datetime(2025, 12, 15, 11, 0, tzinfo=AR_TZ)),
        ("Lunes 16:59", dt.datetime(2025, 12, 15, 16, 59, tzinfo=AR_TZ)),
        ("Lunes 17:01", dt.datetime(2025, 12, 15, 17, 1, tzinfo=AR_TZ)),
    ]

    print("=== TEST is_market_hours() (TZ Argentina) ===")
    print(f"Ventana: {MERCADO_START.strftime('%H:%M')} - {MERCADO_END.strftime('%H:%M')} (L-V)")
    for label, when in cases:
        ok = is_market_hours(when)
        print(f"{label:14} | {when.isoformat()} | weekday={when.weekday()} | ok={ok}")

    return 0


def main() -> None:
    # Modo test
    if "--test" in sys.argv or os.getenv("RUN_MERCADO_TEST") == "1":
        raise SystemExit(run_test())

    logger.info("Iniciando programador de mercado.py")
    logger.info(
        "Horario de ejecucion: %s - %s",
        MERCADO_START.strftime("%H:%M"),
        MERCADO_END.strftime("%H:%M"),
    )

    now = dt.datetime.now(AR_TZ) if AR_TZ else dt.datetime.now()
    within = is_market_hours(now)

    # Si estás fuera de horario y lo corrés a mano: preguntar si querés forzar una corrida
    if not within and _is_interactive():
        logger.warning(
            "Estás fuera de horario (ahora %s, weekday=%s).",
            now.strftime("%H:%M"),
            now.weekday(),
        )
        if _ask_yes_no("¿Querés ejecutar mercado.py igual (forzar una corrida ahora)? [S/N]: "):
            run_mercado()
        else:
            logger.info("No se forzó ejecución. Saliendo.")
            return

    # Loop scheduler normal
    while True:
        try:
            now = dt.datetime.now(AR_TZ) if AR_TZ else dt.datetime.now()

            if is_market_hours(now):
                run_mercado()
                logger.info("Esperando %s minutos hasta la próxima ejecucion...", MERCADO_EVERY_MIN)
                time.sleep(MERCADO_EVERY_MIN * 60)
                continue

            # Fuera de horario: si es finde, cortamos
            if now.weekday() >= 5:
                logger.info("Fin de semana. Programa finalizado por hoy.")
                break

            # Antes de abrir: polling cada 60s
            if now.time() < MERCADO_START:
                logger.info("Aún no abre el mercado. Revisando cada 60s...")
                time.sleep(60)
                continue

            # Ya cerró: cortamos
            logger.info("Fuera del horario de mercado (%s). Programa finalizado por hoy.", MERCADO_END.strftime("%H:%M"))
            break

        except KeyboardInterrupt:
            logger.info("Programa detenido por el usuario")
            break
        except Exception as e:
            logger.error("Error en el bucle principal: %s", str(e))
            time.sleep(60)


if __name__ == "__main__":
    main()
