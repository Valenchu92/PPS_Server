# Inteligencia de Visión Artificial (Nowcasting)

El núcleo predictivo a muy corto plazo (Nowcasting) de nuestro sistema no depende de simuladores climatológicos abstractos, sino de la técnica de **Tratamiento Digital de Imágenes y Visión Computacional** aplicada sobre espectros asincrónicos del satélite GOES-16.

Para lograr predecir el impacto de tormentas con 1 y 2 horas de anticipación, el ecosistema de Python se apoya fundamentalmente sobre las librerías matriciales de `OpenCV` y `NumPy`. El corazón de este mecanismo explota el **Método de Flujo Óptico Denso de Gunnar Farnebäck**.

---

## 1. Fundamentos Matemáticos del Algoritmo de Farnebäck

El flujo óptico es la estimación del movimiento aparente de los objetos (en este caso, patrones de bandas nubosas) entre dos fotogramas consecutivos, causado por el desplazamiento físico o relativo en la imagen bidimensional.

A diferencia del método de *Lucas-Kanade* (que exige extraer de antemano "esquinas rígidas" o vértices estables del objeto a seguir), Farnebäck emplea un algoritmo **denso**, lo cual significa que computa los vectores de desplazamiento geométrico para absolutamente la totalidad de la matriz de píxeles. Esto es imperativo en meteorología descriptiva, dado que las nubes poseen texturas difusas (amorfas) y se deforman isométricamente mientras se desplazan.

El modelo subyacente sigue este rigor técnico:
1.  **Expansión Polinomial Local:** Interpola la intensidad (brillo/escala de grises) de la vecindad inmediata de **cada píxel** aproximándola a una función cuadrática $f(x) \approx x^T A x + b^T x + c$. Básicamente, caracteriza la "topografía del color" en esa arista específica.
2.  **Seguimiento Dinámico:** Observa el vector de desplazamiento necesario para que la "topografía polinomial" del fotograma $T_0$ encaje (se minimice el error residual matricial) con la nueva topografía equivalente hallada en el fotograma $T_1$.
3.  **Campo de Vectores:** El algoritmo devuelve un tensor (grilla tridimensional bidimensional) con las velocidades instantáneas escalares de desplazamiento $(\Delta x, \Delta y)$ para cada píxel individual de la imagen. 

---

## 2. Aplicación y Aprovechamiento en Nuestra Arquitectura

Una vez que OpenCV desgrana y entrega el campo vectorial microscópico, nuestro proyecto `processor/nowcast_storm.py` exprime estos tensores bajo un estricto *pipeline* propio de ingeniería y segmentación:

### Etapa A: Muestreo de Inercia Estocástica (Ponderación)
Las capas satelitales arrastran *ruido blanco* o artefactos esporádicos causados por la transmisión espacial, los cuales inducirían derivas matemáticas catastróficas. Para remediarlo, nuestro código extrae los **últimos tres fotogramas** secuenciales en lugar de dos. 
Cálcula el *Flujo Óptico Previo* ($T_{-20}$ a $T_{-10}$) y el *Flujo Óptico Reciente* ($T_{-10}$ a $T_0$). Seguidamente, mediante mezcla matricial `cv2.addWeighted`, consolida ambos tensores otorgando un 70% de dominancia a los vectores inminentes y 30% a los vestigios pasados. Al inducir esta "inercia térmica", descartamos movimientos erráticos, vibraciones de píxeles y validamos la cizalladura estructural del viento.

### Etapa B: Segmentación y Limpieza Morfológica (Espacio HSV)
Saber para dónde se mueve el viento de la imagen no sirve si no definimos "qué" se está moviendo. Convertimos el último fotograma visible al espacio de color **HSV (Hue, Saturation, Value)**.
Basado en rangos hipercalibrados, la computadora aísla binariamente la matriz de nubes según su frialdad topográfica o luminosidad (ej: rojos/amarillos = convección extrema, blancos puros = nubosidad pasiva).

**Mitigación de Artefactos:** Para evitar que elementos ajenos al clima (como cuadrículas de latitud/longitud o fronteras dibujadas en blanco por el satélite) generen masas de falsos positivos, se aplica una técnica de **Apertura Morfológica** (`cv2.morphologyEx` utilizando `MORPH_OPEN` y un kernel de 5x5). Esta operación matemática (que combina una erosión seguida de una dilatación) "borra" instantáneamente cualquier ruido o línea delgada (menor a 5 píxeles), dejando absolutamente limpias e intactas a las masas sólidas (las nubes).

### Etapa C: Advección por Image Warping (Remapeo de Nubes)
En lugar de extraer polígonos rígidos y trasladar sus centroides geométricos, la arquitectura ahora emplea una técnica avanzada llamada **Advección Semi-Lagrangiana** mediante *Image Warping* (`cv2.remap`).
Para evaluar la extrapolación de la masa nubosa, el algoritmo proyecta el 100% de la morfología de la nube hacia el futuro:
- Aplica los tensores del campo vectorial denso directamente a una grilla de coordenadas matricial.
- Deforma la máscara de nubes actual "deslizándola" matemáticamente hacia dónde estará en 6 periodos temporales (1 Hora) o 12 (2 Horas), respetando su deformación y forma original.
- Finalmente recorta las coordenadas espaciales exclusivas de Río Cuarto en el fotograma proyectado. Si existen suficientes píxeles de cobertura (superando un umbral de ruido técnico), se dispara una aserción positiva de amenaza satelital.

> [!TIP]
> **Aislamiento Temprano del Terreno:** Previo al algoritmo de Farnebäck, el motor fuerza a negro todo píxel por debajo de cierta intensidad luminosa. Esto obliga al sistema a rastrear de forma exclusiva las nubes, erradicando distorsiones o ruidos ópticos provenientes del movimiento aparente del suelo.

### Etapa D: Arquitectura Predictiva Dual (Capa Geocolor)
El espectro "Sandwich" (infrarrojo mejorado) es excelente detectando tormentas severas, pero es ciego frente a la nubosidad pasiva o baja (estratos) que no genera topes fríos significativos. Para garantizar una asertividad total, el sistema implementa un esquema secundario o de reserva.
Si el escáner de tormentas dictamina "Nivel 0 (Despejado)", el núcleo activa una evaluación dinámica sobre el canal visual/Geocolor:
1.  **Filtro Anti-Contaminación Lumínica:** Durante la noche, la iluminación urbana (ciudades como Río Cuarto) genera brillos intensos que confunden a un sensor básico. Nuestro algoritmo soluciona esto usando un umbral HSV ultra-estricto: Saturación Máxima `40` y Brillo Mínimo `130`. Al rechazar coloraciones saturadas, el sistema se vuelve "daltónico" a las luces naranjas/amarillas de la ciudad, detectando exclusivamente el blanco/gris puro de las nubes.
2.  **Movimiento Heredado (Zero-Cost):** En lugar de repetir los hiper-cálculos de la Fase A, la capa Geocolor hereda y reutiliza automáticamente la matriz polinomial de vientos del canal Sandwich. Así, la nube pasiva detectada es proyectada hacia el futuro (1H y 2H), permitiendo pronosticar nubosidad aproximándose sin consumir ni un megabyte extra de procesamiento de CPU.

### Etapa E: Fusión de Datos y Lógica Difusa (Fuzzy Logic)
Basado en las metodologías implementadas en aeropuertos europeos (como el sistema **Cb-TRAM**), predecir tormentas severas exclusivamente por imágenes satelitales arrastra un alto riesgo de *Falsos Positivos*. Que una nube fría apunte hacia una ciudad no garantiza que tenga la energía para sostenerse.

Para mitigar esto, nuestro motor de Nowcasting integra **Sensores de Superficie (Telemetría de OpenWeatherMap)** y pondera matemáticamente el pronóstico a través de una función de Lógica Difusa.

1.  **Motor Termodinámico:** El sistema extrae en vivo desde InfluxDB la Temperatura, Humedad y Presión del aire en superficie, calculando la *Tendencia Barométrica (3 horas)* y el *Punto de Rocío*.
2.  **Funciones de Pertenencia Continuas:** Mediante curvas matemáticas (interpolaciones trapezoidales continuas en lugar de rangos fijos de `if/else`), cada variable arroja una probabilidad real `[0.0 - 1.0]`. Por ejemplo, un Punto de Rocío mayor a 20°C (alto riesgo convectivo) aproxima el score a 1.0, mientras que caídas bruscas en la presión atmosférica elevan exponencialmente el score dinámico.
3.  **Fusión Multivariable:** El puntaje satelital cinemático (que aporta un 50% de peso direccional) se entremezcla (Suma Ponderada) con el factor dinámico de Presión (30%) y el factor termodinámico de Humedad (20%). 
4.  **Decisión Final:** Si la nube viaja hacia Río Cuarto pero la humedad es nula y la presión se mantiene alta, la probabilidad difusa resultará baja y la alerta será automáticamente rebajada ("downgrade") de *Tormenta Severa* a *Mayormente Nublado*, cancelando eficientemente las falsas alarmas sin alterar el desempeño cinemático.

---

## 3. Referencias Científicas y Sustento Teórico

Para garantizar que el núcleo predictivo opere bajo estándares meteorológicos probados y reducir la incidencia empírica de falsas alarmas, esta arquitectura se diseñó implementando técnicas extraídas directamente de las siguientes publicaciones científicas de referencia:

1. **"Optical Flow-Based Forecasting of Surface Irradiance Using Cloud Motion Vectors in Brazil"**
   - **Uso en el proyecto:** Este documento proporcionó la base técnica para la afinación matemática del algoritmo de Farnebäck y la técnica de deformación matricial utilizada en la **Etapa C (Advección por Image Warping)**. Se adoptaron las recomendaciones específicas de aumentar los niveles de pirámide (`5`) y el tamaño de ventana (`25`) para adaptarse al flujo de masas gaseosas. Asimismo, se implementó su directiva crítica de "aislar el terreno", filtrando a negro los píxeles oscuros para evitar que el algoritmo interprete la topografía estática como movimiento atmosférico.
   
2. **"Nowcasting Thunderstorms for Munich Airport" (Forster & Tafferner, DLR)**
   - **Uso en el proyecto:** De esta investigación (que originó el sistema europeo *Cb-TRAM*), se extrajo la arquitectura para la **Etapa E (Fusión de Datos y Lógica Difusa)**. El estudio demostró que el rastreo puramente satelital genera una tasa de falsas alarmas (FAR) del 50%. Para resolverlo, implementamos su paradigma de "Data Fusion": cruzar la trayectoria cinemática de la nube satelital con mediciones termodinámicas de superficie (Tendencia de Presión Barométrica y Punto de Rocío). Esto nos permitió crear el motor de *Fuzzy Logic* que confirma o descarta las tormentas basándose en la inestabilidad real del aire en tierra firme.
