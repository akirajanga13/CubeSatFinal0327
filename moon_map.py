"""
MOON MAP CREATOR
This file creates a map showing all the shadows found across all images
Think of it like creating a map of Moon craters based on all the photos taken
"""

import csv
import os
from datetime import datetime

class MoonMap:
    def __init__(self, data_folder="data"):
        """Initialize the moon map creator"""
        self.data_folder = data_folder
        self.map_file = os.path.join(data_folder, "lunar_shadow_map.txt")
        self.shadow_coordinates_file = os.path.join(data_folder, "shadow_coordinates.csv")
        self.all_shadows = []

        # Make sure old map files are cleared at startup
        if os.path.exists(self.shadow_coordinates_file):
            try:
                os.remove(self.shadow_coordinates_file)
            except Exception as e:
                print(f"Could not remove old shadow coordinates file: {e}")
        if os.path.exists(self.map_file):
            try:
                os.remove(self.map_file)
            except Exception as e:
                print(f"Could not remove old map file: {e}")
    
    def add_shadow(self, image_name, timestamp, shadows):
        """
        Add shadows from one photo to the map database
        """
        for i, shadow in enumerate(shadows):
            shadow_entry = {
                'image_name': image_name,
                'timestamp': timestamp,
                'shadow_number': i + 1,
                'center_x': shadow['center_x'],
                'center_y': shadow['center_y'],
                'width': shadow['width'],
                'height': shadow['height'],
                'area': shadow['area']
            }
            self.all_shadows.append(shadow_entry)
    
    def save_shadow_coordinates(self):
        """Save all shadow coordinates to a CSV file"""
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
        
        try:
            # Create CSV file with shadow data
            with open(self.shadow_coordinates_file, 'w', newline='') as f:
                fieldnames = ['image_name', 'timestamp', 'shadow_number', 
                            'center_x', 'center_y', 'width', 'height', 'area']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                writer.writeheader()
                for shadow in self.all_shadows:
                    writer.writerow(shadow)
            
            return True
        except Exception as e:
            print(f"Error saving shadow coordinates: {e}")
            return False
    
    def create_text_map(self, width=640, height=480):
        """
        Create a simple text-based map showing shadow locations
        Uses a grid system to show where shadows are concentrated
        """
        # Create a grid (like graph paper)
        grid_size = 50  # Each grid cell is 50 pixels
        grid_width = width // grid_size
        grid_height = height // grid_size
        
        # Create empty grid
        grid = [['  .  ' for _ in range(grid_width)] for _ in range(grid_height)]
        
        # Place shadows on the grid
        for shadow in self.all_shadows:
            x = shadow['center_x'] // grid_size
            y = shadow['center_y'] // grid_size
            
            # Make sure coordinates are within grid bounds
            if 0 <= x < grid_width and 0 <= y < grid_height:
                grid[y][x] = '  [*]'
        
        # Create the map string
        map_text = "\n"
        map_text += "="*70 + "\n"
        map_text += "LUNAR SHADOW DISTRIBUTION MAP\n"
        map_text += "="*70 + "\n"
        map_text += f"Total shadows detected: {len(self.all_shadows)}\n"
        map_text += f"Created at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        map_text += "-"*70 + "\n\n"
        
        # Add legend
        map_text += "Legend:\n"
        map_text += "  [*] = Shadow detected in this region\n"
        map_text += "  .   = No shadows in this region\n"
        map_text += "\nGrid: Each cell represents 50x50 pixels\n"
        map_text += "-"*70 + "\n\n"
        
        # Add column headers
        map_text += "     "
        for col in range(grid_width):
            map_text += f"{col*grid_size:5d} "
        map_text += "\n"
        
        # Add rows
        for row in range(grid_height):
            map_text += f"{row*grid_size:3d} "
            for col in range(grid_width):
                map_text += grid[row][col]
            map_text += "\n"
        
        map_text += "\n" + "="*70 + "\n"
        
        return map_text
    
    def save_map(self):
        """Save the map to a text file"""
        try:
            map_text = self.create_text_map()
            
            with open(self.map_file, 'w') as f:
                f.write(map_text)
            
            print(f"Map saved to: {self.map_file}")
            return map_text
        except Exception as e:
            print(f"Error saving map: {e}")
            return None
    
    def print_map(self):
        """Print the map to console"""
        map_text = self.create_text_map()
        print(map_text)
    
    def print_shadow_summary(self):
        """Print a summary of all shadows found"""
        print("\n" + "="*70)
        print("SHADOW LOCATION SUMMARY")
        print("="*70)
        
        if not self.all_shadows:
            print("No shadows detected.")
            return
        
        print(f"Total shadows found: {len(self.all_shadows)}\n")
        print("Top 10 shadows by size:\n")
        
        # Sort shadows by area (largest first)
        sorted_shadows = sorted(self.all_shadows, key=lambda x: x['area'], reverse=True)
        
        for i, shadow in enumerate(sorted_shadows[:10], 1):
            print(f"{i}. Position: ({shadow['center_x']}, {shadow['center_y']}) "
                  f"| Size: {shadow['area']} pixels | Image: {shadow['image_name']}")
        
        print("\n" + "="*70 + "\n")
