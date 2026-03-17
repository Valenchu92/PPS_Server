# Módulo SMN: Datos Oficiales

Este módulo se encarga de procesar la información meteorológica oficial provista por el Servicio Meteorológico Nacional Argentino.

## 🛰️ Adquisición de Datos
n8n descarga periódicamente los archivos ZIP que contienen el estado de todas las estaciones del país desde el servidor del SMN. Estos archivos se guardan en `/raw_data/`.

## ⚙️ Procesamiento (`filter_smn.py`)
El script detecta la llegada del archivo y realiza las siguientes acciones:
1. **Extracción**: Si es un ZIP, lo descomprime temporalmente.
2. **Filtrado**: Busca específicamente la estación **"Río Cuarto"**.
3. **Parsing**: Extrae Temperatura, Humedad, Presión, Velocidad y Dirección del Viento.
4. **Almacenamiento**: Guarda los datos en InfluxDB con el tag `source="smn"`.

## 📌 Campos Almacenados
| Campo | Unidad |
| :--- | :--- |
| `temperature` | Celsius (°C) |
| `humidity` | Porcentaje (%) |
| `pressure` | Hectopascales (hPa) |
| `wind_speed` | km/h |
| `wind_direction` | Texto (ej: "Norte") |

## 🧪 Notas Técnicas
El script maneja la codificación `latin1` para evitar errores con caracteres especiales (tildes) comunes en los reportes del SMN. También evita procesar dos veces el mismo archivo mediante un sistema de hashes.
