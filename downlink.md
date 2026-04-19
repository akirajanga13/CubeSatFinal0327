
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
























