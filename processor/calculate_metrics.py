import os
from datetime import datetime

# from influxdb_client import InfluxDBClient

INFLUX_URL = os.environ.get("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN")
INFLUX_ORG = os.environ.get("INFLUX_ORG")
INFLUX_BUCKET_PREDICTIONS = os.environ.get("INFLUX_BUCKET_PREDICTIONS")

def calculate_metrics():
    print(f"[{datetime.now().isoformat()}] Calculando métricas y pronósticos climáticos periódicos...")
    
    # "La cuarta y última, deberá hacer cálculos en base a todos los datos obtenidos 
    # y determinar pronósticos meteorológicos, por ahora lo vamos a dejar en blanco 
    # porque no tengo las ecuaciones."
    
    # TODO: Recuperar de INFLUX_BUCKET_TELEMETRY o de INFLUX_BUCKET_INDEXES
    # TODO: Aplicar las ecuaciones
    # TODO: Escribir resultados en INFLUX_BUCKET_PREDICTIONS
    
    # Placeholder
    pass

if __name__ == "__main__":
    calculate_metrics()
