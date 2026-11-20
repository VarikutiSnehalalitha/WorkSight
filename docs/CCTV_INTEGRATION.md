# WorkSight — Hardware CCTV & On-Premise AI Vision Integration Guide

## 1. Connecting Physical RTSP Cameras

1. Ensure the WorkSight backend is deployed on-premise (or on a private VLAN/VPN with access to your NVR/IP cameras) and install AI/CV dependencies:
   ```bash
   pip install -r backend/requirements-ai.txt
   ```
2. Set a dedicated production Fernet key in `.env`:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   Assign the output to `CAMERA_ENCRYPTION_KEY` and set `ALLOW_SIMULATED_FEEDS=false`.
3. Sign in as **Super Admin** (`owner@worksight.io`) and open **CCTV Monitoring → Add Camera**.
4. Select **Physical RTSP Stream**, enter your camera URI (e.g. `rtsp://192.168.10.42:554/h264Preview_01_sub`) and credentials, then click **Test Connection**.
5. On save, credentials are encrypted at rest with Fernet. The API only returns a masked endpoint (`rtsp://***@192.168.10.42:554/***`).

## 2. ONVIF Profile S Camera Discovery

Click **ONVIF Discover** in the CCTV Monitoring console to broadcast a WS-Discovery UDP multicast probe (`239.255.255.250:3702`) across the local LAN subnet. Discovered ONVIF cameras can be adopted directly into the camera registration modal.

## 3. Configuring Monitoring Zones

Each camera supports multiple normalized polygon zones (`0.0` to `1.0` coordinates):
- **`workspace`**: Counts anonymous physical occupancy and monitors extended workspace vacancy (spatial utilization only).
- **`entry_exit`**: Uses short-lived ephemeral motion vectors to detect passage crossings across the zone midpoint.
- **`restricted`**: Triggers a `critical` alert whenever an anonymous person enters the perimeter (e.g., server rooms, vaults).
- **`common_area`**: Tracks crowding against `max_occupancy`.

## 4. AI Computer Vision Pipeline (`backend/app/ai_vision/`)

- **Detector (`detector.py`)**: Uses `ultralytics.YOLO` (default `yolov8n.pt`) on PyTorch, strictly filtering `classes=[0]` (**person only**). Falls back to OpenCV HOG person detection if weights are not loaded.
- **Tracker (`EphemeralObjectTracker`)**: Short-lived centroid tracker with a 10-second expiration window. Tracks are never persisted across sessions or matched to employee identities.
- **Health & Obstruction (`manager.py`)**: Detects blacked-out/covered lenses (low luminance & low pixel variance) and manages automatic exponential-backoff reconnections on RTSP drops.

## 5. Encrypted Video Transport

In production deployments, terminate TLS/HTTPS (and WSS for WebSockets) in front of WorkSight using Nginx, Caddy, or Traefik so all MJPEG streams, short-lived stream tokens, and REST traffic are encrypted in transit.
