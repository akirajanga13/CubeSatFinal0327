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
