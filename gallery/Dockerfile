FROM debian:bookworm-slim

# Instalar dependencias y el Nginx Bouncer de CrowdSec
RUN apt-get update && apt-get install -y -q --no-install-recommends \
    nginx wget gnupg ca-certificates curl \
    && curl -s https://install.crowdsec.net | sh \
    && apt-get install -y -q --no-install-recommends crowdsec-nginx-bouncer lua-cjson \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Redireccionar logs
RUN ln -sf /dev/stdout /var/log/nginx/access.log \
    && ln -sf /dev/stderr /var/log/nginx/error.log

# Script de inicio para inyectar la API Key de CrowdSec
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8080
CMD /usr/local/bin/entrypoint.sh && nginx -g 'daemon off;'
