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

echo "Starting memory reporting to ${HOST_IP}:${HOST_PORT} every ${REPORT_INTERVAL} second(s)..."

while true; do
    MEM_INFO=$(free | grep '^Mem:')
    MEM_USED_KB=$(echo "$MEM_INFO" | awk '{print $3}')
    MEM_TOTAL_KB=$(echo "$MEM_INFO" | awk '{print $2}')

    MESSAGE="${VM_HOSTNAME} ${MEM_USED_KB} ${MEM_TOTAL_KB}"

    printf "%s\n" "$MESSAGE" | nc -w 1 "$HOST_IP" "$HOST_PORT"

    sleep "$REPORT_INTERVAL"
done
