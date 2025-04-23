import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import socket
import threading
import time
import errno
import os
import csv
import pandas as pd
from collections import defaultdict
import libvirt
import glob

HOST = "0.0.0.0"
PORT = 4444
CSV_DIR = "metrics_data"
if not os.path.exists(CSV_DIR):
    os.makedirs(CSV_DIR)

RAM_INCREMENT_HIGH_MB = 100
RAM_INCREMENT_LOW_MB = 500
RAM_INCREMENT_HIGH_KB = RAM_INCREMENT_HIGH_MB * 1024
RAM_INCREMENT_LOW_KB = RAM_INCREMENT_LOW_MB * 1024
THRESHOLD_HIGH_PERCENT = 80
THRESHOLD_LOW_PERCENT = 20

CPU_THRESHOLD_HIGH_PERCENT = 90
CPU_THRESHOLD_LOW_PERCENT = 30
MAX_CPU_CORES = 2
MIN_CPU_CORES = 1

NODE_TO_DOMAIN = {
    "grs-node-1": "grs-project-1",
    "grs-node-2": "grs-project-2",
    "grs-node-3": "grs-project-3",
}

NODE_COLORS = {
    "grs-node-1": "blue",
    "grs-node-2": "green",
    "grs-node-3": "red"
}

file_lock = threading.Lock()
listener_running = False
time_counter = 0

[os.remove(f) for f in glob.glob("metrics_data/grs-node-*")]

try:
    conn = libvirt.open("qemu:///session")
    if conn is None:
        print("Failed to open connection to qemu:///session")
    else:
        print("Successfully connected to libvirt")
        domains = conn.listAllDomains()
        print("List of all domains:")
        for domain in domains:
            print(f"Name: {domain.name()}, ID: {domain.ID()}, State: {domain.state()[0]}")
except Exception as e:
    print(f"Error connecting to libvirt: {e}")
    conn = None

def adjust_ram(node, increase=True, increment=RAM_INCREMENT_HIGH_KB):
    """
    Adjusts the RAM allocation for a given node's domain.

    Args:
        node (str): The node name.
        increase (bool): Whether to increase or decrease RAM.
        increment (int): The amount of RAM to adjust in KB.
    """
    if conn is None:
        print("Cannot adjust RAM: No libvirt connection")
        return

    if node not in NODE_TO_DOMAIN:
        print(f"Unknown node: {node}")
        return

    domain_name = NODE_TO_DOMAIN[node].strip()
    print(f"Looking up domain: '{domain_name}'")

    try:
        domain = conn.lookupByName(domain_name)
        if domain is None:
            print(f"Domain {domain_name} not found")
            return

        current_memory = domain.info()[2]
        max_memory = domain.info()[1]

        if increase:
            new_memory = current_memory + increment
            if new_memory > max_memory:
                print(f"Cannot increase memory for {domain_name}: New memory ({new_memory // 1024} MB) exceeds max memory ({max_memory // 1024} MB)")
                return
            print(f"Increasing memory for {domain_name} from {current_memory // 1024} MB to {new_memory // 1024} MB")
        else:
            new_memory = current_memory - increment
            if new_memory < 512 * 1024:
                print(f"Cannot decrease memory for {domain_name}: New memory ({new_memory // 1024} MB) is below the minimum allowed (512 MB)")
                return
            print(f"Decreasing memory for {domain_name} from {current_memory // 1024} MB to {new_memory // 1024} MB")

        domain.setMemoryFlags(new_memory, libvirt.VIR_DOMAIN_AFFECT_LIVE)
    except libvirt.libvirtError as e:
        print(f"Failed to adjust memory for {domain_name}: {e}")
    except Exception as e:
        print(f"Error adjusting memory: {e}")

def adjust_cpu_cores(node, increase=True):
    """
    Adjusts the number of CPU cores for a given node's domain.

    Args:
        node (str): The node name.
        increase (bool): Whether to increase or decrease CPU cores.
    """
    if conn is None:
        print("Cannot adjust CPU cores: No libvirt connection")
        return

    if node not in NODE_TO_DOMAIN:
        print(f"Unknown node: {node}")
        return

    domain_name = NODE_TO_DOMAIN[node].strip()
    print(f"Looking up domain for CPU adjustment: '{domain_name}'")

    try:
        domain = conn.lookupByName(domain_name)
        if domain is None:
            print(f"Domain {domain_name} not found")
            return

        xml_desc = domain.XMLDesc(0)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_desc)
        vcpu_element = root.find('./vcpu')

        if vcpu_element is not None:
            current_vcpus = int(vcpu_element.text or 0)
            print(f"Current vCPUs for {domain_name}: {current_vcpus}")

            if increase and current_vcpus < MAX_CPU_CORES:
                new_vcpus = current_vcpus + 1
                print(f"Increasing vCPUs for {domain_name} from {current_vcpus} to {new_vcpus}")
            elif not increase and current_vcpus > MIN_CPU_CORES:
                new_vcpus = current_vcpus - 1
                print(f"Decreasing vCPUs for {domain_name} from {current_vcpus} to {new_vcpus}")
            else:
                print(f"No CPU adjustment needed for {domain_name}: Already at {'maximum' if increase else 'minimum'} cores")
                return

            domain.setVcpusFlags(new_vcpus, libvirt.VIR_DOMAIN_AFFECT_LIVE)
            print(f"Successfully adjusted vCPUs for {domain_name} to {new_vcpus}")
        else:
            print(f"Could not find vcpu element in domain XML for {domain_name}")

    except libvirt.libvirtError as e:
        print(f"Failed to adjust CPU cores for {domain_name}: {e}")
    except Exception as e:
        print(f"Error adjusting CPU cores: {e}")

def parse_line(line):
    """
    Parses a single line of incoming data and saves it to a CSV file.

    Args:
        line (str): The incoming data line.
    """
    global time_counter
    print(f"parse_line called with line: {line}")

    parts = line.strip().split()

    if len(parts) != 7:
        print(f"Malformed line: {line}")
        return

    try:
        node, mem_used, mem_max, cpu_usage, disk_io, net_rx, net_tx = parts
        mem_used = int(mem_used)
        mem_max = int(mem_max)
        cpu_usage = float(cpu_usage)
        disk_io = float(disk_io)
        net_rx = int(net_rx)
        net_tx = int(net_tx)

        if mem_used * 100 / mem_max > THRESHOLD_HIGH_PERCENT:
            print(f"Memory usage is high for {node} ({mem_used}/{mem_max} KB). Increasing RAM...")
            adjust_ram(node, increase=True, increment=RAM_INCREMENT_HIGH_KB)
        elif mem_used * 100 / mem_max < THRESHOLD_LOW_PERCENT:
            print(f"Memory usage is low for {node} ({mem_used}/{mem_max} KB). Decreasing RAM...")
            adjust_ram(node, increase=False, increment=RAM_INCREMENT_LOW_KB)

        if cpu_usage > CPU_THRESHOLD_HIGH_PERCENT:
            print(f"CPU usage is high for {node} ({cpu_usage}%). Adding CPU core...")
            adjust_cpu_cores(node, increase=True)
        elif cpu_usage < CPU_THRESHOLD_LOW_PERCENT:
            print(f"CPU usage is low for {node} ({cpu_usage}%). Removing CPU core...")
            adjust_cpu_cores(node, increase=False)

        csv_path = os.path.join(CSV_DIR, f"{node}.csv")
        file_exists = os.path.isfile(csv_path)

        with file_lock:
            with open(csv_path, 'a', newline='') as csvfile:
                fieldnames = ['time', 'memory_usage', 'memory_max', 'cpu_usage', 'disk_io', 'net_rx', 'net_tx']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()

                writer.writerow({
                    'time': time_counter,
                    'memory_usage': mem_used,
                    'memory_max': mem_max,
                    'cpu_usage': cpu_usage,
                    'disk_io': disk_io,
                    'net_rx': net_rx,
                    'net_tx': net_tx
                })

            print(f"Saved data for {node} at time {time_counter}")

    except ValueError as e:
        print(f"Error parsing line: {line}, Error: {e}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def listen_for_data():
    """
    Listens for incoming data on the specified port and processes it.

    This function runs in a separate thread.
    """
    global time_counter, listener_running
    if listener_running:
        print("Listener thread is already running. Exiting.")
        return
    listener_running = True

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                server_socket.bind((HOST, PORT))
            except OSError as e:
                if e.errno == errno.EADDRINUSE:
                    print(f"Port {PORT} is already in use. Exiting listener thread.")
                    listener_running = False
                    return
                else:
                    raise

            server_socket.listen(5)
            print(f"Listening for connections on {HOST}:{PORT}...")

            while True:
                client_socket, client_address = server_socket.accept()
                print(f"Connection established with {client_address}")
                with client_socket:
                    while True:
                        try:
                            data_chunk = client_socket.recv(1024)
                            try:
                                decoded_data = data_chunk.decode("utf-8")
                            except UnicodeDecodeError as e:
                                print(f"Decoding error: {e}")
                                continue
                            if not decoded_data:
                                break
                            for line in decoded_data.splitlines():
                                parse_line(line)
                        except Exception as e:
                            print(f"Error receiving data: {e}")
                            break
                time_counter += 1
                print(f"Time counter incremented to {time_counter}")
    except Exception as e:
        print(f"Error in listener thread: {e}")
    finally:
        listener_running = False

def read_node_data():
    """
    Reads data from CSV files and returns it in a dictionary format.

    Returns:
        dict: A dictionary containing node data for plotting.
    """
    node_data = {}

    if not os.path.exists(CSV_DIR):
        return node_data

    csv_files = [f for f in os.listdir(CSV_DIR) if f.endswith('.csv')]

    for csv_file in csv_files:
        try:
            node_name = os.path.splitext(csv_file)[0]
            file_path = os.path.join(CSV_DIR, csv_file)

            with file_lock:
                df = pd.read_csv(file_path)

                if not df.empty:
                    if len(df) > 200:
                        df = df.tail(200)

                    node_data[node_name] = {
                        'time': df['time'].tolist(),
                        'memory_usage': df['memory_usage'].tolist(),
                        'memory_max': df['memory_max'].tolist(),
                        'cpu_usage': df['cpu_usage'].tolist(),
                        'disk_io': df['disk_io'].tolist(),
                        'net_rx': df['net_rx'].tolist(),
                        'net_tx': df['net_tx'].tolist()
                    }
        except Exception as e:
            print(f"Error reading {csv_file}: {e}")

    return node_data

listener_thread = threading.Thread(target=listen_for_data, daemon=True)
listener_thread.start()

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("System Metrics Dashboard", style={'textAlign': 'center'}),
    dcc.Graph(id='memory-usage-graph'),
    dcc.Graph(id='cpu-usage-graph'),
    dcc.Graph(id='disk-io-graph'),
    dcc.Graph(id='network-usage-graph'),
    dcc.Interval(
        id='interval-component',
        interval=1000,
        n_intervals=0
    )
])

@app.callback(
    [
        Output('memory-usage-graph', 'figure'),
        Output('cpu-usage-graph', 'figure'),
        Output('disk-io-graph', 'figure'),
        Output('network-usage-graph', 'figure')
    ],
    [Input('interval-component', 'n_intervals')]
)
def update_plots(n_intervals):
    """
    Updates the plots for memory, CPU, disk I/O, and network usage.

    Args:
        n_intervals (int): The number of intervals that have passed.

    Returns:
        tuple: Updated figures for each graph.
    """
    print(f"update_plots called with n_intervals: {n_intervals}")

    data = read_node_data()

    if not data:
        return go.Figure(), go.Figure(), go.Figure(), go.Figure()

    memory_fig = go.Figure()
    cpu_fig = go.Figure()
    disk_fig = go.Figure()
    network_fig = go.Figure()

    for node in data.keys():
        print(f"Plotting data for {node}")
        values = data[node]
        color = NODE_COLORS.get(node, 'black')

        memory_fig.add_trace(go.Scatter(
            x=values["time"], y=values["memory_usage"],
            mode='lines', name=f"{node} Current Usage", line=dict(color=color)
        ))
        memory_fig.add_trace(go.Scatter(
            x=values["time"], y=values["memory_max"],
            mode='lines', name=f"{node} Max Usage",
            line=dict(color=color, dash='dash'),
            fill='tonexty', fillpattern=dict(shape='x')
        ))

        x_range = values["time"]
        if x_range:
            memory_fig.add_shape(
                type="line",
                x0=min(x_range), y0=max(values["memory_max"]) * THRESHOLD_HIGH_PERCENT / 100,
                x1=max(x_range), y1=max(values["memory_max"]) * THRESHOLD_HIGH_PERCENT / 100,
                line=dict(color="red", width=1, dash="dot"),
                name=f"High Threshold ({THRESHOLD_HIGH_PERCENT}%)"
            )
            memory_fig.add_shape(
                type="line",
                x0=min(x_range), y0=max(values["memory_max"]) * THRESHOLD_LOW_PERCENT / 100,
                x1=max(x_range), y1=max(values["memory_max"]) * THRESHOLD_LOW_PERCENT / 100,
                line=dict(color="green", width=1, dash="dot"),
                name=f"Low Threshold ({THRESHOLD_LOW_PERCENT}%)"
            )

        cpu_fig.add_trace(go.Scatter(
            x=values["time"], y=values["cpu_usage"],
            mode='lines', name=f"{node} CPU Usage (%)", line=dict(color=color)
        ))

        disk_fig.add_trace(go.Scatter(
            x=values["time"], y=values["disk_io"],
            mode='lines', name=f"{node} Disk I/O (KB/s)", line=dict(color=color)
        ))

        network_fig.add_trace(go.Scatter(
            x=values["time"], y=values["net_rx"],
            mode='lines', name=f"{node} Network RX (Bytes)", line=dict(color=color)
        ))
        network_fig.add_trace(go.Scatter(
            x=values["time"], y=values["net_tx"],
            mode='lines', name=f"{node} Network TX (Bytes)",
            line=dict(color=color, dash='dot')
        ))

    memory_fig.update_layout(
        title="Memory Usage Over Time",
        xaxis_title="Time (seconds)",
        yaxis_title="Memory Usage (KB)",
        height=600,
        legend_title="Nodes"
    )

    cpu_fig.update_layout(
        title="CPU Usage Over Time",
        xaxis_title="Time (seconds)",
        yaxis_title="CPU Usage (%)",
        height=400,
        legend_title="Nodes"
    )

    disk_fig.update_layout(
        title="Disk I/O Over Time",
        xaxis_title="Time (seconds)",
        yaxis_title="Disk I/O (KB/s)",
        height=400,
        legend_title="Nodes"
    )

    network_fig.update_layout(
        title="Network Usage Over Time",
        xaxis_title="Time (seconds)",
        yaxis_title="Network Usage (Bytes)",
        height=400,
        legend_title="Nodes"
    )

    return memory_fig, cpu_fig, disk_fig, network_fig

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)
