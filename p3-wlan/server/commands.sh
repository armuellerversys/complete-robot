sudo wpa_cli -i wlan0 status
sudo iwgetid

sudo systemctl stop wpa_supplicant@wlan0.service
sudo systemctl disable wpa_supplicant@wlan0.service
sudo systemctl mask wpa_supplicant@wlan0.service

cat /var/lib/misc/dnsmasq.leases

ip addr show wlan0

sudo systemctl restart dhcpcd
sudo systemctl restart dnsmasq
sudo systemctl restart hostapd

sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo netfilter-persistent save

journalctl -u hostapd


sudo sh -c "echo 1 > /proc/sys/net/ipv4/ip_forward"
/etc/sysctl.conf --> net.ipv4.ip_forward = 1

sudo nano /etc/resolv.conf   --> nameserver 8.8.8.8