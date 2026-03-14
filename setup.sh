#!/bin/bash

# ==============================================================================
# Setup Script - NOAA Climate Information System (Server)
# ==============================================================================
# Este script automatiza la configuración inicial del entorno de despliegue.
# Crea las carpetas necesarias, verifica dependencias y levanta los servicios.

set -e

echo "🚀 Iniciando configuración del entorno Server..."

# 1. Verificar dependencias
echo "🔍 Verificando dependencias..."
for req in docker "docker compose"; do
    if ! command -v $req &> /dev/null; then
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

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

DIR_PNG=${HOST_PNG_OUTPUT_DIR:-png-images}
DIR_RAW=${HOST_RAW_IMAGES_DIR:-raw_images}
DIR_CONFIG=${HOST_CONFIG_DIR:-configs}

DIRECTORIES=(
    "$DIR_PNG"
    "$DIR_RAW"
    "$DIR_CONFIG"
    "$DIR_CONFIG/influxdb"
    "n8n-custom/scripts"
)

for dir in "${DIRECTORIES[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "  - Creado directorio: $dir/"
    else
        echo "  - Directorio '$dir/' ya existe. Omitiendo."
    fi
done

# Copiar configuración inicial de Telegraf si no existe
if [ ! -f "$DIR_CONFIG/telegraf.conf" ]; then
    echo "  - Telegraf conf no encontrado. Si no lo has creado manualmente, asegúrate de tenerlo antes de iniciar Telegraf."
fi

# 3. Configurar Google Drive opcionalmente
echo "☁️ Configuración de Google Drive (Opcional)"
read -p "   ¿Deseas configurar la sincronización interactiva con Google Drive ahora usando Rclone? (S/n): " config_gdrive
if [[ "$config_gdrive" =~ ^[SsYy]$ ]] || [[ -z "$config_gdrive" ]]; then
    echo "   >> Ejecutando entorno temporal de configuración Rclone..."
    echo "   >> Sigue los pasos interactivos. Para crear tu cuenta presiona 'n' (New remote)."
    echo "   >> Cuando pida auto config presiona 'y', esto abrirá tu navegador para aceptar permisos."
    docker run --rm -it \
        -v "$(pwd)/configs:/config/rclone" \
        --net=host \
        rclone/rclone config
    echo "   ✅ Configuración de Rclone creada y guardada en ./configs/rclone.conf"
    echo "   >> Recuerda prender la variable RCLONE_SYNC_ENABLED=true en el archivo .env"
else
    echo "   ⏩ Omitiendo configuración de Google Drive."
fi

# 4. Iniciar servicios con Docker Compose
echo "🐳 Construyendo e iniciando contenedores Docker..."
docker compose up -d --build

echo "⏳ Esperando a que n8n inicie su base de datos y servicios (15 segundos)..."
sleep 15

echo "📥 Importando workflows en n8n..."
for workflow in ./configs/workflows/*.json; do
    if [ -f "$workflow" ]; then
        filename=$(basename -- "$workflow")
        echo "   - Importando $filename..."
        docker exec n8n n8n import:workflow --input="/configs/workflows/$filename" || echo "   ⚠️ Advertencia: No se pudo importar $filename (puede que ya exista)."
    fi
done
docker compose restart n8n

echo ""
echo "=============================================================================="
echo "✨ ¡ENTORNO DESPLEGADO CON ÉXITO! ✨"
echo "=============================================================================="
echo "Siguientes pasos:"
echo "1. Accede a n8n en: http://localhost:${N8N_PORT:-5678} para configurar tus workflows."
echo "2. Accede a Grafana en: http://localhost:${GRAFANA_PORT:-3000} (usuario inicial: admin/admin) y conecta la base de datos InfluxDB."
echo "3. Accede a la Galería estática en: http://localhost:${GALLERY_PORT:-8080}."
echo "4. Accede a InfluxDB en: http://localhost:8086 y verifica el bucket 'telemetry'."
echo "=============================================================================="
