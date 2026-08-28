import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QGroupBox, QProgressBar, QTextEdit
)
from PyQt6.QtCore import QTimer
from ui.gl_widget import PointCloudView
from core.ble_manager import BLEManager
from core.sync_engine import SyncEngine
from config import SERVO_BOTTOM_DEG, SERVO_TOP_DEG, TILT_STEP_DEG

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D LiDAR Scanner - Unified Desktop")
        self.resize(1200, 750)

        self.sync_engine = SyncEngine()
        self.ble_manager = BLEManager()
        
        # Calcolo lista rigida e sequenziale degli angoli di tilt
        self.target_servo_angles = list(range(SERVO_BOTTOM_DEG, SERVO_TOP_DEG - 1, -TILT_STEP_DEG))
        if self.target_servo_angles[-1] != SERVO_TOP_DEG:
            self.target_servo_angles.append(SERVO_TOP_DEG)
            
        self.total_tilt_steps = len(self.target_servo_angles)
        self.current_step_idx = 0
        self.current_plate_azimuth = 0.0
        
        self.base_is_connected = False
        self.payload_is_connected = False
        
        # Variabili temporali
        self.scan_start_time = 0.0
        self.est_lap_duration = 54.0

        # Timer ad alta frequenza (200 ms) per fluidità del countdown
        self.eta_timer = QTimer(self)
        self.eta_timer.setInterval(200)
        self.eta_timer.timeout.connect(self._update_time_display)

        self._setup_ui()
        self._bind_signals()
        
        self.ble_manager.start()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # 1. Visualizzatore 3D (Sinistra)
        self.viewer = PointCloudView()
        main_layout.addWidget(self.viewer, stretch=3)

        # 2. Pannello di Controllo (Destra)
        panel_layout = QVBoxLayout()
        main_layout.addLayout(panel_layout, stretch=1)

        # Gruppo Connessioni
        conn_group = QGroupBox("Dispositivi BLE")
        conn_box = QVBoxLayout(conn_group)
        self.btn_connect = QPushButton("Connetti Dispositivi")
        self.lbl_base_status = QLabel("Base Stepper: Disconnessa")
        self.lbl_payload_status = QLabel("Payload LiDAR: Disconnesso")
        conn_box.addWidget(self.btn_connect)
        conn_box.addWidget(self.lbl_base_status)
        conn_box.addWidget(self.lbl_payload_status)
        panel_layout.addWidget(conn_group)

        # Gruppo Telemetria Live
        telemetry_group = QGroupBox("Telemetria Live")
        tel_box = QVBoxLayout(telemetry_group)
        self.lbl_theta = QLabel("Azimut (Base): --°")
        self.lbl_servo = QLabel(f"Tilt Pitch: {SERVO_BOTTOM_DEG}°")
        self.lbl_distance = QLabel("Distanza LiDAR: -- cm")
        self.lbl_pts_count = QLabel("Punti 3D Acquisiti: 0")
        tel_box.addWidget(self.lbl_theta)
        tel_box.addWidget(self.lbl_servo)
        tel_box.addWidget(self.lbl_distance)
        tel_box.addWidget(self.lbl_pts_count)
        panel_layout.addWidget(telemetry_group)

        # Gruppo Scansione 3D
        scan_group = QGroupBox("Scansione 3D Multi-Livello")
        scan_box = QVBoxLayout(scan_group)
        self.btn_scan = QPushButton("Avvia Scansione 3D")
        self.btn_scan.setEnabled(False)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("In attesa di avvio")

        self.lbl_time_info = QLabel("Tempo rimanente: --:--")
        
        scan_box.addWidget(self.btn_scan)
        scan_box.addWidget(self.progress_bar)
        scan_box.addWidget(self.lbl_time_info)
        panel_layout.addWidget(scan_group)

        # Log Console
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        panel_layout.addWidget(self.log_console)

    def _bind_signals(self):
        self.btn_connect.clicked.connect(self._toggle_connection)
        self.btn_scan.clicked.connect(self._toggle_scan)

        self.ble_manager.base_connected_sig.connect(self._on_base_status)
        self.ble_manager.payload_connected_sig.connect(self._on_payload_status)
        self.ble_manager.azimuth_received_sig.connect(self._on_azimuth)
        self.ble_manager.lidar_received_sig.connect(self._on_lidar)
        self.ble_manager.lap_completed_sig.connect(self._on_lap_completed)
        self.ble_manager.log_sig.connect(self.log_console.append)

    def _toggle_connection(self):
        if not (self.base_is_connected or self.payload_is_connected):
            self.btn_connect.setText("Connessione in corso...")
            self.btn_connect.setEnabled(False)
            self.ble_manager.send_command("CONNECT")
        else:
            if self.btn_scan.text() == "Ferma Scansione":
                self._toggle_scan()
            self.ble_manager.send_command("DISCONNECT")

    def _toggle_scan(self):
        if self.btn_scan.text() == "Avvia Scansione 3D":
            self.sync_engine.clear()
            self.viewer.clear()
            self.current_step_idx = 0
            self.current_plate_azimuth = 0.0
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("0% - Inizializzazione...")
            
            self.scan_start_time = time.time()
            self.lbl_time_info.setText("Tempo rimanente: Calcolo...")
            self.eta_timer.start()

            self.ble_manager.send_command("START_SCAN")
            self.btn_scan.setText("Ferma Scansione")
        else:
            self.eta_timer.stop()
            self.ble_manager.send_command("STOP_SCAN")
            self.btn_scan.setText("Avvia Scansione 3D")
            self.lbl_time_info.setText("Scansione interrotta.")
            self.progress_bar.setFormat("Scansione interrotta")

    def _on_base_status(self, connected: bool, rssi: int):
        self.base_is_connected = connected
        if connected:
            self.lbl_base_status.setText(f"Base Stepper: Connessa ({rssi} dBm)")
        else:
            self.lbl_base_status.setText("Base Stepper: Disconnessa")
            self.lbl_theta.setText("Azimut (Base): --°")
        self._update_connection_ui()

    def _on_payload_status(self, connected: bool, rssi: int):
        self.payload_is_connected = connected
        if connected:
            self.lbl_payload_status.setText(f"Payload LiDAR: Connesso ({rssi} dBm)")
        else:
            self.lbl_payload_status.setText("Payload LiDAR: Disconnesso")
            self.lbl_distance.setText("Distanza LiDAR: -- cm")
        self._update_connection_ui()

    def _update_connection_ui(self):
        self.btn_connect.setEnabled(True)
        if self.base_is_connected or self.payload_is_connected:
            self.btn_connect.setText("Disconnetti Dispositivi")
        else:
            self.btn_connect.setText("Connetti Dispositivi")

        both_ready = self.base_is_connected and self.payload_is_connected
        self.btn_scan.setEnabled(both_ready)
        
        if not both_ready and self.btn_scan.text() == "Ferma Scansione":
            self.btn_scan.setText("Avvia Scansione 3D")

    def _on_azimuth(self, theta_deg):
        self.current_plate_azimuth = theta_deg
        self.sync_engine.add_azimuth(theta_deg)
        self.lbl_theta.setText(f"Azimut (Base): {theta_deg:.1f}°")

    def _on_lidar(self, dist_cm, servo_angle):
        self.lbl_servo.setText(f"Tilt Pitch: {servo_angle}°")
        self.lbl_distance.setText(f"Distanza LiDAR: {dist_cm} cm")
        
        pt = self.sync_engine.add_lidar_reading(dist_cm, servo_angle)
        if pt and len(self.sync_engine.points_3d) % 15 == 0:
            self.viewer.update_cloud(self.sync_engine.points_3d)
            self.lbl_pts_count.setText(f"Punti 3D Acquisiti: {len(self.sync_engine.points_3d)}")

    def _on_lap_completed(self, _):
        if self.btn_scan.text() == "Ferma Scansione":
            now = time.time()
            self.current_step_idx += 1

            # Ricalcola la durata reale del giro
            elapsed = now - self.scan_start_time
            self.est_lap_duration = elapsed / self.current_step_idx

            if self.current_step_idx < self.total_tilt_steps:
                next_angle = self.target_servo_angles[self.current_step_idx]
                self.log_console.append(
                    f">>> Giro completato! Salita a {next_angle}° "
                    f"(Livello {self.current_step_idx + 1}/{self.total_tilt_steps})..."
                )
                self.ble_manager.send_command("STEP_TILT", step=TILT_STEP_DEG)
            else:
                # Tutti i layer (incluso l'ultimo al vertice) sono stati scansionati a 360°
                self.progress_bar.setValue(100)
                self.progress_bar.setFormat("100% - Completato")
                self.lbl_time_info.setText("Scansione 3D completata con successo!")
                self.log_console.append(">>> Scansione 3D completata al 100%! <<<")
                self.eta_timer.stop()
                self._toggle_scan()

    def _update_time_display(self):
        if self.btn_scan.text() != "Ferma Scansione":
            return

        fraction_current_lap = min(1.0, max(0.0, self.current_plate_azimuth / 360.0))
        continuous_progress = self.current_step_idx + fraction_current_lap
        
        perc = int(min(100, (continuous_progress / self.total_tilt_steps) * 100))
        self.progress_bar.setValue(perc)

        remaining_units = max(0.0, self.total_tilt_steps - continuous_progress)
        remaining_sec = int(remaining_units * self.est_lap_duration)

        mins = remaining_sec // 60
        secs = remaining_sec % 60
        time_str = f"{mins:02d}:{secs:02d}"

        self.progress_bar.setFormat(f"{perc}% - Rimangono: {time_str}")
        self.lbl_time_info.setText(f"Tempo rimanente: {mins} min {secs} sec")

    def closeEvent(self, event):
        self.eta_timer.stop()
        self.ble_manager.stop()
        event.accept()