import os
from datetime import datetime
import urllib.request
import urllib.error

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
        print(f"[{datetime.now()}] Descargando GOES {img_type}...")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response, open(filename, 'wb') as out_file:
                out_file.write(response.read())
            print(f"[{datetime.now()}] Imagen {img_type} guardada en {filename}")
        except urllib.error.URLError as e:
            print(f"[{datetime.now()}] Error descargando {img_type}: {e}")
        except Exception as e:
            print(f"[{datetime.now()}] Ocurrió un error general con {img_type}: {e}")

if __name__ == "__main__":
    download_goes()
