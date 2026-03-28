import os
from datetime import datetime
from utils import safe_download

def download_goes():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    base_dir = "/raw_images"
    os.makedirs(base_dir, exist_ok=True)
    
    images = {
        "geocolor": "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR/ssa/GEOCOLOR/7200x4320.jpg",
        "airmass": "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR/ssa/AirMass/7200x4320.jpg",
        "sandwich": "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR/ssa/Sandwich/7200x4320.jpg"
    }
    
    for img_type, url in images.items():
        filename = f"{base_dir}/goes_{img_type}_{timestamp}.jpg"
        print(f"[{datetime.now()}] Iniciando descarga de GOES {img_type}...")
        
        success = safe_download(url, filename, retries=5)
        
        if success:
            print(f"[{datetime.now()}] Imagen {img_type} guardada exitosamente en {filename}")
        else:
            print(f"[{datetime.now()}] ERROR: Falló la obtención de {img_type} tras varios reintentos.")

if __name__ == "__main__":
    download_goes()
