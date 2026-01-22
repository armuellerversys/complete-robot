#!/bin/bash
# Raspberry Pi Access Point Diagnostic Script

echo "=== Raspberry Pi Access Point Diagnostics ==="

echo -e "\n[1/6] Checking rfkill (WiFi block status)..."
rfkill list all || echo "rfkill not installed"

echo -e "\n[2/6] Checking wlan0 interface..."
ip addr show wlan0 2>/dev/null || echo "wlan0 not found!"
iw dev wlan0 info 2>/dev/null || echo "iw tool not available or wlan0 down"

echo -e "\n[3/6] Checking hostapd status..."
systemctl is-enabled hostapd
systemctl is-active hostapd
systemctl --no-pager --full status hostapd | grep -A5 Active

echo -e "\n[4/6] Checking dnsmasq status..."
systemctl is-enabled dnsmasq
systemctl is-active dnsmasq
systemctl --no-pager --full status dnsmasq | grep -A5 Active

echo -e "\n[5/6] Checking NAT/iptables rules..."
sudo iptables -t nat -L -n -v | grep MASQUERADE || echo "No MASQUERADE rule found"

echo -e "\n[6/6] Scanning for AP SSID (may take a few seconds)..."
SSID_LINE=$(iw dev wlan0 scan 2>/dev/null | grep SSID | grep -v "SSID: " | head -n1)
if [ -z "$SSID_LINE" ]; then
    echo "⚠️ No SSID found in scan (hostapd may not be broadcasting)"
else
    echo "Found: $SSID_LINE"
fi

echo -e "\n=== Diagnostics Complete ==="


tail -f /var/log/ap-health.log

ip addr show wlan0

cat /var/lib/misc/dnsmasq.leases