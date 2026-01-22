#!/bin/bash
set -e

echo ">>> Activating OVOS venv"
source /home/ovos/.venv/bin/activate



VOICE_DIR="/home/ovos/.local/share/piper/voices"
mkdir -p $VOICE_DIR

download_voice () {
    LANG=$1
    NAME=$2
    QUALITY=$3
    echo ">>> Downloading $LANG-$NAME-$QUALITY"
    DEST="$VOICE_DIR/$LANG"
    mkdir -p $DEST
    BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/$LANG/$LANG-$NAME/$QUALITY"
    curl -L -o "$DEST/${LANG}-${NAME}-${QUALITY}.onnx" "$BASE_URL/${LANG}-${NAME}-${QUALITY}.onnx"
    curl -L -o "$DEST/${LANG}-${NAME}-${QUALITY}.onnx.json" "$BASE_URL/${LANG}-${NAME}-${QUALITY}.onnx.json"
}

# 

# US English voices
# https://huggingface.co/speaches-ai/piper-en_US-lessac-high/blob/main/speaches-ai/piper-en_US-lessac-high.onnx
# https://huggingface.co/speaches-ai/piper-en_US-lessac-high/resolve/main/model.onnx?download=true
# https://huggingface.co/speaches-ai/piper-en_US-lessac-high/blob/main/speaches-ai/piper-en_US-lessac-high.json
# https://huggingface.co/speaches-ai/piper-en_US-lessac-high/resolve/main/config.json?download=true
download_voice en en_US-amy low
download_voice en en_US-lessac high

# UK English voices
download_voice en en_GB-alan low
download_voice en en_GB-sue low

# German voice
download_voice de de_DE-thorsten low

echo ">>> Updating OVOS config"
CONF_FILE="/home/ovos/.config/mycroft/mycroft.conf"
if [ ! -f "$CONF_FILE" ]; then
  echo "{}" > "$CONF_FILE"
fi

jq '.tts = {
  "module": "ovos-tts-plugin-piper",
  "ovos-tts-plugin-piper": {
    "voice": "en_US-amy-low",
    "model_dir": "/home/ovos/.local/share/piper/voices"
  }
}' "$CONF_FILE" > "$CONF_FILE.tmp" && mv "$CONF_FILE.tmp" "$CONF_FILE"

echo ">>> Restarting OVOS audio service"
docker restart ovos_audio

echo ">>> Installation complete!"
echo "Default voice: en_US-amy-low"
echo "Other installed voices:"
echo "  - en_US-lessac-high"
echo "  - en_GB-alan-low"
echo "  - en_GB-sue-low"
echo "  - de_DE-thorsten-low"
echo
echo "To switch voices, edit /home/ovos/.config/mycroft/mycroft.conf and change:"
echo '    "voice": "en_US-amy-low"'
echo "to another installed voice."
