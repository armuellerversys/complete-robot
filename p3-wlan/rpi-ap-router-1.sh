#!/bin/bash
# Raspberry Pi Access Point (Router Mode) Setup Script
# Tested on Raspberry Pi OS Lite (32-bit) on Pi 3

set -e

SSID="PiAccessPoint"
PASSPHRASE="StrongPasswordHere"
WLAN_IFACE="wlan0"
ETH_IFACE="eth0"
WLAN_IP="192.168.4.1"

echo "[1/6] Updating system..."
sudo apt update && sudo apt -y full-upgrade

echo "[2/6] Installing required packages..."
sudo apt install dhcpcd5
sudo apt install -y hostapd dnsmasq netfilter-persistent iptables-persistent
sudo systemctl enable dhcpcd
sudo systemctl start dhcpcd

echo "[3/6] Configuring static IP for $WLAN_IFACE..."
cat <<EOF | sudo tee -a /etc/dhcpcd.conf

interface $WLAN_IFACE
    static ip_address=$WLAN_IP/24
    nohook wpa_supplicant
EOF
sudo systemctl restart dhcpcd

echo "[4/6] Configuring dnsmasq (DHCP server)..."
sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
cat <<EOF | sudo tee /etc/dnsmasq.conf
interface=$WLAN_IFACE
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
EOF

echo "[5/6] Configuring hostapd (Access Point)..."
cat <<EOF | sudo tee /etc/hostapd/hostapd.conf
interface=$WLAN_IFACE
driver=nl80211
ssid=$SSID
hw_mode=g
channel=6
ieee80211n=1
wmm_enabled=1
ht_capab=[HT40][SHORT-GI-20][DSSS_CCK-40]
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$PASSPHRASE
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

sudo sed -i "s|#DAEMON_CONF=.*|DAEMON_CONF=\"/etc/hostapd/hostapd.conf\"|" /etc/default/hostapd

echo "[6/6] Setting up NAT and enabling services..."
sudo iptables -t nat -A POSTROUTING -o $ETH_IFACE -j MASQUERADE
sudo sh -c "iptables-save > /etc/iptables/rules.v4"

sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq
sudo systemctl enable netfilter-persistent

echo "Setup complete! Rebooting..."
sudo reboot
