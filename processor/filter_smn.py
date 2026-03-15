import sys
import os
import pandas as pd
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUX_URL = os.environ.get("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN")
INFLUX_ORG = os.environ.get("INFLUX_ORG")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET_TELEMETRY")

import zipfile
import glob
import shutil
import tempfile

def filter_smn_data(filepath):
    """
    Lee un archivo de datos del SMN, extrae la fila de Río Cuarto y la envía a InfluxDB.
    Maneja tanto archivos .txt directos como archivos .zip que contengan txt.
    """
    print(f"[{datetime.now().isoformat()}] Procesando archivo SMN: {filepath}")
    
    if not INFLUX_TOKEN:
        print("ERROR: INFLUX_TOKEN no está definido. Omitiendo volcado a BD.")
        return

    # Manejo de la extracción si es un archivo ZIP
    txt_filepath = filepath
    temp_dir = None
    
    if filepath.lower().endswith(".zip"):
        print("Archivo ZIP detectado. Extrayendo contenido...")
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Buscar el archivo de texto extraído
            extracted_txts = glob.glob(os.path.join(temp_dir, "*.txt"))
            if not extracted_txts:
                print("Error: No se encontró ningún archivo .txt dentro del ZIP.")
                shutil.rmtree(temp_dir)
                return
                
            # Tomamos el primer txt encontrado
            txt_filepath = extracted_txts[0]
            print(f"Archivo de texto encontrado: {os.path.basename(txt_filepath)}")
        except zipfile.BadZipFile:
            print("Error: Archivo ZIP corrupto o inválido.")
            if temp_dir:
                shutil.rmtree(temp_dir)
            return

    # Parsear archivo TXT del SMN (delimitador: punto y coma)
    # Ejemplo de fila: Ro Cuarto;15-marzo-2026;11:00;Parcialmente nublado;15 km;22.6;No se calcula; 74;Norte  24;955.4 /
    print("Leyendo el archivo txt y buscando la estación Río Cuarto...")
    rio_cuarto_data = None
    
    try:
        # Se lee con latin1 o ignore para evitar crash con la "í" mal decodificada en SMN
        with open(txt_filepath, 'r', encoding='latin1') as f:
            for line in f:
                if "Cuarto" in line and ("R" in line or "r" in line):
                    cols = line.strip().split(';')
                    if len(cols) >= 10:
                        try:
                            # Col 5: Temperatura
                            temp_str = cols[5].strip()
                            temperature = float(temp_str) if "No" not in temp_str and temp_str else None
                            
                            # Col 7: Humedad
                            hum_str = cols[7].strip()
                            humidity = float(hum_str) if "No" not in hum_str and hum_str else None
                            
                            # Col 9: Presión
                            press_str = cols[9].replace('/', '').strip()
                            pressure = float(press_str) if "No" not in press_str and press_str else None
                            
                            # Col 8: Viento Dirección + Velocidad
                            wind_str = cols[8].strip().split()
                            wind_speed = float(wind_str[-1]) if len(wind_str) > 0 and wind_str[-1].isdigit() else 0.0
                            wind_direction = " ".join(wind_str[:-1]) if len(wind_str) > 1 else "Desconocido"
                            
                            if temperature is not None:
                                rio_cuarto_data = {
                                    "station": "Rio Cuarto",
                                    "temperature": temperature,
                                    "humidity": humidity or 0.0,
                                    "pressure": pressure or 0.0,
                                    "wind_speed": wind_speed,
                                    "wind_direction": wind_direction
                                }
                                break
                        except Exception as parse_err:
                            print(f"Advertencia: No se pudo parsear los valores numéricos ({parse_err})")
                            
        if not rio_cuarto_data:
            print("Métrica abortada: La estación 'Río Cuarto' no fue encontrada en este registro o sus datos no son numéricos.")
        else:
            client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
            write_api = client.write_api(write_options=SYNCHRONOUS)

            point = (
                Point("weather_station")
                .tag("location", rio_cuarto_data["station"])
                .field("temperature", rio_cuarto_data["temperature"])
                .field("humidity", rio_cuarto_data["humidity"])
                .field("pressure", rio_cuarto_data["pressure"])
                .field("wind_speed", rio_cuarto_data["wind_speed"])
                .field("wind_direction", rio_cuarto_data["wind_direction"])
                .time(datetime.utcnow(), WritePrecision.NS)
            )

            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
            print(f"-> ¡Datos reales de SMN {rio_cuarto_data['station']} [{rio_cuarto_data['temperature']}°C] guardados exitosamente en InfluxDB!")
            
    except Exception as e:
        print(f"Error en el procesamiento del archivo: {e}")
        
    finally:
        # Limpieza del directorio temporal si se extrajo un zip
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python filter_smn.py <path_al_archivo>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    filter_smn_data(input_file)
