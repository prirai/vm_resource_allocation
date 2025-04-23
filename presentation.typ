#import "@preview/slydst:0.1.4": *
#import "@preview/fletcher:0.5.7" as fletcher: diagram, node, edge

#import fletcher.shapes: diamond, house, hexagon
#set text(font: "Libertinus Serif", lang: "en", size: 15pt)

#show: slides.with(
  title: "Performance Analysis and Online Resource Management of a VM System",
  subtitle: "GRS Project - Team 23",
  authors: (
    "Priyanshu Kumar Rai",
    "Aman Yadav",
    "Ritesh Gupta",
    "Vanshika Jain"
  ),
  layout: "medium",
  ratio: 16/9,
  title-color: blue.darken(30%),
)

== Abstract

#v(3em)
- Investigates deployment, performance analysis, and resource management of VMs.
- Uses QEMU/KVM and libvirt on a Linux host.
- Benchmarks include miniFE, miniQMC, HPCG, and others.
- Focus on dynamic resource allocation for optimization.

== Problem Statement

#v(3em)
The project focuses on centralized monitoring, performance analysis, and dynamic resource management in virtualized environments. By studying three Alpine Linux VMs on a Linux host, the system aims to:
- Monitor real-time metrics for CPU, memory, network, and disk I/O.
- Execute performance benchmarks to analyze resource utilization under varying workloads.
- Dynamically adjust CPU and memory allocation to optimize performance and resource efficiency.

== Project Goals

#v(1.5em)
#text(weight: "bold", size: 18pt)[Monitoring]
- Centralized monitoring of CPU, memory, network, and disk I/O.
- Real-time metrics collection and visualization.

#text(weight: "bold", size: 18pt)[Benchmarking]
- Execute benchmarks like HPCCG, XSBench, miniFE, and HPCG.
- Analyze performance under resource constraints.

#text(weight: "bold", size: 18pt)[Resource Management]
- Dynamic memory ballooning and CPU core allocation.
- Optimize storage using pooling and sharing strategies.

#let blob(pos, label, tint: white, width: 28mm, ..args) = node(
	pos, align(center, label),
	width: width,
	fill: tint.lighten(60%),
	stroke: 1pt + tint.darken(20%),
	corner-radius: 5pt,
	..args,
)

== For the eyes

#diagram(
  spacing: 10pt,
  cell-size: (20mm, 12mm),
  edge-stroke: 1pt,
  edge-corner-radius: 5pt,
  mark-scale: 70%,

  // Start Node
  blob((0,0), [Project Goals], shape: house.with(angle: 30deg), width: auto, tint: red),
  edge(),

  // Monitoring
  blob((-2,2), [Monitoring], tint: yellow, shape: hexagon),
  edge((0,0), (-2,2), "-|>",),
  edge((-2,2), (-2,4), `Real-time`, "--|>", bend: 30deg),
  blob((-2,4), [Metrics Collection], tint: orange),

  // Benchmarking
  blob((0,2), [Benchmarking], tint: blue, shape: hexagon, width: 32mm),
  edge((0,0), (0,2), "-|>"),
  edge((0,2), (0,4), `ECP Proxy Apps`, "--|>", bend: 30deg),
  blob((0,4), [Application Analysis], tint: green),

  // Resource Management
  blob((2,2), [Resource Management], tint: purple, shape: hexagon),
  edge((0,0), (2,2), "-|>", ``),
  edge((2,2), (2,4), `Memory & CPU`, "--|>", bend: 30deg),
  blob((2,4), [Optimization], tint: teal, width: auto)

)

= Project Structure

== Summary
#diagram(
  spacing: 8pt,
  cell-size: (8mm, 10mm),
  edge-stroke: 1pt,
  edge-corner-radius: 5pt,
  mark-scale: 70%,

  blob((0,0), [Disk Image Creation], shape: house.with(angle: 30deg), width: auto, tint: red),
  edge(),
  blob((0,2), [VM Configuration], tint: yellow, shape: hexagon),
  edge((0,2), (0,2), `gen-xml.sh`, "--|>", bend: -135deg),
  edge((0,2), (2,2), "-|>"),
  blob((2,2), [Metrics Collection], tint: orange),
  edge((2,2), (3,1), `Plotly`, "--|>", bend: 30deg),
  blob((3,3), [Resource Management], tint: blue, shape: hexagon),
  edge((2,2), (3,3), `netcat`, "--|>", bend: -30deg),
  edge((1,2), (2,2), "-|>"),
  blob((3,1), [Visualization], tint: yellow, shape: hexagon),
  edge((3,3), (), "-|>"),
  blob((5,2), [Automation], tint: green),
  edge((3,1), (5,2), `Dash`, "--|>", bend: 25deg),
  edge((3,3), (5,2), `virsh`, "--|>", bend: -25deg),
)

== Components
#table(
  columns: (auto, auto),
  inset: 8pt,
  align: center,
  [*File Name*], [*Purpose*],
  [`alpine-base.qcow2`], [Base Image],
  [`alpine-1.qcow2`, `alpine-2.qcow2`, `alpine-3.qcow2`], [VM Images],
  [`alpine.xml`], [Base XML Template],
  [`alpine-vm-1.xml`, `alpine-vm-2.xml`, `alpine-vm-3.xml`], [VM Configurations],
  [`gen-xml.sh`], [XML Generation Script],
  [`report-memory.sh`], [Metrics Script (VM → Host)],
  [`plot_adv.py`], [Listener, Visualizer and Monitor],
  [`runall.sh`], [Runner Script (VM)],
  [`memory_hog.c`], [Workload Simulation (VM)],
  [`metrics_data/`], [Metrics Storage (Host)],
  [`miniQMC/`], [Quantum Monte Carlo Simulation],
  [`MiniFE/`], [Finite Element Solver],
  [`HPCG/`], [High-Performance Computing Graph],
)

== Resource Management

#v(1em)
#text(weight: "bold", size: 18pt)[Dynamic RAM Adjustment]
- Increase RAM by 100 MB if usage > 80%.
- Decrease RAM by 500 MB if usage < 20%.
- Uses libvirt APIs for live adjustments.

#text(weight: "bold", size: 18pt)[Dynamic CPU Core Adjustment]
- Add CPU core if usage > 90%.
- Remove CPU core if usage < 30%.
- Adjusts cores dynamically (up to 2 cores).

==
#set text(size: 8pt)
#diagram(
  spacing: 10pt,
  cell-size: (10mm, 12mm),
  edge-stroke: 1pt,
  edge-corner-radius: 5pt,
  mark-scale: 70%,

  // Start Node
  blob((-2,-0.5), [Start Monitoring], shape: house.with(angle: 30deg), width: auto, tint: red),
  edge(),

  // RAM Adjustment Decision
  blob((-2,1), [RAM Usage], tint: yellow, shape: diamond),
  edge((-2,0), (-2,1), "-|>", `Check RAM`),
  edge((-2,1), (-2.5,3), `RAM Usage > 80%`, "--|>", bend: -30deg),
  blob((-2.5,3), [Add 100 MB RAM], tint: green, shape: hexagon),
  edge((-2,1), (-1,3), `RAM Usage < 20%`, "--|>", bend: -10deg),
  blob((-1,3), [Remove 500 MB RAM], tint: orange, shape: hexagon),

  // CPU Adjustment Decision
  blob((0,0), [CPU Usage], tint: blue, shape: diamond),
  edge((-2,-0.5), (0,0), "-|>", `Check CPU`),
  edge((0,0), (2.5,2), `CPU Usage > 90%`, "--|>", bend: 30deg),
  blob((2.5,2), [Add 1 CPU Core], tint: green, shape: hexagon),
  edge((0,0), (0,2), `CPU Usage < 30%`, "--|>", bend: -30deg),
  blob((0,2), [Remove 1 CPU Core], tint: orange, shape: hexagon),

  // End Node
  edge((-3,3), (0,4), "-|>"),
  edge((-1,3), (0,4), "-|>"),
  edge((0,2), (0,4), "-|>"),
  edge((2.5,2), (0,4), "-|>"),
  blob((0,4), [Adjustments Complete], shape: house.with(angle: 30deg), width: auto, tint: red)
)

#set text(size: 15pt)
= Metrics Reporting

==
- Memory usage (total and used).
- CPU usage (% utilization).
- Disk I/O (read/write activity).
- Network usage (bytes received/transmitted).
#v(1cm)
*We used:*
- Real-time graphs for memory, CPU, disk I/O, and network usage.
- Threshold indicators for memory and CPU.
- Historical data stored in CSV files.

==
#figure(
    image("ram_usage.png")
)

==
#figure(
    image("cpu_usage.png", height: 100pt)
)
#figure(
    image("cpu2.png")
)

==
#figure(
    image("io.png"),
)
#figure(
    image("network.png")
)

== Automation

#diagram(
  spacing: 12pt,
  cell-size: (10mm, 10mm),
  edge-stroke: 1pt,
  edge-corner-radius: 5pt,
  mark-scale: 70%,

  // Central Node
  blob((0,0), [Scripts Overview], shape: circle, tint: red, width: auto),

  // Outer Nodes
  blob((-2,2), [Runner Script], shape: hexagon, tint: yellow),
  blob((2,2), [Listener Script], shape: hexagon, tint: blue),
  blob((2,-2), [Metrics Script], shape: hexagon, tint: orange),
  blob((-2,-2), [XML Generation Script], shape: hexagon, tint: green),

  // Edges
  edge((0,0), (-2,2), "-|>", `Automates Execution`, bend: -20deg),
  edge((0,0), (2,2), "-|>", `Centralized Listener`, bend: 20deg),
  edge((0,0), (2,-2), "-|>", `Collects Metrics`, bend: -20deg),
  edge((0,0), (-2,-2), "-|>", `Generates XML`, bend: 20deg)
)
== Project Outcomes

#v(2em)
- Automated VM Deployment.
- Real-time Monitoring.
- Dynamic Resource Management.
- Performance Benchmarking.

- Visualization Dashboard.
- Optimized Resource Allocation.

==
#text(size: 24pt, weight: "bold")[Future Work]

#v(2em)
- Extend resource types: Support storage and network bandwidth optimization.

- Advanced Benchmarking: Integrate more comprehensive benchmarking tools.

- Machine Learning: Predict resource usage and optimize allocation.

= Thank You
