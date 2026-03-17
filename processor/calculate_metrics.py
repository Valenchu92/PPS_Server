import os
import math
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Configuración de entornos
INFLUX_URL = os.environ.get("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN")
INFLUX_ORG = os.environ.get("INFLUX_ORG")
INFLUX_BUCKET_TELEMETRY = os.environ.get("INFLUX_BUCKET_TELEMETRY", "telemetry")
INFLUX_BUCKET_PREDICTIONS = os.environ.get("INFLUX_BUCKET_PREDICTIONS", "predictions")

def calculate_dew_point(T, H):
    """Fórmula de Magnus-Tetens para punto de rocío"""
    a = 17.27
    b = 237.7
    alpha = ((a * T) / (b + T)) + math.log(H/100.0)
    return (b * alpha) / (a - alpha)

def get_pressure_trend_text(delta):
    """Categoriza la tendencia de presión según el cambio en 3 horas"""
    if delta > 1.5: return "Subiendo rápidamente"
    if delta > 0.5: return "Subiendo"
    if delta < -1.5: return "Bajando rápidamente"
    if delta < -0.5: return "Bajando"
    return "Estable"

# Diccionario de pronósticos Zambretti (Traducción al español)
ZAMBRETTI_FORECASTS = {
    1:  "Buen tiempo persistente",
    2:  "Buen tiempo",
    3:  "Mejorando",
    4:  "Buen tiempo, volviéndose inestable",
    5:  "Buen tiempo, posibles chubascos",
    6:  "Favorable, mejorando",
    7:  "Favorable, posibles chubascos temprano",
    8:  "Favorable, chubascos más tarde",
    9:  "Chubascos temprano, mejorando",
    10: "Cambiante, mejorando",
    11: "Favorable, lluvias probables",
    12: "Algo inestable, aclarándose más tarde",
    13: "Inestable, probablemente mejorando",
    14: "Chubascos con intervalos soleados",
    15: "Chubascos, volviéndose más inestable",
    16: "Cambiante, algo de lluvia",
    17: "Inestable, cortos intervalos favorables",
    18: "Inestable, lluvia más tarde",
    19: "Inestable, algo de lluvia",
    20: "Mayormente muy inestable",
    21: "Lluvia ocasional, empeorando",
    22: "Lluvia por momentos, muy inestable",
    23: "Lluvia a intervalos frecuentes",
    24: "Lluvia, muy inestable",
    25: "Tormentoso, puede mejorar",
    26: "Tormentoso, mucha lluvia"
}

# Altitud para cálculos de presión
ALTITUDE = float(os.environ.get("METEOROLOGY_ALTITUDE", 441))

def get_slp(p, altitude=ALTITUDE):
    """Calcula la presión a nivel del mar aproximada"""
    return p + (altitude / 8.5)

def calculate_zambretti(p_slp, trend, wind_dir):
    """Algoritmo de Zambretti adaptado para Hemisferio Sur"""
    z = 0
    # Ajuste de viento para Hemisferio Sur (Invertimos lógica Norte/Sur)
    # N -> S, NE -> SE, etc.
    wind_adj = 0
    if "Norte" in wind_dir: wind_adj = -2
    elif "Sur" in wind_dir: wind_adj = 2
    elif "Este" in wind_dir: wind_adj = 1
    elif "Oeste" in wind_dir: wind_adj = -1

    if trend == "Bajando" or trend == "Bajando rápidamente":
        z = 130 - p_slp / 8.1
    elif trend == "Subiendo" or trend == "Subiendo rápidamente":
        z = 179 - p_slp / 12.9
    else: # Estable
        z = 138 - p_slp / 10.5
    
    # Ajuste por viento
    z += wind_adj
    
    # Limitar rango entre 1 y 26
    z_final = int(round(z))
    if z_final < 1: z_final = 1
    if z_final > 26: z_final = 26
    
    return z_final, ZAMBRETTI_FORECASTS.get(z_final, "Cambiante")

def calculate_metrics():
    print(f"[{datetime.now().isoformat()}] Iniciando motor de cálculo meteorológico...")
    
    if not INFLUX_TOKEN:
        print("Error: INFLUX_TOKEN no configurado.")
        return

    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()
    write_api = client.write_api(write_options=SYNCHRONOUS)

    # 1. Obtener últimos datos para Río Cuarto (ventana de 4 horas)
    query = f'''
    from(bucket: "{INFLUX_BUCKET_TELEMETRY}")
        |> range(start: -4h)
        |> filter(fn: (r) => r["_measurement"] == "weather_station")
        |> filter(fn: (r) => r["location"] == "Rio Cuarto")
        |> last()
    '''
    
    results = query_api.query(query)
    current_data = {}
    for table in results:
        for record in table.records:
            current_data[record.get_field()] = record.get_value()

    if not current_data:
        print("No se encontraron datos recientes en InfluxDB para calcular métricas.")
        return

    # 2. Obtener presión de hace 3 horas para la tendencia
    query_old = f'''
    from(bucket: "{INFLUX_BUCKET_TELEMETRY}")
        |> range(start: -4h, stop: -2h)
        |> filter(fn: (r) => r["_measurement"] == "weather_station")
        |> filter(fn: (r) => r["location"] == "Rio Cuarto")
        |> filter(fn: (r) => r["_field"] == "pressure")
        |> last()
    '''
    results_old = query_api.query(query_old)
    old_pressure = None
    for table in results_old:
        for record in table.records:
            old_pressure = record.get_value()

    # --- CÁLCULOS ---
    
    T = current_data.get("temperature")
    H = current_data.get("humidity")
    P = current_data.get("pressure")
    W_DIR = current_data.get("wind_direction", "Calma")
    
    # a. Punto de Rocío
    dew_point = None
    if T is not None and H is not None:
        dew_point = calculate_dew_point(T, H)
        print(f"-> Punto de Rocío calculado: {dew_point:.2f}°C")

    # b. Tendencia de Presión
    pressure_delta = 0.0
    trend_text = "Estable"
    if P is not None and old_pressure is not None:
        pressure_delta = P - old_pressure
        trend_text = get_pressure_trend_text(pressure_delta)
        print(f"-> Tendencia de Presión (3h): {pressure_delta:.2f} hPa ({trend_text})")

    # c. Algoritmo Zambretti
    p_slp = get_slp(P) if P else 1013.25
    z_code, z_phrase = calculate_zambretti(p_slp, trend_text, W_DIR)
    print(f"-> Pronóstico Zambretti: {z_phrase} (Code: {z_code})")

    # --- GUARDAR RESULTADOS ---
    
    point = Point("meteorological_indexes") \
        .tag("location", "Rio Cuarto") \
        .field("dew_point", float(dew_point) if dew_point else 0.0) \
        .field("pressure_trend_value", float(pressure_delta)) \
        .field("pressure_trend_text", trend_text) \
        .field("zambretti_code", z_code) \
        .field("zambretti_phrase", z_phrase) \
        .time(datetime.utcnow(), WritePrecision.NS)

    try:
        write_api.write(bucket=INFLUX_BUCKET_PREDICTIONS, org=INFLUX_ORG, record=point)
        print(f"-> Índices guardados exitosamente en {INFLUX_BUCKET_PREDICTIONS}")
    except Exception as e:
        print(f"Error al guardar predicciones: {e}")

    client.close()

if __name__ == "__main__":
    calculate_metrics()
