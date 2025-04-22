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

# Configuration
HOST = "0.0.0.0"
PORT = 4444
CSV_DIR = "metrics_data"  # Directory to store CSV files
if not os.path.exists(CSV_DIR):
    os.makedirs(CSV_DIR)

# RAM scaling configuration
RAM_INCREMENT_HIGH_MB = 100  # Amount of RAM to increase when usage > 80% (in MB)
RAM_INCREMENT_LOW_MB = 500   # Amount of RAM to decrease when usage < 20% (in MB)
RAM_INCREMENT_HIGH_KB = RAM_INCREMENT_HIGH_MB * 1024  # Convert to KB
RAM_INCREMENT_LOW_KB = RAM_INCREMENT_LOW_MB * 1024    # Convert to KB
THRESHOLD_HIGH_PERCENT = 80  # High memory usage threshold
THRESHOLD_LOW_PERCENT = 20   # Low memory usage threshold

# Mapping of node names to domain names (for libvirt)
NODE_TO_DOMAIN = {
    "grs-node-1": "grs-project-1",
    "grs-node-2": "grs-project-2",
    "grs-node-3": "grs-project-3",
}

# Mapping of node names to colors
NODE_COLORS = {
    "grs-node-1": "blue",
    "grs-node-2": "green",
    "grs-node-3": "red"
}

# Lock for thread-safe file access
file_lock = threading.Lock()
listener_running = False  # Flag to prevent multiple listener threads
time_counter = 0  # Simulated time counter for x-axis

# Connect to libvirt (session-based)
try:
    conn = libvirt.open("qemu:///session")
    if conn is None:
        print("Failed to open connection to qemu:///session")
    else:
        print("Successfully connected to libvirt")
        # List all domains
        domains = conn.listAllDomains()
        print("List of all domains:")
        for domain in domains:
            print(f"Name: {domain.name()}, ID: {domain.ID()}, State: {domain.state()[0]}")
except Exception as e:
    print(f"Error connecting to libvirt: {e}")
    conn = None

# Function to adjust RAM for a domain
def adjust_ram(node, increase=True, increment=RAM_INCREMENT_HIGH_KB):
    if conn is None:
        print("Cannot adjust RAM: No libvirt connection")
        return

    if node not in NODE_TO_DOMAIN:
        print(f"Unknown node: {node}")
        return

    domain_name = NODE_TO_DOMAIN[node].strip()  # Ensure no trailing/leading whitespace
    print(f"Looking up domain: '{domain_name}'")

    try:
        domain = conn.lookupByName(domain_name)
        if domain is None:
            print(f"Domain {domain_name} not found")
            return

        # Get the current memory allocation
        current_memory = domain.info()[2]  # Current memory in KB
        max_memory = domain.info()[1]  # Max memory in KB

        if increase:
            # Ensure we don't exceed the maximum memory
            new_memory = current_memory + increment
            if new_memory > max_memory:
                print(f"Cannot increase memory for {domain_name}: New memory ({new_memory // 1024} MB) exceeds max memory ({max_memory // 1024} MB)")
                return
            print(f"Increasing memory for {domain_name} from {current_memory // 1024} MB to {new_memory // 1024} MB")
        else:
            # Ensure we don't decrease below a reasonable minimum (e.g., 512 MB)
            new_memory = current_memory - increment
            if new_memory < 512 * 1024:  # 512 MB in KB
                print(f"Cannot decrease memory for {domain_name}: New memory ({new_memory // 1024} MB) is below the minimum allowed (512 MB)")
                return
            print(f"Decreasing memory for {domain_name} from {current_memory // 1024} MB to {new_memory // 1024} MB")

        # Set the new current memory allocation
        domain.setMemoryFlags(new_memory, libvirt.VIR_DOMAIN_AFFECT_LIVE)
    except libvirt.libvirtError as e:
        print(f"Failed to adjust memory for {domain_name}: {e}")
    except Exception as e:
        print(f"Error adjusting memory: {e}")

# Function to parse a single line of incoming data and save to CSV
def parse_line(line):
    global time_counter
    print(f"parse_line called with line: {line}")  # Debug log

    # Normalize whitespace and split the line
    parts = line.strip().split()

    # Ensure the line has exactly 7 parts
    if len(parts) != 7:
        print(f"Malformed line: {line}")  # Debug log
        return  # Skip malformed lines

    try:
        # Parse the fields
        node, mem_used, mem_max, cpu_usage, disk_io, net_rx, net_tx = parts
        mem_used = int(mem_used)
        mem_max = int(mem_max)
        cpu_usage = float(cpu_usage)
        disk_io = float(disk_io)
        net_rx = int(net_rx)
        net_tx = int(net_tx)

        # Check if memory usage exceeds the high threshold for RAM scaling
        if mem_used * 100 / mem_max > THRESHOLD_HIGH_PERCENT:
            print(f"Memory usage is high for {node} ({mem_used}/{mem_max} KB). Increasing RAM...")
            adjust_ram(node, increase=True, increment=RAM_INCREMENT_HIGH_KB)
        # Check if memory usage is below the low threshold for RAM scaling
        elif mem_used * 100 / mem_max < THRESHOLD_LOW_PERCENT:
            print(f"Memory usage is low for {node} ({mem_used}/{mem_max} KB). Decreasing RAM...")
            adjust_ram(node, increase=False, increment=RAM_INCREMENT_LOW_KB)

        # Create CSV file path for this node
        csv_path = os.path.join(CSV_DIR, f"{node}.csv")

        # Check if file exists to determine if we need headers
        file_exists = os.path.isfile(csv_path)

        # Write data to CSV file
        with file_lock:
            with open(csv_path, 'a', newline='') as csvfile:
                fieldnames = ['time', 'memory_usage', 'memory_max', 'cpu_usage', 'disk_io', 'net_rx', 'net_tx']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # Write header if file is new
                if not file_exists:
                    writer.writeheader()

                # Write data row
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
        # Handle any parsing errors
        print(f"Error parsing line: {line}, Error: {e}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

# Function to listen for incoming data on the specified port
def listen_for_data():
    global time_counter, listener_running
    if listener_running:
        print("Listener thread is already running. Exiting.")
        return
    listener_running = True

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            # Set socket options to reuse the port
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                server_socket.bind((HOST, PORT))
            except OSError as e:
                if e.errno == errno.EADDRINUSE:
                    print(f"Port {PORT} is already in use. Exiting listener thread.")
                    listener_running = False
                    return  # Exit the thread if the port is already in use
                else:
                    raise  # Re-raise other exceptions

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
                time_counter += 1  # Increment time counter after processing each connection
                print(f"Time counter incremented to {time_counter}")  # Debug log
    except Exception as e:
        print(f"Error in listener thread: {e}")
    finally:
        listener_running = False  # Reset the flag when the thread exits

# Function to read data from CSV files
def read_node_data():
    node_data = {}

    # Check if directory exists
    if not os.path.exists(CSV_DIR):
        return node_data

    # List all CSV files in the directory
    csv_files = [f for f in os.listdir(CSV_DIR) if f.endswith('.csv')]

    for csv_file in csv_files:
        try:
            node_name = os.path.splitext(csv_file)[0]  # Extract node name from filename
            file_path = os.path.join(CSV_DIR, csv_file)

            with file_lock:
                # Read CSV file into DataFrame
                df = pd.read_csv(file_path)

                if not df.empty:
                    # Limit to last 200 data points for performance
                    if len(df) > 200:
                        df = df.tail(200)

                    # Convert DataFrame to dictionary format for plotting
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

# Start the listener in a separate thread
listener_thread = threading.Thread(target=listen_for_data, daemon=True)
listener_thread.start()

# Dash App Setup
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("System Metrics Dashboard with Auto RAM Scaling", style={'textAlign': 'center'}),
    html.Div([
        html.Div([
            html.H3("RAM Scaling Configuration", style={'textAlign': 'center'}),
            html.P(f"High threshold: {THRESHOLD_HIGH_PERCENT}% - Increase by {RAM_INCREMENT_HIGH_MB} MB"),
            html.P(f"Low threshold: {THRESHOLD_LOW_PERCENT}% - Decrease by {RAM_INCREMENT_LOW_MB} MB"),
        ], style={'padding': '10px', 'backgroundColor': '#f0f0f0', 'borderRadius': '5px', 'marginBottom': '20px'})
    ]),
    dcc.Graph(id='memory-usage-graph'),
    dcc.Graph(id='cpu-usage-graph'),
    dcc.Graph(id='disk-io-graph'),
    dcc.Graph(id='network-usage-graph'),
    dcc.Interval(
        id='interval-component',
        interval=1000,  # Update every 1 second
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
    print(f"update_plots called with n_intervals: {n_intervals}")  # Debug log

    # Read data from CSV files
    data = read_node_data()

    # Check if any data has been loaded
    if not data:
        return go.Figure(), go.Figure(), go.Figure(), go.Figure()

    memory_fig = go.Figure()
    cpu_fig = go.Figure()
    disk_fig = go.Figure()
    network_fig = go.Figure()

    for node in data.keys():
        print(f"Plotting data for {node}")  # Debug log
        values = data[node]
        color = NODE_COLORS.get(node, 'black')  # Default to black if not found

        # Memory Usage Subplot with cross-hatching
        memory_fig.add_trace(go.Scatter(
            x=values["time"], y=values["memory_usage"],
            mode='lines', name=f"{node} Current Usage", line=dict(color=color)
        ))
        memory_fig.add_trace(go.Scatter(
            x=values["time"], y=values["memory_max"],
            mode='lines', name=f"{node} Max Usage",
            line=dict(color=color, dash='dash'),
            fill='tonexty', fillpattern=dict(shape='x')  # Add cross-hatching
        ))

        # Add threshold lines to memory figure
        x_range = values["time"]
        if x_range:
            # High threshold line
            memory_fig.add_shape(
                type="line",
                x0=min(x_range), y0=max(values["memory_max"]) * THRESHOLD_HIGH_PERCENT / 100,
                x1=max(x_range), y1=max(values["memory_max"]) * THRESHOLD_HIGH_PERCENT / 100,
                line=dict(color="red", width=1, dash="dot"),
                name=f"High Threshold ({THRESHOLD_HIGH_PERCENT}%)"
            )
            # Low threshold line
            memory_fig.add_shape(
                type="line",
                x0=min(x_range), y0=max(values["memory_max"]) * THRESHOLD_LOW_PERCENT / 100,
                x1=max(x_range), y1=max(values["memory_max"]) * THRESHOLD_LOW_PERCENT / 100,
                line=dict(color="green", width=1, dash="dot"),
                name=f"Low Threshold ({THRESHOLD_LOW_PERCENT}%)"
            )

        # CPU Usage Subplot
        cpu_fig.add_trace(go.Scatter(
            x=values["time"], y=values["cpu_usage"],
            mode='lines', name=f"{node} CPU Usage (%)", line=dict(color=color)
        ))

        # Disk I/O Subplot
        disk_fig.add_trace(go.Scatter(
            x=values["time"], y=values["disk_io"],
            mode='lines', name=f"{node} Disk I/O (KB/s)", line=dict(color=color)
        ))

        # Network Metrics Subplot
        network_fig.add_trace(go.Scatter(
            x=values["time"], y=values["net_rx"],
            mode='lines', name=f"{node} Network RX (Bytes)", line=dict(color=color)
        ))
        network_fig.add_trace(go.Scatter(
            x=values["time"], y=values["net_tx"],
            mode='lines', name=f"{node} Network TX (Bytes)",
            line=dict(color=color, dash='dot')
        ))

    # Update layout for each subplot
    memory_fig.update_layout(
        title="Memory Usage Over Time (with Auto-Scaling Thresholds)",
        xaxis_title="Time (seconds)",
        yaxis_title="Memory Usage (KB)",
        height=600,  # Increased height for better visualization
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
