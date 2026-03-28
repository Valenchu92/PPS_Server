# Módulo GOES-16 (Satelital)

El sistema descarga y procesa imágenes de banda infrarroja y visible del satélite GOES-16 (NOAA).

## 🌍 Area de Cobertura
El procesador realiza un **Crop (recorte)** automático centrado en la región de Río Cuarto.

## ⚙️ Flujo de Trabajo
1. **Descarga**: El script `fetch_goes.py` baja la imagen (`.jpg` o `.png`) desde los servidores de NOAA de forma automática y la guarda en `/raw_images`.
2. **Procesamiento (`crop_goes.py`)**:
   - Detecta la imagen.
   - Aplica coordenadas de recorte específicas para Argentina / Río Cuarto.
   - Guarda el resultado en `/png-images`.
3. **Optimización**: El sistema mantiene solo las últimas 5 imágenes crudas para evitar el llenado del disco.

## 🖼️ Visualización
Las imágenes recortadas se sirven a través del contenedor `gallery` (Nginx) y pueden ser visualizadas directamente en el dashboard de Grafana o mediante la URL:
`http://localhost:8080/`

## 🔮 Futuro: Análisis de Nubes
Este módulo es la base para el futuro análisis de movimiento de nubes mediante OpenCV, lo cual permitirá calcular vectores de viento en altura y mejorar la precisión del pronóstico de corto plazo.
