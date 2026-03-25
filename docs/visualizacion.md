# Visualización y Monitoreo

El sistema ofrece dos interfaces principales para el monitoreo de los datos.

## 📊 Grafana (Dashboard Central)
Es el frontend principal del sistema. 

### Paneles Incluidos:
- **Pronóstico Zambretti**: Un panel "Stat" que muestra la frase actual (ej: "Tormentoso, mucha lluvia") calculada en base a la presión y tendencias.
- **Temperatura (Comparada)**: Gráfico de series temporales que superpone SMN vs OpenWeatherMap. **Filtra automáticamente datos inconsistentes sin fuente.**
- **Presión Atmosférica**: Gráfico comparativo de presión en hPa.

### Acceso:
`http://localhost:3000` (Solo accesible desde el host local por seguridad).
Usuario/Password por defecto: `admin / admin`

## 🖼️ Galería de Imágenes (Gallery)
Un servidor Nginx liviano que permite ver los últimos recortes satelitales y el clima actual en tiempo real.

### Características:
- **Visualización Estática:** Muestra la captura más reciente del GOES para evitar sobrecarga visual.
- **Prioridad de Datos:** Muestra el clima del SMN si está actualizado (< 70 min), de lo cual hace fallback a OWM. Indica la fuente dinámicamente.
- **Seguridad:** Corre como usuario no-root y tiene límites de tráfico (3r/s).

### Acceso:
`http://localhost:8080` (Puerto 8080 mapeado al 8080 interno del contenedor).

## 🔔 Alertas
InfluxDB y Grafana están preparados para configurar alertas (ej: caída brusca de presión) que pueden ser enviadas vía n8n a Telegram o Email.
