import requests
import datetime as dt
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import websocket as ws
from google.oauth2.service_account import Credentials
import json
import os
import time
import logging
import sys
from pandas.tseries.offsets import MonthEnd
from pandas.tseries.holiday import USFederalHolidayCalendar
from config import GOOGLE_SERVICE_ACCOUNT_JSON, MERCADO_END, MERCADO_START, ROFEX_PASS, ROFEX_USER

# Verificar versión de Python
if sys.version_info < (3, 6):
    print("Este script requiere Python 3.6 o superior")
    sys.exit(1)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Asegura que los logs se muestren en la consola
    ]
)
logger = logging.getLogger(__name__)

def pedirtokenROFEX():
    try:
        usuario = ROFEX_USER
        password = ROFEX_PASS
        
        if not usuario or not password:
            logger.error("Credenciales no encontradas en variables de entorno")
            return None
        
        logger.info("Intentando obtener token de ROFEX...")
        r = requests.post(
            url="https://api.remarkets.primary.com.ar/auth/getToken",
            headers={"X-Username": usuario, "X-Password": password},
            timeout=10
        )
        r.raise_for_status()
        token = r.headers['X-Auth-Token']
        logger.info("Token obtenido exitosamente")
        return token
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión al obtener token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al obtener token: {str(e)}")
        return None
#Lista de simbolos y solo 5 posiciones
symbol_list = ["DLR/JUN25", "DLR/JUL25", "DLR/AGO25", "DLR/SEP25","DLR/OCT25"]

hora_inicio = MERCADO_START
cierre_prueba = MERCADO_END

def export_to_sheets_simple(df, sheet_id, sheet_name, columna, fila):
    try:
        logger.info("Preparando datos para exportar a Google Sheets...")
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Verificar que el archivo de credenciales existe
        if not os.path.exists(GOOGLE_SERVICE_ACCOUNT_JSON):
            logger.error("Archivo de credenciales de Google no encontrado")
            return
            
        # Authenticate using service account credentials
        credentials = Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_JSON, scopes=scopes)
        gc = gspread.authorize(credentials)

        # Open the spreadsheet and worksheet
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.worksheet(sheet_name)
        
        # Write the DataFrame to the worksheet
        set_with_dataframe(worksheet, df, col=columna, row=fila, include_index=False, include_column_header=True)
        logger.info("Datos exportados exitosamente a Google Sheets")
        
    except Exception as e:
        logger.error(f"Error al exportar a Google Sheets: {str(e)}")

def create_websocket_connection(token):
    try:
        headers = {'X-Auth-Token': token}
        s = 'wss://api.remarkets.primary.com.ar/'
        logger.info("Intentando establecer conexión WebSocket...")
        conn = ws.create_connection(s, header=headers)
        logger.info("Conexión WebSocket establecida exitosamente")
        return conn
    except Exception as e:
        logger.error(f"Error al crear conexión WebSocket: {str(e)}")
        return None

def subscribe_to_market(conn, symbol):
    try:
        subscribe_msg = f'{{"type":"smd","level":1,"entries":["BI","OF"],"products":[{{"symbol":"{symbol}","marketId":"ROFX"}}],"depth":2}}'
        logger.info(f"Enviando mensaje de suscripción: {subscribe_msg}")
        conn.send(subscribe_msg)
        logger.info("Mensaje de suscripción enviado")
        
        # Esperar respuesta de suscripción
        try:
            response_str = conn.recv()
            logger.info(f"Respuesta de suscripción recibida (raw): {response_str}")
            
            # Convertir el string JSON a diccionario
            response = json.loads(response_str)
            logger.info("Respuesta convertida a diccionario")
            
            # Debug: Verificar la estructura de la respuesta
            logger.info("Estructura de la respuesta:")
            logger.info(f"Keys en response: {response.keys()}")
            
            if 'marketData' in response:
                logger.info(f"Keys en marketData: {response['marketData'].keys()}")
                if 'BI' in response['marketData']:
                    logger.info(f"Primera fila de BI: {response['marketData']['BI'][0] if response['marketData']['BI'] else 'Lista vacía'}")
                if 'OF' in response['marketData']:
                    logger.info(f"Primera fila de OF: {response['marketData']['OF'][0] if response['marketData']['OF'] else 'Lista vacía'}")
            
            # Crear DataFrame solo si tenemos los datos necesarios
            if 'marketData' in response and 'BI' in response['marketData'] and 'OF' in response['marketData']:
                # Crear DataFrame para BI
                df_bi = pd.DataFrame(response['marketData']['BI'])
                logger.info(f"DataFrame BI creado con columnas: {df_bi.columns.tolist()}")
                
                # Renombrar columnas de BI para evitar conflictos
                df_bi.columns = [f'BI_{col}' for col in df_bi.columns]
                
                # Crear DataFrame para OF
                df_of = pd.DataFrame(response['marketData']['OF'])
                logger.info(f"DataFrame OF creado con columnas: {df_of.columns.tolist()}")
                
                # Renombrar columnas de OF para evitar conflictos
                df_of.columns = [f'OF_{col}' for col in df_of.columns]
                
                # Concatenar horizontalmente (por columnas)
                df = pd.concat([df_bi, df_of], axis=1)
                logger.info("DataFrames combinados horizontalmente")
                
                # Agregar timestamp y convertirlo a datetime
                raw_timestamp = response['timestamp'] # raw_timestamp es un int o float
                converted_timestamp = pd.to_datetime(float(raw_timestamp) / 1000, unit='s')
                df['timestamp'] = converted_timestamp
                logger.info("Timestamp convertido a datetime y agregado al DataFrame")
                
                # Reordenar columnas en el orden deseado
                column_order = ['timestamp', 'BI_size', 'BI_price', 'OF_price', 'OF_size']
                # Asegurarse de que todas las columnas existan antes de reordenar
                existing_columns_for_order = [col for col in column_order if col in df.columns]
                df = df[existing_columns_for_order]
                logger.info("Columnas reordenadas según el orden especificado")
                
                print("DataFrame final (dentro de subscribe_to_market):")
                print(df.head())
                return df # Retornar el DataFrame completo
            else:
                logger.error("La respuesta no contiene los datos necesarios (marketData, BI, OF, timestamp) para crear el DataFrame")
                return False
                
        except json.JSONDecodeError as e:
            logger.error(f"Error al decodificar JSON: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error al procesar respuesta de suscripción: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error al suscribirse al mercado: {str(e)}")
        return False
    
def main():
    try:
        logger.info("Iniciando aplicación...")
        logger.info(f"Horario configurado - Inicio: {hora_inicio}, Cierre: {cierre_prueba}")
        
        tokenROFEX = pedirtokenROFEX()
        if not tokenROFEX:
            logger.error("No se pudo obtener el token de ROFEX. Verifica tus credenciales.")
            return

        hora_actual_inicial = dt.datetime.now().time()
        if hora_actual_inicial < hora_inicio or hora_actual_inicial > cierre_prueba:
            logger.warning(f"Fuera del horario de mercado. Hora actual: {hora_actual_inicial}, Horario permitido: {hora_inicio} - {cierre_prueba}")
            return
        
        logger.info(f"Iniciando conexión al mercado. Horario actual: {hora_actual_inicial}")
        
        timeout_errors = 0
        max_timeout_errors = 5

        # Bucle principal de la aplicación, se ejecuta hasta cierre_prueba
        while dt.datetime.now().time() < cierre_prueba:
            try:
                logger.info("Intentando establecer conexión WebSocket...")
                conn = create_websocket_connection(tokenROFEX)
                if not conn:
                    logger.warning("Fallo al crear conexión WebSocket. Reintentando en 5 segundos...")
                    time.sleep(5)
                    continue # Reintentar conexión
                
                # Diccionario para almacenar los DataFrames de cada símbolo
                dataframes_collection = {}
                first_timestamp_series = None
                
                logger.info(f"Iniciando la obtención de datos para los símbolos: {symbol_list}")
                for sym in symbol_list:
                    if dt.datetime.now().time() >= cierre_prueba:
                        logger.info("Horario de cierre alcanzado durante la obtención de datos.")
                        break # Salir del bucle de símbolos

                    logger.info(f"Obteniendo datos para el símbolo: {sym}")
                    # Aquí es donde la lógica de subscribe_to_market necesita un bucle interno
                    # si quieres un flujo continuo. Por ahora, obtiene un snapshot.
                    dataframe_result = subscribe_to_market(conn, sym) 
                    
                    if dataframe_result is not False and isinstance(dataframe_result, pd.DataFrame):
                        dataframes_collection[sym] = dataframe_result
                        logger.info(f"Datos para {sym} obtenidos y almacenados.")
                        
                        # Capturar el timestamp del primer DataFrame exitoso
                        if first_timestamp_series is None and 'timestamp' in dataframe_result.columns:
                            first_timestamp_series = dataframe_result[['timestamp']].copy()
                            logger.info(f"Serie de Timestamps guardada del primer DataFrame ({sym})")
                    else:
                        logger.warning(f"No se pudieron obtener los datos para el símbolo: {sym} o no es un DataFrame.")
                        # Aquí podrías decidir si continuar con otros símbolos o reintentar la conexión general
                        # Por ahora, simplemente continuará con el siguiente símbolo.

                if dt.datetime.now().time() >= cierre_prueba:
                    logger.info("Horario de cierre alcanzado después de obtener todos los datos.")
                    break # Salir del bucle principal de la aplicación
                
                # Exportar los datos recolectados
                start_columns_for_export = [2, 6, 10, 14, 18]
                if first_timestamp_series is not None and not first_timestamp_series.empty:
                    logger.info("Exportando la serie de Timestamps a Google Sheets, columna: 1")
                    export_to_sheets_simple(first_timestamp_series, '1ywgBZAwzBZlALK1g-rEg9E017XwWXzSaQQx7BU3zm3w', 'Dólar futuro', 1, 28)
                else:
                    logger.warning("No se guardó ninguna serie de timestamps para exportar o está vacía.")

                for index, sym_key in enumerate(symbol_list):
                    if sym_key in dataframes_collection and isinstance(dataframes_collection[sym_key], pd.DataFrame):
                        if index < len(start_columns_for_export):
                            df_to_export = dataframes_collection[sym_key].copy()
                            if 'timestamp' in df_to_export.columns:
                                df_to_export = df_to_export.drop(columns=['timestamp'])
                            
                            if not df_to_export.empty:
                                start_col = start_columns_for_export[index]
                                logger.info(f"Exportando datos principales para {sym_key} a Google Sheets, columna: {start_col}")
                                export_to_sheets_simple(df_to_export, '1ywgBZAwzBZlALK1g-rEg9E017XwWXzSaQQx7BU3zm3w', 'Dólar futuro', start_col, 28)
                            else:
                                logger.warning(f"El DataFrame para {sym_key} (sin timestamp) está vacío. Omitiendo exportación.")
                        else:
                            logger.warning(f"No hay columna de inicio definida para el índice {index} ({sym_key}). Omitiendo exportación.")
                    elif sym_key in dataframes_collection:
                        logger.warning(f"El elemento para {sym_key} en el diccionario dataframes_collection no es un DataFrame (tipo: {type(dataframes_collection[sym_key])}). Omitiendo exportación.")
                    else:
                        logger.warning(f"No se encontraron datos para {sym_key} en el diccionario dataframes_collection. Omitiendo exportación.")
                
                logger.info("Proceso de obtención y exportación completado. Esperando para el próximo ciclo o cierre.")
                # Si quieres que este ciclo se repita cada X tiempo ANTES de cierre_prueba,
                # aquí es donde añadirías un time.sleep(). Por ejemplo, para repetir cada minuto:
                # time.sleep(60)
                # Sin un sleep, volverá a ejecutar la obtención de datos inmediatamente si no se ha alcanzado cierre_prueba
                # O, si la idea es que el while True de arriba sea el principal y esto solo un bloque de ejecución,
                # entonces el continue/break es correcto. Por el momento, lo dejo así para que se ejecute una vez
                # y luego el while dt.datetime.now().time() < cierre_prueba lo manejará.
                # Para que se ejecute solo una vez y espere al cierre: 
                continue # Sale del while True interno y espera al while < cierre_prueba

            except ws.WebSocketConnectionClosedException:
                logger.warning("Conexión WebSocket cerrada, intentando reconectar...")
                timeout_errors += 1
                logger.warning(f"Error de timeout #{timeout_errors} de {max_timeout_errors}")
                if timeout_errors >= max_timeout_errors:
                    logger.error(f"Se alcanzó el límite de {max_timeout_errors} errores por timeout. Finalizando programa.")
                    return # Salir de main
                time.sleep(5) # Esperar antes de reintentar conexión
                continue # Reintentar conexión
            except Exception as e:
                logger.error(f"Error general en el bucle de la aplicación: {str(e)}")
                time.sleep(5)
                continue # Reintentar ciclo
        
        logger.info(f"Horario de cierre ({cierre_prueba}) alcanzado. Finalizando aplicación.")

    except Exception as e:
        logger.error(f"Error crítico en la aplicación: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

"""def getinstruments_byCFI(CFI):
    tokenROFEX = pedirtokenROFEX()
    p = {'CFICode': CFI}
    url= 'https://api.remarkets.primary.com.ar/rest/instruments/byCFICode'
    r= requests.get(url= url, headers= {'X-Auth-Token':tokenROFEX}, params = p)
    r= r.json()
    df = pd.DataFrame(r['instruments'])
    return df
"""
