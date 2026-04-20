import sys
import os
import json
from datetime import datetime
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from utils import get_influx_client

def parse_owm_prediction(filepath):
    print(f"[{datetime.utcnow().isoformat()}] Procesando predicción OWM: {filepath}")

    if not os.path.exists(filepath):
        return

    with open(filepath, 'r') as f:
        data = json.load(f)

    predictions_list = data.get("list", [])
    if not predictions_list:
        print("Error: El JSON parseado no posee '.list' con mediciones.")
        return

    client = get_influx_client()
    pts = []
    front_data = []
    
    for item in predictions_list:
        dt = item.get("dt")
        obs_time = datetime.utcfromtimestamp(dt)
        temp = item.get("main", {}).get("temp")
        wind_speed = item.get("wind", {}).get("speed", 0) * 3.6  # kmh
        wind_dir = item.get("wind", {}).get("deg", 0)
        
        pop = item.get("pop", 0)
        rain_3h = item.get("rain", {}).get("3h", 0)

        if client:
            pt = Point("owm_5d_prediction") \
                .tag("location", "Rio Cuarto") \
                .field("temperature", float(temp)) \
                .field("wind_dir", float(wind_dir)) \
                .field("wind_speed", round(wind_speed, 2)) \
                .field("precipitation", float(rain_3h)) \
                .field("pop", float(pop)) \
                .time(obs_time, WritePrecision.NS)
            pts.append(pt)
            
        front_data.append({
            "time": obs_time.isoformat() + "Z", # Marca explícita
            "temperature": float(temp),
            "precipitation": float(rain_3h),
            "wind_speed": round(wind_speed, 2)
        })

    if client:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        bucket = os.environ.get("INFLUX_BUCKET_PREDICTIONS", "predictions")
        org = os.environ.get("INFLUX_ORG", "noaa_org")
        try:
            write_api.write(bucket=bucket, org=org, record=pts)
            print(f"-> {len(pts)} pronósticos 5d OWM ingestados en InfluxDB exitosamente.")
        except Exception as e:
            print(f"Error escribiendo en InfluxDB: {e}")
            
        client.close()

    try:
        latest_json_path = "/png-images/owm_prediction.json"
        with open(latest_json_path, 'w') as jf:
            json.dump({ "source": "owm", "generated_at": datetime.utcnow().isoformat(), "predictions": front_data }, jf)
        print(f"-> JSON de OWM 5D actualizado en {latest_json_path}")
    except Exception as e:
        print(f"Error exportando JSON frontal: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    parse_owm_prediction(sys.argv[1])
