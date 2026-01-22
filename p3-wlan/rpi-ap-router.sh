#!/bin/bash
# Raspberry Pi Access Point (Router Mode) Setup Script
# Auto-detects dhcpcd or NetworkManager
# Includes rfkill safeguard + hostapd startup fix
# Works on Raspberry Pi OS Bullseye/Bookworm and older versions

set -e

SSID="PiAccessPoint"
PASSPHRASE="StrongPasswordHere"
WLAN_IFACE="wlan0"
ETH_IFACE="eth0"
WLAN_IP="192.168.4.1"

echo "=== Raspberry Pi Access Point Setup ==="

echo "[1/8] Updating system..."
sudo apt update && sudo apt -y full-upgrade

echo "[2/8] Installing required packages..."
sudo apt install -y hostapd dnsmasq netfilter-persistent iptables-persistent rfkill

# Ensure WiFi is not blocked by rfkill
echo "[3/8] Checking WiFi block status..."
if rfkill list wifi | grep -q "Soft blocked: yes"; then
    echo "[INFO] WiFi is soft-blocked. Unblocking..."
    sudo rfkill unblock wifi
fi

# Detect if dhcpcd is available
if systemctl list-unit-files | grep -q dhcpcd.service; then
    USE_DHCPCD=true
else
    USE_DHCPCD=false
fi

if $USE_DHCPCD; then
    echo "[4/8] Configuring static IP for $WLAN_IFACE via dhcpcd..."
    if ! grep -q "interface $WLAN_IFACE" /etc/dhcpcd.conf; then
        cat <<EOF | sudo tee -a /etc/dhcpcd.conf

interface $WLAN_IFACE
    static ip_address=$WLAN_IP/24
    nohook wpa_supplicant
EOF
    fi
    sudo systemctl restart dhcpcd
else
    echo "[4/8] Configuring static IP for $WLAN_IFACE via NetworkManager..."
    sudo apt install -y network-manager
    nmcli dev set $WLAN_IFACE managed yes || true
    nmcli con delete "AP" 2>/dev/null || true
    nmcli con add type wifi ifname $WLAN_IFACE con-name AP autoconnect yes ssid $SSID
    nmcli con modify AP 802-11-wireless.mode ap 802-11-wireless.band bg
    nmcli con modify AP ipv4.addresses $WLAN_IP/24 ipv4.method shared
    nmcli con modify AP wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PASSPHRASE"
fi

echo "[5/8] Configuring dnsmasq (DHCP server)..."
sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig 2>/dev/null || true
cat <<EOF | sudo tee /etc/dnsmasq.conf
interface=$WLAN_IFACE
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
EOF

echo "[6/8] Configuring hostapd (Access Point)..."
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

echo "[7/8] Setting up NAT and enabling services..."
sudo iptables -t nat -A POSTROUTING -o $ETH_IFACE -j MASQUERADE
sudo sh -c "iptables-save > /etc/iptables/rules.v4"

sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq
sudo systemctl enable netfilter-persistent

# Create a systemd service to unblock WiFi at every boot
cat <<EOF | sudo tee /etc/systemd/system/unblock-wifi.service
[Unit]
Description=Unblock WiFi at boot
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/sbin/rfkill unblock all

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable unblock-wifi.service

# Add systemd override for hostapd to wait for WiFi and delay startup
echo "[8/8] Adding hostapd startup fix..."
sudo mkdir -p /etc/systemd/system/hostapd.service.d
cat <<EOF | sudo tee /etc/systemd/system/hostapd.service.d/override.conf
[Unit]
After=network.target unblock-wifi.service
Wants=unblock-wifi.service

[Service]
ExecStartPre=/bin/sleep 5
EOF

sudo systemctl daemon-reexec
sudo systemctl daemon-reload

echo "✅ Setup complete! Rebooting..."
sudo reboot
