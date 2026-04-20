import os
import time
from webcam import WebcamCapture

# Conditional import of smbus (only needed for real hardware on Raspberry Pi)
try:
    import smbus
except ImportError:
    smbus = None

def boot_message():
    print("Booting CubeSat...")
    print("Initializing systems...")
    print("IMU: LSM6DSOX")

def create_directories():
    folders = ["data", "data/images", "logs"]
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"{folder} folder created.")
        else:
            print(f"{folder} folder already exists.")


def check_imu(simulation_mode=False):
    try:
        print("Checking IMU...")

        # If running on Windows and smbus is unavailable, force simulation mode.
        # This bypasses the IMU hardware dependency in dev/test environments.
        effective_simulation = simulation_mode
        if smbus is None and os.name == 'nt':
            print("WARNING: smbus library not available on Windows, using simulation mode.")
            effective_simulation = True

        if effective_simulation:
            print("[SIMULATION MODE] Simulating IMU check...")
            time.sleep(1)
            print("IMU device ID: 0x6c (simulated)")
        else:
            if smbus is None:
                print("ERROR: smbus library not available (Raspberry Pi I2C library)")
                print("Running in simulation mode would avoid this error.")
                return False
            
            bus = smbus.SMBus(1)

            IMU_ADDRESS = 0x6A

            who_am_i = bus.read_byte_data(IMU_ADDRESS, 0x0F)
            print("IMU device ID:", hex(who_am_i))

        print("Calibrating gyroscope...")

        samples = 50  
        gyro_offset = 0

        if effective_simulation:
            print("[SIMULATION MODE] Simulating gyroscope calibration...")
            # Simulate gyro data collection
            for i in range(samples):
                gyro_offset += 15 + (i % 5)  # Simulated gyro values
            time.sleep(0.5)
        else:
            for i in range(samples):
                gyro_value = bus.read_byte_data(IMU_ADDRESS, 0x22)
                gyro_offset += gyro_value

        gyro_offset = gyro_offset / samples
        print("Gyro offset calculated:", gyro_offset)

        print("IMU calibration complete.")

        return True

    except Exception as e:
        print("IMU error:", e)
        return False


def read_simulation_mode():
    """Read simulation mode from config.txt"""
    simulation = 0
    moon_sim = 0
    shadow_detect = 0
    shadow_threshold = 120
    create_map = 0
    config_file = "config.txt"
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        parts = line.split('=')
                        key = parts[0].strip()
                        value = parts[1].strip()
                        if key == 'simulation':
                            simulation = int(value)
                        elif key == 'moon_simulation':
                            moon_sim = int(value)
                        elif key == 'shadow_detection':
                            shadow_detect = int(value)
                        elif key == 'shadow_threshold':
                            shadow_threshold = int(value)
                        elif key == 'create_shadow_map':
                            create_map = int(value)
        except Exception as e:
            print(f"Warning: Could not read config: {e}")
    
    return simulation, moon_sim, shadow_detect, shadow_threshold, create_map


def system_initialize():
    boot_message()
    create_directories()

    # Read all configuration settings
    simulation_mode, moon_simulation, shadow_detection, shadow_threshold, create_map = read_simulation_mode()
    
    if simulation_mode:
        print("\n[SIMULATION MODE ENABLED]")
        if moon_simulation:
            print("[MOON SIMULATION MODE ENABLED]")
        if shadow_detection:
            print("[SHADOW DETECTION ENABLED]")
    
    if not check_imu(simulation_mode=simulation_mode):
        print("WARNING: IMU calibration failed - continuing mission without IMU")
    
    print("Systems Initialized; CubeSat Ready")
    
    # Start mission - automatic camera capture
    print("\n[STARTING MISSION]")
    camera = WebcamCapture()
    camera.run(moon_simulation=moon_simulation, shadow_detection=shadow_detection, 
               shadow_threshold=shadow_threshold, create_map=create_map)
    
    return True


if __name__ == "__main__":
    system_initialize()

# Minimal config for Webcam program

# 1 = simulation mode (fake moon generation), 0 = real camera
simulation=0

# 1 = use shake-trigger capture (IMU); 0 = continuous mission
shake_detection=0

# Trigger level for shake in m/s^2; effective only when shake_detection=1
acceleration_threshold=10.0

# Continuous mission settings (runs in webcam.py)
wait_seconds=2
num_pictures=5
run_minutes=1

# Moon/shadow operation
moon_simulation=1
shadow_detection=1
shadow_threshold=120
create_shadow_map=1

import time
import os
import platform
import random
import shutil
from datetime import datetime

LOG_PATH = 'logs/run.log'

def log(message, level='INFO'):
    text = f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{level}] {message}\n"
    print(text.strip())
    try:
        # Ensure logs directory exists
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, 'a') as f:
            f.write(text)
    except Exception as e:
        print(f"Could not write to log: {e}")

# Try to import OpenCV for camera.
try:
    import cv2
    cv2_available = True
except ImportError:
    cv2 = None
    cv2_available = False
    print("OpenCV not installed. Install with: sudo apt update && sudo apt install python3-opencv")
    print("Continuing without OpenCV camera support.")

# Try to import Picamera2 for Raspberry Pi.
try:
    from picamera2 import Picamera2
    picamera2_available = True
except ImportError:
    Picamera2 = None
    picamera2_available = False
    print("Picamera2 not installed. Install with: sudo apt update && sudo apt install python3-picamera2")
    print("Continuing without Picamera2 support.")

# Conditional import of local modules
try:
    from metadata import MetadataManager
    metadata_available = True
except ImportError:
    MetadataManager = None
    metadata_available = False
    print("MetadataManager not available. Metadata saving will be disabled.")

try:
    from moon_generator import MoonGenerator
    moon_gen_available = True
except ImportError:
    MoonGenerator = None
    moon_gen_available = False
    print("MoonGenerator not available. Moon simulation will be disabled.")

try:
    from shadow_detector import ShadowDetector
    shadow_det_available = True
except ImportError:
    ShadowDetector = None
    shadow_det_available = False
    print("ShadowDetector not available. Shadow detection will be disabled.")

try:
    from moon_map import MoonMap
    moon_map_available = True
except ImportError:
    MoonMap = None
    moon_map_available = False
    print("MoonMap not available. Shadow mapping will be disabled.")

class WebcamCapture:
    def __init__(self):
        self.webcam = None
        self.picam2 = None
        self.use_picamera2 = False
        self.image_folder = "images"
        self.data_folder = "data"
        self.settings = None
        self.metadata = None
        self.config = None

        # Reset folders first so each run starts clean
        self.reset_data_and_images()

        # Load mission config from config.txt
        self.load_config()
        
        # Initialize camera
        self.initialize_camera()
        
        # Read run settings (wait duration, picture count, runtime)
        self.read_settings()
        
        # Initialize metadata manager
        if metadata_available:
            self.metadata = MetadataManager(self.data_folder)
        else:
            self.metadata = None
    
    def reset_data_and_images(self):
        for folder in ["data", "images"]:
            try:
                if os.path.exists(folder):
                    shutil.rmtree(folder)
                os.makedirs(folder)
                print(f"{folder} reset")
            except Exception as e:
                print(f"Could not reset {folder}: {e}")

    def read_simulation_mode(self):
        # Simple config reader moved from initi.py
        config = {
            'simulation': 0,
            'moon_simulation': 0,
            'shadow_detection': 0,
            'shadow_threshold': 120,
            'create_shadow_map': 0,
            'shake_detection': 0,
            'acceleration_threshold': 10.0,
            'wait_seconds': 10,
            'num_pictures': 0,
            'run_minutes': 0
        }

        config_file = 'config.txt'
        if not os.path.exists(config_file):
            print('config.txt not found, using defaults')
            return config

        try:
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if key in config:
                            if key in ['shadow_threshold', 'acceleration_threshold']:
                                config[key] = float(value)
                            else:
                                config[key] = int(value)
        except Exception as e:
            print('Could not read config:', e)

        return config
    
    def initialize_camera(self):
        system = platform.system()
        
        if system == "Linux":  # Assume Raspberry Pi
            if picamera2_available:
                try:
                    self.picam2 = Picamera2()
                    self.use_picamera2 = True
                    print("Using Picamera2 for Raspberry Pi camera")
                except Exception as e:
                    print(f"Picamera2 initialization failed: {e}")
                    self.use_picamera2 = False
            else:
                print("Picamera2 not available on Raspberry Pi")
                self.use_picamera2 = False
        
        if not self.use_picamera2:
            if cv2_available:
                try:
                    if system == "Windows":
                        self.webcam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                    else:
                        self.webcam = cv2.VideoCapture(0, cv2.CAP_V4L2)
                    if self.webcam.isOpened():
                        print("Using OpenCV camera")
                    else:
                        print("OpenCV camera failed to open")
                        self.webcam = None
                except Exception as e:
                    print(f"OpenCV camera initialization failed: {e}")
                    self.webcam = None
            else:
                print("No camera library available")
    
    # Read settings from config.txt
    def load_config(self):
        self.config = {
            'simulation': 0,
            'moon_simulation': 0,
            'shadow_detection': 0,
            'create_shadow_map': 0,
            'shake_detection': 0,
            'shadow_threshold': 120,
            'acceleration_threshold': 10.0,
            'wait_seconds': 10,
            'num_pictures': 0,
            'run_minutes': 0
        }

        config_file = 'config.txt'
        if not os.path.exists(config_file):
            print('config.txt not found, using defaults')
            return

        try:
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if key in self.config:
                            if key in ['shadow_threshold', 'acceleration_threshold']:
                                try:
                                    self.config[key] = float(value)
                                except ValueError:
                                    pass
                            else:
                                try:
                                    self.config[key] = int(value)
                                except ValueError:
                                    pass
        except Exception as e:
            print(f'Could not read config: {e}')

    def read_settings(self):
        self.settings = {
            'wait_seconds': 10,
            'num_pictures': 0,
            'run_minutes': 0
        }

        if self.config is not None:
            # Reuse loaded config values for consistency
            self.settings['wait_seconds'] = self.config.get('wait_seconds', 10)
            self.settings['num_pictures'] = self.config.get('num_pictures', 0)
            self.settings['run_minutes'] = self.config.get('run_minutes', 0)

        config_file = "config.txt"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        parts = line.split('=')
                        key = parts[0].strip()
                        value = parts[1].strip()
                        if key in self.settings:
                            try:
                                self.settings[key] = int(value)
                            except:
                                pass
    
    # Show the settings
    def show_settings(self):
        log("SETTINGS:", 'INFO')
        log(f"Wait {self.settings['wait_seconds']} seconds between pictures", 'INFO')
        
        if self.settings['num_pictures'] == 0:
            log("Take as many pictures as you want (no limit)", 'INFO')
            if self.settings['run_minutes'] == 0:
                log("Run forever (no time limit)", 'INFO')
            else:
                log(f"Run for {self.settings['run_minutes']} minutes", 'INFO')
        else:
            log(f"Take {self.settings['num_pictures']} pictures (PRIMARY SETTING)", 'INFO')
            log("[run_minutes is ignored when num_pictures is set]", 'INFO')
    
    # Turn on the webcam
    def start(self):
        log("Starting camera...", 'INFO')
        
        # Detect operating system and use appropriate backend
        system = platform.system()
        
        if system == "Windows":
            # Windows uses DirectShow
            self.webcam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        else:
            # Raspberry Pi (Linux) uses V4L2
            self.webcam = cv2.VideoCapture(0, cv2.CAP_V4L2)
        
        time.sleep(2)
        
        if self.webcam.isOpened():
            # Set camera settings
            self.webcam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            log("Camera is ready!", 'INFO')
            w = int(self.webcam.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.webcam.get(cv2.CAP_PROP_FRAME_HEIGHT))
            log(f"Size: {w}x{h}", 'INFO')
            return True
        else:
            log("Camera failed to start", 'ERROR')
            log(f"System: {system}", 'ERROR')
            log("Troubleshooting (1) make sure webcam is plugged in; (2) sudo usermod -a -G video pi; (3) reboot", 'INFO')
            print("3. Restart Raspberry Pi")
            return False
    
    # Take one picture
    def take_picture(self):
        if self.use_picamera2 and self.picam2:
            try:
                # Configure and capture with Picamera2
                self.picam2.configure(self.picam2.create_still_configuration())
                self.picam2.start()
                time.sleep(1)  # Warm up
                picture = self.picam2.capture_array()
                self.picam2.stop()
                # Convert RGB to BGR for consistency with cv2
                picture = cv2.cvtColor(picture, cv2.COLOR_RGB2BGR)
                return True, picture
            except Exception as e:
                log(f"Picamera2 capture failed: {e}", 'ERROR')
                return False, None
        elif self.webcam and self.webcam.isOpened():
            success, picture = self.webcam.read()
            return success, picture
        else:
            log("No camera available for capture", 'ERROR')
            return False, None
    
    # Save the picture to a file as PNG with simulated high-resolution metadata
    def save_picture(self, picture):
        # Make a name with the date and time - PNG format
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"image_{now}.png"
        file_path = os.path.join(self.image_folder, file_name)
        
        # Save as PNG
        cv2.imwrite(file_path, picture, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        
        # Get actual picture info (from webcam)
        actual_height, actual_width = picture.shape[:2]
        file_size = os.path.getsize(file_path)
        time_taken = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Simulated high-resolution specifications
        simulated_width = 4608
        simulated_height = 2592
        bits_per_pixel = 12
        bytes_per_pixel = 3.75
        uncompressed_mb = 44.79
        
        # Generate varying compression ratio based on simulated image content
        # Range from 2.5:1 (complex scenes) to 4.0:1 (simple scenes)
        compression_ratio_value = random.uniform(2.5, 4.0)
        compression_ratio_str = f"{compression_ratio_value:.2f}:1"
        
        # Calculate simulated compressed size based on varying ratio
        compressed_mb = uncompressed_mb / compression_ratio_value
        
        return file_name, time_taken, simulated_width, simulated_height, bits_per_pixel, bytes_per_pixel, uncompressed_mb, compressed_mb, compression_ratio_str
    
    # Turn off the camera
    def stop(self):
        if self.webcam:
            self.webcam.release()
            print("Camera is off")
        if self.use_picamera2 and self.picam2:
            self.picam2.stop()
    
    def take_single_picture(self, moon_simulation=False, shadow_detection=False, shadow_threshold=120):
        log("Taking single picture...", 'INFO')
        
        # Initialize components if needed
        moon_gen = None
        shadow_detector = None
        if moon_simulation and moon_gen_available:
            moon_gen = MoonGenerator()
        elif moon_simulation and not moon_gen_available:
            print("Moon simulation requested but MoonGenerator not available. Skipping simulation.")
            moon_simulation = False
        
        if shadow_detection and shadow_det_available:
            shadow_detector = ShadowDetector(shadow_threshold=shadow_threshold)
        elif shadow_detection and not shadow_det_available:
            print("Shadow detection requested but ShadowDetector not available. Skipping detection.")
            shadow_detection = False
        
        # Take a picture
        if moon_simulation:
            photo = moon_gen.create_moon_image()
            success = True
        else:
            success, photo = self.take_picture()
        
        if not success:
            log("Error taking picture!", 'ERROR')
            return
        
        # Save the picture and get info
        pic_name, pic_time, pic_width, pic_height, pic_bits, pic_bytes, pic_uncompressed, pic_compressed, pic_ratio = self.save_picture(photo)
        
        # Detect shadows if enabled
        shadow_count = 0
        shadow_details = ""
        if shadow_detection:
            shadows = shadow_detector.find_shadows(photo)
            shadow_count = len(shadows)
            shadow_coords_list = [f"({s['center_x']},{s['center_y']})" for s in shadows]
            shadow_details = ";".join(shadow_coords_list)
            if shadow_count > 0:
                print(f"  --> {shadow_count} shadows detected at: {shadow_details}")
        
        # Save metadata
        if self.metadata:
            self.metadata.save_info(pic_name, pic_time, pic_width, pic_height, pic_bits, pic_bytes, 
                                   pic_uncompressed, pic_compressed, pic_ratio, shadow_count, shadow_details)
        else:
            print("Metadata not saved (MetadataManager not available)")
        
        print(f"Picture saved: {pic_name} ({pic_width}x{pic_height}) - Compressed: {pic_compressed:.2f}MB")
    
    # Run the whole program - autonomous mission
    def run(self, moon_simulation=None, shadow_detection=None, shadow_threshold=None, create_map=None):
        log("CAMERA MISSION STARTING", 'INFO')
        self.show_settings()

        # Use configuration defaults if flags not passed
        if self.config is not None:
            if moon_simulation is None:
                moon_simulation = bool(self.config.get('moon_simulation', 0))
            if shadow_detection is None:
                shadow_detection = bool(self.config.get('shadow_detection', 0))
            if shadow_threshold is None:
                shadow_threshold = self.config.get('shadow_threshold', 120)
            if create_map is None:
                create_map = bool(self.config.get('create_shadow_map', 0))

        moon_simulation = bool(moon_simulation)
        shadow_detection = bool(shadow_detection)
        shadow_threshold = int(shadow_threshold)
        create_map = bool(create_map)

        # Initialize Moon components if moon simulation is enabled
        moon_gen = None
        moon_map = None
        if moon_simulation and moon_gen_available:
            log("Moon simulation enabled, generating synthetic Moon images", 'INFO')
            moon_gen = MoonGenerator()
            if moon_map_available:
                moon_map = MoonMap(self.data_folder)
        elif moon_simulation and not moon_gen_available:
            log("Moon simulation requested but MoonGenerator not available. Disabling simulation.", 'WARNING')
            moon_simulation = False
        
        # Initialize Shadow detector if enabled
        shadow_detector = None
        if shadow_detection and shadow_det_available:
            log("Shadow detection enabled", 'INFO')
            shadow_detector = ShadowDetector(shadow_threshold=shadow_threshold)
        elif shadow_detection and not shadow_det_available:
            log("Shadow detection requested but ShadowDetector not available. Disabling detection.", 'WARNING')
            shadow_detection = False
        
        log("TAKING PICTURES", 'INFO')
        
        try:
            picture_number = 0
            start_time = time.time()
            
            while True:
                # Check if we should stop based on picture count
                if self.settings['num_pictures'] > 0:
                    if picture_number >= self.settings['num_pictures']:
                        log(f"Done! Captured {self.settings['num_pictures']} pictures.", 'INFO')
                        break
                # Check if we should stop based on time
                elif self.settings['run_minutes'] > 0:
                    time_passed = (time.time() - start_time) / 60
                    if time_passed >= self.settings['run_minutes']:
                        log("Mission time limit reached!", 'INFO')
                        break
                
                # Take a picture
                if moon_simulation:
                    # Generate fake Moon image
                    photo = moon_gen.create_moon_image()
                    success = True
                else:
                    # Try to use real camera
                    success, photo = self.take_picture()
                
                if not success:
                    log("Error taking picture!", 'ERROR')
                    break
                
                # Save the picture and get info about it
                pic_name, pic_time, pic_width, pic_height, pic_bits, pic_bytes, pic_uncompressed, pic_compressed, pic_ratio = self.save_picture(photo)
                picture_number = picture_number + 1
                
                # Detect shadows if enabled
                shadow_count = 0
                shadow_details = ""
                if shadow_detection:
                    shadows = shadow_detector.find_shadows(photo)
                    shadow_count = len(shadows)
                    
                    # Create a string of shadow coordinates
                    shadow_coords_list = [f"({s['center_x']},{s['center_y']})" for s in shadows]
                    shadow_details = ";".join(shadow_coords_list)
                    
                    # Add shadows to the moon map
                    if moon_simulation:
                        moon_map.add_shadow(pic_name, pic_time, shadows)
                    
              if shadow_count > 0:
    		log(f"{shadow_count} shadows detected at: {shadow_details}", 'INFO')

if shadow_detection
if shadow_count > 0:
dest_folder = "images/shadows_detected"
else:
dest_folder = "images/no_shadows"
os.makedirs(dest_folder, exist_ok=True)
src = os.path.join(self.image_folder, pic_name)
dst = os.path.join(dest_folder, pic_name)
shutil.move(src, dst)


       
                # Save the info to CSV with shadow data
                if self.metadata:
                    self.metadata.save_info(pic_name, pic_time, pic_width, pic_height, pic_bits, pic_bytes, 
                                           pic_uncompressed, pic_compressed, pic_ratio, shadow_count, shadow_details)
                else:
                    log("Metadata not saved (MetadataManager not available)", 'WARNING')
                
                log(f"Picture {picture_number}: {pic_name} ({pic_width}x{pic_height}) - Compressed: {pic_compressed:.2f}MB", 'INFO')
                
                # Wait before taking next picture
                log(f"Waiting {self.settings['wait_seconds']} seconds...", 'INFO')
                time.sleep(self.settings['wait_seconds'])
            
            # Create shadow map if enabled
            if moon_simulation and shadow_detection and create_map and moon_map:
                log("CREATING SHADOW MAP", 'INFO')
                moon_map.save_shadow_coordinates()
                moon_map.save_map()
                moon_map.print_shadow_summary()
            elif moon_simulation and shadow_detection and create_map and not moon_map:
                log("Shadow map creation requested but MoonMap not available.", 'WARNING')
            
            log("MISSION COMPLETE!", 'INFO')
            log(f"Total pictures captured: {picture_number}", 'INFO')
            log(f"Pictures stored in: {self.image_folder}", 'INFO')
            log(f"Metadata stored in: {self.data_folder}/image_metadata.csv", 'INFO')
            
            if shadow_detection:
                log(f"Shadow data stored in: {self.data_folder}/shadow_coordinates.csv", 'INFO')
            if moon_simulation and shadow_detection and create_map and moon_map:
                log(f"Shadow map stored in: {self.data_folder}/lunar_shadow_map.txt", 'INFO')
            
        except KeyboardInterrupt:
            log('Mission interrupted!', 'INFO')
        except Exception as e:
            log(f"Error: {e}", 'ERROR')
        finally:
            self.stop()
            if self.metadata:
                self.metadata.close_file()
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
import time
import sqlite3
import serial
from datetime import datetime

DATABASE_NAME = "cubesat_images.db"
IMAGE_FOLDER = "images"
PACKET_SIZE = 200

SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 9600

SAT_ID = "CUBESAT1"

os.makedirs(IMAGE_FOLDER, exist_ok=True)


def save_image():
    filename = f"{IMAGE_FOLDER}/image_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg"

    os.system(f"libcamera-still -o {filename}")

    if not os.path.exists(filename):
        print("Camera capture failed.")
        return None

    return filename


def store_image(filename):

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        timestamp TEXT,
        shadow BLOB
    )
    """)

    with open(filename, "rb") as f:
        image_data = f.read()

    cursor.execute("""
    INSERT INTO images (filename, timestamp, shadow)
    VALUES (?, ?, ?)
    """, (filename, datetime.utcnow().isoformat(), image_data))

    conn.commit()
    conn.close()


def create_packets(filename):

    with open(filename, "rb") as f:
        data = f.read()

    packets = []
    total_packets = (len(data) + PACKET_SIZE - 1) // PACKET_SIZE

    for i in range(total_packets):

        start = i * PACKET_SIZE
        end = start + PACKET_SIZE
        chunk = data[start:end]

        header = f"{SAT_ID},{i},{total_packets}|".encode()

        packets.append(header + chunk)

    return packets


def transmit(packets):

    try:
        radio = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)

        for packet in packets:
            radio.write(packet)
            time.sleep(0.1)

        radio.close()

    except serial.SerialException as e:
        print(f"Serial error: {e}")


def main():

    print("Capturing image...")
    image_file = save_image()

    if image_file is None:
        return

    print("Storing image in database...")
    store_image(image_file)

    print("Preparing packets...")
    packets = create_packets(image_file)

    print(f"Total packets: {len(packets)}")

    print("Transmitting to ground station...")
    transmit(packets)

    print("Transmission complete")


if __name__ == "__main__":
    main()
