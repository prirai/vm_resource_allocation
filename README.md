# Performance Analysis and Online Resource Management of a VM System

This project focuses on the deployment, performance analysis, and online resource management of virtual machines (VMs) using QEMU/KVM and libvirt on a Linux host. It provides a system for centralized monitoring, dynamic resource allocation, and performance benchmarking of multiple Alpine Linux VMs.

## Project Structure

The repository is organized into several key directories and files that work together to create, manage, and monitor the virtualized environment.

```
.
├── img/
│   ├── ... (Images for reports and presentations)
├── metrics_data/
│   ├── ... (CSV files for storing VM metrics)
├── scripts/
│   ├── gen-xml.sh
│   ├── report-memory.sh
│   └── runner.sh
├── xmls/
│   ├── alpine-vm-1.xml
│   ├── alpine-vm-2.xml
│   └── alpine-vm-3.xml
├── .gitignore
├── commands.txt
├── main.py
├── memory_hog.c
├── plot_adv.py
├── presentation.pdf
├── presentation.typ
├── pyproject.toml
├── report-final.pdf
├── report-final.typ
└── template.typ
```

### Key Components

| File / Directory | Purpose |
| :--- | :--- |
| `plot_adv.py` | The core component: a Python-based listener, visualizer, and resource manager. It receives metrics from VMs, saves them, displays them on a real-time web dashboard using Dash, and dynamically adjusts VM resources (CPU/RAM) based on predefined thresholds. |
| `main.py` | Main script to orchestrate the VM management and monitoring process. |
| `scripts/` | Contains all the necessary shell scripts for automation. |
| ├── `gen-xml.sh` | Generates unique XML configuration files for each VM from a base template. |
| ├── `report-memory.sh` | Runs inside each VM to collect real-time metrics (CPU, memory, disk I/O, network) and send them to the host listener (`plot_adv.py`) via `netcat`. |
| ├── `runner.sh` | A utility script to automate the execution of workloads (like `memory_hog`) inside the VMs. |
| `memory_hog.c` | A simple C program designed to simulate a memory-intensive workload within the VMs to test dynamic resource allocation. |
| `xmls/` | Stores the libvirt XML configuration files for each VM, defining their hardware properties like CPU, memory, and disk images. |
| `metrics_data/` | The storage directory for historical metrics data, saved in CSV format by the `plot_adv.py` listener. |
| `img/` | Contains images, screenshots, and graphs used in the presentation and final report. |
| `*.typ`, `*.pdf` | The source (`.typ`) and compiled (`.pdf`) files for the project's final report and presentation, created using the Typst typesetting system. |
| `pyproject.toml` | Defines the Python project dependencies required for running the monitoring and visualization dashboard (`Dash`, `pandas`, `libvirt-python`, etc.). |
| `commands.txt` | A reference file containing useful `virsh` and `qemu-img` commands for manual VM management and interaction. |

## System Workflow

1.  **VM Creation**: The `scripts/gen-xml.sh` script generates configuration files for multiple VMs, which are stored in the `xmls/` directory. These VMs are then defined and started using `virsh` commands.
2.  **Metrics Collection**: The `scripts/report-memory.sh` script is executed within each running VM. It continuously gathers performance data and streams it over the network to the host machine.
3.  **Monitoring and Visualization**: On the host, the `plot_adv.py` script listens for incoming data from the VMs. It processes these metrics, stores them in `metrics_data/`, and presents them in a real-time web dashboard.
4.  **Dynamic Resource Management**: Based on the collected metrics, `plot_adv.py` automatically adjusts VM resources. If memory or CPU usage crosses a defined threshold, it uses the `libvirt` API to allocate or deallocate RAM and virtual CPU cores to the VM live, without requiring a reboot.
5.  **Workload Simulation**: The `memory_hog.c` program can be run inside the VMs using `scripts/runner.sh` to simulate high-resource usage and test the system's responsiveness.
