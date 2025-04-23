// grs_project/report.typ
#import "template.typ": *

#show: project.with(
  title: "Performance Analysis and Online Resource Management of a VM System",
  authors: (
    "Priyanshu Kumar Rai",
    "Aman Yadav",
    "Ritesh Gupta",
    "Vanshika Jain"
  ),
  subtitle: "GRS Project - Part A",
)

= Abstract

This project investigates the deployment, performance analysis, and online resource management of virtual machines (VMs) using QEMU @qemu/KVM @kvm and libvirt @libvirt on a Linux host. Multiple Linux VMs are configured as distinct nodes, with the host system acting as a centralized controller for monitoring and analyzing resource utilization (CPU, memory, networking, and disk I/O). Each VM is assigned varying CPU and memory configurations to assess performance under different workloads. Different benchmark applications are executed within each VM. The host system gathers metrics using various `virsh` subcommands from outside the VMs and `perf` inside the VMs. The aim is to understand resource utilization and make decisions about allocation and deallocation to optimize performance.

= Problem Statement

This project studies how virtual machines (VMs) use resources. We analyze three Alpine Linux VMs on a Linux host. The host also monitors and manages the VMs.  Key goals include: setting up the VMs, monitoring them, running performance tests using benchmarking tools, and managing resources on-the-fly. We want to see how changing resources affects VM performance and find ways to improve it.

= Project Goals

- The primary goal is to enable centralized monitoring, and online resource management of VMs on a Linux host using QEMU/KVM and libvirt.
- Measure CPU, memory, network, and disk I/O metrics
- Execute benchmark tests including the ECP Proxy Apps Suite @ecp-proxy-apps which includes HPCCG @hpccg, XSBench, RSBench @rsbench, SimpleMOC @simplemoc and CoHMM @cohmm among others.
- Implement online resource management:
    - Memory ballooning, to dynamically adjust RAM
    - CPU core allocation using `virsh setvcpus` @ibm-vcpus. CPUs allocated can be increased on the fly while for decreasing, a reboot is required.
    - For storage, strategies like storage pooling and sharing can be used to optimize disk usage.

= Expected Outcomes/Deliverables

Through this project we plan to create methods for automatic deployment and running of VMs through bring your own ISO and XML approach. Allpications are deployed on those domains and automated monitoring is done while running different benchmark applications pairs within the VMs. A comparative analysis of the performance impact of different application pairings under varying resource constraints; and optimized resource allocation strategies derived from the analysis to maximize overall system performance.

= Work Done Until Now

The following steps have been completed:

1.  *Host System Preparation:* The host system (running a suitable Linux distribution) was prepared by installing and configuring the necessary virtualization components: QEMU, KVM, and libvirt.

2.  *Base Image Creation:* An Alpine Linux base image (`alpine-base.qcow2`) has been created using the `alpine-virt` ISO.  This base image is cloned to create VM nodes. The following command used and installation done:
    ```bash
    qemu-system-x86_64 -m 512M -smp 2 -boot d -cdrom alpine-virt-3.21.3-x86_64.iso -drive file=alpine-base.qcow2,format=qcow2 -net nic -net user,hostfwd=tcp::2222-:22 -nographic
    ```
    Remove `-cdrom` to run the actual VM after installation.
3.  *VM Image Cloning:* Three qcow2 disk images (`alpine-1.qcow2`, `alpine-2.qcow2`, `alpine-3.qcow2`) were created as copies of the base image:
    ```bash
    qemu-img create -f qcow2 -F qcow2 -b alpine-base.qcow2 alpine-1.qcow2
    qemu-img create -f qcow2 -F qcow2 -b alpine-base.qcow2 alpine-2.qcow2
    qemu-img create -f qcow2 -F qcow2 -b alpine-base.qcow2 alpine-3.qcow2
    ```
4.  *VM XML Generation:* In order to run VMs via KVM/libvirt we need XML configurations which define domains (special name for a virtual machine). A shell script generates libvirt XML configuration files (`alpine-vm-1.xml`, `alpine-vm-2.xml`, `alpine-vm-3.xml`) for each VM. This script ensures unique UUIDs and MAC addresses, correctly references the qcow2 images, and automates modification of a base XML template (`alpine.xml`).
5.  *VM Definition:* The VMs have been defined using `virsh define` with their respective XML files. Once a domain is defined, we start it using `virsh start`. Deletion of a domain is done using `virsh undefine`.
6.  *VM Statistics Script:* A `vm-stats.sh` script gathers and displays CPU and memory usage for each VM, using `virsh domstats` and `virsh dominfo`. Statistics are collected at regular intervals. Using the script we can obtain metrics and perform allocation decisions based on the collected data.

#bibliography("ref.yml")
