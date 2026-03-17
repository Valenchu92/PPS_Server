# Guía de n8n para Descarga Automática de Imágenes GOES

n8n es una potente herramienta de automatización de flujos de trabajo (workflows) basada en nodos. Su contenedor, que ya tienes configurado en el `docker-compose.yml`, ejecutará estos flujos en segundo plano.

En esta guía te explicaré cómo funciona el contenedor definido en tu entorno y paso a paso cómo crear el flujo para descargar imágenes desde la página de GOES Sector (https://www.star.nesdis.noaa.gov/GOES/sector.php?sat=G19&sector=ssa).

## 1. ¿Cómo funciona el contenedor de n8n en tu entorno?

En tu archivo `docker-compose.yml`, el servicio `n8n` está configurado de esta manera:

```yaml
n8n:
  image: n8nio/n8n:latest
  container_name: n8n
  ports:
    - "${N8N_PORT:-5678}:5678"
  volumes:
    - n8n-data:/home/node/.n8n
    - ${HOST_RAW_IMAGES_DIR:-./raw_images}:/raw_images:rw
    - ${HOST_RAW_DATA_DIR:-./raw_data}:/raw_data:rw
  restart: unless-stopped
```

**Puntos clave:**
- **Acceso:** Expone el puerto `5678` (por defecto). Accede mediante `http://localhost:5678`.
- **Persistencia:** El volumen `n8n-data` guarda tus workflows y credenciales.
- **Volúmenes de Datos:** 
    - `/raw_images`: Donde n8n guarda las imágenes satelitales crudas para que el `processor` las recorte.
    - `/raw_data`: Donde n8n guarda los JSON/TXT de telemetría para su ingesta en InfluxDB.

## 2. Accediendo a n8n por primera vez

1. Asegúrate de que los contenedores estén corriendo (`docker compose up -d`).
2. Abre tu navegador y ve a `http://localhost:5678`.
3. La primera vez que entres, n8n te pedirá crear una cuenta de administrador local.

## 3. Crear el Workflow para GOES

Vamos a crear un workflow que de forma periódica descargue las imágenes más recientes de 7200x4320 píxeles.

> [!NOTE]
> Puedes copiar el siguiente bloque de código JSON, ir a n8n en blanco, y simplemente **pegarlo** (Ctrl+V). n8n lo convertirá automáticamente en los nodos del workflow.

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
            "responseFormat": "file"
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
  "active": true,
  "settings": {
    "executionOrder": "v1"
  }
}
```

## 4. Explicación nodo por nodo

### Nodo 1: Schedule Trigger
Despierta el flujo cada 10 minutos (puedes ajustarlo según necesidad).

### Nodo 2: HTTP Request
Descarga la imagen binaria (7200x4320) de la NOAA. Es vital que el **Response Format** esté seteado en `File`.

### Nodo 3: Write to Disk
Escribe la imagen en la carpeta `/raw_images`. 
- El `processor` detectará este archivo instantáneamente.
- El archivo resultante será procesado, recortado y luego guardado en `png-images`.

## 5. Validación

1. Selecciona el **Modo de Prueba (Test Workflow)** en n8n.
2. Si los 3 pasos se ven en verde:
   - Revisa la carpeta local `./raw_images`: deberías ver el archivo balanceado.
   - Revisa la carpeta local `./png-images`: segundos después debería aparecer el recorte de Córdoba.
3. Puedes ver la imagen procesada en la Galería Estática (`http://localhost:8080/goes/`).
4. No olvides **Activar (Active)** el workflow para que funcione de forma autónoma.
