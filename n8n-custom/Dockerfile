FROM docker.n8n.io/n8nio/n8n:latest

USER root

# Instalar dependencias necesarias para Python, OpenCV y Rclone
RUN apk add --no-cache \
    python3 \
    py3-pip \
    opencv-python \
    curl \
    unzip \
    bash

# Instalar Rclone
RUN curl -O https://downloads.rclone.org/v1.65.2/rclone-v1.65.2-linux-amd64.zip && \
    unzip rclone-v1.65.2-linux-amd64.zip && \
    cp rclone-v1.65.2-linux-amd64/rclone /usr/bin/ && \
    chown root:root /usr/bin/rclone && \
    chmod 755 /usr/bin/rclone && \
    rm -rf rclone-v1.65.2-linux-amd64 rclone-v1.65.2-linux-amd64.zip

# Cambiar de vuelta al usuario node de n8n
USER node
