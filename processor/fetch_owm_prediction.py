import os
from datetime import datetime
import urllib.request
import urllib.parse
import json

def fetch_owm_prediction():
    city = os.environ.get("OPENWEATHERMAP_CITY", "Rio Cuarto,AR")
    api_key = os.environ.get("OPENWEATHERMAP_API_KEY", "")
    
    if not api_key:
        print(f"[{datetime.now()}] OWM Pred Error: OPENWEATHERMAP_API_KEY no encontrada.")
        return
        
    encoded_city = urllib.parse.quote(city)
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={encoded_city}&appid={api_key}&units=metric&lang=es"
    
    base_dir = "/raw_data"
    os.makedirs(base_dir, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{base_dir}/owm_pred_{timestamp_str}.json"
    
    print(f"[{datetime.now()}] Descargando pronóstico aéreo 5 días OWM para {city}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            with open(filename, 'w', encoding='utf-8') as out_file:
                json.dump(data, out_file, ensure_ascii=False, indent=4)
        print(f"[{datetime.now()}] Predicción OWM guardada en {filename}")
    except Exception as e:
        print(f"[{datetime.now()}] Ocurrió un error con OWM Pred: {e}")

if __name__ == "__main__":
    fetch_owm_prediction()
