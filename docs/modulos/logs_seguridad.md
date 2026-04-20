# Observabilidad y Seguridad (PLG + CrowdSec)

Este módulo describe la arquitectura de telemetría y protección activa implementada en el Sistema de Información Climática. El objetivo principal es mantener una visibilidad total sobre los contenedores y proteger la aplicación web (la galería de imágenes) frente a ataques automatizados, todo sin comprometer la filosofía de contenedores sin privilegios root.

## Arquitectura de Observabilidad (Stack PLG)

El sistema centraliza los registros (logs) de todos los contenedores utilizando el ecosistema PLG, que destaca por su eficiencia y bajo consumo de recursos al no indexar el texto completo, sino apoyarse en etiquetas (*labels*).

### 1. Promtail (Recolector)
Promtail actúa como un agente en segundo plano. Mediante acceso de solo lectura al socket de Docker (`/var/run/docker.sock`), captura la salida estándar (`stdout`/`stderr`) de cada uno de los contenedores del proyecto.
*   **Etiquetado Automático:** Promtail añade metadatos vitales a cada línea de log, como el ID del contenedor, el nombre del servicio de Compose (`compose_service`) y la imagen utilizada.
*   **Envío:** Transfiere los logs procesados hacia Loki en tiempo real.

### 2. Loki (Almacenamiento y Motor)
Loki es el cerebro de los logs. Recibe el flujo de Promtail, lo comprime en bloques de tiempo y lo guarda en el almacenamiento persistente.
*   **Almacenamiento Local (Sin Root):** Para cumplir con las normativas de seguridad, el volumen de Loki (`/tmp/loki`) está montado mediante un *Bind Mount* hacia la carpeta del host `./loki-data`. Esta carpeta es gestionada con permisos `777` en el script inicializador, permitiendo que el usuario interno de Loki (`uid: 10001`) almacene la información sin necesidad de que el contenedor requiera privilegios `root`.
*   **Compactor:** Se encuentra configurado para limpiar y retener logs por un máximo de 7 días, garantizando que el almacenamiento del servidor no se sature.

### 3. Grafana (Visualización)
Actúa como la única interfaz gráfica del proyecto. Además de mostrar los dashboards del clima (vía InfluxDB), permite la exploración de logs utilizando el lenguaje **LogQL**. Los administradores pueden acceder a la pestaña *Explore* para correlacionar eventos de errores climáticos con fallos en los contenedores.

---

## Arquitectura de Seguridad (CrowdSec)

Para asegurar la interfaz web (contenedor `gallery`), se implementó un Sistema de Prevención de Intrusiones (IPS) colaborativo y moderno llamado CrowdSec.

### 1. Motor CrowdSec
El motor centralizado se encarga de analizar los logs (vía lectura directa del socket de Docker) y aplicar expresiones regulares y parseos específicos para Nginx y tráfico HTTP.
*   **Detección Local:** Si detecta escaneos de puertos, ataques de fuerza bruta o escaneos web maliciosos en tiempo real, bloquea la IP automáticamente.
*   **Exclusiones:** Posee reglas de exclusión (Whitelists) nativas para evitar el bloqueo accidental de IPs de la red local o privadas (ej. `127.0.0.1`).
*   **Inteligencia Colectiva (CAPI):** Constantemente descarga una "Lista Negra de la Comunidad" con miles de direcciones IP reportadas mundialmente por otros servidores, bloqueándolas de forma preventiva.

### 2. Nginx Bouncer
El componente de aplicación de seguridad reside directamente en el servidor web.
*   Se compiló un módulo oficial de CrowdSec para Nginx (`crowdsec-nginx-bouncer`) en una imagen basada en `debian:bookworm-slim`.
*   El Bouncer intercepta cada solicitud entrante al servidor web en el puerto 8080 y la contrasta con el motor CrowdSec (vía API local HTTP).
*   Si la IP del cliente está en la lista de bloqueos o ha sido detectada realizando un ataque local, el Bouncer interrumpe inmediatamente la conexión y devuelve un `HTTP 403 Forbidden`, protegiendo al servidor de procesamiento innecesario.

---

## Guía de Verificación y Administración (Cheatsheet)

Como administrador del sistema, puedes auditar y gestionar el entorno de seguridad y observabilidad utilizando los siguientes comandos directamente desde la terminal del servidor.

### Gestión de CrowdSec
Todos los comandos de CrowdSec se ejecutan comunicándose con el agente interno mediante Docker Compose.

*   **Ver reglas (escenarios) activos:** Enumera todas las reglas de ataque y vulnerabilidades que el sistema está vigilando activamente.
    ```bash
    docker compose exec crowdsec cscli scenarios list
    ```
*   **Ver métricas internas:** Muestra estadísticas en tiempo real sobre cuántas líneas de log se han leído y cuántas peticiones se han excluido o procesado.
    ```bash
    docker compose exec crowdsec cscli metrics
    ```
*   **Ver estado del Bouncer:** Verifica que el agente de Nginx está correctamente conectado y registrado en el motor de seguridad.
    ```bash
    docker compose exec crowdsec cscli bouncers list
    ```

### Simulacro y Gestión de Bloqueos (Baneos)
*   **Bloquear una IP manualmente:** Útil para realizar simulacros de seguridad (ej. bloquear localhost) o sancionar una IP conocida.
    ```bash
    docker compose exec crowdsec cscli decisions add -i 127.0.0.1 -d 1h
    ```
*   **Ver IPs bloqueadas localmente:** (No muestra la lista masiva de la comunidad para evitar saturar la terminal).
    ```bash
    docker compose exec crowdsec cscli decisions list
    ```
*   **Retirar bloqueo de una IP:** Elimina una IP de la lista negra local para restaurar su acceso.
    ```bash
    docker compose exec crowdsec cscli decisions delete -i 127.0.0.1
    ```

### Monitoreo del Stack PLG
*   **Explorar logs visualmente:** Ingresa a `http://localhost:3000` (Grafana), ve a la pestaña **Explore**, selecciona el Data Source **Loki** y utiliza **LogQL** para filtrar por aplicación. Ejemplo: `{compose_service="gallery"}`.
*   **Auditar estado de Promtail:** Si los logs no parecen estar llegando a la interfaz, verifica si el recolector tiene errores leyendo el socket de Docker.
    ```bash
    docker compose logs -f promtail
    ```
*   **Auditar estado de Loki:** Útil si hay problemas de lectura/escritura en disco o de persistencia local.
    ```bash
    docker compose logs -f loki
    ```
