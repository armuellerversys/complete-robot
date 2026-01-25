#!/bin/bash

# Configuration
CONTAINER_NAME="ovos_skill_vehicle_control"

echo "--- 🛠️ Building Vehicle Control Skill ---"
docker compose build ovos_skill_vehicle_control

echo "--- 🚀 Restarting Skill Container ---"
# This only stops and starts the specific skill container
docker compose up -d ovos_skill_vehicle_control

echo "--- 📋 Checking Logs (Ctrl+C to exit) ---"
docker logs -f $CONTAINER_NAME