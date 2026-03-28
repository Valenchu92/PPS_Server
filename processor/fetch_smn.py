import os
from datetime import datetime
from utils import safe_download

def fetch_smn():
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    timestamp_str = now.strftime("%Y%m%d_%H%M")
    
    base_dir = "/raw_data"
    os.makedirs(base_dir, exist_ok=True)
    
    url = f"https://ssl.smn.gob.ar/dpd/descarga_opendata.php?file=observaciones/tiepre{date_str}.txt"
    filename = f"{base_dir}/smn_data_{timestamp_str}.txt"
    
    print(f"[{datetime.now()}] Iniciando descarga de datos SMN...")
    
    success = safe_download(url, filename, retries=5)
    
    if success:
        print(f"[{datetime.now()}] Datos SMN guardados exitosamente en {filename}")
    else:
        print(f"[{datetime.now()}] ERROR: El SMN no está devolviendo datos válidos en este momento.")

if __name__ == "__main__":
    fetch_smn()
