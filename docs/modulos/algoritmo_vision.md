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

### Etapa B: Segmentación en Espacio HSV (Umbrales Térmicos)
Saber para dónde se mueve el viento de la imagen no sirve si no definimos "qué" se está moviendo. Convertimos el último fotograma visible al espacio de color morfológico **HSV (Hue, Saturation, Value)**.
Basado en rangos hipercalibrados, la computadora aísla binariamente la matriz de nubes según su frialdad topográfica (ej: rojos/amarillos = convección extrema, cianes/grises = lloviznas).

### Etapa C: Extrapolación de Topología Bounding-Box
Una vez generadas las "máscaras" de píxeles peligrosos mediante el clasificador HSV, extraemos los contornos poligonales limpios usando `cv2.findContours`. 
Para cada celda o clúster de tormenta delimitada y validada paramétricamente (>25px² para filtrar ruidos), inyectamos a las coordenadas centrales de masa su propia muestra topográfica de viento recabada en el Etapa A:
- Los píxeles de velocidad instantánea se multiplican aritméticamente para expandir "hasta dónde llegarían esos clústers" al cabo de 6 periodos temporales (1 Hora) o 12 (2 Horas).
- Si en ese futuro extrapolado virtualmente el polígono exterior colisiona geométricamente contra el rectángulo espacial pre-definido de *Río Cuarto* (`bounding_boxes_intersect()`), el script tracciona un *raise* positivo de Alerta Semafórica (`severity_1H / severity_2h`) y la graba sincrónicamente en InfluxDB.

> [!TIP]
> **Tuning de Abrasión Fija:** Se implementó una sub-cláusula de corte estricto `abs(dx) < 0.3`. Obliga a OpenCV a ignorar todo contorno detectado que no exhiba un desplazamiento temporal coherente. Esta criba técnica aniquila para siempre los "falsos positivos" procedentes de topografía escura del suelo, embalses hídricos erráticos y manchas de estática de la cámara de la NOAA.
