#!/bin/bash

# === ReSpeaker 2-Mic Pi HAT — Persistent Mixer Settings ===
# Output path: DAC → Line Mixer → Line Out
# sudo nano /usr/local/bin/respeaker-mixer.sh
# sudo chmod +x /usr/local/bin/respeaker-mixer.sh
# Enable DAC-to-LineOut mixers
amixer -c seeed2micvoicec sset 'Left Line Mixer DACL1' on
amixer -c seeed2micvoicec sset 'Right Line Mixer DACR1' on

# Enable LineOut switch
amixer -c seeed2micvoicec sset Line on

# Set playback volumes
amixer -c seeed2micvoicec sset 'PCM' 80%
amixer -c seeed2micvoicec sset 'Line DAC' 80%
amixer -c seeed2micvoicec sset Line 80%
