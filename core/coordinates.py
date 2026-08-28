import math
from config import SERVO_HORIZON_DEG, SERVO_DEG_SCALE

def spherical_to_cartesian(distance_cm: float, azimuth_deg: float, servo_angle: int):
    """
    Converte coordinate sferiche (distanza, azimut, pitch servo) in cartesiane (X, Y, Z).
    - Quando servo_angle == 135°, elevation_deg == 0.0° (piano orizzontale Z = 0)
    - Quando servo_angle == 165°, elevation_deg == -30.0° (punta verso il basso)
    - Quando servo_angle == 70°, elevation_deg == +65.0° (punta verso l'alto)
    """
    if distance_cm <= 0 or distance_cm > 1200:
        return None

    # Calcolo elevazione relativo al punto neutro a 135°
    # Il segno è invertito perché il servo decresce (165 -> 135 -> 70) mentre l'elevazione sale (-30° -> 0° -> +65°)
    elevation_deg = (SERVO_HORIZON_DEG - servo_angle) * SERVO_DEG_SCALE

    phi_rad = math.radians(elevation_deg)
    theta_rad = math.radians(azimuth_deg)
    r = float(distance_cm)

    # Coordinate Cartesiane assolute
    x = r * math.cos(phi_rad) * math.sin(theta_rad)
    y = r * math.cos(phi_rad) * math.cos(theta_rad)
    z = r * math.sin(phi_rad)

    return (x, y, z)