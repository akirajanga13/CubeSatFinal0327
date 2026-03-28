import csv
import os

class MetadataManager:
    def __init__(self, data_folder):
        self.data_folder = data_folder
        self.csv_file_path = os.path.join(data_folder, "image_metadata.csv")
        self.csv_file = None
        self.csv_writer = None
        self.start_csv()
    
    # Set up the CSV file
    def start_csv(self):
        # Initialize the file as a fresh CSV each run (not append across runs)
        self.csv_file = open(self.csv_file_path, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        headers = ["Filename", "Timestamp", "Image_Width", "Image_Height", "Bits_Per_Pixel", "Bytes_Per_Pixel", "Uncompressed_Size_MB", "Compressed_Size_MB", "Compression_Ratio", "Shadows_Detected", "Shadow_Coordinates"]
        self.csv_writer.writerow(headers)
        self.csv_file.flush()
    
    # Add a new row to the CSV with image and shadow info
    def save_info(self, name, time, simulated_width, simulated_height, bits_per_pixel, bytes_per_pixel, uncompressed_mb, compressed_mb, compression_ratio, shadows_detected=0, shadow_coords=""):
        self.csv_writer.writerow([name, time, simulated_width, simulated_height, bits_per_pixel, bytes_per_pixel, f"{uncompressed_mb:.2f}", f"{compressed_mb:.2f}", compression_ratio, shadows_detected, shadow_coords])
        self.csv_file.flush()
    
    # Close the file when done
    def close_file(self):
        if self.csv_file:
            self.csv_file.close()
