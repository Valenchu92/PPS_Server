import sys
import os
import re
import json
from datetime import datetime, timedelta
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from utils import get_influx_client, get_file_hash, is_already_processed, mark_as_processed

HASH_DB_PATH = "/raw_data/.processed_hashes"

def parse_smn_prediction(filepath):
    print(f"[{datetime.now().isoformat()}] Procesando predicción SMN: {filepath}")
    
    file_hash = get_file_hash(filepath)
    if is_already_processed(file_hash, HASH_DB_PATH):
        print(f"Skipping: File {os.path.basename(filepath)} was already processed.")
        return

    meses = { "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12 }
    
    predictions = []
    found_rio_cuarto = False
    skip_headers = 0
    
    with open(filepath, 'r', encoding='latin1') as f:
        for line in f:
            if "RIO_CUARTO_AERO" in line:
                found_rio_cuarto = True
                skip_headers = 4
                continue
                
            if found_rio_cuarto:
                if skip_headers > 0:
                    skip_headers -= 1
                    continue
                    
                if "=====" in line or line.strip() == "" or "AERO" in line:
                    break
                
                # Regex for: 14/ABR/2026 00Hs.        16.6        21 |  18         0.0 
                m = re.match(r'\s*(\d{2})/([A-Z]{3})/(\d{4})\s+(\d{2})Hs\.\s+([\d\.-]+)\s+(\d+)\s*\|\s*(\d+)\s+([\d\.-]+)', line)
                if m:
                    day, month_str, year, hour, temp, wind_dir, wind_speed, precip = m.groups()
                    month = meses.get(month_str, 1)
                    # SMN gives local time. Convert to UTC.
                    target_time_local = datetime(int(year), int(month), int(day), int(hour), 0)
                    target_time_utc = target_time_local + timedelta(hours=3)
                    
                    predictions.append({
                        "time_utc": target_time_utc,
                        "time_local": target_time_local.isoformat(),
                        "temperature": float(temp),
                        "wind_dir": int(wind_dir),
                        "wind_speed": float(wind_speed),
                        "precipitation": float(precip)
                    })
                    
    if not predictions:
        print("Métrica abortada: RIO_CUARTO_AERO no encontrado o formato inválido.")
        return

    client = get_influx_client()
    if client:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        bucket = os.environ.get("INFLUX_BUCKET_PREDICTIONS", "predictions")
        org = os.environ.get("INFLUX_ORG", "noaa_org")

        pts = []
        for p in predictions:
            pt = Point("smn_5d_prediction") \
                .tag("location", "Rio Cuarto") \
                .field("temperature", p["temperature"]) \
                .field("wind_dir", p["wind_dir"]) \
                .field("wind_speed", p["wind_speed"]) \
                .field("precipitation", p["precipitation"]) \
                .time(p["time_utc"], WritePrecision.NS)
            pts.append(pt)

        try:
            write_api.write(bucket=bucket, org=org, record=pts)
            print(f"-> {len(pts)} pronósticos 5d SMN ingestados en InfluxDB exitosamente.")
        except Exception as e:
            print(f"Error escribiendo en InfluxDB: {e}")
        
        client.close()

    # JSON export for Gallery
    try:
        latest_json_path = "/png-images/smn_prediction.json"
        
        # Export all predictions (full 5-day forecast, no 24h cap)
        front_data = []
        for p in predictions:
            front_data.append({
                "time": p["time_local"],
                "temperature": p["temperature"],
                "precipitation": p["precipitation"],
                "wind_speed": p["wind_speed"]
            })
            
        with open(latest_json_path, 'w') as jf:
            json.dump({ "source": "smn", "generated_at": datetime.utcnow().isoformat(), "predictions": front_data }, jf)
        print(f"-> JSON de SMN 5D actualizado en {latest_json_path}")
    except Exception as e:
        print(f"Error exportando JSON frontal: {e}")

    mark_as_processed(file_hash, HASH_DB_PATH)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    parse_smn_prediction(sys.argv[1])
