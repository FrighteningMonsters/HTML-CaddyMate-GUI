#!/bin/bash
# TurtleBot P2P WiFi Direct Setup
# Run: bash ~/turtlebot_p2p_setup.sh
# Must run Pi p2p_connect.sh within 60 seconds after this completes

set -e

echo "[1/5] Removing existing P2P groups..."
# Each run should tear down old GO interfaces; otherwise p2p-wlan0-0 becomes -1, -2, ...
# Repeat until none left (drivers sometimes need a second pass + short delay).
for _round in 1 2 3; do
  IFACES=$(ip link show 2>/dev/null | grep -oE 'p2p-wlan0-[0-9]+' 2>/dev/null | sort -u || true)
  [ -z "$IFACES" ] && break
  for iface in $IFACES; do
    sudo wpa_cli -i p2p-dev-wlan0 p2p_group_remove "$iface" 2>/dev/null || true
  done
  sudo wpa_cli -i p2p-dev-wlan0 p2p_flush 2>/dev/null || true
  sleep 1
done
if ip link show 2>/dev/null | grep -qE 'p2p-wlan0-[0-9]+'; then
  echo "    WARNING: Some p2p-wlan0-* still present. If problems persist: reboot or restart wpa_supplicant."
fi

echo "[2/5] Creating P2P group..."
sudo wpa_cli -i p2p-dev-wlan0 p2p_group_add || true
sleep 3

echo "[3/5] Detecting P2P interface..."
P2P_IFACE=$(ip link show | grep -oE 'p2p-wlan0-[0-9]+' | head -1)
if [ -z "$P2P_IFACE" ]; then
  echo "ERROR: No p2p-wlan0-X interface found"
  exit 1
fi
echo "    Found: $P2P_IFACE"

echo "[4/5] Setting IP 10.0.0.1/24 on $P2P_IFACE..."
sudo ip addr flush dev "$P2P_IFACE" 2>/dev/null || true
sudo ip addr add 10.0.0.1/24 dev "$P2P_IFACE" 2>/dev/null || true
echo "    Waiting for GO beacon to stabilize..."
sleep 3

echo "[5/5] Activating WPS PBC..."
if ! sudo wpa_cli -i "$P2P_IFACE" wps_pbc | grep -q OK; then
  echo "ERROR: wps_pbc failed"
  exit 1
fi

echo ""
echo "=== P2P ready. Run Pi p2p_connect.sh within 60 seconds ==="
