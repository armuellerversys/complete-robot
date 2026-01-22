sudo wpa_cli -i wlan0 status
sudo iw dev wlan0 link
sudo iwgetid
iwgetid -r
ip -brief address show wlan0
ip -brief address show eth0

sudo systemctl unmask wpa_supplicant@wlan0.service
sudo systemctl enable wpa_supplicant@wlan0.service
sudo systemctl start wpa_supplicant@wlan0.service

sudo systemctl restart wpa_supplicant@wlan0.service
systemctl status wpa_supplicant@wlan0.service

sudo wpa_cli -i wlan0 -p /var/run/wpa_supplicant reconfigure

sudo ip link set wlan0 down
sudo ip link set wlan0 up

sudo systemctl restart wpa_supplicant@wlan0.service
sudo systemctl restart systemd-networkd

nmcli connection show
nmcli dev wifi list
nmcli dev wifi connect "PiAccessPoint" password "Robot2025"
nmcli dev wifi connect "MueFritz2022" password "psw!"
nmcli connection delete "MueFritz2022"
nmcli connection modify "PiAccessPoint" connection.priority 10
nmcli connection modify "MueFritz2022" connection.priority 1
nmcli connection up "PiAccessPoint"
nmcli connection down "MueFritz2022"
nmcli device status
nmcli -p connection show --active
ip -brief addr show wlan0

sudo iwlist wlan0 scan | grep ESSID

#
nmcli connection add type wifi ifname wlan0 con-name PiAccessPoint ssid PiAccessPoint
nmcli connection modify PiAccessPoint wifi-sec.key-mgmt wpa-psk
nmcli connection modify PiAccessPoint wifi-sec.psk "Robot2025"
nmcli connection up PiAccessPoint

sudo journalctl -u NetworkManager -f

nslookup raspberrypi-3 192.168.4.1