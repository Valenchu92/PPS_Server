# Propuestas de Mejoras Futuras

A medida que el Sistema de Información Climática NOAA ha ido evolucionando, se han detectado oportunidades tecnológicas para llevar el proyecto al siguiente nivel. Esta sección documenta las posibles hojas de ruta y actualizaciones arquitectónicas que se podrían implementar en el futuro para aumentar la precisión, escalabilidad y robustez del sistema.

---

## 1. Evolución del Algoritmo Predictivo (Nowcasting)

Actualmente, el sistema utiliza técnicas de *Computer Vision* clásica (umbrales de color HSV y Flujo Óptico de Farnebäck) para predecir el clima. Si bien funciona bien como un Producto Mínimo Viable (MVP), presenta limitaciones en situaciones complejas (como nubes densas y lentas que engañan al flujo óptico).

**Mejoras propuestas:**
*   **Implementación de Inteligencia Artificial (Deep Learning):** Reemplazar los umbrales de color por una red neuronal convolucional (como U-Net) entrenada con el enorme dataset histórico de imágenes GOES. Esto permitiría la segmentación semántica exacta de tipos de nubes (granizo, cumulonimbus, estratos).
*   **Proyección de Máscaras vs. Bounding Boxes:** Actualmente, la predicción asume que las tormentas son cajas rectangulares, lo que puede causar falsos positivos si un frente tormentoso tiene forma diagonal o curva. La mejora consistiría en proyectar la máscara de bits (polígono exacto) calculando la colisión real sobre el área de la ciudad.

---

## 2. Infraestructura y Observabilidad

El entorno actual se basa en un esquema monolítico containerizado mediante Docker Compose.

**Mejoras propuestas:**
*   **Orquestación con Kubernetes (K8s):** Si el proyecto necesita procesar imágenes de todo el país o el continente, el procesamiento por CPU será un cuello de botella. Migrar a Kubernetes permitiría escalar los contenedores de `processor` horizontalmente.
*   **Colas de Mensajería (Message Brokers):** En lugar de utilizar bucles o temporizadores (cron jobs) para procesar las imágenes, integrar **RabbitMQ** o **Kafka** para que cada vez que `n8n` o el descargador de GOES baje una imagen nueva, se envíe un evento asíncrono que dispare el procesamiento instantáneo.

---

## 3. Frontend y Experiencia de Usuario (UI/UX)

La visualización actual con Grafana cumple perfectamente la tarea de mostrar métricas temporales y medidores (gauges) de severidad.

**Mejoras propuestas:**
*   **Mapas Meteorológicos Interactivos:** Desarrollar un dashboard personalizado (ej. usando React + Leaflet/Mapbox) que superponga las imágenes satelitales en tiempo real sobre un mapa de calles interactivo.
*   **Vectores de Proyección Visuales:** Dibujar sobre este mapa interactivo flechas que indiquen hacia dónde se dirige la tormenta visualmente, coloreadas por su severidad (ej. radar meteorológico estilo *Windy*).
*   **Notificaciones Push/Telegram:** Conectar las alertas críticas de 1HR/2HR que se guardan en InfluxDB con un bot de Telegram o alertas push para los administradores o la comunidad de la ciudad.

---

## 4. Adquisición de Datos Propios (Hardware y Satélites)

Durante el desarrollo de las prácticas profesionales, se llevó a cabo un intento de adquisición directa de datos satelitales (imágenes APT) provenientes del satélite **NOAA-19**. Para esto, se utilizó un receptor SDR **NESDR SMArtTee XTR**, acoplado a una antena sintonizada para la banda de **137.1 MHz** (frecuencia típica donde operan antenas de aficionados como la V-Dipole o la Quadrifilar Helix - QFH) y el software de decodificación **GQRX**.

Este intento no arrojó resultados positivos. Tras investigar las causas de la falta de señal, se confirmó la sospecha: **el satélite NOAA-19 fue dado de baja permanentemente el 13 de agosto de 2025** debido a un fallo crítico en sus baterías, cesando por completo sus transmisiones.

Para mitigar esta dependencia externa y robustecer el sistema desde el campus de la UNRC, se plantean las siguientes propuestas de mejora a nivel hardware:

**Mejoras propuestas:**
*   **Sistemas de Recepción Satelital de Nueva Generación:** Diseñar y construir los sistemas de adquisición de radiofrecuencia (antenas y decodificadores) necesarios para captar imágenes de satélites meteorológicos más actuales y activos, como el **NOAA-20** o **NOAA-21** (serie JPSS). Esto permitiría embeber el sistema con imágenes capturadas directamente desde las instalaciones de la UNRC.
*   **Estación Meteorológica Terrena Propia:** Poner en funcionamiento dispositivos de detección en tierra (sensores de temperatura, presión atmosférica, velocidad/dirección del viento, humedad) utilizando microcontroladores como **Arduino**, ESP32 o hardware similar. Esto eliminaría la dependencia de APIs externas (como OpenWeatherMap o el SMN) para los datos locales de Río Cuarto.
*   **Interoperabilidad Interna en la UNRC:** Establecer convenios internos con otros departamentos de la universidad (por ejemplo, la Facultad de Agronomía y Veterinaria) que ya posean estaciones meteorológicas. El objetivo es solicitar a la UTI (Unidad de Tecnología de la Información) los permisos de red correspondientes para compartir e integrar estos datos directamente a nuestra base de datos InfluxDB a través de la red interna de la UNRC.
