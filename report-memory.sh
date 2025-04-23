#!/bin/sh

HOST_IP="10.0.2.2"
HOST_PORT=4444
REPORT_INTERVAL=1

VM_HOSTNAME=$(hostname -s)

if ! command -v nc > /dev/null 2>&1; then
    echo "Error: 'nc' (netcat) command not found. Please install it (e.g., apk add netcat-openbsd or apk add busybox-extras)." >&2
    exit 1
fi

echo "Starting system metrics reporting to ${HOST_IP}:${HOST_PORT} every ${REPORT_INTERVAL} second(s)..."

while true; do
    MEM_INFO=$(free | grep '^Mem:')
    MEM_USED_KB=$(echo "$MEM_INFO" | awk '{print $3}')
    MEM_TOTAL_KB=$(echo "$MEM_INFO" | awk '{print $2}')

    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4}')

    DISK_IO=$(iostat -d | grep -m 1 '^vda' | awk '{print $3}')

    NET_RX=$(cat /sys/class/net/eth0/statistics/rx_bytes)
    NET_TX=$(cat /sys/class/net/eth0/statistics/tx_bytes)

    MESSAGE="${VM_HOSTNAME} ${MEM_USED_KB} ${MEM_TOTAL_KB} ${CPU_USAGE} ${DISK_IO} ${NET_RX} ${NET_TX}"

    printf "%s\n" "$MESSAGE" | nc -w 1 "$HOST_IP" "$HOST_PORT"

    sleep "$REPORT_INTERVAL"
done
{{REWRITTEN_CODE}}
