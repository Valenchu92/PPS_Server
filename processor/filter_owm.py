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
        
        # Extraer estado del tiempo (descripción e icono)
        weather_info = data.get("weather", [{}])[0]
        description = weather_info.get("description", "N/A")
        icon_code = weather_info.get("icon", "")

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
        
        # Guardar el JSON del clima para la página web
        try:
            latest_json_path = "/png-images/latest_weather.json"
            
            # Lógica de Prioridad: No sobrescribir SMN si es reciente (< 70 min)
            should_update = True
            if os.path.exists(latest_json_path):
                try:
                    with open(latest_json_path, 'r') as jf:
                        existing_data = json.load(jf)
                    
                    if existing_data.get("source") == "smn":
                        last_time = datetime.fromisoformat(existing_data.get("time"))
                        diff = datetime.now() - last_time
                        # Si el dato del SMN tiene menos de 70 min, lo respetamos
                        if diff.total_seconds() < 4200: # 70 minutos
                            print(f"-> Prioridad SMN: El dato actual es oficial y reciente ({int(diff.total_seconds()/60)} min). No se sobrescribe con OWM.")
                            should_update = False
                except Exception as e:
                    print(f"Advertencia leyendo JSON existente: {e}")

            if should_update:
                weather_data = {
                    "station": "Rio Cuarto",
                    "temperature": float(temp),
                    "humidity": float(humidity) if humidity else 0.0,
                    "pressure": float(pressure) if pressure else 0.0,
                    "wind_speed": float(wind_speed) if wind_speed else 0.0,
                    "wind_direction": str(wind_deg) if wind_deg else "0",
                    "description": description,
                    "icon": icon_code,
                    "time": obs_time.isoformat(),
                    "source": "owm"
                }
                with open(latest_json_path, 'w') as jf:
                    json.dump(weather_data, jf)
                print(f"-> Archivo JSON actualizado en {latest_json_path} (Fuente: OWM)")
            
        except Exception as j_err:
            print(f"Error escribiendo latest_weather.json: {j_err}")
            
        # Siempre intentar actualizar el historial (él mismo decide si sobreescribir o no)
        update_weather_history(data, obs_time)
            
        client.close()

    except Exception as e:
        print(f"Error procesando OWM: {e}")

def update_weather_history(new_data, obs_time):
    """
    Mantiene un historial de los últimos 12 registros en weather_history.json.
    Lógica Fallback: Solo agrega si NO existe un dato del SMN para esa hora.
    """
    history_path = "/png-images/weather_history.json"
    history = []
    
    if os.path.exists(history_path):
        try:
            with open(history_path, 'r') as f:
                history = json.load(f)
        except:
            history = []

    new_time_str = obs_time.isoformat()
    
    # Buscar si ya existe la misma hora
    found_index = -1
    for i, entry in enumerate(history):
        if entry["time"] == new_time_str:
            found_index = i
            break
    
    # Si existe y es del SMN, NO hacer nada (respetar prioridad)
    if found_index != -1 and history[found_index].get("source") == "smn":
        print(f"-> Historial: Ya existe dato oficial (SMN) para {new_time_str}. Omitiendo OWM.")
        return

    record = {
        "time": new_time_str,
        "temperature": float(new_data.get("main", {}).get("temp")),
        "humidity": float(new_data.get("main", {}).get("humidity", 0)),
        "pressure": float(new_data.get("main", {}).get("pressure", 0)),
        "wind_speed": float(new_data.get("wind", {}).get("speed", 0)),
        "description": new_data.get("weather", [{}])[0].get("description", "N/A"),
        "icon": new_data.get("weather", [{}])[0].get("icon", ""),
        "source": "owm"
    }

    if found_index != -1:
        history[found_index] = record
    else:
        history.append(record)

    # Ordenar y limitar
    history.sort(key=lambda x: x["time"])
    history = history[-12:]

    with open(history_path, 'w') as f:
        json.dump(history, f)
    print(f"-> Historial actualizado en {history_path} (Fuente: OWM)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python filter_owm.py <path_al_json>")
        sys.exit(1)
    
    process_owm_data(sys.argv[1])
