import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QPushButton, QLabel, QGroupBox, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QComboBox, QSlider, QScrollArea,
    QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

from ui.gl_widget import PointCloudView
from core.ble_manager import BLEManager
from core.sync_engine import SyncEngine
from core.exporter import export_to_ply, export_to_xyz, save_to_json, load_from_json
from config import SERVO_BOTTOM_DEG, SERVO_TOP_DEG

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D LiDAR Scanner - Unified Desktop")
        self.resize(1280, 800)

        self.sync_engine = SyncEngine()
        self.ble_manager = BLEManager()
        
        self.tilt_step_deg = 5
        self._recalculate_tilt_sequence()

        self.base_is_connected = False
        self.payload_is_connected = False
        self.current_plate_azimuth = 0.0
        
        self.scan_start_time = 0.0
        self.est_lap_duration = 54.0

        self.eta_timer = QTimer(self)
        self.eta_timer.setInterval(200)
        self.eta_timer.timeout.connect(self._update_time_display)

        self._create_menu_bar()
        self._setup_ui()
        self._bind_signals()
        
        self.ble_manager.start()

    def _recalculate_tilt_sequence(self):
        self.target_servo_angles = list(range(SERVO_BOTTOM_DEG, SERVO_TOP_DEG - 1, -self.tilt_step_deg))
        if self.target_servo_angles[-1] != SERVO_TOP_DEG:
            self.target_servo_angles.append(SERVO_TOP_DEG)
        self.total_tilt_steps = len(self.target_servo_angles)
        self.current_step_idx = 0

    def _create_menu_bar(self):
        menubar = self.menuBar()

        # --- MENU FILE (ESPORTAZIONE E SALVATAGGI) ---
        file_menu = menubar.addMenu("&File")

        act_export_ply = QAction("Esporta come Mesh/Point Cloud (.ply)...", self)
        act_export_ply.triggered.connect(self._export_ply)
        file_menu.addAction(act_export_ply)

        act_export_xyz = QAction("Esporta coordinate XYZ (.xyz / .csv)...", self)
        act_export_xyz.triggered.connect(self._export_xyz)
        file_menu.addAction(act_export_xyz)

        file_menu.addSeparator()

        act_save_json = QAction("Salva Scansione (.json)...", self)
        act_save_json.triggered.connect(self._save_session)
        file_menu.addAction(act_save_json)

        act_load_json = QAction("Carica Scansione (.json)...", self)
        act_load_json.triggered.connect(self._load_session)
        file_menu.addAction(act_load_json)

        file_menu.addSeparator()

        act_screenshot = QAction("Cattura Screenshot 3D (.png)...", self)
        act_screenshot.triggered.connect(self._capture_screenshot)
        file_menu.addAction(act_screenshot)

        # --- MENU VISTA ---
        view_menu = menubar.addMenu("&Vista")
        
        act_iso = QAction("Vista Isometrica (3D)", self)
        act_iso.triggered.connect(lambda: self.viewer.set_view_iso())
        view_menu.addAction(act_iso)

        act_top = QAction("Vista dall'Alto (Pianta 2D)", self)
        act_top.triggered.connect(lambda: self.viewer.set_view_top())
        view_menu.addAction(act_top)

        act_front = QAction("Vista Frontale", self)
        act_front.triggered.connect(lambda: self.viewer.set_view_front())
        view_menu.addAction(act_front)

        act_side = QAction("Vista Laterale", self)
        act_side.triggered.connect(lambda: self.viewer.set_view_side())
        view_menu.addAction(act_side)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # 1. Visualizzatore 3D (Sinistra)
        self.viewer = PointCloudView()
        main_layout.addWidget(self.viewer, stretch=3)

        # 2. Pannello di Controllo con Scroll Area (Destra)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        panel_widget = QWidget()
        panel_layout = QVBoxLayout(panel_widget)
        scroll.setWidget(panel_widget)
        main_layout.addWidget(scroll, stretch=1)

        # Gruppo Connessioni BLE
        conn_group = QGroupBox("Dispositivi BLE")
        conn_box = QVBoxLayout(conn_group)
        self.btn_connect = QPushButton("Connetti Dispositivi")
        self.lbl_base_status = QLabel("Base Stepper: Disconnessa")
        self.lbl_payload_status = QLabel("Payload LiDAR: Disconnesso")
        conn_box.addWidget(self.btn_connect)
        conn_box.addWidget(self.lbl_base_status)
        conn_box.addWidget(self.lbl_payload_status)
        panel_layout.addWidget(conn_group)

        # Gruppo Parametri di Scansione
        config_group = QGroupBox("Parametri di Scansione")
        cfg_box = QVBoxLayout(config_group)
        
        cfg_box.addWidget(QLabel("Risoluzione / Densità:"))
        self.combo_res = QComboBox()
        self.combo_res.addItem("⚡ Fast Test (Passo 15° ~4 min)", 15)
        self.combo_res.addItem("⚡ Standard (Passo 5° ~15 min)", 5)
        self.combo_res.addItem("🔬 Ultra High-Density (Passo 2° ~35 min)", 2)
        self.combo_res.setCurrentIndex(1)
        self.combo_res.currentIndexChanged.connect(self._on_resolution_changed)
        cfg_box.addWidget(self.combo_res)

        cfg_box.addWidget(QLabel("Altezza Sensore da Terra (cm):"))
        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(0.0, 300.0)
        self.spin_height.setValue(0.0)
        self.spin_height.setSingleStep(1.0)
        self.spin_height.setSuffix(" cm")
        cfg_box.addWidget(self.spin_height)

        panel_layout.addWidget(config_group)

        # Gruppo Rendering & Telecamera
        render_group = QGroupBox("Strumenti di Rendering & Vista")
        render_box = QVBoxLayout(render_group)

        render_box.addWidget(QLabel("Mappa Colori:"))
        self.combo_cmap = QComboBox()
        self.combo_cmap.addItems(["Elevation (Gradient)", "Heatmap (Turbo)", "Radar Green", "Monochrome White"])
        self.combo_cmap.currentTextChanged.connect(self.viewer.set_colormap)
        render_box.addWidget(self.combo_cmap)

        render_box.addWidget(QLabel("Dimensione Punti:"))
        self.slider_pt_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_pt_size.setRange(1, 8)
        self.slider_pt_size.setValue(3)
        self.slider_pt_size.valueChanged.connect(self.viewer.set_point_size)
        render_box.addWidget(self.slider_pt_size)

        cam_grid = QGridLayout()
        btn_top = QPushButton("Top 2D")
        btn_top.clicked.connect(self.viewer.set_view_top)
        btn_iso = QPushButton("Iso 3D")
        btn_iso.clicked.connect(self.viewer.set_view_iso)
        btn_front = QPushButton("Frontale")
        btn_front.clicked.connect(self.viewer.set_view_front)
        btn_side = QPushButton("Laterale")
        btn_side.clicked.connect(self.viewer.set_view_side)
        
        cam_grid.addWidget(btn_top, 0, 0)
        cam_grid.addWidget(btn_iso, 0, 1)
        cam_grid.addWidget(btn_front, 1, 0)
        cam_grid.addWidget(btn_side, 1, 1)
        render_box.addLayout(cam_grid)

        panel_layout.addWidget(render_group)

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

        # Gruppo Avanzamento Scansione
        scan_group = QGroupBox("Avanzamento Scansione")
        scan_box = QVBoxLayout(scan_group)
        self.btn_scan = QPushButton("Avvia Scansione 3D")
        self.btn_scan.setEnabled(False)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Pronto")

        self.lbl_time_info = QLabel("Tempo rimanente: --:--")
        
        scan_box.addWidget(self.btn_scan)
        scan_box.addWidget(self.progress_bar)
        scan_box.addWidget(self.lbl_time_info)
        panel_layout.addWidget(scan_group)

        # Log Console
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(120)
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

    def _on_resolution_changed(self, idx):
        self.tilt_step_deg = self.combo_res.currentData()
        self._recalculate_tilt_sequence()
        self.log_console.append(f"Risoluzione aggiornata: Passo = {self.tilt_step_deg}° ({self.total_tilt_steps} livelli)")

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
            self.sync_engine.sensor_height_cm = self.spin_height.value()
            self.current_step_idx = 0
            self.current_plate_azimuth = 0.0
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("0% - Inizializzazione...")
            
            self.combo_res.setEnabled(False)
            self.spin_height.setEnabled(False)
            self.scan_start_time = time.time()
            self.lbl_time_info.setText("Tempo rimanente: Calcolo...")
            self.eta_timer.start()

            self.ble_manager.send_command("START_SCAN")
            self.btn_scan.setText("Ferma Scansione")
        else:
            self.eta_timer.stop()
            self.ble_manager.send_command("STOP_SCAN")
            self.btn_scan.setText("Avvia Scansione 3D")
            self.combo_res.setEnabled(True)
            self.spin_height.setEnabled(True)
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
            self.combo_res.setEnabled(True)
            self.spin_height.setEnabled(True)

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

            elapsed = now - self.scan_start_time
            self.est_lap_duration = elapsed / self.current_step_idx

            if self.current_step_idx < self.total_tilt_steps:
                next_angle = self.target_servo_angles[self.current_step_idx]
                self.log_console.append(
                    f">>> Giro completato! Salita a {next_angle}° "
                    f"(Livello {self.current_step_idx + 1}/{self.total_tilt_steps})..."
                )
                self.ble_manager.send_command("STEP_TILT", step=self.tilt_step_deg)
            else:
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

    # --- METODI ESPORTAZIONE FILE ---
    def _export_ply(self):
        if not self.sync_engine.points_3d:
            QMessageBox.warning(self, "Attenzione", "Nessun punto 3D presente da esportare.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Esporta Nuvola di Punti (.ply)", "", "Polygon File Format (*.ply)")
        if path:
            if not path.endswith(".ply"):
                path += ".ply"
            export_to_ply(path, self.sync_engine.points_3d, self.viewer.current_colors)
            self.log_console.append(f"Scansione esportata in PLY: {path}")
            QMessageBox.information(self, "Successo", f"File PLY salvato con successo:\n{path}")

    def _export_xyz(self):
        if not self.sync_engine.points_3d:
            QMessageBox.warning(self, "Attenzione", "Nessun punto 3D presente da esportare.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Esporta Coordinate XYZ (.xyz)", "", "Text XYZ (*.xyz);;CSV (*.csv)")
        if path:
            export_to_xyz(path, self.sync_engine.points_3d)
            self.log_console.append(f"Scansione esportata in XYZ: {path}")
            QMessageBox.information(self, "Successo", f"File XYZ salvato con successo:\n{path}")

    def _save_session(self):
        if not self.sync_engine.points_3d:
            QMessageBox.warning(self, "Attenzione", "Nessuna scansione presente da salvare.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salva Sessione JSON (.json)", "", "JSON Files (*.json)")
        if path:
            if not path.endswith(".json"):
                path += ".json"
            meta = {
                "tilt_step": self.tilt_step_deg,
                "sensor_height_cm": self.spin_height.value(),
                "total_points": len(self.sync_engine.points_3d),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            save_to_json(path, self.sync_engine.points_3d, meta)
            self.log_console.append(f"Sessione salvata in JSON: {path}")

    def _load_session(self):
        path, _ = QFileDialog.getOpenFileName(self, "Carica Sessione JSON (.json)", "", "JSON Files (*.json)")
        if path:
            pts, meta = load_from_json(path)
            if pts:
                self.sync_engine.points_3d = [tuple(p) for p in pts]
                self.viewer.update_cloud(self.sync_engine.points_3d)
                self.lbl_pts_count.setText(f"Punti 3D Acquisiti: {len(pts)}")
                if "sensor_height_cm" in meta:
                    self.spin_height.setValue(meta["sensor_height_cm"])
                self.log_console.append(f"Caricata sessione da {path} ({len(pts)} punti)")
                QMessageBox.information(self, "Caricato", f"Caricati {len(pts)} punti 3D!")

    def _capture_screenshot(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salva Screenshot (.png)", "", "PNG Image (*.png)")
        if path:
            if not path.endswith(".png"):
                path += ".png"
            self.viewer.capture_image(path)
            self.log_console.append(f"Screenshot salvato: {path}")

    def closeEvent(self, event):
        self.eta_timer.stop()
        self.ble_manager.stop()
        event.accept()