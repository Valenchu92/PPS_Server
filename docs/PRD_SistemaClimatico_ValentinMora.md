# PRODUCT REQUIREMENTS DOCUMENT (Actualizado)

**Sistema de Información Climática con Integración de Imágenes Satelitales y Telemetría Meteorológica**

**Proyecto**: Sistema de Información Climática NOAA/GOES  
**Autor**: Valentín Mora  
**Versión**: 2.0 (Refactorización InfluxDB/Grafana)  
**Fecha**: Marzo 2026  

## 1. Descripción General del Sistema

El sistema tiene como objetivo centralizar, procesar y visualizar datos meteorológicos y satelitales. Se enfoca en tres pilares:
1.  **Telemetría**: Ingesta de datos reales del SMN y OpenWeatherMap.
2.  **Imágenes Satelitales**: Procesamiento de imágenes GOES-19 (recorte de Córdoba) y sincronización de imágenes NOAA.
3.  **Análisis Local**: Cálculo de índices meteorológicos (Punto de Rocío, Pronóstico Zambretti) para la región de Río Cuarto.
4.  **Nowcasting Predictivo**: Motor de visión artificial (Optical Flow de Farnebäck) que proyecta el movimiento de nubes a 1 y 2 horas para alertar sobre tormentas inminentes.

El sistema está desplegado íntegramente con Docker y visualizado mediante Grafana y una Galería Web estática.

## 2. Arquitectura del Sistema

### 2.1 Componentes Principales

| Componente | Tecnología | Descripción |
| :--- | :--- | :--- |
| **Python Fetchers** | Contenedor | Scripts nativos que descargan datos de APIs (OWM) y servidores externos (SMN y GOES) de manera programada. |
| **Processor** | Python/OpenCV | Motor que recorta imágenes GOES, parsea datos crudos y calcula métricas. Incluye el motor de Nowcasting ponderado de 3 imágenes. |
| **InfluxDB** | Time-Series DB | Almacenamiento persistente de telemetría y predicciones. |
| **Grafana** | Dashboards | Panel visual para monitoreo de variables climáticas. |
| **Gallery** | Nginx | Servidor web estático para la visualización de imágenes procesadas. |

### 2.2 Flujo de Datos

1.  **Adquisición**: Los scripts de Python (Fetchers) descargan archivos crudos de internet y los depositan localmente en `/raw_data` o `/raw_images`.
2.  **Procesamiento**: El contenedor `processor` detecta los archivos. 
    *   Si es imagen GOES: La recorta y guarda en `/png-images`.
    *   Si es Telemetría: La procesa y la envía a InfluxDB.
    *   Cálculos extra: Genera métricas cada hora y las guarda en InfluxDB.
3.  **Visualización**: El usuario accede a Grafana para ver gráficos históricos y a la Galería para ver las últimas capturas satelitales.

## 3. Especificación de Directorios

- `raw_data/`: Directorio de intercambio para archivos de texto/json.
- `raw_images/`: Directorio para imágenes GOES originales (purga automática: solo se mantienen 5).
- `png-images/`: Resultado final del recorte de Córdoba.
- `png-NOAA/`: Imágenes sincronizadas desde Google Drive vía Rclone.

## 4. Requerimientos No Funcionales

- **Portabilidad**: Configuración centralizada en `.env`.
- **Eficiencia**: Uso de `inotify` para evitar polling constante en el procesador.
- **Resiliencia**: Reinicio automático de contenedores y persistencia de datos en volúmenes Docker.

---
*Este PRD refleja la implementación actual del sistema, habiendo migrado de una arquitectura basada en Immich a una solución más ligera y técnica basada en Grafana e InfluxDB.*
