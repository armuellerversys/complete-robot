#!/bin/bash
# ap-self-heal.sh
# Self-healing script for Raspberry Pi WiFi Access Point with reboot fallback

LOGFILE="/var/log/ap-self-heal.log"
WLAN_IF="wlan0"
STATIC_IP="192.168.4.1/24"
STATEFILE="/tmp/ap-fail-count"
MAX_FAILS=5   # after 5 minutes of failure -> reboot

echo "=== $(date) Starting AP self-heal check ===" >> "$LOGFILE"

# Initialize fail counter if not exists
if [ ! -f "$STATEFILE" ]; then
  echo 0 > "$STATEFILE"
fi
FAILS=$(cat "$STATEFILE")

HEALTHY=1

# 1. Ensure WiFi is not blocked
if rfkill list wifi | grep -q "yes"; then
  echo "$(date) WiFi was blocked, unblocking..." >> "$LOGFILE"
  rfkill unblock wifi
  HEALTHY=0
fi

# 2. Ensure wlan0 has the static IP
if ! ip addr show "$WLAN_IF" | grep -q "$STATIC_IP"; then
  echo "$(date) $WLAN_IF missing IP, reassigning $STATIC_IP" >> "$LOGFILE"
  ip addr flush dev "$WLAN_IF"
  ip addr add "$STATIC_IP" dev "$WLAN_IF"
  ip link set "$WLAN_IF" up
  HEALTHY=0
fi

# 3. Ensure hostapd is active
if ! systemctl is-active --quiet hostapd; then
  echo "$(date) hostapd not running, restarting..." >> "$LOGFILE"
  systemctl restart hostapd
  HEALTHY=0
fi

# 4. Ensure dnsmasq is active
if ! systemctl is-active --quiet dnsmasq; then
  echo "$(date) dnsmasq not running, restarting..." >> "$LOGFILE"
  systemctl restart dnsmasq
  HEALTHY=0
fi

# 5. Check if clients have DHCP leases
LEASE_COUNT=$(grep -c "" /var/lib/misc/dnsmasq.leases 2>/dev/null || echo 0)
echo "$(date) Current DHCP leases: $LEASE_COUNT" >> "$LOGFILE"

if [ "$LEASE_COUNT" -eq 0 ]; then
  echo "$(date) ⚠️ No clients connected, may indicate DHCP issue." >> "$LOGFILE"
  HEALTHY=0
fi

# Update failure counter
if [ "$HEALTHY" -eq 1 ]; then
  echo 0 > "$STATEFILE"
  echo "$(date) ✅ AP healthy, reset fail counter" >> "$LOGFILE"
else
  FAILS=$((FAILS+1))
  echo "$FAILS" > "$STATEFILE"
  echo "$(date) ❌ AP unhealthy, consecutive fails: $FAILS" >> "$LOGFILE"
fi

# Emergency reboot if exceeded limit
if [ "$FAILS" -ge "$MAX_FAILS" ]; then
  echo "$(date) 🔄 AP failed $FAILS times in a row, rebooting system!" >> "$LOGFILE"
  rm -f "$STATEFILE"
  /sbin/reboot
fi

echo "=== $(date) AP self-heal check complete ===" >> "$LOGFILE"
