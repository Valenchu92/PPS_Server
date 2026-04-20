#!/bin/sh
set -e

# Asegurarse de que el directorio del bouncer exista
mkdir -p /etc/crowdsec/bouncers/

# Inyectar la URL de la API local de CrowdSec (el contenedor 'crowdsec')
if [ -f /etc/crowdsec/bouncers/crowdsec-nginx-bouncer.conf ]; then
    sed -i "s|API_URL=.*|API_URL=http://crowdsec:8080|g" /etc/crowdsec/bouncers/crowdsec-nginx-bouncer.conf
    sed -i "s|API_KEY=.*|API_KEY=${CROWDSEC_BOUNCER_KEY}|g" /etc/crowdsec/bouncers/crowdsec-nginx-bouncer.conf
fi

echo "CrowdSec Nginx Bouncer configurado."
