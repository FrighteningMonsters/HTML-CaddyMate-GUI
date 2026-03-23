#!/bin/bash
# Collect WiFi / P2P state for debugging. No changes to the system.
# Usage:
#   Pi:         bash p2p_diag.sh
#   TurtleBot:  bash p2p_diag.sh turtlebot

# Do not use set -e — we want full output even if a command fails.
ROLE="${1:-pi}"
WLAN_IF="${WLAN_IF:-wlan0}"

hr() { echo "=== $1 ==="; }

if [ "$ROLE" = "turtlebot" ] || [ "$ROLE" = "tb" ]; then
  hr "date"
  date
  hr "ip link (p2p / wlan)"
  ip link show 2>/dev/null | grep -E 'wlan|p2p' || true
  hr "iw reg"
  sudo iw reg get 2>/dev/null || true
  if [ -e /sys/class/net/p2p-dev-wlan0 ]; then
    hr "wpa_cli -i p2p-dev-wlan0 status"
    sudo wpa_cli -i p2p-dev-wlan0 status 2>/dev/null || true
  fi
  for iface in $(ip link show 2>/dev/null | grep -oE 'p2p-wlan0-[0-9]+' | sort -u); do
    hr "iface $iface: ip addr"
    ip addr show dev "$iface" 2>/dev/null || true
    hr "iface $iface: iw dev link"
    sudo iw dev "$iface" link 2>/dev/null || true
  done
  exit 0
fi

hr "date"
date
hr "iw reg"
sudo iw reg get 2>/dev/null || true
if command -v nmcli >/dev/null 2>&1; then
  hr "nmcli device status"
  nmcli device status 2>/dev/null || true
  hr "nmcli device show $WLAN_IF (if any)"
  nmcli device show "$WLAN_IF" 2>/dev/null || true
fi
hr "wpa_cli -i $WLAN_IF status"
sudo wpa_cli -i "$WLAN_IF" status 2>/dev/null || true
hr "wpa_cli -i $WLAN_IF scan_results (DIRECT only)"
sudo wpa_cli -i "$WLAN_IF" scan_results 2>/dev/null | grep -i DIRECT || echo "(no DIRECT in scan_results)"
hr "ip addr $WLAN_IF"
ip addr show dev "$WLAN_IF" 2>/dev/null || true
hr "dmesg tail (wlan / brcm / cfg80211)"
sudo dmesg 2>/dev/null | tail -n 80 | grep -iE 'wlan|brcm|cfg80211|80211|wifi' || echo "(no recent matches)"
