import sys
import os
import json
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Configuración de InfluxDB
INFLUX_URL = os.environ.get("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN")
INFLUX_ORG = os.environ.get("INFLUX_ORG")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET_TELEMETRY", "telemetry")

def process_owm_data(json_path):
    """
    Lee un JSON de OpenWeatherMap y guarda los datos en InfluxDB.
    """
    if not os.path.exists(json_path):
        print(f"Error: El archivo {json_path} no existe.")
        return

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        # n8n suele enviar una lista [ {...} ]
        if isinstance(data, list):
            data = data[0]

        # Extraer datos básicos
        temp = data.get("main", {}).get("temp")
        humidity = data.get("main", {}).get("humidity")
        pressure = data.get("main", {}).get("pressure")
        wind_speed = data.get("wind", {}).get("speed")
        wind_deg = data.get("wind", {}).get("deg")
        dt = data.get("dt") # Timestamp UTC (Unix)

        if temp is None:
            print("Error: El JSON de OWM no contiene datos de temperatura validos.")
            return

        # Conectar a InfluxDB
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)

        # Usamos utcfromtimestamp para asegurar que la hora de OWM se guarde en UTC real
        # InfluxDB asume UTC, y Grafana se encarga de mostrarla en hora local (GMT-3)
        obs_time = datetime.utcfromtimestamp(dt)

        point = (
            Point("weather_station")
            .tag("location", "Rio Cuarto")
            .tag("source", "owm")
            .field("temperature", float(temp))
            .field("humidity", float(humidity) if humidity else 0.0)
            .field("pressure", float(pressure) if pressure else 0.0)
            .field("wind_speed", float(wind_speed) if wind_speed else 0.0)
            .field("wind_deg", float(wind_deg) if wind_deg else 0.0)
            .time(obs_time, WritePrecision.NS)
        )

        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        print(f"-> ¡Datos de OpenWeatherMap [{temp}°C] para el {obs_time} UTC guardados exitosamente!")
        client.close()

    except Exception as e:
        print(f"Error procesando OWM: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python filter_owm.py <path_al_json>")
        sys.exit(1)
    
    process_owm_data(sys.argv[1])
