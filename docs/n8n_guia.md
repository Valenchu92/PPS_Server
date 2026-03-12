# Guía de n8n para Descarga Automática de Imágenes GOES

n8n es una potente herramienta de automatización de flujos de trabajo (workflows) basada en nodos. Su contenedor, que ya tienes configurado en el `docker-compose.yml`, ejecutará estos flujos en segundo plano.

En esta guía te explicaré cómo funciona el contenedor definido en tu entorno y paso a paso cómo crear el flujo para descargar imágenes desde la página de GOES Sector (https://www.star.nesdis.noaa.gov/GOES/sector.php?sat=G19&sector=ssa).

## 1. ¿Cómo funciona el contenedor de n8n en tu entorno?

En tu archivo `docker-compose.yml`, el servicio `n8n` está configurado de esta manera:

```yaml
n8n:
  image: docker.n8n.io/n8nio/n8n
  container_name: n8n
  ports:
    - "5678:5678"
  volumes:
    - n8n-data:/home/node/.n8n
    - ./png-images:/output:rw
  restart: unless-stopped
```

**Puntos clave:**
- **Acceso:** Expone el puerto `5678`. Podrás acceder a la interfaz gráfica entrando a `http://localhost:5678` en tu navegador.
- **Persistencia de Flujos:** El volumen `n8n-data` guarda tus workflows, credenciales y configuraciones en Docker, así que no los perderás si se reinicia el contenedor.
- **Volumen de Imágenes:** El volumen `./png-images:/output:rw` es crítico. Es la carpeta donde n8n debe guardar los archivos que descargue. Todo lo que el flujo guarde en la ruta interna `/output` aparecerá en la carpeta `./png-images` de tu computadora y, por lo tanto, Immich las detectará.

## 2. Accediendo a n8n por primera vez

1. Asegúrate de que los contenedores estén corriendo (`docker compose up -d`).
2. Abre tu navegador y ve a `http://localhost:5678`.
3. La primera vez que entres, n8n te pedirá crear una cuenta de administrador local. Completa tus datos para proteger tu instancia.

## 3. Crear el Workflow para GOES

La página de sector *South America* provee múltiples imágenes que se actualizan frecuentemente. Lo ideal es leer el feed RSS o el JSON de la página (que usan de forma interna para cargar los últimos datos).
El formato que analizaremos es la imagen geocolor, cuyo patrón de URL es algo así como:
`https://cdn.star.nesdis.noaa.gov/GOES19/ABI/SECTOR/ssa/GEOCOLOR/1000x1000.jpg`

Vamos a crear un workflow que de forma periódica descargue las imágenes más recientes.

> [!NOTE]
> Puedes copiar el siguiente bloque de código JSON, ir a n8n en blanco, y simplemente **pegarlo** (Ctrl+V). n8n convertirá el JSON automáticamente en los nodos del workflow. Después de pegarlo, asegúrate de activar el flujo arriba a la derecha.

```json
{
  "name": "Descarga de Imágenes GOES",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "minutes",
              "minutesInterval": 10
            }
          ]
        }
      },
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [0, 0],
      "id": "e98e29dc-dcab-4c38-8c11-9a70f2098b1b",
      "name": "Schedule Trigger"
    },
    {
      "parameters": {
        "url": "https://cdn.star.nesdis.noaa.gov/GOES19/ABI/SECTOR/ssa/GEOCOLOR/7200x4320.jpg",
        "options": {
          "response": {
            "response": {
              "responseFormat": "file"
            }
          }
        }
      },
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [220, 0],
      "id": "5bdc4486-538a-44e2-bef0-27f31b8166c3",
      "name": "Descargar Imagen"
    },
    {
      "parameters": {
        "operation": "write",
        "fileName": "=/raw_images/goes19_ssa_geocolor_{{$now.toFormat('yyyyMMdd_HHmm')}}.jpg"
      },
      "type": "n8n-nodes-base.readWriteFile",
      "typeVersion": 1.1,
      "position": [440, 0],
      "id": "298059e6-1c21-432d-9af2-0c9f1a26af72",
      "name": "Guardar en Volumen"
    }
  ],
  "pinData": {},
  "connections": {
    "Schedule Trigger": {
      "main": [
        [
          {
            "node": "Descargar Imagen",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Descargar Imagen": {
      "main": [
        [
          {
            "node": "Guardar en Volumen",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "active": false,
  "settings": {
    "executionOrder": "v1"
  },
  "versionId": "df0618ce-16e5-4a11-b4ec-868bf0dc221c",
  "meta": {
    "instanceId": "local"
  },
  "tags": []
}
```

## 4. Explicación nodo por nodo

Si prefieres construirlo tú mismo a mano, esta es la secuencia de nodos que debes usar:

### Nodo 1: Schedule Trigger (Trigger programado)
- **Función:** Este nodo despierta a tu workflow cada cierta cantidad de tiempo.
- **Configuración:** Ponlo en "Interval" -> cada X tiempo (ej. `6 Hours`).
- *Nota: Empieza con un tiempo alto para no sobrecargar el servidor de la NOAA durante tus pruebas.*

### Nodo 2: HTTP Request (Descargar Imagen)
- **Función:** Descargará el archivo estático que contiene la imagen pre-generada de 7200x4320 píxeles.
- **URL:** `https://cdn.star.nesdis.noaa.gov/GOES19/ABI/SECTOR/ssa/GEOCOLOR/7200x4320.jpg`
- **Settings importantes:** En las opciones del nodo asegúrate de expandir "Options", ir a "Response" y setear **Response Format** a `File`. De esta forma n8n sabe que está bajando una imagen binaria en lugar de texto o JSON.

### Nodo 3: Read/Write Files from Disk (Guardar en Volumen)
- **Función:** Tomará el archivo que descargó el nodo anterior en memoria y lo guardará físicamente en el volumen de Docker correspondiente.
- **Operation:** `Write`
- **File Name:** `=/raw_images/goes19_ssa_geocolor_{{$now.toFormat('yyyyMMdd_HHmm')}}.jpg`
  - Aquí estamos diciéndole que lo guarde en la carpeta `/raw_images` (que en tu PC es la carpeta local `./raw_images`).
  - Usamos una expresión para nombrar al archivo e insertarle el timestamp actual (ej. `goes19_ssa_geocolor_20260310_1900.jpg`), de modo que con cada bajada no sobreescriba a la anterior.

## 5. Validación

1. Selecciona el **Modo de Prueba (Test Workflow)** en n8n para correrlo manualmente por primera vez.
2. Si los 3 pasos se ven en verde, significa que descargó y guardó.
3. Puedes ir a la carpeta de tu computadora llamada `png-images`. Deberías ver el archivo `.jpg` recién descargado allí.
4. Debido a que `immich-server` tiene acceso al mismo volumen en `docker-compose.yml`, verás que la galería en Immich reflejará pronto la gráfica de GOES.
5. No olvides **Activar (Active)** el workflow con el switch superior derecho, para que siga corriendo en los intervalos automáticos sin ti.
