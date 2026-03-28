# Procesamiento Automatizado de Imágenes Satelitales GOES

Este documento detalla la arquitectura y el flujo de trabajo implementado para la obtención, procesamiento y almacenamiento de imágenes satelitales del satélite GOES-19.

## 1. Justificación del Sistema
La fuente de datos de NOAA proporciona imágenes de altísima definición (7200x4320 píxeles). Almacenarlas crudas consume excesivo espacio. El sistema diseñado optimiza este proceso mediante:
1. Descarga periódica.
2. Recorte automático de la región de **Córdoba**.
3. Depuración de archivos crudos para ahorrar espacio.
4. Publicación en galería web estática.

## 2. Arquitectura del Pipeline

El sistema involucra dos componentes principales:
- **Processor (Python):** Se encarga tanto de ejecutar la descarga periódica de NOAA con `fetch_goes.py`, como de detectar el nuevo archivo y aplicarle el recorte mediante OpenCV.
- **Gallery (Nginx):** Sirve las imágenes resultantes.

### Flujo de Trabajo

1.  **Descarga Programada (`fetch_goes.py`):**
    El motor de Python ejecuta este downloader nativo en segundo plano de forma continua. Descarga la imagen Geocolor SSA (7200x4320) cada 10 minutos y la deposita en `/raw_images`.

2.  **Detección por Inotify (Processor):**
    El motor en Python está "escuchando" eventos en el filesystem. Al finalizar la escritura del JPG gigante, dispara el script de procesamiento.

3.  **Recorte con OpenCV:**
    Se utiliza una `Bounding Box` estática (ya que el satélite es geoestacionario) para extraer la provincia de Córdoba:
    - **Ancho (X):** 2700 a 3120 (420px)
    - **Alto (Y):** 1651 a 2255 (604px)
    El resultado se guarda como un archivo liviano en `/png-images`.

4.  **Limpieza Automática:**
    Para evitar llenar el disco, el procesador mantiene únicamente las **últimas 5 imágenes crudas** en `/raw_images`, eliminando las anteriores automáticamente.

5.  **Visualización:**
    Las imágenes recortadas están disponibles inmediatamente en:
    `http://localhost:8080/goes/`

## 3. Configuración

Todo el proceso está automatizado por el script `inicializador.sh`. Asegúrate de que las variables de entorno en `.env` (puertos y rutas) sean las correctas. No se requiere configuración manual adicional para este módulo una vez que los contenedores están arriba.
