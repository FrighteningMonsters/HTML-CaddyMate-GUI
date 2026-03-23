# P2P WiFi Direct connection guide (TurtleBot ↔ Raspberry Pi)

This document describes how to use the scripts and how they work so the TurtleBot acts as a **WiFi Direct Group Owner (GO)** and creates a `DIRECT-xx` network, the Pi joins as a **client** via WPS, and both sides talk over a **static IP** setup.

---

## 1. How the connection works (one-line summary)

**WiFi Direct** creates a small wireless AP (group) on the TurtleBot side, and the Pi connects to that SSID using **WPS PBC (Push Button Configuration)**. Without DHCP, **manually assigned IPs on the same subnet** are used so L3 connectivity is predictable.

### 1.1 Role split

| Device | Role | From `wpa_supplicant`’s view |
|--------|------|-------------------------------|
| **TurtleBot** | P2P **Group Owner** | Group via `p2p-dev-wlan0` → GO role on virtual `p2p-wlan0-*` |
| **Raspberry Pi** | **Client (STA)** | `wlan0` associates to the `DIRECT-xx` AP (WPS) |

### 1.2 What the scripts do (flow)

**TurtleBot (`turtlebot_p2p_setup.sh`)**

1. Remove any existing `p2p-wlan0-*` group and clear state with `p2p_flush` (so interface numbers do not pile up on reruns).
2. Create a new P2P group with `p2p_group_add` → a `DIRECT-xx` SSID appears nearby.
3. Assign **`10.0.0.1/24`** on the GO interface (`p2p-wlan0-*`).
4. Open a WPS window on that interface with **`wps_pbc`** (the client must match with the same method).

**Pi (`pi_p2p_connect.sh`)**

1. On `wlan0`, scan for the **BSSID** of a `DIRECT` SSID (if several, pick the stronger RSSI) and connect with **`wps_pbc <BSSID>`**.
2. Wait until `wpa_state=COMPLETED` (default ~60s, tunable via environment variable).
3. Add **`10.0.0.2/24`** on `wlan0`.
4. Check reachability to the TurtleBot with **`ping 10.0.0.1`**.

### 1.3 What the IPs mean

| IP | Device | Interface (typical) |
|----|--------|---------------------|
| **10.0.0.1** | TurtleBot (GO) | `p2p-wlan0-*` |
| **10.0.0.2** | Raspberry Pi | `wlan0` |

This setup assumes **no DHCP on the GO side**, so on the Pi you **must assign `10.0.0.2` manually** (as the script does) to be on the same `/24` as the TurtleBot.

### 1.4 Difference from “connect only in WiFi settings”

Even if the OS WiFi UI shows you connected to `DIRECT-xx`, if **static IP (`10.0.0.2`) and routing do not match**, you may not get application-level “connected” behavior for `ping 10.0.0.1`, ROS2, Nav2, etc. The UI “connected” state is usually **wireless association** only; these scripts align the **L3 addressing** this stack expects.

---

## 2. Recommended way to run

### 2.1 Prerequisites

- `wpa_cli` works on both TurtleBot and Pi (typically with `wpa_supplicant`).
- On the Pi, if **NetworkManager owns `wlan0`**, it can conflict with `wpa_cli` → for testing, turn that interface off in NM or mark it **unmanaged**.
- **Order and timing matter.** The GO-side WPS window often requires the client to complete WPS within about **~2 minutes**; by message timing, run the Pi script **as soon as possible after** **`P2P ready`**.

### 2.2 Recommended order (each connection)

1. On the **TurtleBot**:
   ```bash
   bash ~/turtlebot_p2p_setup.sh
   ```
2. When you see `=== P2P ready. Run Pi p2p_connect.sh within 60 seconds ===`, **immediately** (ideally within tens of seconds)
3. On the **Pi**:
   ```bash
   bash ~/pi_p2p_connect.sh
   ```
4. On success you get `=== P2P connected. You can now run python3 server.py ===` and the final `10.0.0.1` ping check passes.

### 2.3 On retries (e.g. `BUSY_FAIL`)

- If you see **`BUSY_FAIL`**, **do not hammer `wps_pbc` back-to-back**; wait **10–15+ seconds**, then **rerun TurtleBot setup from the start** and run the Pi script **once**.
- It is usually more stable to align while the **GO-side WPS window is freshly open** than to loop only on the Pi.

### 2.4 Pi options (when needed)

- Different wireless interface name:
  ```bash
  WLAN_IF=wlan1 bash ~/pi_p2p_connect.sh
  ```
- Longer wait for association (starting Pi too late can miss the GO WPS validity window):
  ```bash
  WPA_WAIT_SEC=90 bash ~/pi_p2p_connect.sh
  ```

---

## 3. Verifying connectivity (ping)

| Where | Command | Checks |
|-------|---------|--------|
| **Pi** | `ping 10.0.0.1` | Pi → TurtleBot (GO) |
| **TurtleBot** | `ping 10.0.0.2` | TurtleBot → Pi |

If both reply, **IP-level** connectivity on that P2P link is OK. Nav2/ROS2 may still need domain ID, firewall, nodes started, etc.

---

## 4. File layout

```
turtlebot3/
└── scripts/
    ├── turtlebot_p2p_setup.sh   ← run on TurtleBot
    ├── pi_p2p_connect.sh        ← run on Raspberry Pi
    ├── p2p_diag.sh              ← optional: collect state when connection fails
    └── README_P2P.md            ← this document
```

---

## 5. How to deploy

### TurtleBot

**USB**

1. Copy `turtlebot_p2p_setup.sh` from your PC to USB.
2. Plug USB into the TurtleBot, then:
   ```bash
   cp /media/ubuntu/*/turtlebot_p2p_setup.sh ~/
   chmod +x ~/turtlebot_p2p_setup.sh
   ```

**SCP example**

```bash
scp scripts/turtlebot_p2p_setup.sh ubuntu@<TURTLEBOT_IP>:~/
ssh ubuntu@<TURTLEBOT_IP> chmod +x ~/turtlebot_p2p_setup.sh
```

### Raspberry Pi

**USB**

```bash
cp /media/pi/*/pi_p2p_connect.sh ~/
chmod +x ~/pi_p2p_connect.sh
```

**If the repo is already cloned**

```bash
cd ~/turtlebot3
cp scripts/pi_p2p_connect.sh ~/
chmod +x ~/pi_p2p_connect.sh
```

---

## 6. Troubleshooting summary

| Symptom | What to check |
|---------|----------------|
| `p2p-wlan0-0` → `p2p-wlan0-1` only increments | Setup tries to remove the old group, but driver/state may leave leftovers. If warnings repeat, **reboot** or **restart `wpa_supplicant`**. |
| WPS timeout / no connect | Run Pi right after TurtleBot messages, check **country code** (`sudo iw reg get`), NM vs `wpa_cli` conflict. |
| `BUSY_FAIL` | Do not rerun in tight loops; wait and **rerun TurtleBot setup from the start**. |

---

## 7. Run order (short)

1. **TurtleBot:** `bash ~/turtlebot_p2p_setup.sh`
2. **Pi as soon as possible:** `bash ~/pi_p2p_connect.sh`
3. Confirm success message and `ping 10.0.0.1`, then run your app (e.g. `python3 server.py`)

---

## 8. When connection fails — narrowing causes

Errors look similar whenever `wpa_state=COMPLETED` is never reached, so **right after failure** collect the items below once; that makes it easier to separate NM conflict, BSSID, regulatory, driver issues, etc.

### 8.1 Diagnostic script (recommended)

Copy `p2p_diag.sh` from the repo to each device, then:

**Raspberry Pi** (right after a failed attempt, same terminal session):

```bash
bash ~/p2p_diag.sh 2>&1 | tee ~/p2p_diag_pi.txt
```

**TurtleBot** (while GO is up at the same time):

```bash
bash ~/p2p_diag.sh turtlebot 2>&1 | tee ~/p2p_diag_tb.txt
```

From `p2p_diag_pi.txt` and `p2p_diag_tb.txt` you can check in one place:

- On Pi, whether **`nmcli device status`** shows `wlan0` under NetworkManager,
- Whether **`wpa_cli status`** `wpa_state` / `ssid` / `bssid` match expectations,
- Whether **`scan_results`** `DIRECT` rows match the TurtleBot GO,
- Whether **`iw reg`** looks wrong,
- On TurtleBot, whether **`p2p-wlan0-*` addresses and `iw dev … link`** look correct for GO.

### 8.2 Minimal manual checks

- Pi: `sudo wpa_cli -i wlan0 status`
- Pi: `nmcli device status` (if using NetworkManager)
- TurtleBot: `ip addr show p2p-wlan0-0` (adjust index for your environment)

These three often separate “NM conflict” from “no association at all”.
