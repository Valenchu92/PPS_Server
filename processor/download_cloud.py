import os
import subprocess
import datetime

def main():
    print(f"[{datetime.datetime.now().isoformat()}] Starting Cloud Downloader sync...")
    # Sincroniza desde el Google Drive (remote 'gdrive:') a la carpeta local de imagenes procesadas
    # Requiere que el archivo rclone.conf este configurado
    try:
        # Verifica si el archivo de config existe (fue mapeado desde host)
        if not os.path.exists("/configs/rclone.conf"):
            print("ERROR: /configs/rclone.conf no encontrado. Configura Rclone primero.")
            return

        cmd = [
            "rclone", "sync", 
            "--config", "/configs/rclone.conf",
            "gdrive:/pps_server/images", 
            "/png-images",
            "-v"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("Sync successful.")
        else:
            print(f"Rclone sync failed: {result.stderr}")
            
    except Exception as e:
        print(f"Error executing rclone: {e}")

if __name__ == "__main__":
    main()
