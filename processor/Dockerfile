FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    inotify-tools \
    bash \
    procps \
    cron \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Rclone
RUN curl -O https://downloads.rclone.org/v1.65.2/rclone-v1.65.2-linux-amd64.zip && \
    unzip rclone-v1.65.2-linux-amd64.zip && \
    cp rclone-v1.65.2-linux-amd64/rclone /usr/bin/ && \
    chmod 755 /usr/bin/rclone && \
    rm -rf rclone-v1.65.2-linux-amd64 rclone-v1.65.2-linux-amd64.zip

# Install python dependencies 
RUN pip install --no-cache-dir \
    numpy \
    opencv-python-headless \
    influxdb-client \
    pandas

# Create app directory
WORKDIR /app

# Copy all scripts
COPY entrypoint.sh /app/entrypoint.sh
COPY download_cloud.py /app/download_cloud.py
COPY crop_goes.py /app/crop_goes.py
COPY filter_smn.py /app/filter_smn.py
COPY filter_owm.py /app/filter_owm.py
COPY calculate_metrics.py /app/calculate_metrics.py

RUN chmod +x /app/entrypoint.sh

# Run the entrypoint script
CMD ["/app/entrypoint.sh"]
