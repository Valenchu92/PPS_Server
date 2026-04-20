# Frontend: Dashboard del Sistema (Nginx)

El proyecto cuenta con un frontend estático, ligero y reactivo que no requiere motores pesados como Node.js ni re-creación de vistas en servidor. Actúa como el centro neural principal para visualizar los recortes del GOES, alertas tempranas (Nowcasting) y cruzar pronósticos extendidos.

## Arquitectura de Distribución
Toda la interfaz y los estilos residen en la carpeta `gallery-ui/`. Cuando el contenedor Nginx se despliega (`default.conf`), monta esta ruta como `/var/www/html` operando bajo el puerto `8080`. 

Para que este front funcione sin necesidad de base de datos directa, implementamos un esquema de acoplamiento débil basado en **JSON en disco**:
- El contenedor `processor` (Python) genera regularmente archivos estáticos como `latest_weather.json`, `owm_prediction.json`, `smn_prediction.json`, y `latest_predictions.json` sobre volúmenes compartidos.
- El Javascript frontend consume asincrónicamente (`fetch()`) estos ficheros JSON en intervalos de 2 minutos para auto-refrescar la pantalla.

## Componentes Analíticos Principales

### 1. Panel de Reproducción Satelital (GOES)
Aprovechando el `autoindex` de Nginx configurado para devolver los contenidos de un directorio listados en formato JSON, la interfaz consulta automáticamente qué recortes existen en sub-rutas como `/goes/sandwich/`. 

- **Renderizado Fluido:** Obtiene la lista, filtra por `.png`, y extrae los 10 fotogramas más recientes (ordenados cronológicamente).
- **Animación en el Cliente:** Emplea pre-caching agresivo para dibujar en canvas interactivo `<img>` los frames capturados, brindando animaciones a demanda sin sobrecargar la red.

### 2. Tablero Cruzado de Predicción (SMN vs OWM)
Uno de los puntos de orgullo de nuestra UI es la estandarización y fusión de proveedores dispares bajo una misma métrica visual empleando **Chart.js**. 

**El Motor Inteligente de Pestañas:**
Para evitar confusiones al operador, la interfaz inspecciona la firma de la fuente principal de observación de temperatura (`data.source`). Si los polígonos del SMN se cayeron y el clima actual es suministrado por OpenWeatherMap, la lógica de JS activará automáticamente la pestaña inferior de predicciones para OWM.

### 3. Filtros Interactivos de Escala Diaria
Como la API de OWM provee hasta 5 días de predicción por hora continua, creamos un **Day Selector dinámico**. Este componente de `script.js` escanea los datos JSON, agrupa las mediciones usando UTC unificado y genera tarjetas ("chips") clicables dinámicos, que revelan la curva de calor/lluvia individual del día seleccionado en el canvas maestro.
