# NOAA Climate Information System

Este proyecto implementa el sistema de procesamiento y visualización de datos e imágenes satelitales (GOES/NOAA) y telemetría meteorológica (SMN/OpenWeatherMap).

## 🏗️ Arquitectura del Proyecto

El sistema está diseñado para capturar, procesar y visualizar datos meteorológicos de diversas fuentes en tiempo real.

```mermaid
graph TD
    %% Bloque 1: Adquisición
    subgraph Adquisicion ["1. Adquisición y Orquestación"]
        A1["Antena / SatDump"] --> D1["Archivos de Datos/Audio"]
        A2["OpenWeatherMap API"] --> N8N["n8n (Workflow)"]
        A3["SMN (Web)"] --> N8N
        N8N --"JSON / TXT"--> RAW_DATA["/raw_data"]
    end

    %% Bloque 2: Procesamiento
    subgraph Procesamiento ["2. Motor de Procesamiento"]
        RAW_DATA --> PROC{{"Processor (Python)"}}
        RAW_IMG["/raw_images (GOES)"] --> PROC
        PROC --"Cálculo Métricas"--> METRICS["Variables (Punto Rocío, Zambretti)"]
        PROC --"Recorte"--> GOES_PNG["/png-images"]
        DRIVE["Google Drive"] --"Rclone Sync"--> NOAA_PNG["/png-NOAA"]
    end

    %% Bloque 3: Almacenamiento
    subgraph Almacenamiento ["3. Almacenamiento"]
        PROC --"Ingesta"--> INFLUX[("InfluxDB")]
        GOES_PNG --"Volumen"--> FS[("FS Local")]
        NOAA_PNG --"Volumen"--> FS
    end

    %% Bloque 4: Visualización
    subgraph Visualizacion ["4. Visualización"]
        INFLUX --> GRAFANA["Grafana (Dashboards)"]
        FS --> GALLERY["Gallery (Nginx Static)"]
        GRAFANA --> USER["Usuario Final"]
        GALLERY --> USER
    end

    %% Estilos
    classDef hardware fill:#e0f2fe,stroke:#0369a1,stroke-width:2px;
    classDef docker fill:#dcfce7,stroke:#15803d,stroke-width:2px;
    classDef db fill:#fef9c3,stroke:#a16207,stroke-width:2px;

    class N8N,PROC,GALLERY docker;
    class INFLUX,GRAFANA db;
```

## 🚀 Componentes del Sistema

1.  **n8n**: Orquestador encargado de descargar datos de OpenWeatherMap y SMN.
2.  **Processor (Custom)**: Motor en Python que monitorea directorios:
    *   **GOES**: Recorta imágenes de satélite GOES-19 enfocándose en la región de Córdoba.
    *   **Telemetría**: Parsea datos de SMN y OWM para enviarlos a InfluxDB.
    *   **Métricas**: Calcula índices como el Punto de Rocío y el Pronóstico Zambretti.
    *   **Sincronización**: Descarga imágenes NOAA procesadas desde Google Drive vía Rclone.
3.  **InfluxDB**: Base de datos de series temporales para telemetría y predicciones.
4.  **Grafana**: Visualización de datos meteorológicos mediante tableros pre-configurados.
5.  **Gallery (Nginx)**: Interfaz web simple para visualizar las imágenes recortadas de GOES y NOAA.

## 📂 Estructura de Directorios

*   `raw_data/`: Datos crudos (JSON/TXT/ZIP) de SMN y OWM.
*   `raw_images/`: Imágenes satelitales GOES sin procesar.
*   `png-images/`: Imágenes GOES recortadas (Córdoba).
*   `png-NOAA/`: Imágenes satelitales NOAA sincronizadas desde la nube.
*   `configs/`: Configuraciones de n8n, dashboards de Grafana y tokens.

## ⚙️ Despliegue Rápido

1.  **Requisitos**: Docker y Docker Compose v2+.
2.  **Configuración**:
    ```bash
    cp .env.template .env
    # Edita el .env con tu OPENWEATHERMAP_API_KEY
    ```
3.  **Ejecución**:
    ```bash
    chmod +x setup.sh
    ./setup.sh
    ```

## ⚓ Puertos y Acceso

| Servicio | URL | Descripción |
| :--- | :--- | :--- |
| **n8n** | `http://localhost:5678` | Workflows y automatización |
| **Grafana** | `http://localhost:3000` | Tableros meteorológicos (admin/admin) |
| **Galería** | `http://localhost:8080` | Imágenes satelitales (GOES/NOAA) |
| **InfluxDB** | `http://localhost:8086` | Consola de base de datos |

---
*Este proyecto está diseñado para funcionar de manera autónoma una vez configurado el archivo `.env`.*
