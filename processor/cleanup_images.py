import os
import time

def cleanup_old_images(directory, days=7):
    """Elimina archivos .png más antiguos que 'days' días en el directorio indicado."""
    print(f"[Cleanup] Buscando imágenes con más de {days} días en {directory}...")
    if not os.path.exists(directory):
        print(f"[Cleanup] El directorio {directory} no existe.")
        return

    now = time.time()
    cutoff = now - (days * 86400)
    count = 0

    for root_dir, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".png"):
                filepath = os.path.join(root_dir, filename)
                try:
                    if os.path.isfile(filepath):
                        file_mtime = os.path.getmtime(filepath)
                        if file_mtime < cutoff:
                            os.remove(filepath)
                            count += 1
                except Exception as e:
                    print(f"[Cleanup] Error al procesar o borrar {filename}: {e}")
    
    print(f"[Cleanup] Tarea finalizada. Se eliminaron {count} imágenes.")

if __name__ == "__main__":
    # Asegurar que se ejecuta la limpieza en png-images
    cleanup_old_images("/png-images", days=7)
    
    # Opcional: También podríamos limpiar png-NOAA si hace falta
    # cleanup_old_images("/png-NOAA", days=7)
