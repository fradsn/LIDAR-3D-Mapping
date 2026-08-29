# 🌐 3D LiDAR Scanner — Hardware Setup & System Architecture

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PyQt6%20%7C%20PyQtGraph-green.svg)](https://riverbankcomputing.com/software/pyqt/)
[![Rendering](https://img.shields.io/badge/3D%20Engine-OpenGL%20Hardware%20Accel-orange.svg?logo=opengl&logoColor=white)](https://www.opengl.org/)
[![Hardware](https://img.shields.io/badge/Hardware-Dual%20ESP32%20%7C%20TF--Luna%20%7C%20SG90-red.svg)](https://en.wikipedia.org/wiki/ESP32)
[![Protocol](https://img.shields.io/badge/BLE-Multi--Link%20Telemetry-blueviolet.svg)](https://www.bluetooth.com/)
[![Export](https://img.shields.io/badge/Export-PLY%20%7C%20XYZ%20%7C%20CSV%20%7C%20JSON-lightgrey.svg)](https://en.wikipedia.org/wiki/PLY_(file_format))
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A modular, cable-free 3D point cloud LiDAR scanning system combining a **TF-Luna** Time-of-Flight (ToF) sensor, an **SG90** servo gimbal for vertical pitch elevation, and an independent **28BYJ-48** stepper-driven rotary stage for full horizontal azimuth scanning.

> **Universal Hardware & Firmware Ecosystem:** Shares identical physical hardware and unified ESP32 firmware with **LiDAR Studio 2D**. Operates in multi-layer volumetric 3D mode by synchronizing automatic gimbal pitch stepping with continuous 360° azimuth sweeps and real-time RPM modulation.

---

## 📸 System Overview & Demonstration

### 🖥️ Desktop GUI (Real-Time 3D Point Cloud View)
<p align="center">
  <img src="docs/images/gui_preview.png" width="95%" alt="3D LiDAR Scanner GUI Preview"/>
</p>

### 🎬 Scanning In Action
<p align="center">
  <video src="docs/videos/demo.mp4" width="90%" controls></video>
</p>

---

## 🛠️ Physical Hardware Architecture

| Front View | Top View | Side Angle |
| :---: | :---: | :---: |
| <img src="docs/images/hardware_front.png" width="100%" alt="Front View"/> | <img src="docs/images/hardware_top.png" width="100%" alt="Top View"/> | <img src="docs/images/hardware_side1.png" width="100%" alt="Side Angle"/> |

| Elevation Detail | Base & Gimbal Assembly |
| :---: | :---: |
| <img src="docs/images/hardware_side2.png" width="100%" alt="Elevation Detail"/> | <img src="docs/images/hardware_detail.png" width="100%" alt="Assembly Detail"/> |

---

## 1. Dual-Node Distributed Architecture (BLE Multi-Link)

The system physically and logically decouples the rotating base from the moving sensor payload stage. This eliminates the need for expensive slip rings and prevents cable tangling. Both ESP32 nodes act as independent BLE peripheral servers streaming high-frequency telemetry to a central **Python Desktop Controller (PyQt6 + Bleak + PyOpenGL)** via non-blocking, low-latency GATT characteristics (`PROPERTY_WRITE_NR`).

```text
┌──────────────────────────────┐                 ┌──────────────────────────────┐
│        BASE ESP32 NODE       │                 │      PAYLOAD ESP32 NODE      │
│     (Fixed Base / Rotor)     │                 │    (Onboard Moving Stage)    │
├──────────────────────────────┤                 ├──────────────────────────────┤
│ • 28BYJ-48 Stepper + ULN2003 │                 │ • TF-Luna LiDAR (UART / ToF) │
│ • Half-Step Phase Sequencer  │                 │ • SG90 Micro-Servo (PWM Gim) │
│ • Real-Time Azimuth Stream θ │                 │ • Continuous UART Flush Loop │
│ • Remote RPM Speed Control   │                 │ • Streams [Dist R, Pitch φ]  │
└──────────────┬───────────────┘                 └──────────────┬───────────────┘
               │                                                │
               │ BLE Notify (Azimuth Stream 6B)                 │ BLE Notify (Distance & Pitch 7B)
               ▼                                                ▼
       ┌────────────────────────────────────────────────────────────────┐
       │             PYTHON DESKTOP MASTER (Bleak Engine)               │
       ├────────────────────────────────────────────────────────────────┤
       │ • Dual concurrent BLE client links with auto-reconnection      │
       │ • Time-aligned interpolation of θ(t), R(t), and φ(t)           │
       │ • Real-time spherical-to-Cartesian coordinate mapping          │
       │ • Real-time 3D visualization (PyQtGraph / OpenGL)              │
       │ • Dynamic RPM Stepper Speed Adjustment (4–16 RPM)              │
       │ • Dynamic ETA & Multi-Layer Pitch Stepping upon full 360° lap  │
       └────────────────────────────────────────────────────────────────┘
