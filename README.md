# 3D LiDAR Scanner - Hardware Setup & System Architecture

A modular, cable-free 3D point cloud LiDAR scanning system combining a **TF-Luna** Time-of-Flight (ToF) sensor, an **SG90** servo gimbal for vertical pitch elevation, and an independent **28BYJ-48** stepper-driven rotary stage for full horizontal azimuth scanning.

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
