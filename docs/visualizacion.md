# Visualización y Monitoreo

El sistema ofrece dos interfaces principales para el monitoreo de los datos.

## 📊 Grafana (Dashboard Central)
Es el frontend principal del sistema. 

### Paneles Incluidos:
- **Pronóstico Zambretti**: Un panel "Stat" que muestra la frase actual (ej: "Tormentoso, mucha lluvia") calculada en base a la presión y tendencias.
- **Temperatura (Comparada)**: Gráfico de series temporales que superpone SMN vs OpenWeatherMap.
- **Presión Atmosférica**: Gráfico comparativo de presión en hPa.
- **Tendencia Barométrica**: Visualización de la evolución de la presión en las últimas 3 horas.

### Acceso:
`http://localhost:3000`
Usuario/Password por defecto: `admin / admin`

## 🖼️ Galería de Imágenes (Gallery)
Un servidor Nginx liviano que permite ver los últimos recortes satelitales directamente desde un navegador.

### Acceso:
`http://localhost:8080`

## 🔔 Alertas
InfluxDB y Grafana están preparados para configurar alertas (ej: caída brusca de presión) que pueden ser enviadas vía n8n a Telegram o Email.
