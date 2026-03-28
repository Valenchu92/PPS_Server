#!/bin/bash
echo "Starting NOAA/SMN Central Processor Engine (Robust Mode)..."

# --- Manejo de Señales ---
cleanup() {
    echo "Terminating all background processes..."
    kill $(jobs -p)
    exit 0
}
trap cleanup SIGINT SIGTERM

# --- Función para Tareas Periódicas ---
run_periodic() {
    local script=$1
    local interval=$2
    local name=$3
    echo "[Init] Setting up $name every $interval seconds."
    while true; do
        python3 /app/"$script"
        sleep "$interval"
    done
}

# --- Tareas Periódicas (Segundo Plano) ---
run_periodic "download_cloud.py"  10800 "Rclone Cloud Sync" &
run_periodic "calculate_metrics.py" 3600 "Meteorology Engine" &
run_periodic "fetch_goes.py"        600 "GOES Fetcher" &
run_periodic "fetch_smn.py"        1200 "SMN Fetcher" &
run_periodic "fetch_owm.py"        1800 "OWM Fetcher" &

echo "Watches established. Listening for new files in /raw_images and /raw_data..."

# Loop principal con inotifywait
# Si inotifywait muere, el contenedor se detendrá (correcto para Docker)
inotifywait -m -e close_write --format "%w%f" /raw_images /raw_data | while read NEWFILE
do
    echo "-----------------------------------------"
    echo "[$(date -u)] Event: $NEWFILE"
    
    if [[ "$NEWFILE" == /raw_images/* ]]; then
        if [[ "$NEWFILE" == *.jpg || "$NEWFILE" == *.png ]]; then
            echo "-> Dispatching GOES Crop..."
            python3 /app/crop_goes.py "$NEWFILE" &
            
            # Limpieza: Mantener solo las últimas 5 imágenes crudas
            ls -1tr /raw_images/*.jpg /raw_images/*.png 2>/dev/null | head -n -5 | xargs -r rm
        fi
    elif [[ "$NEWFILE" == /raw_data/* ]]; then
        if [[ "$NEWFILE" == *.txt || "$NEWFILE" == *.zip ]]; then
            echo "-> Dispatching SMN Filter..."
            python3 /app/filter_smn.py "$NEWFILE" &
        elif [[ "$NEWFILE" == *.json ]]; then
            echo "-> Dispatching OWM Filter..."
            python3 /app/filter_owm.py "$NEWFILE" &
        fi
    fi
done
