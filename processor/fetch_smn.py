import os
from datetime import datetime
import urllib.request
import urllib.error

def fetch_smn():
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    timestamp_str = now.strftime("%Y%m%d_%H%M")
    
    base_dir = "/raw_data"
    os.makedirs(base_dir, exist_ok=True)
    
    url = f"https://ssl.smn.gob.ar/dpd/descarga_opendata.php?file=observaciones/tiepre{date_str}.txt"
    filename = f"{base_dir}/smn_data_{timestamp_str}.txt"
    
    print(f"[{datetime.now()}] Descargando datos SMN para la fecha {date_str}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
            # Validamos si descargó un html en vez del txt (que a veces el SMN falla devolviendo 404 disfrazado)
            if b"404 Not Found" in content or b"<html" in content[:100].lower():
                 print(f"[{datetime.now()}] SMN devolvió página de error en lugar del archivo esperado.")
                 return
            
            with open(filename, 'wb') as out_file:
                out_file.write(content)
        print(f"[{datetime.now()}] Datos SMN guardados en {filename}")
    except urllib.error.URLError as e:
        print(f"[{datetime.now()}] Error descargando datos de SMN: {e}")
    except Exception as e:
        print(f"[{datetime.now()}] Ocurrió un error general con SMN: {e}")

if __name__ == "__main__":
    fetch_smn()
