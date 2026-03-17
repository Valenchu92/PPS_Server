# Guía de Instalación y Despliegue

Sigue estos pasos para levantar el servidor desde cero en un entorno Linux con Docker.

## 🛠️ Requisitos Previos

- Docker y Docker Compose v2.
- Conexión a Internet.
- Archivo `.env` configurado (puedes usar `.env.template`).

## ⚙️ Paso 1: Configuración de Variables de Entorno

El sistema utiliza un archivo `.env` para gestionar credenciales, puertos y rutas. Para comenzar, copia el archivo de plantilla:

```bash
cp .env.template .env
```

### Variables Principales

| Variable | Descripción | Valor por Defecto |
| :--- | :--- | :--- |
| `N8N_PORT` | Puerto para la interfaz de n8n | `5678` |
| `GRAFANA_PORT` | Puerto para los tableros de Grafana | `3000` |
| `INFLUXDB_INIT_ADMIN_TOKEN` | Token de acceso para InfluxDB | `my-super-secret-auth-token` |
| `METEOROLOGY_ALTITUDE` | Altitud local (m) para corrección de presión | `441` |
| `OPENWEATHERMAP_API_KEY` | Token de API de OpenWeatherMap | (Requerido) |
| `RCLONE_GDRIVE_PATH` | Carpeta en GDrive para descarga de imágenes | `images_pps` |

> [!IMPORTANT]
> **Seguridad**: Asegúrate de cambiar las contraseñas y tokens por defecto en entornos de producción. El archivo `.env` está en el `.gitignore` para evitar que tus credenciales se suban al repositorio.

## 🚀 Paso 2: Ejecutar el Setup

El script `setup.sh` se encarga de crear la estructura de carpetas, validar las dependencias y levantar los contenedores.

```bash
./setup.sh
```

### ¿Qué hace este script?
1. Verifica si tienes `docker`, `curl` y `unzip`.
2. Crea el archivo `.env` si no existe.
3. Crea las carpetas de volúmenes con los permisos correctos.
4. (Opcional) Te ayuda a configurar Rclone si deseas sincronizar con Google Drive.
5. Ejecuta `docker compose up -d`.

## ⚙️ Paso 3: Configuración Post-Instalación

### InfluxDB
El sistema se inicializa con los buckets `telemetry` y `predictions`. El token de administración se define en el `.env`.

### Grafana
Accede a `http://localhost:3000`.
- **Usuario**: `admin`
- **Password**: (definido en el `.env`)
Los tableros y la base de datos se cargan automáticamente gracias al sistema de **Provisioning**.

### n8n
Accede a `http://localhost:5678`. Deberás importar los workflows ubicados en `configs/workflows` para comenzar a recibir datos reales.

## 🩺 Resolución de Problemas

**Ver estado de contenedores:**
```bash
docker compose ps
```

**Ver logs del procesador de datos:**
```bash
docker compose logs -f processor
```

**Reiniciar un servicio específico:**
```bash
docker compose restart grafana
```
