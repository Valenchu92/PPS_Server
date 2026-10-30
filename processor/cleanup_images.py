import os
import re
from datetime import datetime, timedelta

TIMESTAMP_PATTERN = re.compile(r"(\d{8})_(\d{6})")

def get_file_datetime(filename, filepath):
    """
    Intenta extraer la fecha/hora desde el nombre del archivo (formato YYYYMMDD_HHMMSS).
    Si no coincide con el patrón, recurre a la fecha de modificación del archivo (mtime).
    """
    match = TIMESTAMP_PATTERN.search(filename)
    if match:
        try:
            date_str = f"{match.group(1)}_{match.group(2)}"
            return datetime.strptime(date_str, "%Y%m%d_%H%M%S")
        except ValueError:
            pass

    # Fallback a fecha de modificación del filesystem
    return datetime.fromtimestamp(os.path.getmtime(filepath))

def cleanup_old_images(directory, days=7):
    """Elimina archivos .png con antigüedad mayor a 'days' días en el directorio indicado."""
    print(f"[Cleanup] Buscando imágenes con más de {days} días en {directory}...")
    if not os.path.exists(directory):
        print(f"[Cleanup] El directorio {directory} no existe.")
        return

    cutoff_date = datetime.now() - timedelta(days=days)
    count = 0

    for root_dir, dirs, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith(".png"):
                filepath = os.path.join(root_dir, filename)
                try:
                    if os.path.isfile(filepath):
                        file_dt = get_file_datetime(filename, filepath)
                        if file_dt < cutoff_date:
                            os.remove(filepath)
                            count += 1
                except Exception as e:
                    print(f"[Cleanup] Error al procesar o borrar {filename}: {e}")

    print(f"[Cleanup] Tarea finalizada. Se eliminaron {count} imágenes.")

if __name__ == "__main__":
    cleanup_old_images("/png-images", days=7)

