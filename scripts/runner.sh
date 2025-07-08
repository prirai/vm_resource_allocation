#!/bin/sh
# run_binary_repeatedly.sh
# Located inside the VM. Runs the specified binary over and over.

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
BINARY_NAME="memory_hog" # Or change to your desired binary name
BINARY_PATH="${SCRIPT_DIR}/${BINARY_NAME}"
RESTART_DELAY=1 # Seconds to wait before restarting

if [ ! -x "${BINARY_PATH}" ]; then
  echo "Error: Binary not found or not executable: ${BINARY_PATH}" >&2
  exit 1
fi

echo "Continuously running ${BINARY_NAME}. Press Ctrl+C in console or kill script PID to stop." >&2

while true; do
    echo "Starting ${BINARY_PATH}..." >&2
    "${BINARY_PATH}" # Execute the binary directly
    EXIT_CODE=$?
    echo "Binary exited with code ${EXIT_CODE}. Restarting in ${RESTART_DELAY}s..." >&2
    sleep ${RESTART_DELAY}
done
