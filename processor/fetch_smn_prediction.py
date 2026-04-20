import os
from datetime import datetime
from utils import safe_download

def fetch_smn_prediction():
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    timestamp_str = now.strftime("%Y%m%d_%H%M")
    
    base_dir = "/raw_data"
    os.makedirs(base_dir, exist_ok=True)
    
    url = f"https://ssl.smn.gob.ar/dpd/descarga_opendata.php?file=pron5d/pron{date_str}.txt"
    filename = f"{base_dir}/smn_pred_{timestamp_str}.txt"
    
    print(f"[{datetime.now()}] Iniciando descarga de pronóstico 5 días SMN...")
    
    success = safe_download(url, filename, retries=5)
    
    if success:
        print(f"[{datetime.now()}] Pronóstico SMN guardado en {filename}")
    else:
        print(f"[{datetime.now()}] ERROR: SMN no retorna datos de predicciones.")

if __name__ == "__main__":
    fetch_smn_prediction()
