#!/bin/bash
# Reset Raspberry Pi from Access Point (Router Mode) back to normal WiFi client
# Tested on Raspberry Pi OS Lite (32-bit) on Pi 3

set -e

WLAN_IFACE="wlan0"

echo "[1/5] Stopping services..."
sudo systemctl stop hostapd || true
sudo systemctl stop dnsmasq || true

echo "[2/5] Disabling services..."
sudo systemctl disable hostapd || true
sudo systemctl disable dnsmasq || true
sudo systemctl disable netfilter-persistent || true

echo "[3/5] Restoring config files..."
# Restore original dnsmasq config if backup exists
if [ -f /etc/dnsmasq.conf.orig ]; then
    sudo mv /etc/dnsmasq.conf.orig /etc/dnsmasq.conf
fi

# Remove hostapd config
if [ -f /etc/hostapd/hostapd.conf ]; then
    sudo rm /etc/hostapd/hostapd.conf
fi

# Reset dhcpcd wlan0 static IP section
sudo sed -i "/^interface $WLAN_IFACE/,/^nohook wpa_supplicant/d" /etc/dhcpcd.conf

echo "[4/5] Flushing iptables rules..."
sudo iptables -F
sudo iptables -t nat -F
sudo sh -c "iptables-save > /etc/iptables/rules.v4"

echo "[5/5] Enabling wpa_supplicant for normal WiFi use..."
sudo systemctl enable wpa_supplicant
sudo systemctl start wpa_supplicant

echo "✅ Cleanup complete! Rebooting..."
sudo reboot
