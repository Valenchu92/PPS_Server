import os
import glob
import cv2
import numpy as np
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
    Busca centroides del nivel especificado, los proyecta 'target_time_hours' (6 o 12 steps)
    y retorna True si chocan con Río Cuarto.
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
        
    contours, _ = cv2.findContours(mask_accumulator, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        if cv2.contourArea(cnt) < 25:
            continue
            
        x, y, w, h = cv2.boundingRect(cnt)
        cx = x + w//2
        cy = y + h//2
        
        dx, dy = flow[cy, cx]
        
        # Filtro de velocidad: Ignorar contornos que casi no se mueven (terreno rojizo/marcas estáticas)
        # Excepción crucial: Si la nube ya cubre la ciudad, no la ignoramos, ya que representa nubosidad estancada actual.
        if abs(dx) < 0.3 and abs(dy) < 0.3:
            if not bounding_boxes_intersect((x, y, x+w, y+h), rc_box):
                continue
            
        proj_x1 = int(x + (dx * STEPS))
        proj_y1 = int(y + (dy * STEPS))
        proj_x2 = proj_x1 + w
        proj_y2 = proj_y1 + h
        
        if bounding_boxes_intersect((proj_x1, proj_y1, proj_x2, proj_y2), rc_box):
            print(f"DEBUG MATcH: Lvl={level_config['level']} area={cv2.contourArea(cnt)} bbox=({x},{y},{w},{h}) dx/dy=({dx:.2f},{dy:.2f})")
            return True
            
    return False

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
    
    # HSV del frame más reciente para detección de niveles
    hsv_latest = cv2.cvtColor(f3, cv2.COLOR_BGR2HSV)

    # 1. Flujo previo (f1 -> f2)
    flow_prev = cv2.calcOpticalFlowFarneback(g1, g2, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    
    # 2. Flujo reciente (f2 -> f3) 
    flow_recent = cv2.calcOpticalFlowFarneback(g2, g3, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    
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
            
    # Arquitectura Híbrida Secundaria (Capa Geocolor Dual - Lógica Simplificada)
    # Sólo evaluamos nubosidad pasiva si el radar de tormenta dictamina Despejado (0)
    if impact_1h["level"] == 0 or impact_2h["level"] == 0:
        geo_files = glob.glob("/png-images/geocolor/goes_geocolor_*.png")
        if geo_files:
            latest_geo = sorted(geo_files)[-1]
            print(f"-> [Dual-Channel] Activando capa Geocolor (Lógica Simplificada)...")
            f_g = cv2.imread(latest_geo)
            hsv_g = cv2.cvtColor(f_g, cv2.COLOR_BGR2HSV)
            
            # Filtro amplio para blanco/gris (cualquier Hue, baja Saturación, alto Valor/Brillo)
            mask = cv2.inRange(hsv_g, np.array([0, 0, 90]), np.array([180, 80, 255]))
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            rc_box = (RC_X_START, RC_Y_START, RC_X_END, RC_Y_END)
            is_cloudy = False
            
            for cnt in contours:
                if cv2.contourArea(cnt) < 100:
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                # Si una masa blanca o gris está sobre la ciudad ahora, asumimos que sigue nublado
                if bounding_boxes_intersect((x, y, x+w, y+h), rc_box):
                    print(f"DEBUG MATCH Geocolor: area={cv2.contourArea(cnt)} bbox=({x},{y},{w},{h})")
                    is_cloudy = True
                    break
                    
            if is_cloudy:
                lvl = GEOCOLOR_LEVELS[0]
                if impact_1h["level"] == 0:
                    impact_1h = lvl
                if impact_2h["level"] == 0:
                    impact_2h = lvl

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
        
    try:
        write_api.write(bucket=bucket, org=org, record=pt)
        print("-> [DB] Proyecciones guardadas exitosamente en InfluxDB.")
        
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
        with open("/png-images/latest_predictions.json", "w") as f:
            json.dump(prediction_data, f)
            
    except Exception as e:
        print(f"-> [ERROR DB] Falló la subida a InfluxDB: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    run_nowcast()
