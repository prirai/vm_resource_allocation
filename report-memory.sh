#!/bin/sh
# report_memory.sh

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
    # Memory metrics
    MEM_INFO=$(free | grep '^Mem:')
    MEM_USED_KB=$(echo "$MEM_INFO" | awk '{print $3}')
    MEM_TOTAL_KB=$(echo "$MEM_INFO" | awk '{print $2}')

    # CPU usage metrics
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4}') # User + System CPU usage

    # Disk I/O metrics
    DISK_IO=$(iostat -d | grep -m 1 '^vda' | awk '{print $3}') # Replace 'sda' with your disk name if different

    # Network metrics (bytes received and transmitted)
    NET_RX=$(cat /sys/class/net/eth0/statistics/rx_bytes) # Replace 'eth0' with your network interface
    NET_TX=$(cat /sys/class/net/eth0/statistics/tx_bytes)

    # Construct the message
    MESSAGE="${VM_HOSTNAME} ${MEM_USED_KB} ${MEM_TOTAL_KB} ${CPU_USAGE} ${DISK_IO} ${NET_RX} ${NET_TX}"

    # Send the message
    printf "%s\n" "$MESSAGE" | nc -w 1 "$HOST_IP" "$HOST_PORT"

    sleep "$REPORT_INTERVAL"
done
