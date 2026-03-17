# Sistema de Información Climática Río Cuarto

Bienvenido a la documentación oficial del Servidor de Procesamiento Meteorológico. Este sistema está diseñado para la adquisición, procesamiento y visualización de datos climáticos y satelitales centrados en la ciudad de Río Cuarto, Córdoba.

## 🌟 Características Principales

- **Multi-fuente**: Integración de datos del Servicio Meteorológico Nacional (SMN) y OpenWeatherMap.
- **Predicción Local**: Algoritmo de Zambretti adaptado al hemisferio sur para pronósticos de corto plazo (24h).
- **Procesamiento Satelital**: Adquisición y recorte automático de imágenes del satélite GOES-16.
- **Visualización Profesional**: Dashboards en Grafana con comparación de fuentes en tiempo real.
- **Automatización Total**: Flujos de trabajo gestionados por n8n y contenedores Docker.

## 📋 Resumen del Stack Tecnológico

| Componente | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Base de Datos** | InfluxDB 2.x | Almacenamiento de series temporales (Telemetría) |
| **Visualización** | Grafana | Dashboards interactivos y alertas |
| **Automatización** | n8n | Orquestación de descargas y APIs |
| **Procesador** | Python 3.12 (Docker) | Lógica de cálculo, filtrado y OpenCV |
| **Galería** | Nginx | Servidor web para imágenes procesadas |

## 🚀 Inicio Rápido

Para poner en marcha el servidor por primera vez, consulta la [Guía de Instalación](configuracion.md).

```bash
./setup.sh
```
