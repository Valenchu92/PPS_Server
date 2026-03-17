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

## 📊 Comparativa en Grafana
En el tablero principal, los ráficos de **Temperatura** y **Presión** están configurados para mostrar ambas fuentes simultáneamente. Esto facilita la detección de anomalías o retrasos en la actualización de los datos oficiales.

## 🛠️ Requisitos
Es necesario contar con una `API_KEY` válida de OpenWeatherMap configurada en el workflow de n8n.
