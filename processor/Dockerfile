FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    curl \
    inotify-tools \
    bash \
    unzip \
    ca-certificates \
    jq \
    python3 \
    python3-pip \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp
RUN curl -L -A "Mozilla/5.0" -o noaa-apt.zip "https://github.com/martinber/noaa-apt/releases/download/v1.4.1/noaa-apt-1.4.1-x86_64-linux-gnu-nogui.zip" \
    && unzip noaa-apt.zip \
    && mv noaa-apt /usr/local/bin/ \
    && chmod +x /usr/local/bin/noaa-apt \
    && rm -rf /tmp/noaa-apt*

COPY crop_cordoba.py /crop_cordoba.py
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

ENV WAV_INPUT_DIR=/input
ENV PNG_OUTPUT_DIR=/output
ENV MAX_AGE_DAYS=7
ENV CLEANUP_INTERVAL_MIN=60

ENTRYPOINT ["/entrypoint.sh"]