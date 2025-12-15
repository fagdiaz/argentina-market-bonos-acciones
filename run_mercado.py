import subprocess
import time
import datetime
import logging
from config import MERCADO_EVERY_MIN, MERCADO_END, MERCADO_START

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
        subprocess.run(['python', 'mercado.py'], check=True)
        logger.info("mercado.py ejecutado exitosamente")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error al ejecutar mercado.py: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")

def main():
    logger.info("Iniciando programador de mercado.py")
    logger.info("Horario de ejecuciÍn: %s - %s", MERCADO_START.strftime('%H:%M'), MERCADO_END.strftime('%H:%M'))
    
    while True:
        try:
            current_time = datetime.datetime.now().time()
            
            if is_market_hours():
                # Ejecutar mercado.py
                run_mercado()
                
                # Esperar intervalo configurado
                logger.info("Esperando %s minutos hasta la prÍxima ejecuciÍn...", MERCADO_EVERY_MIN)
                time.sleep(MERCADO_EVERY_MIN * 60)  # minutos en segundos
            else:
                # Si estamos fuera del horario, esperar hasta la prÍxima hora
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
