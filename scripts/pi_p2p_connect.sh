#!/bin/bash
# Pi P2P WiFi Direct Connect
# Run: bash ~/pi_p2p_connect.sh
# Run within 60 seconds after TurtleBot p2p_setup.sh completes
#
# If you see BUSY_FAIL: wait 10–15 s before retrying; do not spam wps_pbc.
# If NetworkManager manages Wi-Fi, wpa_cli may fail — unmanage wlan0 or use nmcli.

WLAN_IF="${WLAN_IF:-wlan0}"
# Seconds to poll for COMPLETED after wps_pbc (often 10–40s; GO WPS window ~120s total)
WPA_WAIT_SEC="${WPA_WAIT_SEC:-60}"

set -e

echo "[1/7] Removing existing 10.0.0.2 from $WLAN_IF..."
sudo ip addr del 10.0.0.2/24 dev "$WLAN_IF" 2>/dev/null || true

echo "[2/7] Clearing stale WPS / association (reduces BUSY_FAIL)..."
sudo wpa_cli -i "$WLAN_IF" wps_cancel 2>/dev/null || true
sudo wpa_cli -i "$WLAN_IF" disconnect 2>/dev/null || true
sleep 2

echo "[3/7] Scanning for DIRECT network..."
sudo wpa_cli -i "$WLAN_IF" scan
sleep 5

echo "[4/7] Checking for DIRECT network..."
SCAN=$(sudo wpa_cli -i "$WLAN_IF" scan_results)
if ! echo "$SCAN" | grep -q DIRECT; then
  echo "ERROR: No DIRECT network found. Run TurtleBot p2p_setup.sh first."
  exit 1
fi

# Pick strongest DIRECT-* by signal (field 3); avoids stale/wrong BSSID if several appear
BSSID=$(echo "$SCAN" | awk '/DIRECT/ {print $1, $3}' | sort -k2 -nr | head -1 | awk '{print $1}')
if [ -z "$BSSID" ]; then
  echo "ERROR: Could not parse BSSID for DIRECT network."
  exit 1
fi
echo "    Connecting to BSSID: $BSSID"

echo "[5/7] WPS PBC connection..."
if ! sudo wpa_cli -i "$WLAN_IF" wps_pbc "$BSSID" | grep -q OK; then
  echo "ERROR: wps_pbc failed (if BUSY_FAIL, wait 15s and run TurtleBot setup again, then this script)."
  exit 1
fi

echo "[6/7] Waiting for wpa_state=COMPLETED (up to ${WPA_WAIT_SEC}s)..."
deadline=$((SECONDS + WPA_WAIT_SEC))
while [ "$SECONDS" -lt "$deadline" ]; do
  if sudo wpa_cli -i "$WLAN_IF" status | grep -q "wpa_state=COMPLETED"; then
    break
  fi
  sleep 2
done

if ! sudo wpa_cli -i "$WLAN_IF" status | grep -q "wpa_state=COMPLETED"; then
  echo "ERROR: Connection not completed. WPS may have timed out."
  echo "    Check: same 60s window as TurtleBot, country code (sudo iw reg get), NetworkManager off for $WLAN_IF."
  exit 1
fi

echo "[7/7] Setting IP 10.0.0.2/24..."
sudo ip addr add 10.0.0.2/24 dev "$WLAN_IF" 2>/dev/null || true

echo "Verifying connectivity..."
if ! ping -c 3 -W 5 10.0.0.1 > /dev/null 2>&1; then
  echo "WARNING: ping failed. Check TurtleBot P2P setup."
  exit 1
fi

echo ""
echo "=== P2P connected. You can now run python3 server.py ==="
