# Guía de Instalación y Despliegue

Sigue estos pasos para levantar el servidor desde cero en un entorno Linux con Docker.

## 🛠️ Requisitos Previos

- Docker y Docker Compose v2.
- Conexión a Internet.
- Archivo `.env` configurado (puedes usar `.env.template`).

## 📥 Paso 1: Clonar y Preparar

Asegúrate de tener todos los archivos en tu directorio de trabajo y otorga permisos de ejecución al script de configuración:

```bash
chmod +x setup.sh
```

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
