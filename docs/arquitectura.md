# Arquitectura del Sistema

El sistema funciona como un conjunto de microservicios orquestados por Docker Compose, donde el núcleo es el intercambio de archivos a través de volúmenes compartidos.

![Diagrama de Arquitectura](assets/img/diagrama_arquitectura.png)

## 🏗️ Diagrama de Flujo de Datos

```mermaid
graph TD
    A[Python Fetchers (Cron/Loop)] -->|Descarga TXT/JSON/JPG| B[(Directorios Raw)]
    A -->|Descarga JPG| C[(raw_images)]
    
    D[Processor Container] -->|Vigila| B
    D -->|Vigila| C
    
    D -->|Filtra y Procesa| E[InfluxDB]
    D -->|Corta Imágenes| F[(png-images)]
    
    E -->|Visualiza| G[Grafana]
    F -->|Sirve| H[Web Gallery]
```

## 📂 Estructura de Directorios Clave

- `/configs`: Configuraciones de Grafana, InfluxDB y Rclone.
- `/raw_data`: Directorio de entrada para datos crudos (TXT, ZIP, JSON).
- `/raw_images`: Directorio de entrada para imágenes GOES originales.
- `/png-images`: Imágenes recortadas y procesadas listas para la web.
- `/processor`: Código fuente del motor de procesamiento en Python.

## ⚙️ Componentes

### 1. InfluxDB
Motor de base de datos de series temporales. Utiliza dos buckets principales:
- `telemetry`: Datos de estaciones meteorológicas (SMN, OWM).
- `predictions`: Resultados del algoritmo de Zambretti y métricas calculadas.

### 2. Processor (Python Engine)
Contenerizado bajo una arquitectura **Multi-stage Build**, lo que optimiza su peso (~515MB) y acelera la reconstrucción de capas de Python (OpenCV, Pandas).
- **Workers Inotify**: Reaccionan instantáneamente cuando los scripts Fetcher guardan un archivo nuevo en disco.
- **Cron Jobs**: Tareas programadas como el cálculo de índices cada hora.
- **Seguridad**: Ejecuta sus procesos como un usuario no privilegiado (`appuser`) para proteger el host.

### 3. Fetchers en Python
Cerebro de la automatización embebido en el propio sub-sistema de procesamiento. Son scripts independientes (`fetch_goes.py`, `fetch_owm.py`, `fetch_smn.py`) que corren nativamente de manera continua extrayendo datos y ahorrando drásticamente recursos del host ya que no dependen de ningún contenedor tercero masivo ni de su propia base de datos estructurada.

### 4. Watchtower
Sistema subyacente de monitoreo pasivo acoplado al socket de Docker y condicionado a un *cron schedule* estricto de UTC-3. Encargado de purgar imágenes caídas (`CLEANUP=true`) y reemplazar dinámicamente el stack subyacente con las contramedidas CVEs más recientes proveídas por Docker Hub.

## 🛡️ Medidas de Seguridad Implementadas

- **Aislamiento de Red:** InfluxDB y Grafana están vinculados a `127.0.0.1`, siendo inaccesibles desde fuera del host.
- **Hardening de Nignx:** La galería web corre como usuario `nginx` (no-root) en el puerto 8080.
- **Control de Tráfico:** Implementación de *Rate Limiting* (3r/s) y *Connection Limiting* para mitigar ataques DoS.
- **Protección de Datos:** Bloqueo de acceso a archivos ocultos y auditoría de XSS en el frontend.
