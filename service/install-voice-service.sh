#sudo nano /etc/systemd/system/voice_server.service
sudo nano /etc/systemd/system/voice_server.service

# cp start voice_server.service /etc/systemd/system

# Reload systemd to read the new service
sudo systemctl daemon-reload

# Enable it to start on boot
sudo systemctl enable voice_server.service
sudo systemctl restart voice_server.service
sudo systemctl disable voice_server.service

# Start it immediately
sudo systemctl start voice_server.service

sudo systemctl stop voice_server.service

systemctl status voice_server.service


journalctl -u voice_server.service -f