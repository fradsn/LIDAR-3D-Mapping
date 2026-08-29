import math
from config import SERVO_HORIZON_DEG, SERVO_DEG_SCALE

def spherical_to_cartesian(distance_cm: float, azimuth_deg: float, servo_angle: int, sensor_h_cm: float = 0.0):
    """
    Converte coordinate sferiche in cartesiane.
    - Quando servo_angle == 135°, elevation_deg == 0.0°
    - Aggiunge sensor_h_cm a Z: il pavimento diventa Z = 0 e tutti i punti stanno sopra la griglia.
    - Inverte l'asse X (-r * ...) per compensare il montaggio capovolto del sensore ToF.
    """
    if distance_cm <= 0 or distance_cm > 1200:
        return None

    elevation_deg = (SERVO_HORIZON_DEG - servo_angle) * SERVO_DEG_SCALE

    phi_rad = math.radians(elevation_deg)
    theta_rad = math.radians(azimuth_deg)
    r = float(distance_cm)

    # Inversione asse X coerente con la versione 2D
    x = -r * math.cos(phi_rad) * math.sin(theta_rad)
    y =  r * math.cos(phi_rad) * math.cos(theta_rad)
    z = (r * math.sin(phi_rad)) + sensor_h_cm

    return (x, y, z)