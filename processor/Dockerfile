# --- Stage 1: Builder ---
FROM python:3.12-slim as builder

# Install tools needed for downloading/extracting
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Download and extract Rclone
RUN curl -O https://downloads.rclone.org/v1.65.2/rclone-v1.65.2-linux-amd64.zip && \
    unzip rclone-v1.65.2-linux-amd64.zip && \
    mv rclone-v1.65.2-linux-amd64/rclone /usr/bin/rclone && \
    chmod +x /usr/bin/rclone

# --- Stage 2: Final Runtime ---
FROM python:3.12-slim

# Create a non-root user
RUN useradd -m -u 1000 appuser

# Copy rclone from builder
COPY --from=builder /usr/bin/rclone /usr/bin/rclone

# Install minimal runtime system dependencies 
# We group them and clean in one layer to save space
RUN apt-get update && apt-get install -y --no-install-recommends \
    inotify-tools \
    bash \
    procps \
    cron \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install python dependencies in a single step
RUN pip install --no-cache-dir \
    numpy \
    opencv-python-headless \
    influxdb-client \
    pandas

WORKDIR /app

# Copy scripts and set ownership
COPY --chown=appuser:appuser calculate_metrics.py download_cloud.py crop_goes.py filter_smn.py filter_owm.py entrypoint.sh /app/

RUN chmod +x /app/entrypoint.sh

USER appuser

CMD ["/app/entrypoint.sh"]
