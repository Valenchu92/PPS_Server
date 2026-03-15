import sys
import os
import cv2
import numpy as np
import datetime

# Coordenadas estáticas (Ajustadas para la GOES-19 Sector SSA 7200x4320)
Y_START = 1651
Y_END = 2255
X_START = 2700
X_END = 3120

def process_goes_image(input_path):
    output_dir = "/png-images"
    
    # Check if input file exists
    if not os.path.exists(input_path):
        print(f"Error: Input file {input_path} not found.")
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

    print(f"Cropping Córdoba bounding box: X({X_START}-{X_END}) Y({Y_START}-{Y_END})")
    cropped_img = img[Y_START:Y_END, X_START:X_END]

    # Generate output filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"goes_cordoba_{timestamp}.png"
    output_path = os.path.join(output_dir, output_filename)

    # Save cropped image
    success = cv2.imwrite(output_path, cropped_img)
    if success:
        print(f"Success! Cropped image saved to {output_path}")
        # Opcional: Eliminar la imagen cruda para ahorrar espacio
        # os.remove(input_path) 
    else:
        print("Error: Failed to write output image.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_goes.py <input_image_path>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    process_goes_image(input_file)
