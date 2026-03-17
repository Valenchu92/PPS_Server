#!/bin/bash
echo "Starting NOAA/SMN Central Processor Engine..."

# Ensure directories exist via volume mapping
mkdir -p /raw_images
mkdir -p /raw_data
mkdir -p /png-images
mkdir -p /png-NOAA

echo "Setting up CRON tasks..."
# 1. Download Cloud (Rclone) every 3 hours
echo "PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" > /etc/cron.d/processor_crons
echo "0 */3 * * * python3 /app/download_cloud.py >> /proc/1/fd/1 2>&1" >> /etc/cron.d/processor_crons
echo "0 * * * * python3 /app/calculate_metrics.py >> /proc/1/fd/1 2>&1" >> /etc/cron.d/processor_crons

chmod 0644 /etc/cron.d/processor_crons
crontab /etc/cron.d/processor_crons
service cron start

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
