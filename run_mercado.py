# -*- coding: utf-8 -*-
import datetime
import logging
import subprocess
import sys
import time
from config import MERCADO_EVERY_MIN, MERCADO_END, MERCADO_START

# Asegura consola en UTF-8 en Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mercado_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def is_market_hours():
    """Verifica si estamos dentro del horario de mercado (configurable)"""
    now = datetime.datetime.now().time()
    return MERCADO_START <= now <= MERCADO_END

def run_mercado():
    try:
        logger.info("Ejecutando mercado.py...")
        subprocess.run([sys.executable, 'mercado.py'], check=True)
        logger.info("mercado.py ejecutado exitosamente")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error al ejecutar mercado.py: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")

def main():
    logger.info("Iniciando programador de mercado.py")
    logger.info("Horario de ejecucion: %s - %s", MERCADO_START.strftime('%H:%M'), MERCADO_END.strftime('%H:%M'))
    
    while True:
        try:
            current_time = datetime.datetime.now().time()
            
            if is_market_hours():
                # Ejecutar mercado.py
                run_mercado()
                
                # Esperar intervalo configurado
                logger.info("Esperando %s minutos hasta la proxima ejecucion...", MERCADO_EVERY_MIN)
                time.sleep(MERCADO_EVERY_MIN * 60)  # minutos en segundos
            else:
                # Si estamos fuera del horario, esperar hasta la proxima hora
                if current_time < MERCADO_START:
                    logger.info("Esperando hasta las %s para comenzar...", MERCADO_START.strftime('%H:%M'))
                    time.sleep(60)  # Revisar cada minuto
                else:
                    logger.info("Fuera del horario de mercado (%s). Programa finalizado por hoy.", MERCADO_END.strftime('%H:%M'))
                    break
            
        except KeyboardInterrupt:
            logger.info("Programa detenido por el usuario")
            break
        except Exception as e:
            logger.error(f"Error en el bucle principal: {str(e)}")
            time.sleep(60)  # Esperar 1 minuto antes de reintentar

if __name__ == "__main__":
    main() 
