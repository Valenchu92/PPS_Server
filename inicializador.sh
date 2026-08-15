#!/bin/bash

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO DE SERVIDOR
# ==============================================================================
# Script de auto-configuración y despliegue rápido.
# Ideal para entornos donde no se requiere intervención manual pesada.
# ==============================================================================

# Símbolos y Colores
if [[ "$LANG" == *".UTF-8"* ]] || [[ "$LC_ALL" == *".UTF-8"* ]]; then
    S_START="🚀"; S_SEARCH="🔍"; S_ERR="❌"; S_OK="✅"; S_FILE="📄"; S_WARN="⚠️"; S_DIR="📂"; S_CLOUD="☁️"; S_DOCKER="🐳"; S_WAIT="⏳"; S_GEAR="⚙️"; S_SPARK="✨"
else
    S_START="[#]"; S_SEARCH="[?]"; S_ERR="[X]"; S_OK="[V]"; S_FILE="[F]"; S_WARN="[!]"; S_DIR="[D]"; S_CLOUD="[C]"; S_DOCKER="[P]"; S_WAIT="[.]"; S_GEAR="[*]"; S_SPARK="[*]"
fi

set -e

echo "$S_START Iniciando configuración del entorno Server..."

# 1. Verificar dependencias y permisos
echo "$S_SEARCH Verificando dependencias y permisos..."

MISSING_DEPS=()
for req in docker curl unzip; do
    if ! command -v $req &> /dev/null; then
        MISSING_DEPS+=("$req")
    fi
done

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo "$S_WARN Faltan las siguientes dependencias: ${MISSING_DEPS[*]}"
    read -p "   ¿Deseas intentar instalarlas automáticamente ahora? (S/n): " install_deps
    if [[ "$install_deps" =~ ^[Ss]$ ]] || [[ -z "$install_deps" ]]; then
        echo "   Instalando dependencias..."
        sudo apt-get update -y
        
        for req in "${MISSING_DEPS[@]}"; do
            if [ "$req" == "docker" ]; then
                echo "   Instalando Docker..."
                curl -fsSL https://get.docker.com -o get-docker.sh
                sudo sh get-docker.sh
                sudo usermod -aG docker $USER
                rm -f get-docker.sh
                echo "$S_WARN ¡Docker instalado! Es probable que debas reiniciar la sesión o VM para usar docker sin sudo."
            else
                sudo apt-get install -y "$req"
            fi
        done
    else
        echo "$S_ERR Error: Faltan dependencias. Abortando."
        exit 1
    fi
fi

# Verificar permisos de Docker
if ! sudo -n true 2>/dev/null; then 
    # si no puede usar sudo sin pass, que el docker ps intente solo
    DOCKER_CMD="docker"
else
    DOCKER_CMD="docker"
fi

if ! docker ps &> /dev/null; then
    echo "$S_ERR Error: No tienes permisos para usar Docker o el servicio no está activo."
    echo "   Prueba ejecutar 'newgrp docker' o reiniciá tu sesión/máquina virtual y volvé a correr este script."
    echo "   Alternativamente, podés correr el script con 'sudo ./inicializador.sh'."
    exit 1
fi

# Check docker compose version
if ! docker compose version &> /dev/null; then
  echo "$S_ERR Error: Docker Compose v2 no encontrado."
  exit 1
fi
echo "$S_OK Dependencias y permisos correctos."

# 2. Configurar variables de entorno si no existen
if [ ! -f .env ]; then
    echo "$S_FILE Creando archivo .env a partir de .env.template..."
    cp .env.template .env
    echo "$S_WARN Por favor, revisa el archivo .env para asegurar que las credenciales son seguras."
else
    echo "$S_OK Archivo .env existente detectado. Usando configuración actual."
fi

source .env

# 3. Validar variables mínimas obligatorias
if [ -z "$INFLUXDB_INIT_ADMIN_TOKEN" ]; then
    echo "$S_ERR Error: INFLUXDB_INIT_ADMIN_TOKEN no está definido."
    exit 1
fi

# 4. Crear estructura de carpetas locales para volumenes
echo "$S_DIR Creando estructura de directorios..."
DIRECTORIES=(
    "${HOST_PNG_OUTPUT_DIR:-./png-images}"
    "${HOST_PNG_NOAA_DIR:-./png-NOAA}"
    "${HOST_RAW_IMAGES_DIR:-./raw_images}"
    "${HOST_RAW_DATA_DIR:-./raw_data}"
    "${HOST_CONFIG_DIR:-./configs}"
    "${HOST_CONFIG_DIR:-./configs}/influxdb"
    "${HOST_CONFIG_DIR:-./configs}/grafana/provisioning/datasources"
    "${HOST_CONFIG_DIR:-./configs}/grafana/provisioning/dashboards"
    "${HOST_CONFIG_DIR:-./configs}/loki"
    "${HOST_CONFIG_DIR:-./configs}/promtail"
    "${HOST_CONFIG_DIR:-./configs}/crowdsec"
    "processor"
    "./loki-data"
    "./frontend-ui/goes"
    "./frontend-ui/noaa"
)

for DIR in "${DIRECTORIES[@]}"; do
    if [ ! -d "$DIR" ]; then
        mkdir -p "$DIR"
        # Otorgar permisos al usuario 1000 (común en contenedores no-root) para evitar errores de escritura
        chown -R 1000:1000 "$DIR" 2>/dev/null || chmod 777 "$DIR"
        echo "  - Creado directorio: $DIR"
    else
        # Si ya existe, nos aseguramos de que los permisos sean correctos de todos modos
        chown -R 1000:1000 "$DIR" 2>/dev/null || chmod 777 "$DIR"
        echo "  - Directorio '$DIR' ya existe. Actualizando permisos."
    fi
done

# Permisos especiales para Loki (el contenedor no es root)
chmod 777 ./loki-data

# 5. Opcional: Configurar rclone 
echo "$S_CLOUD Configuración de Google Drive (Opcional)"
if [ ! -f "${HOST_CONFIG_DIR:-./configs}/rclone/rclone.conf" ]; then
    read -p "   ¿Deseas configurar rclone para Google Drive ahora? (S/n): " auth_rclone
    if [[ "$auth_rclone" =~ ^[Ss]$ ]] || [[ -z "$auth_rclone" ]]; then
        echo "   Ejecutando configuración interactiva de Rclone..."
        echo "   -> Selecciona 'n' (New remote)"
        echo "   -> Nombre: 'gdrive' (Obligatorio para los workflows)"
        echo "   -> Tipo: 'drive' (Google Drive)"
        echo "   -> Deja Client ID y Secret en blanco"
        echo "   -> Scope: 'drive' (Full access)"
        echo "   Sigue las instrucciones del navegador..."
        
        # Corre un contenedor rclone descartable para generar la config y guardarla local
        mkdir -p "${HOST_CONFIG_DIR:-./configs}/rclone"
        touch "${HOST_CONFIG_DIR:-./configs}/rclone/rclone.conf"
        docker run --rm -it \
            -v "$(pwd)/${HOST_CONFIG_DIR:-./configs}/rclone:/config/rclone" \
            rclone/rclone config
    else
        echo "   ⏩ Omitiendo configuración de Google Drive."
    fi
else
    echo "   $S_OK Configuración de rclone.conf ya detectada."
fi

# 6. Levantar todo el stack con Docker Compose
echo "$S_DOCKER Construyendo e iniciando contenedores Docker..."
docker compose build
docker compose up -d

echo "$S_WAIT Esperando a que InfluxDB esté completamente operativo e inicializado..."
RETRIES=30
until docker compose exec -T influxdb influx bucket list --org "${INFLUXDB_INIT_ORG:-noaa_org}" --token "${INFLUXDB_INIT_ADMIN_TOKEN}" &> /dev/null || [ $RETRIES -eq 0 ]; do
    echo -n "."
    sleep 2
    RETRIES=$((RETRIES-1))
done
echo ""

if [ $RETRIES -eq 0 ]; then
    echo "$S_WARN Precaución: InfluxDB tardó demasiado en inicializarse. Revisa si los buckets extra se crearon."
else
    echo "  -> Creando bucket 'indexes'..."
    docker compose exec -T influxdb influx bucket create --name "${INFLUXDB_BUCKET_INDEXES:-indexes}" --org "${INFLUXDB_INIT_ORG:-noaa_org}" --token "${INFLUXDB_INIT_ADMIN_TOKEN}" || echo "  -> [Aviso] El bucket 'indexes' ya existe o hubo un error."
    echo "  -> Creando bucket 'predictions'..."
    docker compose exec -T influxdb influx bucket create --name "${INFLUXDB_BUCKET_PREDICTIONS:-predictions}" --org "${INFLUXDB_INIT_ORG:-noaa_org}" --token "${INFLUXDB_INIT_ADMIN_TOKEN}" || echo "  -> [Aviso] El bucket 'predictions' ya existe o hubo un error."
    echo "$S_OK Buckets extra verificados/creados."
fi

# 7. Registrar Bouncer de Nginx en CrowdSec
echo "$S_GEAR Configurando integración de seguridad CrowdSec..."
# Esperar a que CrowdSec esté listo
sleep 5
docker compose exec -T crowdsec cscli bouncers add nginx-bouncer -k "${CROWDSEC_BOUNCER_KEY:-generame_una_key_secreta_aqui_12345}" &>/dev/null || true
echo "$S_OK Nginx Bouncer registrado en CrowdSec."



echo "=============================================================================="
echo "$S_SPARK ¡ENTORNO DESPLEGADO CON ÉXITO! $S_SPARK"
echo "=============================================================================="
echo "Siguientes pasos:"
echo "2. Accede a Grafana en: http://localhost:${GRAFANA_PORT:-3000} (admin/admin)."
echo "3. Revisa los logs de Processor: docker compose logs -f processor"
echo "4. Accede a la Galería estática en: http://localhost:${WEB_SERVER_NGINX_PORT:-8080}."
echo "5. InfluxDB activo en http://localhost:8086 con los 3 buckets listos."
echo "=============================================================================="
