import sys
import os
import cv2
import numpy as np
import datetime

import hashlib

# Coordenadas estáticas (Ajustadas para la GOES-19 Sector SSA 7200x4320)
Y_START = 1651
Y_END = 2255
X_START = 2700
X_END = 3120

HASH_DB_PATH = "/raw_images/.processed_hashes"

def get_file_hash(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def is_already_processed(file_hash):
    if not os.path.exists(HASH_DB_PATH):
        return False
    with open(HASH_DB_PATH, "r") as f:
        processed_hashes = f.read().splitlines()
        return file_hash in processed_hashes

def mark_as_processed(file_hash):
    with open(HASH_DB_PATH, "a") as f:
        f.write(file_hash + "\n")

def process_goes_image(input_path):
    output_dir = "/png-images"
    
    # Check if input file exists
    if not os.path.exists(input_path):
        print(f"Error: Input file {input_path} not found.")
        return

    # Check Hash to avoid duplicate processing
    file_hash = get_file_hash(input_path)
    if is_already_processed(file_hash):
        print(f"Skipping: Image {os.path.basename(input_path)} was already processed (Hash match).")
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
        mark_as_processed(file_hash)
    else:
        print("Error: Failed to write output image.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_goes.py <input_image_path>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    process_goes_image(input_file)
