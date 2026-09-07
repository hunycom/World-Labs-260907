import math
import numpy as np
from PIL import Image

def analyze_woobles_images():
    img_paths = [
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788144080255.png", # Front
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788144087933.png", # Right
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788144054208.png", # Back
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788144080253.png", # Top
    ]

    for i, p in enumerate(img_paths):
        im = Image.open(p)
        print(f"Image {i}: size={im.size}, mode={im.mode}")

if __name__ == '__main__':
    analyze_woobles_images()
