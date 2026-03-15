#!/bin/bash

# ==============================================================================
# CONFIGURACIÓN DEL ENTORNO DE SERVIDOR
# ==============================================================================
# Script de auto-configuración y despliegue rápido.
# Ideal para entornos donde no se requiere intervención manual pesada.
# ==============================================================================

set -e # Detener script si algún comando falla

echo "🚀 Iniciando configuración del entorno Server..."

# 1. Verificar dependencias
echo "🔍 Verificando dependencias..."
for req in docker curl unzip; do
    if ! command -v $req &> /dev/null; then
        echo "❌ Error: $req no está instalado. Por favor instálalo primero."
        exit 1
    fi
done

# Check docker compose version
if ! docker compose version &> /dev/null; then
  echo "❌ Error: Docker Compose v2 no encontrado."
  exit 1
fi
echo "✅ Dependencias correctas."

# 2. Configurar variables de entorno si no existen
if [ ! -f .env ]; then
    echo "📄 Creando archivo .env a partir de .env.template..."
    cp .env.template .env
    echo "⚠️ Por favor, revisa el archivo .env para asegurar que las credenciales son seguras."
else
    echo "✅ Archivo .env existente detectado. Usando configuración actual."
fi

source .env

# 3. Validar variables mínimas obligatorias
if [ -z "$INFLUXDB_INIT_ADMIN_TOKEN" ]; then
    echo "❌ Error: INFLUXDB_INIT_ADMIN_TOKEN no está definido."
    exit 1
fi

# 4. Crear estructura de carpetas locales para volumenes
echo "📂 Creando estructura de directorios..."
DIRECTORIES=(
    "${HOST_PNG_OUTPUT_DIR:-./png-images}"
    "${HOST_RAW_IMAGES_DIR:-./raw_images}"
    "${HOST_RAW_DATA_DIR:-./raw_data}"
    "${HOST_CONFIG_DIR:-./configs}"
    "${HOST_CONFIG_DIR:-./configs}/influxdb"
    "processor"
)

for DIR in "${DIRECTORIES[@]}"; do
    if [ ! -d "$DIR" ]; then
        mkdir -p "$DIR"
        chmod 755 "$DIR"
        echo "  - Creado directorio: $DIR"
    else
        echo "  - Directorio '$DIR' ya existe. Omitiendo."
    fi
done

# 5. Opcional: Configurar rclone 
echo "☁️ Configuración de Google Drive (Opcional)"
if [ ! -f "${HOST_CONFIG_DIR:-./configs}/rclone.conf" ]; then
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
        mkdir -p "${HOST_CONFIG_DIR:-./configs}"
        touch "${HOST_CONFIG_DIR:-./configs}/rclone.conf"
        docker run --rm -it \
            -v "$(pwd)/${HOST_CONFIG_DIR:-./configs}:/config/rclone" \
            rclone/rclone config
    else
        echo "   ⏩ Omitiendo configuración de Google Drive."
    fi
else
    echo "   ✅ Configuración de rclone.conf ya detectada."
fi

# 6. Levantar todo el stack con Docker Compose
echo "🐳 Construyendo e iniciando contenedores Docker..."
docker compose build
docker compose up -d

# 7. Esperar a n8n y restaurar los workflows nuevos (Opcional si los creamos luego)
echo "⏳ Esperando a que InfluxDB y N8N arranquen... (15 segundos)"
sleep 15

echo "=============================================================================="
echo "✨ ¡ENTORNO DESPLEGADO CON ÉXITO! ✨"
echo "=============================================================================="
echo "Siguientes pasos:"
echo "1. Accede a n8n en: http://localhost:${N8N_PORT:-5678} para configurar los fetchers."
echo "2. Accede a Grafana en: http://localhost:${GRAFANA_PORT:-3000} (admin/admin)."
echo "3. Revisa los logs de Processor: docker compose logs -f processor"
echo "4. Accede a la Galería estática en: http://localhost:${GALLERY_PORT:-8080}."
echo "5. InfluxDB activo en http://localhost:8086 con los 3 buckets listos."
echo "=============================================================================="
