# 🌐 3D LiDAR Scanner — Hardware Setup & System Architecture

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PyQt6%20%7C%20PyQtGraph-green.svg)](https://riverbankcomputing.com/software/pyqt/)
[![Rendering](https://img.shields.io/badge/3D%20Engine-OpenGL%20Hardware%20Accel-orange.svg?logo=opengl&logoColor=white)](https://www.opengl.org/)
[![Hardware](https://img.shields.io/badge/Hardware-Dual%20ESP32%20%7C%20TF--Luna%20%7C%20SG90-red.svg)](https://en.wikipedia.org/wiki/ESP32)
[![Protocol](https://img.shields.io/badge/BLE-Multi--Link%20Telemetry-blueviolet.svg)](https://www.bluetooth.com/)
[![Export](https://img.shields.io/badge/Export-PLY%20%7C%20XYZ%20%7C%20CSV%20%7C%20JSON-lightgrey.svg)](https://en.wikipedia.org/wiki/PLY_(file_format))
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A modular, cable-free 3D point cloud LiDAR scanning system combining a **TF-Luna** Time-of-Flight (ToF) sensor, an **SG90** servo gimbal for vertical pitch elevation, and an independent **28BYJ-48** stepper-driven rotary stage for full horizontal azimuth scanning.

> **Universal Hardware Support:** Seamlessly shares the same physical hardware and ESP32 firmware with **LiDAR Studio 2D**. Operates in multi-layer volumetric 3D mode by synchronizing automatic gimbal pitch stepping with 360° azimuth rotations.

---
<img width="1887" height="955" alt="Screenshot 2026-08-28 165730" src="https://github.com/user-attachments/assets/1dbd738b-b4a4-406a-9b78-87b1882f1b8c" />

https://github.com/user-attachments/assets/b3a8f110-796a-41e4-b7f8-edfbe0a71f65

---

## 1. Dual-Node Distributed Architecture (BLE Multi-Link)

The system physically and logically decouples the rotating base from the moving sensor payload stage. This eliminates the need for expensive slip rings and prevents cable tangling. Both ESP32 nodes act as independent BLE peripheral servers streaming high-frequency telemetry to a central **Python Desktop Controller (PyQt6 + Bleak + PyOpenGL)**.

```text
┌──────────────────────────────┐                 ┌──────────────────────────────┐
│       BASE ESP32 NODE        │                 │      PAYLOAD ESP32 NODE      │
│     (Fixed Base / Rotor)     │                 │    (Onboard Moving Stage)    │
├──────────────────────────────┤                 ├──────────────────────────────┤
│ • 28BYJ-48 Stepper + ULN2003 │                 │ • TF-Luna LiDAR (UART / ToF) │
│ • Half-Step Phase Sequencer  │                 │ • SG90 Micro-Servo (PWM Gim) │
│ • Streams real-time θ angle  │                 │ • Streams [Distance R, Pitch]│
└──────────────┬───────────────┘                 └──────────────┬───────────────┘
               │                                                │
               │ BLE Notify (Azimuth Stream)                    │ BLE Notify (Distance & Pitch)
               ▼                                                ▼
       ┌────────────────────────────────────────────────────────────────┐
       │             PYTHON DESKTOP MASTER (Bleak Engine)               │
       ├────────────────────────────────────────────────────────────────┤
       │ • Dual concurrent BLE client links with auto-reconnection      │
       │ • Time-aligned interpolation of θ(t), R(t), and φ(t)           │
       │ • Real-time spherical-to-Cartesian coordinate mapping          │
       │ • Real-time 3D visualization (PyQtGraph / OpenGL)              │
       │ • Automatic pitch elevation stepping upon full 360° rotation   │
       └────────────────────────────────────────────────────────────────┘
