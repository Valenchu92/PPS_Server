# NOAA Climate Information System

Este proyecto implementa el sistema de procesamiento y visualización de datos e imágenes satelitales (GOES/NOAA) y telemetría meteorológica (SMN/OpenWeatherMap).

## 🏗️ Arquitectura del Proyecto

El sistema está diseñado para capturar, procesar y visualizar datos meteorológicos de diversas fuentes en tiempo real.

![Diagrama de Arquitectura](Diagrama%20PPS.drawio.png)

## 🚀 Componentes del Sistema

1.  **Processor**: Contenedor principal de Python encargado de descargar datos de satélites (GOES), OpenWeatherMap y SMN utilizando scripts nativos programados continuamente, y luego filtrarlos vía Inotify.
2.  **Processor (Custom)**: Motor en Python que monitorea directorios:
    *   **GOES**: Recorta imágenes de satélite GOES-19 enfocándose en la región de Córdoba.
    *   **Telemetría**: Parsea datos de SMN y OWM para enviarlos a InfluxDB.
    *   **Métricas**: Calcula índices como el Punto de Rocío y el Pronóstico Zambretti.
    *   **Sincronización**: Descarga imágenes NOAA procesadas desde Google Drive vía Rclone.
3.  **InfluxDB**: Base de datos de series temporales para telemetría y predicciones.
4.  **Grafana**: Visualización de datos meteorológicos mediante tableros pre-configurados.
5.  **Gallery (Nginx)**: Interfaz web para visualización de datos e imágenes, incluyendo:
    - 🌦️ **Módulo Meteorológico:** Reporte en tiempo real (SMN) con fallback automático a OpenWeatherMap (OWM).
    - 📈 **Gráficos Históricos:** Visualización interactiva de las últimas 12 mediciones para temperatura, viento y presión.
    - 🎞️ **Animación Satelital:** Reproducción secuencial de las últimas 10 imágenes del GOES-19 con pre-carga optimizada.
6.  **Watchtower**: Guardián de seguridad pasivo que purga imágenes e inyecta parches críticos (Zero-Day) de manera autónoma cada madrugada.

## 📂 Estructura de Directorios

*   `raw_data/`: Datos crudos (JSON/TXT/ZIP) de SMN y OWM.
*   `raw_images/`: Imágenes satelitales GOES sin procesar.
*   `png-images/`: Imágenes GOES recortadas (Córdoba).
*   `png-NOAA/`: Imágenes satelitales NOAA sincronizadas desde la nube.
*   `configs/`: Configuraciones de Rclone, dashboards y datasources de Grafana, y tokens.

## ⚙️ Despliegue Rápido

1.  **Requisitos**: Docker y Docker Compose v2+.
2.  **Configuración**:
    ```bash
    cp .env.template .env
    # Edita el .env con tu OPENWEATHERMAP_API_KEY
    ```
3.  **Ejecución**:
    ```bash
    chmod +x inicializador.sh
    ./inicializador.sh
    ```

## ⚓ Puertos y Acceso

| Servicio | URL | Descripción |
| :--- | :--- | :--- |
| **Galería** | `http://localhost:8080` | Imágenes satelitales (Única expuesta) |

| **Grafana** | `http://127.0.0.1:3000` | Solo acceso local por seguridad |
| **InfluxDB** | `http://127.0.0.1:8086` | Solo acceso local por seguridad |

## ✨ Mejoras Recientes (Marzo 2026)

- **Optimización Docker:** Procesador migrado a *Multi-stage Build* (ahorro de espacio y tiempo).
- **Lógica de Prioridad:** Sistema de fallback SMN > OWM para la galería web.
- **Seguridad Avanzada:**
    - Aislamiento de red para servicios sensibles.
    - Contenedores corriendo sin privilegios (no-root).
    - Limitación de tráfico, caché estático anti-enumeración y cortes de Slowloris en Nginx.
    - Parcheo pasivo automatizado contra CVEs mediante Watchtower.

---
*Este proyecto está diseñado para funcionar de manera autónoma una vez configurado el archivo `.env`.*
