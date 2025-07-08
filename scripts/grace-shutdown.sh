#!/bin/bash
    # grace-shutdown.sh
    # Attempts to gracefully shut down all defined GRS project VMs.

    VM_BASENAME="grs-project"
    NUM_VMS=3
    SHUTDOWN_TIMEOUT=60 # Seconds to wait for shutdown before giving up

    echo "--- Attempting Graceful Shutdown ---"

    for i in $(seq 1 ${NUM_VMS}); do
        VM_NAME="${VM_BASENAME}-${i}"
        echo "Requesting shutdown for ${VM_NAME}..."
        virsh shutdown "${VM_NAME}" >/dev/null 2>&1
        if [ $? -ne 0 ]; then
             echo "  ${VM_NAME} was likely not running or definition not found."
        fi
    done

    echo "Waiting up to ${SHUTDOWN_TIMEOUT} seconds for VMs to stop..."
    elapsed=0
    while [ $elapsed -lt $SHUTDOWN_TIMEOUT ]; do
        running_vms=$(virsh list --name --state-running | grep "^${VM_BASENAME}-" | wc -l)
        if [ $running_vms -eq 0 ]; then
            echo "All target VMs have stopped."
            break
        fi
        sleep 5
        elapsed=$((elapsed + 5))
        echo -n "."
    done
    echo

    if [ $elapsed -ge $SHUTDOWN_TIMEOUT ]; then
        echo "Timeout reached. Some VMs might still be running."
        echo "Force stop with 'virsh destroy <vm_name>' if necessary."
    fi

    echo "--- Shutdown Attempt Complete ---"
    echo "Current VM status:"
    virsh list --all
