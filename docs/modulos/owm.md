# Módulo OpenWeatherMap (API)

Este módulo complementa los datos oficiales del SMN utilizando la API global de OpenWeatherMap, permitiendo una comparación en tiempo real.

## 🔗 Integración con n8n
El flujo en n8n realiza una petición HTTP al endpoint `weather` de OWM cada hora. 

Para que el servidor procese estos datos, el flujo de n8n debe guardar el resultado en:
`/raw_data/owm_current.json`.

## ⚙️ Procesamiento (`filter_owm.py`)
Al detectar el archivo JSON, el procesador:
1. Lee el timestamp original de la medición (UTC).
2. Extrae las métricas principales.
3. Guarda en InfluxDB con el tag `source="owm"`.

## 🔄 Lógica de Prioridad (Robustez y Fallback)
El sistema está diseñado para que la información oficial (SMN) sea la protagonista, pero garantizando que nunca haya "huecos" de información si el SMN falla. 

### ¿Cómo se calcula la antigüedad?
Es crucial entender que el sistema no mide cuánto tiempo pasó desde que se descargó el archivo, sino la **edad de la observación real**:
1. El archivo del SMN tiene una hora interna (ej: 11:00). Esa hora se guarda en `latest_weather.json`.
2. El procesador de OWM compara la hora actual contra esa hora de observación. 
3. **Umbral de 70 minutos:** Si han pasado más de 70 minutos desde la última medición oficial (por ejemplo, son las 12:11 y el último dato es de las 11:00), el sistema asume que el reporte oficial se retrasó o falló.
4. En ese caso, OWM toma el control del dashboard web marcando `source: owm`.

### Ventajas de una alta frecuencia de descarga
Aunque n8n descargue el archivo del SMN cada 20 minutos, los 70 minutos de espera no se "reinician" con la descarga. Solo se reiniciarán cuando el SMN publique un archivo con una **nueva hora de observación** (ej: 12:00). 
- Esto permite capturar el dato oficial apenas es publicado, minimizando el tiempo que el sistema permanece con datos de OWM (que es una estimación API).

## 📊 Comparativa en Grafana
En el tablero principal, los ráficos de **Temperatura** y **Presión** están configurados para mostrar ambas fuentes simultáneamente. Esto facilita la detección de anomalías o retrasos en la actualización de los datos oficiales.

## 🛠️ Requisitos
Es necesario contar con una `API_KEY` válida de OpenWeatherMap configurada en el workflow de n8n.
