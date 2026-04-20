# Bitácora de Desafíos y Lecciones Aprendidas

Este documento registra los desafíos técnicos, errores críticos y soluciones implementadas durante el desarrollo del Sistema de Información Climática. El objetivo es documentar la evolución del proyecto y servir como referencia para futuros desarrollos.

---

## ⚡ Incidente: El Falso Positivo de la "Bounding Box" Roja
**Fecha:** 28 de Marzo, 2026  
**Módulo afectado:** `processor` (OpenCV / Nowcasting)

### 🔍 El Problema
Durante las pruebas del tablero de **Nowcast Predictivo** en Grafana, se observó que el sistema reportaba consistentemente un **Nivel 3 (Lluvia Fuerte)** en Río Cuarto, a pesar de que las imágenes satelitales del GOES mostraban cielos despejados. Los velocímetros en Grafana fluctuaban erráticamente y marcaban alertas máximas sin justificación meteorológica.

### 🕵️ Diagnóstico
Tras una investigación profunda del flujo de datos, se descubrieron dos causas raíz interconectadas:

1.  **Fuego Amigo (Visualización vs. Análisis):** 
    En el script `crop_goes.py`, se dibujaba un recuadro de color **Rojo Puro (BGR: 0,0,255)** sobre la ciudad de Río Cuarto para facilitar su ubicación visual en la galería. 
    Posteriormente, el script `nowcast_storm.py` analizaba esa *misma* imagen. Al buscar píxeles rojos (indicadores de nubes convectivas frías), encontraba el recuadro artificial y lo interpretaba como una tormenta severa estacionada exactamente sobre la ciudad.

2.  **Umbrales HSV Permisivos:**
    Los rangos de color para el nivel de "Lluvia Fuerte" eran demasiado amplios. Esto provocaba que tonalidades marrones oscuras del suelo cordobés o ruidos en la imagen satelital fueran clasificados erróneamente como núcleos de tormenta.

### 🛠️ Solución Implementada
Se aplicó un enfoque de tres capas para robustecer el detector:

1.  **Cambio de Espectro Cronático:** Se modificó el color de la Bounding Box visual a **Verde Puro (0,255,0)**. El verde es un color que no existe en las capas analíticas del satélite (Sandwich/Radiatión), por lo que el analizador de tormentas ahora lo ignora por completo.
2.  **Ajuste de Sensibilidad (Tuning):** Se incrementaron los requisitos de **Saturación y Valor (Brillo)** en el espacio HSV para los niveles 3 y 4. Ahora, solo los colores rojos y amarillos intensos "neón" (típicos de los topes de nubes muy fríos) activan la alerta, descartando el ruido del terreno.
3.  **Filtro de Ruido Estático:** Se implementó un filtro de velocidad en el script de Nowcasting. Cualquier objeto que no se desplace al menos **0.3 píxeles** entre frames es descartado. Esto elimina detecciones accidentales de bordes políticos o características geográficas estáticas.

### 💡 Lección Aprendida
> "Nunca utilices para visualización decorativa colores que formen parte de tu lógica de procesamiento de imágenes." 
> Separar las capas de "anotación para humanos" de las capas de "entrada para algoritmos" es fundamental en sistemas de visión artificial.

---

## 📈 Evolución a Proyección Tendencial Ponderada (3 Imágenes)
**Fecha:** 28 de Marzo, 2026  
**Mejora:** Estabilidad de vectores de movimiento.

### 🔍 El Problema Original
El sistema inicial solo comparaba **2 imágenes** (1 intervalo de 10 min). Esto lo hacía muy sensible a "saltos" momentáneos o ruidos en la imagen satelital. Una nube que crecía lateralmente podía generar un vector de movimiento exagerado, disparando alertas falsas de impacto.

### 🛠️ La Solución: Historial de Corto Plazo
Se modificó el algoritmo para cargar las **últimas 3 imágenes disponibles**. Esto genera dos campos de movimiento:
1.  **Flujo Previo ($V_{prev}$):** Movimiento entre $T_{-20min}$ y $T_{-10min}$.
2.  **Flujo Reciente ($V_{rec}$):** Movimiento entre $T_{-10min}$ y $T_{actual}$.

Se implementó una **Combinación Ponderada** mediante la fórmula:
$$V_{final} = (V_{rec} \times 0.7) + (V_{prev} \times 0.3)$$

Esta decisión técnica permite que el sistema tenga **inercia** (no cambia de rumbo por un solo frame ruidoso) pero mantenga **sensibilidad** (el 70% del peso sigue siendo la realidad más inmediata).

---

## 🛡️ Refactorización Estructural y Endurecimiento (Hardening)
**Fecha:** 28 de Marzo, 2026  
**Mejora:** Robustez, Seguridad y Mantenibilidad.

### ⚙️ El Problema: Código Duplicado y Fragilidad
A medida que el proyecto creció, se detectaron tres áreas de riesgo:
1.  **DRY (Don't Repeat Yourself):** Funciones como el cálculo de hashes o la conexión a InfluxDB estaban copiadas en 6 archivos diferentes. Cualquier cambio de configuración requería editar todos esos archivos.
2.  **Fragilidad de Red:** Si el servidor del SMN o NOAA fallaba por solo 1 segundo, el script daba error y se perdían datos hasta la siguiente ejecución (10-30 min después).
3.  **Seguridad (Mínimo Privilegio):** El contenedor `processor` corría como usuario **root**, lo cual es una vulnerabilidad de seguridad innecesaria.

### 🛠️ Soluciones Implementadas

1.  **Módulo Central de Utilidades ([`utils.py`](file:///home/valentin/Desktop/Practicas/PPS_Server/processor/utils.py)):**
    Se creó una "librería interna" para el proyecto. Ahora, si se necesita cambiar el Token de InfluxDB o la lógica de seguridad, se hace en un solo lugar. Esto reduce drásticamente las posibilidades de error humano durante el mantenimiento.

2.  **Resiliencia con Exponential Backoff:**
    Se implementó la función `safe_download`. Si una descarga falla, el sistema "respira" y reintenta automáticamente:
    - Intento 1: Inmediato.
    - Intento 2: +2 segundos.
    - Intento 3: +4 segundos.
    - Intento 4: +8 segundos.
    Esto permite que el sistema sea inmune a micro-cortes de internet o saturaciones temporales de los servidores oficiales.

3.  **Seguridad No-Root:**
    Se modificó el `Dockerfile` para crear un usuario dedicado (`appuser`). El procesador ahora ejecuta su lógica sin permisos de administrador, protegiendo al host de posibles ataques que exploten vulnerabilidades en las librerías de procesamiento (como OpenCV o NumPy).

4.  **Orquestación de Procesos Internos:**
    Se rediseñó el [`entrypoint.sh`](file:///home/valentin/Desktop/Practicas/PPS_Server/processor/entrypoint.sh) utilizando una función `run_periodic`. Esto asegura que si una tarea de fondo (como la sincronización con la nube) muere, el contenedor pueda ser monitoreado o reiniciado de forma más limpia, evitando "procesos zombie".

---

## 🔬 ¿Cómo funciona el Algoritmo de Gunnar Farnebäck?
Para el cálculo del desplazamiento de nubes, utilizamos el método de **Farnebäck** (implementado en OpenCV como `calcOpticalFlowFarneback`). Es uno de los algoritmos de flujo óptico densos más respetados en la industria.

### Conceptos Clave:
1.  **Expansión Polinomial:** El algoritmo estima la vecindad de cada píxel utilizando una **función cuadrática** ($f(x) \approx x^T A x + b^T x + c$). En lugar de solo mirar el brillo, intenta entender la "geometría" local de la nube.
2.  **Seguimiento de Desplazamiento:** Al comparar dos imágenes, el algoritmo busca cómo se ha desplazado esa superficie polinomial. Si la "parábola" que representa a la nube se movió 3 píxeles a la derecha, ese es el vector resultante.
3.  **Flujo Denso:** A diferencia de otros métodos que solo siguen "esquinas" (como Lucas-Kanade), Farnebäck calcula el movimiento para **cada píxel de la imagen**. Esto es ideal para meteorología, donde las nubes no tienen bordes definidos ni esquinas rígidas, sino que son masas difusas que cambian de forma constantemente.

---

## 🎨 Sprint Final: Endurecimiento, Desacoplamiento y Responsive Design
**Fecha:** 19 de Abril, 2026  
**Mejoras Claves Registradas:**

En nuestro proceso iterativo final sobre la interfaz `gallery-ui` y el soporte de Back-End, lidiamos con múltiples lecciones enfocadas puramente en el diseño web y arquitectura subyacente.

### 1. El Dilema del CSS Grid ("Grid Blow-out")
- **Problema:** Al dotar a la galería de previsiones expandidas (OWM entrega hasta 5 días de proyecciones), el contenedor horizontal de pestañas excedió la barrera física de la pantalla en dispositivos móviles. Sorprendentemente, pese a tener `overflow-x: auto`, el contenedor "empujó" al grid padre, ensanchando toda la pantalla y deformando todos nuestros márgenes derechos y encogimiento de *Chart.js*.
- **Solución/Lección:** Este fallo clásico se resolvió inyectando en el CSS la vital propiedad `min-width: 0;` a los hijos inmediatos del bloque, garantizando que respeten estrictamente la restricción espacial del móvil. De allí en más, siempre desconfiar de las columnas CSS Grid que contienen carriles expandibles.

### 2. Sincronización UI Inteligente (El Fallback Táctico)
- **Problema:** Si el sistema entraba en "Fallback" hacia OWM para capturar la temperatura (debido a la caída de una estación del SMN), el panel inferior de la web seguía mostrando "Pronóstico Extendido de SMN" - rompiendo la experiencia e induciendo a confusión.
- **Solución/Lección:** Optamos por añadir una validación al ciclo de vida en `updateWeatherUI()`. Con ello, la interfaz escucha de dónde provienen verdaderamente los datos actuales, y emite de fondo un switch al panel para que ambos originen simétricamente desde la misma fuente.

### 3. Fugas de Rendimiento y Desacople del DOM
- **Problema:** Un error arquitectónico inicial encadenó las peticiones: *FetchPhotos -> FetchWeather -> FetchPredictions*. Por ende, si el usuario apretaba el botón de la capa del satélite para cambiar entre colores, recargaba indiscriminadamente APIs meteorológicos enteros, reiniciando inútilmente los gráficos.
- **Solución/Lección:** Separar dominios lógicos (Responsabilidad Única). Ahora los gráficos de *Chart.js* operan en un ciclo autómata, y la galería de fotos solo busca sus recursos específicos cuando interactúan con ella. Asimismo, la variable de "fotograma freno de animación" se ajustó a la posición temporal correcta (`length - 1`) para evitar dar un pantallazo retroactivo.

### 4. Estabilización Segura del Core (Docker Hardening)
- **Problema:** Previo a nuestra gran refactorización, todos los servicios operaban implícitamente siendo superusuarios (`root`) dentro del contenedor, lo que exponía el *socket* y volúmenes a violaciones de base. Además InfluxDB era inestable en el pre-arranque (`setup`).
- **Solución/Lección:** Se aplicaron perfiles restrictivos `no-new-privileges: true` y volúmenes Read-Only para Nginx. Paralelamente, en el `entrypoint.sh` se incrustó de forma metódica un bucle de latencia adaptativo para asegurarse de no disparar el Python Processor hasta recibir respuestas `HTTP 204` sólidas del InfluxDB (Ping de estado de salud), unificando todo bajo el usuario mitigado `appuser`.
