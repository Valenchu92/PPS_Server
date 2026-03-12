#!/bin/bash

# ==============================================================================
# Setup Script - NOAA Climate Information System
# ==============================================================================
# Este script automatiza la configuración inicial del entorno de despliegue.
# Crea las carpetas necesarias, verifica dependencias y levanta los servicios.

set -e

echo "🚀 Iniciando configuración del entorno NOAA..."

# 1. Verificar dependencias
echo "🔍 Verificando dependencias..."
for req in docker "docker compose"; do
    if ! command -v $req &> /dev/null; then
        # Check standard docker-compose if 'docker compose' fails
        if [ "$req" = "docker compose" ] && command -v docker-compose &> /dev/null; then
            continue
        fi
        echo "❌ Error: $req no está instalado. Por favor, instálalo antes de continuar."
        exit 1
    fi
done
echo "✅ Dependencias correctas."

# 2. Crear estructura de directorios
echo "📂 Creando estructura de directorios..."

# Cargar variables de entorno si existe el archivo .env
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

DIR_WAV=${HOST_WAV_INPUT_DIR:-input-wav}
DIR_PNG=${HOST_PNG_OUTPUT_DIR:-png-images}
DIR_RAW=${HOST_RAW_IMAGES_DIR:-raw_images}
DIR_CONFIG=${HOST_CONFIG_DIR:-configs}

DIRECTORIES=(
    "$DIR_WAV"
    "$DIR_PNG"
    "$DIR_RAW"
)

for dir in "${DIRECTORIES[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "  - Creado directorio: $dir/"
    else
        echo "  - Directorio '$dir/' ya existe. Omitiendo."
    fi
done

# 3. Preparar archivo de token
if [ ! -d "$DIR_CONFIG" ]; then
    mkdir -p "$DIR_CONFIG"
fi
if [ ! -f "$DIR_CONFIG/token" ]; then
    echo "🔑 Creando archivo de token vacío en $DIR_CONFIG/token..."
    touch "$DIR_CONFIG/token"
    echo "  - ¡IMPORTANTE! Recuerda pegar tu API Key de Immich en este archivo posteriormente."
fi

# 4. Iniciar servicios con Docker Compose
echo "🐳 Construyendo e iniciando contenedores Docker..."
docker compose up -d --build

echo "⏳ Esperando a que n8n inicie su base de datos (15 segundos)..."
sleep 15
echo "📥 Importando y activando el workflow de descarga de GOES en n8n..."
docker exec n8n n8n import:workflow --input=/configs/n8n_workflow.json || true
docker exec n8n n8n update:workflow --id=goes_download --active=true || true
docker compose restart n8n

echo ""
echo "=============================================================================="
echo "✨ ¡ENTORNO DESPLEGADO CON ÉXITO! ✨"
echo "=============================================================================="
echo "Siguientes pasos:"
echo "1. Ingresa a Immich en: http://localhost:${IMMICH_PORT:-2283}"
echo "2. Crea la librería externa mapeando la ruta '/png-output'."
echo "3. Genera una API Key en Immich y pégala dentro del archivo '$DIR_CONFIG/token'."
echo "4. Reinicia el procesador para que tome tu clave ejecutando:"
echo "   docker compose restart processor"
echo "=============================================================================="
