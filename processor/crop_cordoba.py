#!/usr/bin/env python3
import sys
import os
import cv2

def crop_cordoba(input_path, output_path):
    # Coordenadas estáticas (Ajustadas para la GOES-19 Sector SSA 7200x4320)
    # Estas coordenadas encapsulan geográficamente un área un poco mayor 
    # a la provincia de Córdoba para asegurar que el contorno blanco siempre esté visible.
    # [Y_START:Y_END, X_START:X_END]
    
    # Ajuste: Coordenadas exactas obtenidas por el usuario
    # [Y_START:Y_END, X_START:X_END]
    Y_START = 1651
    Y_END = 2255
    X_START = 2700
    X_END = 3120

    print(f"Loading image from {input_path}...")
    img = cv2.imread(input_path)
    if img is None:
        print(f"Error: Could not load image at {input_path}")
        sys.exit(1)
        
    height, width = img.shape[:2]
    # Simple check just to be sure we are looking at the 7200x4320
    if width < X_END or height < Y_END:
        print(f"Error: The image is too small ({width}x{height}) to be cropped at ({X_START},{Y_START}) to ({X_END},{Y_END})")
        sys.exit(1)

    print(f"Cropping Córdoba bounding box: X({X_START}-{X_END}) Y({Y_START}-{Y_END})")
    cropped_img = img[Y_START:Y_END, X_START:X_END]

    # Save as PNG since we output to Immich png-output folder
    print(f"Saving cropped image to {output_path}...")
    success = cv2.imwrite(output_path, cropped_img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    
    if success:
        print("Successfully saved.")
    else:
        print("Failed to save the image.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python crop_cordoba.py <input.jpg> <output.png>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    crop_cordoba(input_file, output_file)
