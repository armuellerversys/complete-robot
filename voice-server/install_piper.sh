#!/bin/bash
set -e

echo ">>> Activating OVOS venv"
source /home/ovos/.venv/bin/activate

echo ">>> Installing OVOS Piper TTS plugin"
pip install --upgrade pip setuptools wheel
pip install ovos-tts-plugin-piper

echo ">>> Downloading Piper binary (arm64)"
mkdir -p /home/ovos/.local/bin
cd /home/ovos/.local/bin
curl -L -o piper.tar.gz https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_arm64.tar.gz
tar -xzf piper.tar.gz
rm piper.tar.gz
chmod +x piper
echo ">>> Piper binary installed to /home/ovos/.local/bin/piper"

echo ">>> Adding Piper to PATH"
export PATH=$PATH:/home/ovos/.local/bin
echo 'export PATH=$PATH:/home/ovos/.local/bin' >> /home/ovos/.bashrc

echo ">>> Downloading Piper voice model (en_US-amy-low)"
mkdir -p /home/ovos/.local/share/piper/voices/en_US
cd /home/ovos/.local/share/piper/voices/en_US
curl -L -O https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/low/en_US-amy-low.onnx
curl -L -O https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/low/en_US-amy-low.onnx.json

echo ">>> Updating OVOS config"
CONF_FILE="/home/ovos/.config/mycroft/mycroft.conf"
if [ ! -f "$CONF_FILE" ]; then
  echo "{}" > "$CONF_FILE"



jq '.tts = {
  "module": "ovos-tts-plugin-piper",
  "ovos-tts-plugin-piper": {
    "voice": "en_US-amy-low",
    "model_dir": "/home/ovos/.local/share/piper/voices/en_US"
  }
}' "$CONF_FILE" > "$CONF_FILE.tmp" && mv "$CONF_FILE.tmp" "$CONF_FILE"

echo ">>> Restarting OVOS audio service"
docker restart ovos_audio

echo ">>> Installation complete! Check logs with: docker logs -f ovos_audio"