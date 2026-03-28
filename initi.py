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
