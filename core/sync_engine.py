import time
import numpy as np
from core.coordinates import spherical_to_cartesian

class SyncEngine:
    def __init__(self):
        self.azimuth_buffer = []  # tuple: (local_time, theta_deg)
        self.points_3d = []
        self.last_theta = 0.0
        self.total_revolutions = 0
        self.previous_angle = 0.0
        self.sensor_height_cm = 0.0  # Quota impostata da interfaccia utente

    def add_azimuth(self, theta_deg: float):
        now = time.time()
        self.azimuth_buffer.append((now, theta_deg))
        
        # Mantiene uno storico temporale di ~200 campioni
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

        # Interpola l'azimut all'esatto timestamp d'arrivo del frame LiDAR
        theta_interp = float(np.interp(now, times, angles))
        
        pt = spherical_to_cartesian(
            distance_cm=distance_cm, 
            azimuth_deg=theta_interp, 
            servo_angle=servo_angle, 
            sensor_h_cm=self.sensor_height_cm
        )
        
        if pt:
            self.points_3d.append(pt)
        return pt

    def clear(self):
        self.azimuth_buffer.clear()
        self.points_3d.clear()
        self.total_revolutions = 0