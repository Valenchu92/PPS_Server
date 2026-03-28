#!/bin/bash
echo "Starting NOAA/SMN Central Processor Engine..."

# Ensure directories exist via volume mapping
mkdir -p /raw_images
mkdir -p /raw_data
mkdir -p /png-images
mkdir -p /png-NOAA

echo "Setting up periodic tasks..."
# Tareas originales
(while true; do python3 /app/download_cloud.py; sleep 10800; done) &
(while true; do python3 /app/calculate_metrics.py; sleep 3600; done) &

# Nuevos Fetchers Nativos 
(while true; do python3 /app/fetch_goes.py; sleep 600; done) &
(while true; do python3 /app/fetch_smn.py; sleep 1200; done) &
(while true; do python3 /app/fetch_owm.py; sleep 1800; done) &


echo "Watches established. Listening for new files..."
# Loop to watch for new files in BOTH directories concurrently
# We use inotifywait in monitor mode to trigger Python logic when new files arrive
inotifywait -m -e close_write --format "%w%f" /raw_images /raw_data | while read NEWFILE
do
    echo "========================================="
    echo "[$(date -u)] Detected modified file: $NEWFILE"
    
    if [[ "$NEWFILE" == /raw_images/* ]]; then
        if [[ "$NEWFILE" == *.jpg || "$NEWFILE" == *.png ]]; then
            echo "-> Dispatching GOES Crop worker..."
            python3 /app/crop_goes.py "$NEWFILE" &
            
            # Keep only the last 5 raw images to save space
            ls -1tr /raw_images/*.jpg /raw_images/*.png 2>/dev/null | head -n -5 | xargs -r rm
        fi
    elif [[ "$NEWFILE" == /raw_data/* ]]; then
        if [[ "$NEWFILE" == *.txt || "$NEWFILE" == *.zip ]]; then
            echo "-> Dispatching SMN Filter worker..."
            python3 /app/filter_smn.py "$NEWFILE" &
        elif [[ "$NEWFILE" == *.json ]]; then
            echo "-> Dispatching OWM Filter worker..."
            python3 /app/filter_owm.py "$NEWFILE" &
        fi
    else
        echo "Ignored: Pattern not recognized."
    fi
done
