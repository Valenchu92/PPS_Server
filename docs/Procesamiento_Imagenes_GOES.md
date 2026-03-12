# Procesamiento Automatizado de Imágenes Satelitales GOES

Este documento detalla la arquitectura y el flujo de trabajo implementado para la obtención, procesamiento y almacenamiento de imágenes satelitales GEOCOLOR provenientes del satélite GOES-16/19.

## 1. Justificación del Sistema
La fuente de datos de NOAA proporciona imágenes satelitales continuas de muy alta definición (7200x4320 píxeles) de su constelación GOES. Descargar y almacenar estas imágenes crudas de manera constante consume rápidamente el almacenamiento disponible, además de contener información geográfica de todo el continente sudamericano que no es relevante para el enfoque local del proyecto.

Por ello, se ha diseñado un *pipeline* automatizado que:
1. Descarga la imagen periódicamente.
2. Extrae (recorta) exclusivamente la región correspondiente a la provincia de Córdoba.
3. Elimina los excedentes para optimizar el almacenamiento.
4. Disponibiliza el resultado optimizado en una galería para su visualización.

## 2. Arquitectura del Pipeline

El sistema involucra tres componentes principales corriendo sobre contenedores de Docker:
- **n8n (Orquestador):** Se encarga del *cron job* de descarga.
- **processor (Procesador Inteligente):** Detecta las descargas y ejecuta Python con OpenCV.
- **Immich (Galería):** Indexa el resultado final.

### Flujo de Trabajo (Paso a Paso)

1. **Descarga Programada (n8n):** 
   - Un *workflow* en n8n está configurado para ejecutarse cada 10 minutos.
   - Accede a la URL oficial de GOES GEOCOLOR Sector SSA y descarga la imagen en máxima resolución (7200x4320).
   - Guarda el archivo directamente en un volumen de Docker local llamado `raw_images`. El archivo adquiere automáticamente un sello de tiempo (timestamp) del satélite GOES (ej: `goes19_ssa_geocolor_20260310_2150.jpg`).

2. **Detección Automática (Inotifywait):**
   - El contenedor `processor` (basado en Debian) cuenta con un script de inicio (`entrypoint.sh`) que utiliza la herramienta del kernel de Linux `inotifywait`.
   - Este *daemon* vigila en tiempo real la carpeta montada `/raw_images`. Dicho monitoreo no consume CPU activa hasta que el sistema de archivos emite un evento `CLOSE_WRITE`.
   - Al detectarse que n8n ha terminado de escribir el archivo gigante en disco, se dispara el proceso de recorte.

3. **Recorte Geográfico (Python + OpenCV):**
   - El `entrypoint.sh` invoca al script `/crop_cordoba.py` diseñado a medida.
   - Dado que el satélite meteorológico es **geoestacionario**, el encuadre fotográfico jamás cambia. Se aprovechó esta ventaja técnica para establecer coordenadas estáticas exactas (`Bounding Box`) que encierran a la provincia de Córdoba a la perfección.
   - **Coordenadas de Extracción calculadas (Eje X, Y):**
     - `X_START = 2700`, `X_END = 3120` (420px de ancho)
     - `Y_START = 1651`, `Y_END = 2255` (604px de alto)
   - El script lee la imagen usando la librería nativa de C++ optimizada `OpenCV`, ejecuta el *slice* de la matriz de la imagen en milisegundos y lo guarda compilado en la carpeta de destino `/png-images` con la extensión modificada para identificarla (ej: `..._2150_cordoba.png`).
   
4. **Optimización de Almacenamiento Cíclico:**
   - Una vez que la imagen recortada se guarda exitosamente, el script `entrypoint.sh` procede a realizar una purga controlada sobre el volumen `raw_images`.
   - Ordena los archivos JPG gigantes basándose en su fecha de creación y **conserva únicamente las 5 imágenes observacionales más recientes**, descartando de manera permanente todo historial antiguo. Esta técnica de retención en ventana de tiempo protege al servidor de alcanzar picos críticos de almacenamiento.

5. **Visualización y Consumo (Immich):**
   - Inmediatamente después del procesamiento, el `processor` envía un evento de indexación a la API de Ingestión de la interfaz gráfica (Immich).
   - La aplicación detecta la nueva imagen ligera de Córdoba, la procesa y la hace disponible a través de su cliente web/móvil casi en tiempo real (aproximadamente a los 3 segundos de concluida la descarga de n8n).

## 3. Despliegue Consolidado Cross-Platform (Scripts de Setup)

Se ha creado un mecanismo de instalación automatizada unificado tanto para distribuciones basadas en Linux (Bash) como en Windows (PowerShell). Dichos scripts (`setup.sh` y `setup.ps1`):
1. Verifican pre-requisitos de Docker en la máquina del anfitrión.
2. Inyectan de manera automatizada las carpetas compartidas inter-contenedor (`input-wav`, `png-images`, `raw_images`, `configs`) necesarias para el montaje eficiente de volúmenes.
3. Importan programáticamente a la base de datos de n8n el archivo JSON (`n8n_workflow.json`) con la lógica *serverless* y lo activan sin requerir intervención humana (CLI automatizada `n8n import:workflow`).

## 4. Configuración Post-Instalación (Manual requerida)

Dado que Immich requiere que el usuario cree una cuenta de administrador la primera vez que se inicia el sistema, hay un último paso que **no puede automatizarse** completamente por motivos de seguridad. 

Cada vez que el proyecto se levante desde cero en una computadora nueva, el operador deberá realizar estos 5 pasos por única vez:

1. **Crear cuenta local:** Ingresar a \`http://localhost:2283\` y crear el usuario administrador inicial.
2. **Crear la Librería Externa:** Ir a *Administration -> External Libraries*, crear una nueva librería (ej. "NOAA") y en "Edit Import Paths", añadir la ruta `/png-output`.
3. **Generar el Token:** Ir a *Account Settings -> API Keys*, generar una nueva llave y **copiar su valor secreto**.
4. **Almacenar el Token:** Pegar el valor de la llave generada dentro del archivo `configs/token` ubicado en la carpeta del repositorio.
5. **Reiniciar Procesador:** Ejecutar en la terminal `docker compose restart processor` para que el script de automatización adquiera los permisos y comience a indexar las imágenes automáticamente en la galería.
