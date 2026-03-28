import sys
import os
import cv2
import numpy as np
import datetime
from utils import get_file_hash, is_already_processed, mark_as_processed

# Coordenadas estáticas (Ajustadas para la GOES-19 Sector SSA 7200x4320)
Y_START = 1651
Y_END = 2255
X_START = 2700
X_END = 3120

def process_goes_image(input_path):
    output_base_dir = "/png-images"
    
    # Check if input file exists
    if not os.path.exists(input_path):
        print(f"Error: Input file {input_path} not found.")
        return

    # Extract product type from filename (e.g., goes_geocolor_*.jpg -> geocolor)
    filename = os.path.basename(input_path)
    if "geocolor" in filename.lower():
        product = "geocolor"
    elif "airmass" in filename.lower():
        product = "airmass"
    elif "sandwich" in filename.lower():
        product = "sandwich"
    else:
        product = "geocolor" # Fallback

    output_dir = os.path.join(output_base_dir, product)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Check Hash to avoid duplicate processing
    file_hash = get_file_hash(input_path)
    if is_already_processed(file_hash, "/raw_images/.processed_hashes"):
        print(f"Skipping: Image {filename} was already processed (Hash match).")
        return

    print(f"Loading image {input_path} into memory...")
    img = cv2.imread(input_path)
    
    if img is None:
        print("Error: Could not decode image.")
        return

    height, width = img.shape[:2]

    # Simple check just to be sure the image is large enough
    if width < X_END or height < Y_END:
        print(f"Error: The image is too small ({width}x{height}) to be cropped at ({X_START},{Y_START}) to ({X_END},{Y_END})")
        return

    print(f"Cropping Córdoba bounding box for {product}: X({X_START}-{X_END}) Y({Y_START}-{Y_END})")
    cropped_img = img[Y_START:Y_END, X_START:X_END]

    # Dibujar la Bounding Box de Río Cuarto (Puntos dados manualmente)
    # Coordenadas: (138, 368) a (158, 383). Color BGR: Verde puro (0, 255, 0), 1px de grosor
    # Se usa verde puro porque el Hue 60 no es detectado por el analizador de tormentas (rojo/azul/amarillo).
    cv2.rectangle(cropped_img, (138, 368), (158, 383), (0, 255, 0), 1)

    # Generate output filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"goes_{product}_{timestamp}.png"
    output_path = os.path.join(output_dir, output_filename)

    # Save cropped image
    success = cv2.imwrite(output_path, cropped_img)
    if success:
        print(f"Success! Cropped {product} image saved to {output_path}")
        mark_as_processed(file_hash, "/raw_images/.processed_hashes")
        
        # Disparar pronóstico Nowcast SÓLO si es Sandwich (ahorro extremo de CPU)
        if product == "sandwich":
            import subprocess
            print("-> Disparando análisis predictivo Nowcast (Optical Flow) para Sandwich...")
            subprocess.Popen(["python3", "/app/nowcast_storm.py"])
    else:
        print("Error: Failed to write output image.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_goes.py <input_image_path>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    process_goes_image(input_file)
