"""
SHADOW DETECTOR
This file finds dark regions (shadows) in Moon images
Think of it like finding all the craters in a Moon photo
"""

# Optional opencv and numpy support
try:
    import cv2
    cv2_available = True
except ImportError:
    cv2 = None
    cv2_available = False
    print("OpenCV not installed for shadow_detector. Install with: pip install opencv-python")

try:
    import numpy as np
    np_available = True
except ImportError:
    np = None
    np_available = False
    print("numpy not installed for shadow_detector. Install with: pip install numpy")

class ShadowDetector:
    def __init__(self, shadow_threshold=120):
        """
        Initialize the shadow detector
        
        shadow_threshold: Brightness level below this is considered a shadow
                         Lower numbers = darker pixels
                         0 = pure black, 255 = pure white
                         120 is a good middle ground
        """
        self.shadow_threshold = shadow_threshold
    
    def find_shadows(self, image):
        """
        Find all shadow regions in an image
        
        Returns: List of shadows with their coordinates
        """
        
        if not cv2_available:
            print("ShadowDetector: OpenCV not available. Cannot detect shadows.")
            return []

        # Step 1: Create a "shadow mask" - a black and white image
        # where shadows show as white and non-shadows as black
        _, shadow_mask = cv2.threshold(image, self.shadow_threshold, 255, cv2.THRESH_BINARY_INV)
        
        # Step 2: Find the outline (contours) of each shadow region
        contours, _ = cv2.findContours(shadow_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        # Step 3: Process each shadow region found
        shadows = []
        for contour in contours:
            # Calculate the area of this shadow
            area = cv2.contourArea(contour)
            
            # Ignore very small shadows (noise)
            if area > 100:
                # Find the center point (X, Y) of this shadow
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    center_x = int(M["m10"] / M["m00"])
                    center_y = int(M["m01"] / M["m00"])
                    
                    # Get the bounding box (smallest rectangle around shadow)
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Store shadow information
                    shadow_info = {
                        'center_x': center_x,
                        'center_y': center_y,
                        'area': area,
                        'width': w,
                        'height': h,
                        'left': x,
                        'top': y
                    }
                    shadows.append(shadow_info)
        
        return shadows
    
    def draw_shadows_on_image(self, image, shadows):
        """
        Draw circles around detected shadows for visualization
        This helps you see what the program found
        """
        if not cv2_available:
            print("ShadowDetector: OpenCV not available. Cannot draw shadows.")
            return image

        # Convert to color so we can draw colored circles
        image_with_circles = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        
        # Draw a circle around each shadow
        for shadow in shadows:
            x = shadow['center_x']
            y = shadow['center_y']
            radius = int(shadow['height'] / 2)  # Approximate radius
            
            # Draw green circle (shows detected shadow)
            cv2.circle(image_with_circles, (x, y), radius, (0, 255, 0), 2)
            
            # Add text showing shadow number and coordinates
            text = f"({x},{y})"
            cv2.putText(image_with_circles, text, (x - 20, y - radius - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 0), 1)
        
        return image_with_circles
    
    def get_shadow_report(self, shadows):
        """
        Create a simple text report of all detected shadows
        """
        report = f"\n{'='*50}\n"
        report += f"SHADOW DETECTION REPORT\n"
        report += f"{'='*50}\n"
        report += f"Total shadows found: {len(shadows)}\n"
        report += f"{'-'*50}\n"
        
        for i, shadow in enumerate(shadows, 1):
            report += f"\nShadow #{i}:\n"
            report += f"  Position: X={shadow['center_x']}, Y={shadow['center_y']}\n"
            report += f"  Size: {shadow['width']}x{shadow['height']} pixels\n"
            report += f"  Area: {shadow['area']} sq pixels\n"
        
        report += f"\n{'='*50}\n"
        return report
