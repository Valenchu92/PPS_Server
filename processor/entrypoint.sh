#!/bin/bash

# Configuration
WAV_INPUT_DIR="${WAV_INPUT_DIR:-/input}"
PNG_OUTPUT_DIR="${PNG_OUTPUT_DIR:-/output}"
MAX_AGE_DAYS="${MAX_AGE_DAYS:-7}"
CLEANUP_INTERVAL_MIN="${CLEANUP_INTERVAL_MIN:-60}"

echo "$(date) - Starting NOAA processor..."

# Cleanup function
cleanup() {
    echo "$(date) - Running cleanup routine..."
    if [ -d "$WAV_INPUT_DIR" ]; then
        find "$WAV_INPUT_DIR" -maxdepth 1 -name "*.wav" -type f -mtime +"$MAX_AGE_DAYS" -exec rm -v {} \;
        echo "$(date) - Cleanup routine configured for files older than $MAX_AGE_DAYS days."
    else
        echo "$(date) - Warning: $WAV_INPUT_DIR does not exist."
    fi
}

# Periodic cleanup loop
periodic_cleanup() {
    while true; do
        sleep $(( CLEANUP_INTERVAL_MIN * 60 ))
        cleanup
    done
}

# Immich notification
immich_notify() {
    echo "$(date) - Notifying Immich to scan library..."
    if [ -f "/etc/immich/token" ]; then
        TOKEN=$(cat /etc/immich/token)
        
        # Fetch all library IDs (ignoring errors if any)
        LIBRARY_IDS=$(curl -s -X GET "http://immich-server:2283/api/libraries" \
             -H "Accept: application/json" \
             -H "x-api-key: $TOKEN" | jq -r '.[].id' 2>/dev/null || true)
             
        if [ -z "$LIBRARY_IDS" ]; then
            echo "$(date) - Could not fetch library IDs from Immich. Check token."
            return
        fi

        for ID in $LIBRARY_IDS; do
            echo "$(date) - Triggering scan and offline removal for library: $ID"
            curl -s -X POST "http://immich-server:2283/api/libraries/$ID/scan" \
                 -H "Accept: application/json" \
                 -H "x-api-key: $TOKEN" > /dev/null
                 
            curl -s -X POST "http://immich-server:2283/api/libraries/$ID/removeOffline" \
                 -H "Accept: application/json" \
                 -H "x-api-key: $TOKEN" > /dev/null
        done
        echo "$(date) - Immich scan triggered."
    else
        echo "$(date) - Immich token not found at /etc/immich/token, skipping notification."
    fi
}

# Process a single WAV file
process_wav() {
    local wav_file="$1"
    local filename=$(basename -- "$wav_file")
    local name="${filename%.*}"
    local png_file="${PNG_OUTPUT_DIR}/${name}.png"

    if [ -f "$png_file" ]; then
        echo "$(date) - File $png_file already exists, skipping."
        return
    fi
    
    echo "$(date) - Processing $wav_file -> $png_file"
    noaa-apt "$wav_file" -o "$png_file"
    if [ $? -eq 0 ]; then
        echo "$(date) - Successfully processed $wav_file"
        immich_notify
    else
        echo "$(date) - Error processing $wav_file"
    fi
}

# Run initial cleanup
cleanup

# Start periodic cleanup in background
periodic_cleanup &
CLEANUP_PID=$!

# Trap termination signals
trap "echo 'Shutting down...'; kill $CLEANUP_PID; exit 0" SIGINT SIGTERM

echo "$(date) - Monitoring $WAV_INPUT_DIR for new .wav files and $PNG_OUTPUT_DIR for deletions..."

# Monitor WAV input for new files AND raw_images output for creations
inotifywait -m -r -e close_write -e moved_to -e delete --format "%w%e %f" "$WAV_INPUT_DIR" "$PNG_OUTPUT_DIR" "/raw_images" | while read -r DIR_EVENT FILE
do
    # Process new WAV
    if [[ "$DIR_EVENT" == *"/input/"* ]] && [[ "$FILE" == *.wav ]]; then
        sleep 1
        process_wav "$WAV_INPUT_DIR/$FILE"
    
    # Process new RAW JPG from n8n
    elif [[ "$DIR_EVENT" == *"/raw_images/"* ]] && [[ "$DIR_EVENT" == *"CLOSE_WRITE"* ]] && [[ "$FILE" == *.jpg ]]; then
        echo "$(date) - Detected new raw image from n8n: $FILE"
        sleep 2 # Dar tiempo por las dudas a que termine de escribir el disco
        
        # Generar PNG de salida basado en el nombre original de n8n
        # Formato original n8n: goes19_ssa_geocolor_20260310_2110.jpg
        filename=$(basename -- "$FILE")
        name="${filename%.*}"
        png_output="${PNG_OUTPUT_DIR}/${name}_cordoba.png"
        
        echo "$(date) - Cropping Cordoba..."
        python3 /crop_cordoba.py "/raw_images/$FILE" "$png_output"
        
        if [ $? -eq 0 ]; then
            echo "$(date) - Sucessfully cropped $FILE to $png_output"
            
            # Limpiar versiones enteras de /raw_images dejando solo las 5 mas nuevas
            echo "$(date) - Eliminando imagenes antiguas de /raw_images..."
            cd /raw_images
            ls -t *.jpg | tail -n +6 | xargs -I {} rm -- {} 2>/dev/null || true
            cd - > /dev/null
            
            immich_notify
        else
            echo "$(date) - Failed to crop $FILE"
        fi

    # Notify Immich on other changes in png-output
    elif [[ "$DIR_EVENT" == *"/output/"* ]]; then
        if [[ "$DIR_EVENT" == *"DELETE"* ]] || [[ "$DIR_EVENT" == *"CLOSE_WRITE"* ]] || [[ "$DIR_EVENT" == *"MOVED_TO"* ]]; then
            # Ignore temporary files
            if [[ "$FILE" != .* ]]; then
                # Debounce to avoid spamming the API (sleep briefly and then notify)
                echo "$(date) - Detected change in output: $FILE ($DIR_EVENT). Notifying Immich."
                immich_notify
            fi
        fi
    fi
done
