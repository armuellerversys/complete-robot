#sudo nano /etc/systemd/system/menu_server.service
sudo nano /etc/systemd/system/menu_server.service

# cp start menu_server.service /etc/systemd/system

# Reload systemd to read the new service
sudo systemctl daemon-reload

# Enable it to start on boot
sudo systemctl enable menu_server.service
sudo systemctl restart menu_server.service
sudo systemctl disable menu_server.service

# Start it immediately
sudo systemctl start menu_server.service

sudo systemctl stop menu_server.service

systemctl status menu_server.service


journalctl -u menu_server.service -f

sudo systemd-analyze verify /etc/systemd/system/menu_server.service