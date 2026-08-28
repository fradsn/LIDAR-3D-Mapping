import numpy as np
import time
from core.coordinates import spherical_to_cartesian

class SyncEngine:
    def __init__(self):
        self.azimuth_buffer = []  # tuple: (local_time, theta_deg)
        self.points_3d = []
        self.last_theta = 0.0
        self.total_revolutions = 0
        self.previous_angle = 0.0

    def add_azimuth(self, theta_deg: float):
        now = time.time()
        self.azimuth_buffer.append((now, theta_deg))
        
        # Mantieni uno storico temporale di 2 secondi
        if len(self.azimuth_buffer) > 200:
            self.azimuth_buffer.pop(0)

        # Rilevamento passaggio giro completo (wrap-around da 360° a 0°)
        if self.previous_angle > 300.0 and theta_deg < 60.0:
            self.total_revolutions += 1
        self.previous_angle = theta_deg
        self.last_theta = theta_deg

    def add_lidar_reading(self, distance_cm: float, servo_angle: int):
        if not self.azimuth_buffer:
            return None

        now = time.time()
        times = [t for t, _ in self.azimuth_buffer]
        angles = [a for _, a in self.azimuth_buffer]

        # Estrapola o interpola l'azimut al momento dell'arrivo del pacchetto LiDAR
        theta_interp = float(np.interp(now, times, angles))
        
        pt = spherical_to_cartesian(distance_cm, theta_interp, servo_angle)
        if pt:
            self.points_3d.append(pt)
        return pt

    def clear(self):
        self.azimuth_buffer.clear()
        self.points_3d.clear()
        self.total_revolutions = 0