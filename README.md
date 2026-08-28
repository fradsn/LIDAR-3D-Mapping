# 3D LiDAR Scanner - Hardware Setup & System Architecture

A modular 3D point cloud LiDAR scanning system using a **TF-Luna** Time-of-Flight sensor, an **SG90** servo gimbal for vertical pitch elevation, and an independent **28BYJ-48** stepper-driven rotary base for horizontal azimuth scanning.

---

## 1. Dual-Node Distributed Architecture (BLE Multi-Link)

The system physically and logically decouples the rotating base from the moving sensor payload to prevent cable tangling. Both ESP32 nodes act as independent BLE peripheral servers streaming telemetry to a central **Python Desktop Controller (Bleak)**, which merges and synchronizes the streams in real time.

```text
┌──────────────────────────────┐                 ┌──────────────────────────────┐
│       BASE ESP32 NODE        │                 │      PAYLOAD ESP32 NODE      │
│     (Fixed Base / Rotor)     │                 │     (Onboard Moving Stage)   │
├──────────────────────────────┤                 ├──────────────────────────────┤
│ • 28BYJ-48 Stepper + ULN2003 │                 │ • TF-Luna LiDAR (UART)       │
│ • Rotary Azimuth Encoder     │                 │ • SG90 Micro-Servo (PWM)     │
│ • Streams real-time θ angle  │                 │ • Streams [Distance R, Pitch]│
└──────────────┬───────────────┘                 └──────────────┬───────────────┘
               │                                                │
               │ BLE Notify (Azimuth Stream)                    │ BLE Notify (Distance & Pitch)
               ▼                                                ▼
       ┌────────────────────────────────────────────────────────────────┐
       │             PYTHON DESKTOP MASTER (Bleak Engine)               │
       ├────────────────────────────────────────────────────────────────┤
       │ • Dual simultaneous BLE client connections                     │
       │ • Time-aligned synchronization of θ(t), R(t), and φ(t)         │
       │ • Real-time spherical-to-Cartesian point cloud reconstruction  │
       │ • Automatic layer stepping (increments pitch every 360° turn)  │
       └────────────────────────────────────────────────────────────────┘
