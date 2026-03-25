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

## 🔄 Lógica de Prioridad (Fallback)
El procesador de OWM implementa una lógica de respeto hacia los datos oficiales:
- Antes de actualizar `latest_weather.json`, verifica si el SMN ha reportado datos hace menos de **70 minutos**.
- Si el SMN está actualizado, OWM guarda sus datos en InfluxDB pero **no** sobrescribe la información de la galería web.
- Si el SMN falla o sus datos son viejos, OWM toma el control del dashboard web para asegurar que la información nunca sea obsoleta.

## 📊 Comparativa en Grafana
En el tablero principal, los ráficos de **Temperatura** y **Presión** están configurados para mostrar ambas fuentes simultáneamente. Esto facilita la detección de anomalías o retrasos en la actualización de los datos oficiales.

## 🛠️ Requisitos
Es necesario contar con una `API_KEY` válida de OpenWeatherMap configurada en el workflow de n8n.
