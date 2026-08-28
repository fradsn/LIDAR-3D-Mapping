# --- PARAMETRI MECCANICI & RIDUZIONE ---
GEAR_RATIO = 6.0        # 6 giri di stepper = 1 giro completo del piatto (360°)
DEFAULT_STEPPER_RPM = 10  # Velocità standard di default dello stepper

# --- CALIBRAZIONE GIMBAL TILT ---
SERVO_BOTTOM_DEG = 165  # Punto di partenza servo (sotto l'orizzontale)
SERVO_TOP_DEG = 70      # Punto di arrivo servo (sopra l'orizzontale)
SERVO_HORIZON_DEG = 135 # Angolo servo in cui il laser è PERFETTAMENTE ORIZZONTALE (0°)
TILT_STEP_DEG = 5      # Passo di test

SENSOR_HEIGHT_CM = 85.0  # Altezza del perno del sensore dal pavimento (in cm)
SERVO_DEG_SCALE = 1.0

# --- BLE NODES CONFIGURATION ---
BASE_NODE_NAME = "ESP32-Stepper-Base"
BASE_SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
BASE_AZIMUTH_CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
BASE_CTRL_CHAR_UUID = "beb5483f-36e1-4688-b7f5-ea07361b26a8"

PAYLOAD_NODE_NAME = "ESP32-LiDAR-Tilt"
PAYLOAD_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
PAYLOAD_SCAN_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
PAYLOAD_CTRL_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"