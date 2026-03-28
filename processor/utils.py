import os
import hashlib
import time
import urllib.request
import urllib.error
from datetime import datetime
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

# ==============================================================================
# CONFIGURACIÓN CENTRALIZADA (INFLUXDB)
# ==============================================================================
INFLUX_URL = os.environ.get("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN")
INFLUX_ORG = os.environ.get("INFLUX_ORG", "noaa_org")
INFLUX_BUCKET_TELEMETRY = os.environ.get("INFLUX_BUCKET_TELEMETRY", "telemetry")
INFLUX_BUCKET_PREDICTIONS = os.environ.get("INFLUX_BUCKET_PREDICTIONS", "predictions")
INFLUX_BUCKET_INDEXES = os.environ.get("INFLUX_BUCKET_INDEXES", "indexes")

def get_influx_client():
    """Retorna un cliente configurado de InfluxDB."""
    if not INFLUX_TOKEN:
        print("[ERROR] INFLUX_TOKEN no configurado en el entorno.")
        return None
    return InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)

# ==============================================================================
# GESTIÓN DE ARCHIVOS Y HASHING (DEDUPLICACIÓN)
# ==============================================================================
def get_file_hash(filepath):
    """Calcula el hash SHA256 de un archivo."""
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"[ERROR Utils] No se pudo hashear el archivo {filepath}: {e}")
        return None

def is_already_processed(file_hash, db_path):
    """Verifica si un hash ya existe en la base de datos de persistencia local."""
    if not file_hash or not os.path.exists(db_path):
        return False
    try:
        with open(db_path, "r") as f:
            processed_hashes = f.read().splitlines()
            return file_hash in processed_hashes
    except Exception as e:
        print(f"[ERROR Utils] Error leyendo DB de hashes {db_path}: {e}")
        return False

def mark_as_processed(file_hash, db_path):
    """Registra un hash como procesado."""
    if not file_hash:
        return
    try:
        with open(db_path, "a") as f:
            f.write(file_hash + "\n")
    except Exception as e:
        print(f"[ERROR Utils] No se pudo escribir en DB de hashes {db_path}: {e}")

# ==============================================================================
# COMUNICACIONES ROBUSTAS (RETRIES)
# ==============================================================================
def safe_download(url, dest_path, retries=3, backoff=2):
    """
    Descarga un archivo con reintentos automáticos (Exponential Backoff).
    """
    attempt = 0
    while attempt < retries:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
                
                # Validación básica para SMN (evitar 404 disfrazados de HTML)
                if b"404 Not Found" in content or b"<html" in content[:100].lower():
                    raise ValueError("El servidor devolvió contenido inválido (404/HTML).")
                
                with open(dest_path, 'wb') as out_file:
                    out_file.write(content)
                return True
        except Exception as e:
            attempt += 1
            wait_time = backoff ** attempt
            print(f"[REINTENTO {attempt}/{retries}] Error descargando {url}: {e}. Esperando {wait_time}s...")
            if attempt < retries:
                time.sleep(wait_time)
            else:
                print(f"[ERROR CRÍTICO] Se agotaron los reintentos para {url}.")
    return False
