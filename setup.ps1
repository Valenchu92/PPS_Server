$ErrorActionPreference = "Stop"

Write-Host "Iniciando configuracion del entorno NOAA en Windows..." -ForegroundColor Cyan

# 1. Verificar dependencias
Write-Host "Verificando dependencias..." -ForegroundColor Yellow
$dockerExists = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerExists) {
    Write-Host "Error: Docker no esta instalado o no esta en el PATH. Por favor, instala Docker Desktop antes de continuar." -ForegroundColor Red
    exit 1
}

$composeExists = docker compose version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker Compose no esta funcionando correctamente." -ForegroundColor Red
    exit 1
}
Write-Host "Dependencias correctas." -ForegroundColor Green

# 2. Crear estructura de directorios
Write-Host "Creando estructura de directorios..." -ForegroundColor Yellow

if (Test-Path ".env") {
    Get-Content ".env" | Where-Object { $_ -match '^(?!#)([^=]+)=(.*)$' } | ForEach-Object {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}

$DIR_WAV = if ($env:HOST_WAV_INPUT_DIR) { $env:HOST_WAV_INPUT_DIR } else { "input-wav" }
$DIR_PNG = if ($env:HOST_PNG_OUTPUT_DIR) { $env:HOST_PNG_OUTPUT_DIR } else { "png-images" }
$DIR_RAW = if ($env:HOST_RAW_IMAGES_DIR) { $env:HOST_RAW_IMAGES_DIR } else { "raw_images" }
$DIR_CONFIG = if ($env:HOST_CONFIG_DIR) { $env:HOST_CONFIG_DIR } else { "configs" }

$directories = @($DIR_WAV, $DIR_PNG, $DIR_RAW)

foreach ($dir in $directories) {
    if (-not (Test-Path -Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Write-Host "  - Creado directorio: $dir/"
    } else {
        Write-Host "  - Directorio $dir/ ya existe. Omitiendo."
    }
}

# 3. Preparar archivo de token
if (-not (Test-Path -Path $DIR_CONFIG)) {
    New-Item -ItemType Directory -Force -Path $DIR_CONFIG | Out-Null
}
$tokenPath = "$DIR_CONFIG\token"
if (-not (Test-Path -Path $tokenPath)) {
    Write-Host "Creando archivo de token vacio en $tokenPath..." -ForegroundColor Yellow
    New-Item -ItemType File -Force -Path $tokenPath | Out-Null
    Write-Host "  - IMPORTANTE: Recuerda pegar tu API Key de Immich en este archivo." -ForegroundColor Red
}

# 4. Iniciar servicios con Docker Compose
Write-Host "Construyendo e iniciando contenedores Docker..." -ForegroundColor Cyan
docker compose up -d --build

Write-Host "Esperando a que n8n inicie su base de datos (15 segundos)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15
Write-Host "Importando y activando el workflow de descarga de GOES en n8n..." -ForegroundColor Cyan
docker exec n8n n8n import:workflow --input=/configs/n8n_workflow.json
docker exec n8n n8n update:workflow --id=goes_download --active=true
docker compose restart n8n

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "ENTORNO DESPLEGADO CON EXITO!" -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "Siguientes pasos:"
$IMMICH_PORT = if ($env:IMMICH_PORT) { $env:IMMICH_PORT } else { "2283" }
Write-Host "1. Ingresa a Immich en: http://localhost:$IMMICH_PORT"
Write-Host "2. Crea la libreria externa mapeando la ruta /png-output"
Write-Host "3. Genera una API Key en Immich y pegala dentro del archivo $DIR_CONFIG\token"
Write-Host "4. Reinicia el procesador para que tome tu clave ejecutando:"
Write-Host "   docker compose restart processor"
Write-Host "==============================================================================" -ForegroundColor Green
