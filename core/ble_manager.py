import asyncio
from bleak import BleakClient, BleakScanner
from PyQt6.QtCore import QThread, pyqtSignal
from config import (
    BASE_NODE_NAME, BASE_AZIMUTH_CHAR_UUID, BASE_CTRL_CHAR_UUID,
    PAYLOAD_NODE_NAME, PAYLOAD_SCAN_CHAR_UUID, PAYLOAD_CTRL_CHAR_UUID
)

class BLEManager(QThread):
    base_connected_sig = pyqtSignal(bool, int)      # status, rssi
    payload_connected_sig = pyqtSignal(bool, int)   # status, rssi
    azimuth_received_sig = pyqtSignal(float)        # theta_deg
    lidar_received_sig = pyqtSignal(int, int)       # dist_cm, servo_angle
    log_sig = pyqtSignal(str)
    lap_completed_sig = pyqtSignal(int)             # revolution count

    def __init__(self):
        super().__init__()
        self.loop = None
        self.client_base = None
        self.client_payload = None
        self.is_running = True
        self.command_queue = asyncio.Queue()
        self.prev_plate_deg = 0.0

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._main_loop())

    async def _main_loop(self):
        while self.is_running:
            try:
                cmd, args = await asyncio.wait_for(self.command_queue.get(), timeout=0.1)
                if cmd == "CONNECT":
                    await self._connect_nodes()
                elif cmd == "DISCONNECT":
                    await self._disconnect_nodes()
                elif cmd == "START_SCAN":
                    rpm = args.get("rpm", 10)
                    self.prev_plate_deg = 0.0
                    
                    # 1. Avvia prima il Payload LiDAR
                    await self._send_payload_cmd(bytes([0x01]))
                    await asyncio.sleep(0.15)
                    
                    # 2. Avvia la Base Stepper su 360° completi [0x01, rpm, 0, 0, 3600_H, 3600_L]
                    min_enc = 0
                    max_enc = 3600
                    base_payload = bytearray([
                        0x01, int(rpm),
                        (min_enc >> 8) & 0xFF, min_enc & 0xFF,
                        (max_enc >> 8) & 0xFF, max_enc & 0xFF
                    ])
                    await self._send_base_cmd(base_payload)
                elif cmd == "STOP_SCAN":
                    await self._send_base_cmd(bytes([0x00]))
                    await asyncio.sleep(0.1)
                    await self._send_payload_cmd(bytes([0x00]))
                elif cmd == "SET_SPEED":
                    rpm = args.get("rpm", 10)
                    min_enc = 0
                    max_enc = 3600
                    base_payload = bytearray([
                        0x01, int(rpm),
                        (min_enc >> 8) & 0xFF, min_enc & 0xFF,
                        (max_enc >> 8) & 0xFF, max_enc & 0xFF
                    ])
                    await self._send_base_cmd(base_payload)
                elif cmd == "STEP_TILT":
                    step = args.get("step", 5)
                    await self._send_payload_cmd(bytes([0x03, step]))
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                self.log_sig.emit(f"BLE MainLoop Error: {e}")

    def _on_base_disconnected(self, client: BleakClient):
        self.log_sig.emit("[BLE] Base Stepper disconnessa!")
        self.base_connected_sig.emit(False, 0)
        self.client_base = None

    def _on_payload_disconnected(self, client: BleakClient):
        self.log_sig.emit("[BLE] Payload LiDAR disconnesso!")
        self.payload_connected_sig.emit(False, 0)
        self.client_payload = None

    async def _connect_nodes(self):
        self.log_sig.emit("Scansione dispositivi BLE in corso...")
        devices = await BleakScanner.discover(timeout=4.0, return_adv=True)
        
        base_dev, payload_dev = None, None
        base_rssi, payload_rssi = -100, -100

        for d, adv in devices.values():
            if d.name == BASE_NODE_NAME:
                base_dev = d
                base_rssi = adv.rssi
            elif d.name == PAYLOAD_NODE_NAME:
                payload_dev = d
                payload_rssi = adv.rssi

        # Connessione Base Stepper
        if base_dev and (not self.client_base or not self.client_base.is_connected):
            try:
                self.client_base = BleakClient(
                    base_dev, 
                    disconnected_callback=self._on_base_disconnected
                )
                await self.client_base.connect()
                await self.client_base.start_notify(BASE_AZIMUTH_CHAR_UUID, self._on_base_notify)
                self.base_connected_sig.emit(True, base_rssi)
                self.log_sig.emit(f"Base Connessa ({base_rssi} dBm)")
            except Exception as e:
                self.log_sig.emit(f"Errore connessione Base: {e}")
                self.base_connected_sig.emit(False, 0)
        elif not base_dev:
            self.log_sig.emit("Base Stepper non trovata.")

        # Connessione Payload LiDAR
        if payload_dev and (not self.client_payload or not self.client_payload.is_connected):
            try:
                self.client_payload = BleakClient(
                    payload_dev, 
                    disconnected_callback=self._on_payload_disconnected
                )
                await self.client_payload.connect()
                await self.client_payload.start_notify(PAYLOAD_SCAN_CHAR_UUID, self._on_payload_notify)
                self.payload_connected_sig.emit(True, payload_rssi)
                self.log_sig.emit(f"Payload Connesso ({payload_rssi} dBm)")
            except Exception as e:
                self.log_sig.emit(f"Errore connessione Payload: {e}")
                self.payload_connected_sig.emit(False, 0)
        elif not payload_dev:
            self.log_sig.emit("Payload LiDAR non trovato.")

    async def _disconnect_nodes(self):
        self.log_sig.emit("Disconnessione dai nodi BLE in corso...")
        
        await self._send_base_cmd(bytes([0x00]))
        await asyncio.sleep(0.05)
        await self._send_payload_cmd(bytes([0x00]))

        if self.client_base and self.client_base.is_connected:
            try:
                await self.client_base.disconnect()
            except Exception as e:
                self.log_sig.emit(f"Errore disconnect Base: {e}")
            self.client_base = None
            self.base_connected_sig.emit(False, 0)

        if self.client_payload and self.client_payload.is_connected:
            try:
                await self.client_payload.disconnect()
            except Exception as e:
                self.log_sig.emit(f"Errore disconnect Payload: {e}")
            self.client_payload = None
            self.payload_connected_sig.emit(False, 0)

        self.log_sig.emit("Tutti i dispositivi BLE sono stati disconnessi.")

    def _on_base_notify(self, sender, data: bytearray):
        if len(data) >= 6:
            theta_enc = (data[0] << 8) | data[1]
            plate_deg = theta_enc / 10.0

            self.azimuth_received_sig.emit(plate_deg)

            # Trigger fine giro del piatto a 360°
            if self.prev_plate_deg > 320.0 and plate_deg < 40.0:
                self.lap_completed_sig.emit(1)
            self.prev_plate_deg = plate_deg

    def _on_payload_notify(self, sender, data: bytearray):
        if len(data) >= 7:
            dist = (data[0] << 8) | data[1]
            servo_angle = data[2]
            self.lidar_received_sig.emit(dist, servo_angle)

    async def _send_base_cmd(self, payload: bytes):
        if self.client_base and self.client_base.is_connected:
            try:
                await self.client_base.write_gatt_char(BASE_CTRL_CHAR_UUID, payload, response=False)
            except Exception as e:
                self.log_sig.emit(f"Errore invio comando Base: {e}")

    async def _send_payload_cmd(self, payload: bytes):
        if self.client_payload and self.client_payload.is_connected:
            try:
                await self.client_payload.write_gatt_char(PAYLOAD_CTRL_CHAR_UUID, payload, response=False)
            except Exception as e:
                self.log_sig.emit(f"Errore invio comando Payload: {e}")

    def send_command(self, cmd: str, **kwargs):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.command_queue.put_nowait, (cmd, kwargs))

    def stop(self):
        self.is_running = False
        self.send_command("DISCONNECT")
        self.quit()
        self.wait()