# Seguridad y Hardening

Este documento detalla las medidas de seguridad implementadas en el PPS_Server para proteger el host, los contenedores y los servicios web contra ataques comunes.

## 1. Seguridad en el Servidor Web (Nginx)

Se han implementado cabeceras de seguridad y restricciones de acceso en `configs/gallery/default.conf`.

### Cabeceras de Seguridad (HTTP Headers)
Se añadieron las siguientes cabeceras para proteger al usuario y al servidor:
- **X-Frame-Options (SAMEORIGIN):** Previene ataques de *Clickjacking* al prohibir que la galería sea embebida en sitios de terceros.
- **X-Content-Type-Options (nosniff):** Evita que el navegador intente adivinar el tipo de contenido, mitigando ataques de ejecución de scripts maliciosos disfrazados de imágenes.
- **Referrer-Policy:** Protege la privacidad del usuario al limitar la información de referencia enviada a otros sitios.
- **Content-Security-Policy (CSP):** Define qué fuentes de contenido (scripts, estilos, imágenes) son confiables, bloqueando la ejecución de código no autorizado o inyectado.

### Restricción de Métodos
- Solo se permiten los métodos `GET` y `HEAD`. Esto convierte a la galería en un servicio puramente de **Solo Lectura**, bloqueando intentos de envío de datos (`POST`), modificación (`PUT`) o eliminación (`DELETE`).

## 2. Seguridad en Contenedores (Docker)

Se han aplicado restricciones en `docker-compose.yml` siguiendo el principio de mínimo privilegio.

### Restricción de Privilegios
- **no-new-privileges:true:** Evita que los procesos dentro del contenedor ganen nuevos privilegios mediante binarios SUID/SGID. Si un atacante tomara control de un proceso, no podría escalar a privilegios de root fácilmente.

### Aislamiento de Sistema de Archivos
- El contenedor de la **galería** está configurado en modo `read_only: true`. Esto impide que se realicen cambios permanentes en el sistema de archivos del contenedor en tiempo de ejecución, bloqueando la persistencia de malware.

### Límites de Recursos (DoS Protection)
Se han definido límites de CPU y Memoria para todos los servicios para evitar que un proceso comprometido consuma todos los recursos del host:
- **Gallery:** 256MB RAM / 0.5 CPU
- **n8n / Grafana:** 512MB RAM / 0.5 CPU
- **Processor:** 1GB RAM / 1.0 CPU
- **InfluxDB:** 2GB RAM / 1.0 CPU

## 3. Verificación de Resultados

Se han realizado pruebas manuales con `curl` para confirmar que las medidas de seguridad están activas.

### Prueba de Restricción de Métodos
Si se intenta un método de envío o modificación (como `POST` o `DELETE`), el servidor debe rechazarlo con un error 405:
```bash
# Intento de envío de datos (POST)
$ curl -X POST http://localhost:8080/ -I
HTTP/1.1 405 Method Not Allowed

# Intento de borrado de archivos (DELETE)
$ curl -X DELETE http://localhost:8080/index.html -I
HTTP/1.1 405 Method Not Allowed
```

### Prueba de Cabeceras de Seguridad
Al solicitar cualquier recurso, el servidor debe devolver las cabeceras de protección:
```bash
$ curl -I http://localhost:8080/
HTTP/1.1 200 OK
...
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; ...
```

## 4. Próximos Pasos Recomendados (Manuales)

Per decisión del usuario, no se han automatizado cambios en el host, pero se recomienda:
- **Firewall (UFW):** Permitir solo el puerto de la galería (`8080`) y SSH desde IPs de confianza.
- **Fail2Ban:** Instalar en el host para bloquear IPs que realicen intentos fallidos de conexión por SSH.
- **Seguridad SSH:** Deshabilitar login por contraseña y usar solo llaves (SSH Keys).
