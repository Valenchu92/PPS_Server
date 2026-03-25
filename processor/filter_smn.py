import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUX_URL = os.environ.get("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN")
INFLUX_ORG = os.environ.get("INFLUX_ORG")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET_TELEMETRY")

import hashlib
import zipfile
import glob
import shutil
import tempfile
import json

HASH_DB_PATH = "/raw_data/.processed_hashes"

def get_file_hash(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def is_already_processed(file_hash):
    if not os.path.exists(HASH_DB_PATH):
        return False
    with open(HASH_DB_PATH, "r") as f:
        processed_hashes = f.read().splitlines()
        return file_hash in processed_hashes

def mark_as_processed(file_hash):
    with open(HASH_DB_PATH, "a") as f:
        f.write(file_hash + "\n")

def filter_smn_data(filepath):
    """
    Lee un archivo de datos del SMN, extrae la fila de Río Cuarto y la envía a InfluxDB.
    Maneja tanto archivos .txt directos como archivos .zip que contengan txt.
    """
    print(f"[{datetime.now().isoformat()}] Procesando archivo SMN: {filepath}")
    
    # Check Hash to avoid duplicate processing
    file_hash = get_file_hash(filepath)
    if is_already_processed(file_hash):
        print(f"Skipping: File {os.path.basename(filepath)} was already processed (Hash match).")
        return

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
                            # Col 1: Fecha (ej: 15-marzo-2026), Col 2: Hora (ej: 11:00)
                            date_str = cols[1].strip()
                            time_str = cols[2].strip()
                            
                            # Mapeo de meses en español
                            meses = {
                                "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
                                "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
                            }
                            
                            try:
                                # Desglosar "15-marzo-2026"
                                d_parts = date_str.split('-')
                                if len(d_parts) == 3:
                                    day = int(d_parts[0])
                                    month = meses.get(d_parts[1].lower(), 1)
                                    year = int(d_parts[2])
                                    
                                    # Desglosar "11:00"
                                    h_parts = time_str.split(':')
                                    hour = int(h_parts[0])
                                    minute = int(h_parts[1])
                                    
                                    # Crear objeto datetime (Argentina es UTC-3, sumamos 3 para guardar como UTC real)
                                    observation_time = datetime(year, month, day, hour, minute) + timedelta(hours=3)
                                else:
                                    observation_time = datetime.utcnow()
                            except Exception as time_err:
                                print(f"Error parseando fecha/hora: {time_err}. Usando tiempo actual.")
                                observation_time = datetime.utcnow()

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
                                    "wind_direction": wind_direction,
                                    "time": observation_time
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
                .tag("source", "smn")
                .field("temperature", rio_cuarto_data["temperature"])
                .field("humidity", rio_cuarto_data["humidity"])
                .field("pressure", rio_cuarto_data["pressure"])
                .field("wind_speed", rio_cuarto_data["wind_speed"])
                .field("wind_direction", rio_cuarto_data["wind_direction"])
                .time(rio_cuarto_data["time"], WritePrecision.NS)
            )

            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
            print(f"-> ¡Datos reales de SMN {rio_cuarto_data['station']} [{rio_cuarto_data['temperature']}°C] para el {rio_cuarto_data['time']} guardados exitosamente!")
            
            # Guardar el JSON del clima para la página web
            try:
                latest_json_path = "/png-images/latest_weather.json"
                # Copiar el diccionario pero convertir el objeto datetime a string
                json_data = rio_cuarto_data.copy()
                json_data["time"] = json_data["time"].isoformat()
                json_data["source"] = "smn"
                with open(latest_json_path, 'w') as jf:
                    json.dump(json_data, jf)
                print(f"-> Archivo JSON actualizado en {latest_json_path}")
            except Exception as j_err:
                print(f"Error escribiendo latest_weather.json: {j_err}")

            mark_as_processed(file_hash)
            
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
