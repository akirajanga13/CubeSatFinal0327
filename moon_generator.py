"""
MOON IMAGE GENERATOR
This file creates fake Moon images with craters and shadows
Perfect for simulating what the camera would see when looking at the Moon
"""

import random
from datetime import datetime

# Optional dependencies with fallback
try:
    import numpy as np
    np_available = True
except ImportError:
    np = None
    np_available = False
    print("numpy not installed. Install with: pip install numpy")

try:
    import cv2
    cv2_available = True
except ImportError:
    cv2 = None
    cv2_available = False
    print("OpenCV not installed for moon_generator. Install with: pip install opencv-python")

class MoonGenerator:
    def __init__(self):
        """Initialize the moon image generator"""
        self.image_width = 640
        self.image_height = 480
        self.num_craters = random.randint(8, 15)  # Each image has 8-15 craters
        self.can_use_numpy = np_available
        self.can_use_cv2 = cv2_available
        if not self.can_use_numpy:
            print("MoonGenerator: numpy not available; generating reduced detail image.")
        if not self.can_use_cv2:
            print("MoonGenerator: cv2 not available; generating simple image output.")        
    def create_moon_image(self):
        """Create a fake Moon image with craters and shadows"""
        
        if not self.can_use_numpy or not self.can_use_cv2:
            width = self.image_width
            height = self.image_height
            # fallback simple generated pattern as 2D list
            simple_image = [[random.randint(100, 200) for _ in range(width)] for _ in range(height)]
            return simple_image

        # Step 1: Create a base Moon surface (light gray background)
        # This represents the Moon's surface lit by sunlight
        moon_image = np.ones((self.image_height, self.image_width, 3), dtype=np.uint8) * 180
        
        # Step 2: Add some random noise to make it look realistic
        noise = np.random.randint(-30, 30, moon_image.shape, dtype=np.int16)
        moon_image = np.clip(moon_image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        # Step 3: Add craters (dark circles that represent shadows)
        for i in range(self.num_craters):
            crater_x = random.randint(50, self.image_width - 50)
            crater_y = random.randint(50, self.image_height - 50)
            crater_radius = random.randint(10, 50)
            crater_darkness = random.randint(30, 100)  # How dark the shadow is
            
            # Draw the crater as a dark circle
            cv2.circle(moon_image, (crater_x, crater_y), crater_radius, 
                      (crater_darkness, crater_darkness, crater_darkness), -1)
            
            # Make the edge of crater darker (shadow effect)
            cv2.circle(moon_image, (crater_x, crater_y), crater_radius, 
                      (crater_darkness - 20, crater_darkness - 20, crater_darkness - 20), 2)
        
        # Step 4: Add some mountains (bright spots)
        num_mountains = random.randint(3, 8)
        for i in range(num_mountains):
            mountain_x = random.randint(50, self.image_width - 50)
            mountain_y = random.randint(50, self.image_height - 50)
            mountain_radius = random.randint(5, 20)
            mountain_brightness = random.randint(230, 255)  # Very bright
            
            cv2.circle(moon_image, (mountain_x, mountain_y), mountain_radius,
                      (mountain_brightness, mountain_brightness, mountain_brightness), -1)
        
        # Convert to grayscale because we only need brightness info
        moon_image_gray = cv2.cvtColor(moon_image, cv2.COLOR_BGR2GRAY)
        
        return moon_image_gray
    
    def add_timestamp_text(self, image):
        """Add timestamp text to the image (like a real camera would)"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Add text to bottom right of image
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.4
        color = (255, 255, 255)  # White text
        thickness = 1
        
        cv2.putText(image, "MOON: " + timestamp, (10, self.image_height - 10),
                   font, font_scale, color, thickness)
        
        return image
