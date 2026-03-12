# PRODUCT REQUIREMENTS DOCUMENT

**Sistema de Información Climática con Integración de Imágenes Satelitales NOAA y Datos Meteorológicos**


**Proyecto**: Sistema de Información Climática NOAA  
**Autor**: Valentín Mora  
**Institución**: GIDAT – Facultad de Ingeniería, UNRC  
**Tutor UNRC**: Noelia Veglia  
**Tutor GIDAT**: Sebastián J. Tosco  
**Período**: Febrero – Abril 2026  
**Versión**: 1.0  
**Fecha**: Marzo 2026  

## 1. Descripción General del Sistema

Este documento describe los requerimientos del sistema de información climática desarrollado como Práctica Profesional Supervisada en el marco del GIDAT (Grupo de Investigación y Desarrollo Aplicado a las Telecomunicaciones) de la Facultad de Ingeniería de la UNRC.

El sistema tiene como objetivo centralizar, procesar y visualizar imágenes satelitales NOAA provenientes de dos fuentes: descarga automatizada desde una página web pública, y decodificación local de señales APT capturadas con hardware SDR (Software Defined Radio). Todas las imágenes se almacenan en un volumen Docker compartido y se visualizan mediante Immich, una plataforma de gestión de fotos auto-hospedada.

El sistema está diseñado para ser operado por una única persona y desplegado íntegramente con Docker y Docker Compose.

## 2. Arquitectura del Sistema

### 2.1 Diagrama de componentes

El sistema se compone de cuatro bloques principales que interactúan a través de volúmenes Docker compartidos:

| Componente | Tipo | Descripción |
| --- | --- | --- |
| Página web pública | Fuente externa | Repositorio web con imágenes PNG de satélites NOAA, accesible públicamente. |
| n8n | Automatización / Docker | Orquestador de workflows que descarga periódicamente PNGs desde la web y los deposita en el volumen compartido. |
| Procesador noaa-apt | Docker (imagen custom) | Contenedor que monitorea una carpeta de WAV, decodifica archivos nuevos con noaa-apt y exporta PNGs al volumen compartido. También elimina WAVs con más de 7 días de antigüedad. |
| Volumen compartido | Docker Volume | Carpeta persistente montada en múltiples contenedores. Actúa como punto de integración entre fuentes y visualizador. |
| Immich | Docker (imagen oficial) | Plataforma de gestión de imágenes auto-hospedada. Lee el volumen compartido y presenta todas las imágenes en una galería web. |

### 2.2 Flujo de datos

**Flujo A – Descarga automática desde la web**
1. n8n ejecuta un workflow programado (cron) que consulta la página web pública.
2. El workflow descarga los PNG más recientes disponibles.
3. Los archivos PNG se guardan en la carpeta compartida (volumen Docker).
4. Immich detecta los archivos nuevos y los agrega a la galería.

**Flujo B – Decodificación local de señales WAV**
1. El usuario deposita archivos WAV (grabaciones SDR de señales APT NOAA) en una carpeta de entrada.
2. El contenedor Procesador monitorea continuamente esa carpeta en busca de WAVs nuevos.
3. Al detectar un archivo nuevo, ejecuta noaa-apt para decodificarlo y genera el PNG correspondiente.
4. El PNG resultante se guarda en el volumen compartido.
5. Immich detecta el archivo nuevo y lo agrega a la galería.

**Limpieza automática de WAVs**
1. El Procesador también ejecuta periódicamente una rutina de limpieza.
2. Todo archivo WAV en la carpeta de entrada con fecha de creación mayor a 7 días es eliminado automáticamente.

## 3. Especificación de Componentes

### 3.1 Procesador noaa-apt (imagen Docker custom)

Este es el componente central de desarrollo propio. Se trata de un contenedor Docker basado en una imagen Linux liviana (Debian o Alpine) que incluye el binario de noaa-apt de Martín Bernardi.

**Responsabilidades**
- Monitorear la carpeta `/input` (volumen montado) en busca de archivos `.wav` nuevos.
- Para cada WAV nuevo detectado, ejecutar el comando noaa-apt y generar el PNG de salida.
- Guardar el PNG resultante en la carpeta `/output` (volumen compartido con Immich y n8n).
- Ejecutar periódicamente una rutina de limpieza que elimine WAVs con antigüedad mayor a 7 días.
- Registrar en logs cada operación realizada (decodificación y eliminación de archivos).

**Lógica de monitoreo**
- Usar `inotifywait` (Linux) o polling con intervalo configurable para detectar archivos nuevos en `/input`.
- Evitar reprocesar un WAV ya decodificado. Se puede mantener un archivo de registro o comparar con los PNGs ya existentes en `/output`.
- El nombre del PNG de salida debe preservar el nombre base del WAV original (p. ej., `noaa15_20260301.wav` → `noaa15_20260301.png`).

**Lógica de limpieza**
- Ejecutar la rutina de limpieza cada hora (o al iniciar el contenedor, y luego periódicamente).
- Listar todos los archivos `.wav` en `/input`.
- Si la fecha de creación (o modificación) del archivo es anterior a 7 días respecto a la fecha actual, eliminarlo.
- Registrar en log cada archivo eliminado con su nombre y fecha.

**Opciones de noaa-apt**
- Comando base: `noaa-apt <input.wav> -o <output.png>`
- Opciones recomendadas: agregar `--rotate` si el paso del satélite es ascendente (de sur a norte).
- Opciones opcionales a evaluar: `--false-color`, `--map` overlays.

### 3.2 n8n – Automatización de descarga web

n8n es una plataforma de automatización de workflows que se desplegará como contenedor Docker usando su imagen oficial.

**Workflow a implementar**
- **Trigger**: Cron job con intervalo configurable (p. ej., cada 6 horas).
- **Paso 1**: HTTP Request al endpoint de la página web pública para obtener el listado de imágenes disponibles.
- **Paso 2**: Filtrar los archivos PNG más recientes (por fecha o nombre).
- **Paso 3**: Descargar cada PNG nuevo.
- **Paso 4**: Guardar el archivo en la carpeta `/output` (volumen compartido).
- **Paso 5** (opcional): Registro en log o notificación de éxito/error.

**Consideraciones**
- El workflow debe verificar si el archivo ya existe en `/output` antes de descargarlo, para evitar duplicados.
- n8n persiste sus datos (workflows, credenciales) en un volumen propio para sobrevivir reinicios.

### 3.3 Immich – Visualización de imágenes

Immich es una aplicación de galería de fotos auto-hospedada que se desplegará usando su `docker-compose` oficial.

**Configuración requerida**
- Montar el volumen compartido como una biblioteca externa en Immich.
- Configurar Immich para escanear periódicamente la carpeta de la biblioteca externa y detectar imágenes nuevas.
- Las imágenes PNG de ambas fuentes (n8n y Procesador) deben ser visibles en la misma galería.

**Consideraciones**
- Immich requiere una base de datos PostgreSQL y un servicio Redis, que se incluyen en su docker-compose oficial.
- La sincronización de la biblioteca externa puede configurarse manualmente o mediante un cron interno de Immich.
- No se requiere autenticación multi-usuario; un único usuario administrador es suficiente.

## 4. Estructura de Carpetas y Volúmenes Docker

A continuación se describe la estructura de directorios del proyecto y la relación con los volúmenes Docker:

```text
noaa-system/
├── docker-compose.yml          # Orquestación general
├── processor/                  # Imagen Docker del Procesador
│   ├── Dockerfile
│   └── entrypoint.sh           # Script principal de monitoreo y limpieza
├── volumes/
│   ├── wav-input/              # WAVs cargados por el usuario (→ Procesador)
│   ├── png-output/             # PNGs generados (→ Immich + n8n escriben aquí)
│   ├── immich-data/            # Datos internos de Immich
│   └── n8n-data/               # Workflows y configuración de n8n
└── .env                        # Variables de entorno
```

## 5. Especificación del docker-compose.yml

El archivo `docker-compose.yml` debe definir los siguientes servicios y sus relaciones:

### 5.1 Servicios

| Componente | Tipo | Descripción |
| --- | --- | --- |
| processor | `build: ./processor` | Imagen custom. Monta `wav-input` como `/input` y `png-output` como `/output`. Ejecuta `entrypoint.sh`. |
| n8n | `image: n8nio/n8n` | Imagen oficial. Expone puerto 5678. Monta `png-output` como `/output` y `n8n-data` para persistencia. |
| immich-server | `image: ghcr.io/immich-app/immich-server` | Servidor principal de Immich. Monta `png-output` como biblioteca externa e `immich-data` para persistencia. |
| immich-machine-learning | `image: ghcr.io/immich-app/immich-machine-learning` | Servicio de ML de Immich (reconocimiento facial, búsqueda). Requerido por la arquitectura oficial. |
| postgres | `image: postgres:14` | Base de datos de Immich. |
| redis | `image: redis:7` | Cache de Immich. |

### 5.2 Volúmenes compartidos

- **png-output**: Compartido entre `processor` (escritura), `n8n` (escritura) e `immich-server` (lectura como biblioteca externa).
- **wav-input**: Exclusivo del `processor` (lectura/escritura para limpieza).
- **n8n-data**: Exclusivo de `n8n` (persistencia de workflows).
- **immich-data**: Exclusivo de `immich-server` (persistencia de metadatos).

## 6. Dockerfile del Procesador

El Dockerfile del Procesador debe construir una imagen que incluya:

- **Imagen base**: `debian:bookworm-slim` o `ubuntu:22.04`.
- **Instalación de dependencias**: `curl`, `inotify-tools`, `bash`, y cualquier librería requerida por noaa-apt.
- **Descarga del binario** de noaa-apt desde el repositorio oficial de Martín Bernardi (https://noaa-apt.mbernardi.com.ar/download.html) o compilación desde el código fuente en GitHub (https://github.com/martinber/noaa-apt).
- Copia del script `entrypoint.sh` al contenedor.
- Definición de **variables de entorno** configurables: `WAV_INPUT_DIR`, `PNG_OUTPUT_DIR`, `MAX_AGE_DAYS` (default: 7).
- `ENTRYPOINT` apuntando a `entrypoint.sh`.

## 7. Script entrypoint.sh del Procesador

El script `entrypoint.sh` es el proceso principal del contenedor. Debe implementar la siguiente lógica:

### 7.1 Estructura general

- Al iniciar, ejecutar la rutina de limpieza una vez.
- Lanzar en paralelo: el loop de monitoreo de WAVs y un timer de limpieza periódica (cada 60 minutos).
- Manejar señales de terminación (SIGTERM, SIGINT) para apagado limpio.

### 7.2 Función de decodificación

- Recibe como argumento la ruta completa del WAV.
- Construye el nombre de salida del PNG basándose en el nombre del WAV (reemplazando la extensión).
- Verifica si el PNG ya existe en `/output`. Si existe, omite el procesamiento.
- Ejecuta: `noaa-apt <ruta_wav> -o <ruta_png>`
- Registra en stdout la operación realizada con timestamp.

### 7.3 Función de monitoreo

- Usa `inotifywait -m -e close_write -e moved_to ${WAV_INPUT_DIR}` para detectar nuevos archivos WAV en tiempo real.
- Para cada evento, verifica que el archivo tenga extensión `.wav` antes de procesar.
- Llama a la función de decodificación con la ruta del archivo detectado.

### 7.4 Función de limpieza

- Lista todos los archivos `.wav` en `${WAV_INPUT_DIR}`.
- Para cada archivo, obtiene su fecha de modificación con `stat`.
- Calcula la diferencia en días respecto a la fecha actual.
- Si la diferencia supera `${MAX_AGE_DAYS}` (default: 7), elimina el archivo con `rm`.
- Registra en stdout cada archivo eliminado con su nombre y antigüedad.

## 8. Variables de Entorno (.env)

El archivo `.env` centraliza la configuración del sistema. Debe incluir las siguientes variables:

| Variable | Valor por defecto | Descripción |
| --- | --- | --- |
| `WAV_INPUT_DIR` | `/input` | Ruta de la carpeta de WAVs dentro del contenedor |
| `PNG_OUTPUT_DIR` | `/output` | Ruta de la carpeta de salida de PNGs |
| `MAX_AGE_DAYS` | `7` | Días máximos de retención de archivos WAV |
| `CLEANUP_INTERVAL_MIN` | `60` | Intervalo en minutos entre rutinas de limpieza |
| `N8N_PORT` | `5678` | Puerto expuesto por n8n |
| `IMMICH_PORT` | `2283` | Puerto expuesto por Immich |
| `DB_PASSWORD` | (a definir) | Contraseña de PostgreSQL para Immich |
| `UPLOAD_LOCATION` | `./volumes/png-output` | Ruta del host para el volumen compartido de PNGs |

## 9. Configuración de Immich

### 9.1 Biblioteca externa

Para que Immich lea las imágenes generadas por ambas fuentes, se debe configurar una biblioteca externa apuntando a la carpeta `/png-output` dentro del contenedor Immich. Los pasos son:
1. Iniciar sesión en Immich con el usuario administrador.
2. Ir a Administration > Libraries > Create Library.
3. Seleccionar tipo External Library.
4. Configurar la ruta de la biblioteca como `/png-output` (ruta dentro del contenedor).
5. Activar la opción de escaneo periódico automático (Scan Schedule).

### 9.2 Usuario administrador

- Crear un único usuario administrador durante el primer inicio.
- Las credenciales deben guardarse en el archivo `.env` o en un gestor de contraseñas local.

## 10. Workflow de n8n

### 10.1 Estructura del workflow

El workflow de n8n para la descarga automática de imágenes debe seguir la siguiente secuencia de nodos:
- **Nodo 1 – Cron**: Trigger programado. Frecuencia recomendada: cada 6 horas.
- **Nodo 2 – HTTP Request**: GET al endpoint de la página web pública para obtener el listado de imágenes disponibles.
- **Nodo 3 – Code / Function**: Parsear la respuesta HTML o JSON para extraer URLs y nombres de los PNGs más recientes.
- **Nodo 4 – IF**: Verificar si el archivo PNG ya existe en `/output` (usando el nodo Read Binary File o comparando nombres). Si existe, omitir.
- **Nodo 5 – HTTP Request**: Descargar el PNG desde su URL.
- **Nodo 6 – Write Binary File**: Guardar el PNG en `/output` con el nombre original.
- **Nodo 7** – (Opcional) Respond to Webhook / Log: Registrar éxito o error.

### 10.2 Consideraciones de la web pública

- La URL exacta de la página web pública debe relevarse durante el Estudio teórico-técnico (A1).
- El formato de respuesta (HTML scraping vs. API JSON) determinará la lógica del Nodo 3.
- Manejar errores de red con reintentos configurables en n8n.

## 11. Requerimientos No Funcionales

### 11.1 Despliegue

- Todo el sistema debe poder iniciarse con un único comando: `docker compose up -d`
- El sistema debe sobrevivir reinicios del host (`restart: unless-stopped` en todos los servicios).
- No se requiere acceso desde fuera de la red local (localhost o IP local del host).

### 11.2 Almacenamiento

- Los WAVs en `/wav-input` se limpian automáticamente a los 7 días.
- Los PNGs en `/png-output` no tienen política de limpieza automática (Immich actúa como repositorio permanente).
- El espacio en disco del host debe ser monitoreado manualmente.

### 11.3 Logs

- El Procesador debe generar logs en stdout (accesibles con `docker logs processor`).
- n8n tiene su propio sistema de logs accesible desde su interfaz web.
- Immich tiene su propio sistema de logs.

### 11.4 Red

- Todos los contenedores deben estar en la misma red Docker interna (bridge).
- Solo los puertos de n8n (5678) e Immich (2283) deben exponerse al host.
- El Procesador no expone ningún puerto.

## 12. Guía de Implementación

Se recomienda el siguiente orden de implementación:

1. **Paso 1**: Crear la estructura de carpetas del proyecto.
2. **Paso 2**: Escribir el Dockerfile del Procesador e instalar noaa-apt. Verificar que el binario funcione correctamente dentro del contenedor ejecutando una decodificación manual de prueba.
3. **Paso 3**: Escribir el script `entrypoint.sh`. Probar individualmente la función de decodificación, la función de monitoreo y la función de limpieza.
4. **Paso 4**: Escribir el `docker-compose.yml` con el servicio processor solo, montando volúmenes de prueba. Verificar funcionamiento end-to-end.
5. **Paso 5**: Agregar Immich al `docker-compose.yml` siguiendo su documentación oficial. Configurar la biblioteca externa apuntando a png-output. Verificar que las imágenes del Procesador aparezcan en Immich.
6. **Paso 6**: Agregar n8n al `docker-compose.yml`. Crear y probar el workflow de descarga. Verificar que los PNGs descargados aparezcan en Immich.
7. **Paso 7**: Configurar variables de entorno en `.env` y ajustar `docker-compose.yml` para usarlas.
8. **Paso 8**: Ejecutar el sistema completo y validar ambos flujos de datos de extremo a extremo.

## 13. Referencias

- noaa-apt por Martín Bernardi: https://noaa-apt.mbernardi.com.ar/
- Repositorio GitHub de noaa-apt: https://github.com/martinber/noaa-apt
- Documentación oficial de Immich: https://immich.app/docs/overview/introduction
- Documentación oficial de n8n: https://docs.n8n.io/
- Docker Compose reference: https://docs.docker.com/compose/
- inotify-tools (Linux): https://github.com/inotify-tools/inotify-tools
- APT (Automatic Picture Transmission) en Wikipedia: https://en.wikipedia.org/wiki/Automatic_picture_transmission

— Fin del documento —
