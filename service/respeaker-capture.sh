#!/bin/bash

# === ReSpeaker 2-Mic Pi HAT — Persistent Microphone Settings ===
# Configures TLV320AIC32 capture path (PGA → ADC → ALSA)
# sudo nano /usr/local/bin/respeaker-capture.sh
# sudo chmod +x /usr/local/bin/respeaker-capture.sh
# sudo nano /etc/systemd/system/respeaker-capture.service
##########################
#   INPUT ROUTING
##########################

# Enable input from Line1L (Mic 1)
amixer -c seeed2micvoicec sset 'Left PGA Mixer Line1L' on

# Enable input from Line1R (Mic 2)
amixer -c seeed2micvoicec sset 'Right PGA Mixer Line1R' on

##########################
#   CAPTURE GAIN
##########################

# Set microphone gain (adjust to your taste)
# 103 ≈ +51.5 dB (your current working level)
amixer -c seeed2micvoicec sset 'PGA' 103

##########################
#   ADC CLEANUP SETTINGS
##########################

# Disable high-pass filter (HPF)
amixer -c seeed2micvoicec sset 'ADC HPF Cut-off' Disabled

# Disable AGC (auto gain control)
amixer -c seeed2micvoicec sset AGC off

