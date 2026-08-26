import os
import glob
import cv2
import numpy as np
import math
from datetime import datetime
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from utils import get_influx_client

# Coordenadas de Riesgo (Bounding Box de Río Cuarto)
RC_X_START, RC_Y_START = 138, 368
RC_X_END,   RC_Y_END   = 158, 383

# Capas Analíticas (Ordenadas de Peor a Mejor)
STORM_LEVELS = [
    {
        "level": 4,
        "name": "Tormenta Severa (Granizo Posible)",
        "desc": "Altísimo riesgo. Updrafts intensos con topes muy fríos aproximándose.",
        "hsv_ranges": [[(20, 180, 180), (45, 255, 255)]] # YELLOW VIVID
    },
    {
        "level": 3,
        "name": "Lluvia Fuerte",
        "desc": "Nubes convectivas profundas. Probabilidad alta de precipitación intensa o descargas.",
        "hsv_ranges": [[(0, 180, 150), (10, 255, 255)], [(170, 180, 150), (180, 255, 255)]] # RED / PURE RED
    },
    {
        "level": 2,
        "name": "Lluvia Leve (Chaparrones)",
        "desc": "Frentes de capa media u oscuros. Precipitaciones aisladas o llovizna.",
        "hsv_ranges": [[(80, 150, 150), (140, 255, 255)], [(100, 40, 100), (150, 149, 255)]] # VIVID BLUE / CYAN y DULL BLUES
    }
]

GEOCOLOR_LEVELS = [
    {
        "level": 1,
        "name": "Mayormente Nublado",
        "desc": "Cielo parcial o totalmente nuboso (Estratos aislados). Baja probabilidad de precipitación.",
        "hsv_ranges": [[(0, 0, 110), (180, 60, 255)]] # GRAYS / WHITES (Extended Low saturation, Mid+ brightness)
    }
]

def get_geocolor_match(sandwich_path):
    basename = os.path.basename(sandwich_path)
    # Nombre base: goes_sandwich_20260420_192054.png
    # Buscamos coincidencias ignorando los segundos porque las descargas pueden tener desfasajes.
    parts = basename.split('_')
    if len(parts) >= 4:
        date_part = parts[2]
        time_part_hhmm = parts[3][:4] # '1920'
        search_pattern = os.path.join("/png-images/geocolor", f"goes_geocolor_{date_part}_{time_part_hhmm}*.png")
        matches = glob.glob(search_pattern)
        if matches:
            return matches[0]
    return None

def get_last_three_sandwich_images(directory="/png-images/sandwich/"):
    search_pattern = os.path.join(directory, "*.png")
    files = glob.glob(search_pattern)
    files.sort(key=os.path.getmtime, reverse=True)
    if len(files) < 3:
        return None, None, None
    # Retorna: (antigua, intermedia, reciente)
    return files[2], files[1], files[0]

def bounding_boxes_intersect(box1, box2):
    b1_x1, b1_y1, b1_x2, b1_y2 = box1
    b2_x1, b2_y1, b2_x2, b2_y2 = box2
    return not (b1_x2 < b2_x1 or b1_x1 > b2_x2 or b1_y1 > b2_y2 or b1_y2 < b2_y1)

def evaluate_level_intersection(hsv_img, flow, level_config, target_time_hours):
    """
    Evalúa la intersección proyectando el mapa completo de la nube hacia el futuro
    usando deformación de imagen (Image Warping) basado en flujo óptico.
    """
    STEPS = target_time_hours * 6  # 6 steps de 10 minutos = 1 hora
    rc_box = (RC_X_START, RC_Y_START, RC_X_END, RC_Y_END)
    
    # Crear máscara maestra para este nivel sumando todos sus umbrales
    mask_accumulator = np.zeros((hsv_img.shape[0], hsv_img.shape[1]), dtype=np.uint8)
    for hr in level_config["hsv_ranges"]:
        lower = np.array(hr[0])
        upper = np.array(hr[1])
        m = cv2.inRange(hsv_img, lower, upper)
        mask_accumulator = cv2.bitwise_or(mask_accumulator, m)
        
    # Aplicar apertura morfológica para eliminar ruido fino
    kernel = np.ones((5, 5), np.uint8)
    mask_accumulator = cv2.morphologyEx(mask_accumulator, cv2.MORPH_OPEN, kernel)
        
    # Si no hay nada detectado en este nivel, salimos rápido
    if cv2.countNonZero(mask_accumulator) == 0:
        return False
        
    # Image Warping (Advección Semi-Lagrangiana recomendada por el paper)
    # En lugar de asumir que la nube es un bloque sólido y mover su centroide,
    # deformamos la forma exacta de la nube hacia el futuro.
    h_img, w_img = mask_accumulator.shape
    X, Y = np.meshgrid(np.arange(w_img), np.arange(h_img))
    
    # Para mapear hacia el futuro (cv2.remap usa mapeo inverso):
    # El valor futuro en (x,y) proviene del pasado en (x - dx*STEPS, y - dy*STEPS)
    map_x = np.float32(X - flow[..., 0] * STEPS)
    map_y = np.float32(Y - flow[..., 1] * STEPS)
    
    # Deformar la máscara hacia el futuro usando los vectores del flujo denso
    warped_mask = cv2.remap(mask_accumulator, map_x, map_y, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    
    # Comprobar si hay nubes pronosticadas sobre el área de Río Cuarto
    rc_region = warped_mask[rc_box[1]:rc_box[3], rc_box[0]:rc_box[2]]
    pixels_in_rc = cv2.countNonZero(rc_region)
    
    if pixels_in_rc > 10:  # Umbral de tolerancia de 10 píxeles para evitar falsos positivos por micro-ruidos
        print(f"DEBUG MATCH WARPING: Lvl={level_config['level']} impactará RC con {pixels_in_rc} píxeles de cobertura.")
        return True
            
    return False

def calculate_dew_point(T, H):
    """Fórmula de Magnus-Tetens para calcular el Punto de Rocío."""
    if T is None or H is None: return 10.0
    a = 17.27
    b = 237.7
    alpha = ((a * T) / (b + T)) + math.log(H/100.0)
    return (b * alpha) / (a - alpha)

def get_owm_telemetry():
    """Obtiene exclusivamente datos de OpenWeatherMap de InfluxDB para el cálculo difuso."""
    client = get_influx_client()
    if not client: return 0.0, 10.0
    
    query_api = client.query_api()
    bucket = os.environ.get("INFLUX_BUCKET_TELEMETRY", "telemetry")
    
    # 1. Obtener Temp, Humedad y Presión actual (OWM exclusivo)
    query_current = f'''
    from(bucket: "{bucket}")
        |> range(start: -2h)
        |> filter(fn: (r) => r["_measurement"] == "weather_station")
        |> filter(fn: (r) => r["location"] == "Rio Cuarto")
        |> filter(fn: (r) => r["source"] == "owm")
        |> last()
    '''
    
    # 2. Obtener Presión de hace ~3 horas (OWM exclusivo) para tendencia
    query_old = f'''
    from(bucket: "{bucket}")
        |> range(start: -4h, stop: -2h)
        |> filter(fn: (r) => r["_measurement"] == "weather_station")
        |> filter(fn: (r) => r["location"] == "Rio Cuarto")
        |> filter(fn: (r) => r["source"] == "owm")
        |> filter(fn: (r) => r["_field"] == "pressure")
        |> last()
    '''
    
    current_data = {}
    for table in query_api.query(query_current):
        for record in table.records:
            current_data[record.get_field()] = record.get_value()
            
    old_pressure = None
    for table in query_api.query(query_old):
        for record in table.records:
            old_pressure = record.get_value()
            
    client.close()

    # Cálculos
    P_current = current_data.get("pressure")
    pt = (P_current - old_pressure) if P_current and old_pressure else 0.0
    dp = calculate_dew_point(current_data.get("temperature"), current_data.get("humidity"))
    
    return pt, dp

def calculate_fuzzy_hazard_probability(sat_level):
    """
    Motor de Inferencia Difusa (Cb-TRAM methodology)
    Utiliza funciones de pertenencia matemáticas continuas.
    """
    # 1. Valor Discreto Satelital
    sat_scores = {4: 0.95, 3: 0.75, 2: 0.50, 1: 0.25, 0: 0.0}
    sat_score = sat_scores.get(sat_level, 0.0)
    
    # 2. Obtener precursores OWM exclusivos
    pt, dp = get_owm_telemetry()
        
    # 3. Funciones de Pertenencia Matemáticas (Curvas Difusas)
    # A. Curva de Presión: max(0, min(1, (0.5 - pt) / 2.5))
    press_score = max(0.0, min(1.0, (0.5 - pt) / 2.5))
        
    # B. Curva de Humedad: max(0, min(1, (dp - 10.0) / 10.0))
    dew_score = max(0.0, min(1.0, (dp - 10.0) / 10.0))
        
    # 4. Fusión de Datos: (Cinemática 50% + Dinámica 30% + Termodinámica 20%)
    hazard_probability = (sat_score * 0.50) + (press_score * 0.30) + (dew_score * 0.20)
    
    print(f"-> [Fuzzy Logic] Sat={sat_score:.2f} | Press({pt:.1f})={press_score:.2f} | DewP({dp:.1f})={dew_score:.2f}")
    print(f"-> [Fuzzy Logic] Riesgo Combinado = {hazard_probability:.2f} ({(hazard_probability*100):.1f}%)")
    
    return hazard_probability

def run_nowcast():
    print(f"\n[{datetime.now().isoformat()}] INICIANDO ANÁLISIS PREDICTIVO (NOWCASTING OF PONDERADO)")
    img1_path, img2_path, img3_path = get_last_three_sandwich_images()
    
    if not img1_path or not img2_path or not img3_path:
        print("[AVISO] Faltan imágenes (mínimo 3 necesarias) para OF ponderado.")
        return

    # Cargar los 3 frames
    f1 = cv2.imread(img1_path)
    f2 = cv2.imread(img2_path)
    f3 = cv2.imread(img3_path)
    
    # Conversión a escala de grises para el algoritmo de Farnebäck
    g1 = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY)
    g3 = cv2.cvtColor(f3, cv2.COLOR_BGR2GRAY)
    
    # AISLAMIENTO DE NUBOSIDAD (Filtrar ruido de fondo/terreno)
    # Mandamos a negro (0) cualquier píxel menor a 40 para que Farnebäck
    # solo rastree el movimiento de las estructuras nubosas brillantes.
    _, g1 = cv2.threshold(g1, 40, 255, cv2.THRESH_TOZERO)
    _, g2 = cv2.threshold(g2, 40, 255, cv2.THRESH_TOZERO)
    _, g3 = cv2.threshold(g3, 40, 255, cv2.THRESH_TOZERO)
    
    # HSV del frame más reciente para detección de niveles
    hsv_latest = cv2.cvtColor(f3, cv2.COLOR_BGR2HSV)

    # 1. Flujo previo (f1 -> f2)
    # Parámetros ajustados (levels=5, winsize=25) según el paper para rastreo óptimo de nubes
    flow_prev = cv2.calcOpticalFlowFarneback(g1, g2, None, 0.5, 5, 25, 3, 5, 1.2, 0)
    
    # 2. Flujo reciente (f2 -> f3) 
    # Parámetros ajustados (levels=5, winsize=25) según el paper para rastreo óptimo de nubes
    flow_recent = cv2.calcOpticalFlowFarneback(g2, g3, None, 0.5, 5, 25, 3, 5, 1.2, 0)
    
    # COMBINACIÓN PONDERADA: 70% Reciente + 30% Previo
    # Esto da estabilidad (inercia) pero prioriza el movimiento actual.
    flow = cv2.addWeighted(flow_recent, 0.7, flow_prev, 0.3, 0)
    
    # Evaluar horizonte a 1_hora y 2_horas
    impact_1h = {"level": 0, "name": "Cielo Despejado", "desc": "Sin nubosidad aproximándose confirmada por ambos canales satelitales."}
    impact_2h = {"level": 0, "name": "Cielo Despejado", "desc": "Sin nubosidad aproximándose confirmada por ambos canales satelitales."}
    
    # Evaluar en cascada: De Peor (4) a Menos Peligroso (2) [Capa Sandwich Primaria]
    for lvl in STORM_LEVELS:
        if impact_1h["level"] == 0 and evaluate_level_intersection(hsv_latest, flow, lvl, target_time_hours=1):
            impact_1h = lvl
        if impact_2h["level"] == 0 and evaluate_level_intersection(hsv_latest, flow, lvl, target_time_hours=2):
            impact_2h = lvl
            
    # Arquitectura Híbrida Secundaria (Capa Geocolor Dual - Lógica Predictiva)
    # Sólo evaluamos nubosidad pasiva si el radar de tormenta dictamina Despejado (0)
    if impact_1h["level"] == 0 or impact_2h["level"] == 0:
        geo_files = glob.glob("/png-images/geocolor/goes_geocolor_*.png")
        if geo_files:
            latest_geo = sorted(geo_files)[-1]
            print(f"-> [Dual-Channel] Activando capa Geocolor Predictiva...")
            f_g = cv2.imread(latest_geo)
            hsv_g = cv2.cvtColor(f_g, cv2.COLOR_BGR2HSV)
            
            # Filtro estricto: Blanco/Gris puro para evitar luces amarillas/naranjas de ciudad
            geo_level = {
                "level": 1,
                "name": "Mayormente Nublado",
                "hsv_ranges": [
                    [(0, 0, 130), (180, 40, 255)] # Sat máxima 40, Brillo min 130
                ]
            }
            
            # Evaluar proyección a 1 hora usando el mismo viento (flow) de Sandwich
            if impact_1h["level"] == 0 and evaluate_level_intersection(hsv_g, flow, geo_level, target_time_hours=1):
                impact_1h = geo_level
                
            # Evaluar proyección a 2 horas
            if impact_2h["level"] == 0 and evaluate_level_intersection(hsv_g, flow, geo_level, target_time_hours=2):
                impact_2h = geo_level

    # -------------------------------------------------------------------------
    # DATA FUSION: Aplicar Lógica Difusa (Cb-TRAM methodology)
    # -------------------------------------------------------------------------
    def apply_fuzzy_logic_to_impact(impact_dict, label):
        if impact_dict["level"] > 0:
            print(f"\n--- Evaluando Fuzzy Logic {label} ---")
            prob = calculate_fuzzy_hazard_probability(impact_dict["level"])
            if prob >= 0.70:
                impact_dict["level"] = 4
                impact_dict["name"] = "Tormenta Severa Confirmada"
            elif prob >= 0.50:
                impact_dict["level"] = 3
                impact_dict["name"] = "Lluvia Fuerte Probable"
            elif prob >= 0.30:
                impact_dict["level"] = 2
                impact_dict["name"] = "Lluvia Leve (Chaparrones)"
            else:
                impact_dict["level"] = 1
                impact_dict["name"] = "Mayormente Nublado (Riesgo Mitigado)"

    apply_fuzzy_logic_to_impact(impact_1h, "1H")
    apply_fuzzy_logic_to_impact(impact_2h, "2H")

    print("================ STATUS DE PRONÓSTICO (NOWCAST) ================")
    if impact_1h["level"] == 4:
        print(f"🚨 [ALERTA 1HR] SEVERIDAD CRÍTICA INMINENTE: {impact_1h['name']}")
    else:
        print(f"-> Impacto Estimado a 1 Hora: Nivel {impact_1h['level']} - {impact_1h['name']}")
        
    if impact_2h["level"] == 4:
        print(f"🚨 [ALERTA 2HR] SEVERIDAD CRÍTICA ACERCÁNDOSE: {impact_2h['name']}")
    else:
        print(f"-> Impacto Estimado a 2 Horas: Nivel {impact_2h['level']} - {impact_2h['name']}")
    print("================================================================")
    
    # ============ PERSISTENCIA EN INFLUXDB ============
    client = get_influx_client()
    if not client:
        return
    write_api = client.write_api(write_options=SYNCHRONOUS)
    bucket = os.environ.get("INFLUX_BUCKET_PREDICTIONS", "predictions")
    org = os.environ.get("INFLUX_ORG", "noaa_org")
    
    pt = Point("nowcast_radar") \
        .tag("location", "Rio Cuarto") \
        .field("severity_1h", int(impact_1h["level"])) \
        .field("condition_1h", impact_1h["name"]) \
        .field("severity_2h", int(impact_2h["level"])) \
        .field("condition_2h", impact_2h["name"]) \
        .time(datetime.utcnow(), WritePrecision.NS)
        
    # EXPORTACIÓN JSON PARA GALERÍA (UX)
    import json
    prediction_data = {
        "location": "Rio Cuarto",
        "time": datetime.utcnow().isoformat(),
        "severity_1h": impact_1h["level"],
        "condition_1h": impact_1h["name"],
        "severity_2h": impact_2h["level"],
        "condition_2h": impact_2h["name"]
    }
    try:
        with open("/png-images/latest_predictions.json", "w") as f:
            json.dump(prediction_data, f)
    except Exception as e:
        print(f"-> [ERROR] Falló la escritura del JSON local: {e}")

    try:
        write_api.write(bucket=bucket, org=org, record=pt)
        print("-> [DB] Proyecciones guardadas exitosamente en InfluxDB.")
    except Exception as e:
        print(f"-> [ERROR DB] Falló la subida a InfluxDB: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    run_nowcast()
