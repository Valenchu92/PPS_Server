import os
from datetime import datetime
import urllib.request
import urllib.parse
import urllib.error
import json

def fetch_owm():
    city = os.environ.get("OPENWEATHERMAP_CITY", "Rio Cuarto,AR")
    api_key = os.environ.get("OPENWEATHERMAP_API_KEY", "")
    
    if not api_key:
        print(f"[{datetime.now()}] OWM Error: OPENWEATHERMAP_API_KEY no encontrada.")
        return
        
    encoded_city = urllib.parse.quote(city)
    url = f"https://api.openweathermap.org/data/2.5/weather?q={encoded_city}&appid={api_key}&units=metric&lang=es"
    
    base_dir = "/raw_data"
    os.makedirs(base_dir, exist_ok=True)
    filename = f"{base_dir}/owm_current.json"
    
    print(f"[{datetime.now()}] Descargando clima de OWM para {city}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            with open(filename, 'w', encoding='utf-8') as out_file:
                json.dump(data, out_file, ensure_ascii=False, indent=4)
        print(f"[{datetime.now()}] Clima guardado en {filename}")
    except urllib.error.URLError as e:
        print(f"[{datetime.now()}] Error descargando datos de OWM: {e}")
        if hasattr(e, 'read'):
            print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"[{datetime.now()}] Ocurrió un error general con OWM: {e}")

if __name__ == "__main__":
    fetch_owm()
