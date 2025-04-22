import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import socket
import threading
import time
import errno
from collections import defaultdict

# Configuration
HOST = "0.0.0.0"
PORT = 4444

# Initialize data storage for metrics
data = defaultdict(lambda: {
    "time": [],
    "memory_usage": [],
    "memory_max": [],
    "cpu_usage": [],
    "disk_io": [],
    "net_rx": [],
    "net_tx": []
})
time_counter = 0  # Simulated time counter for x-axis
listener_running = False  # Flag to prevent multiple listener threads

# Lock for thread-safe access to the data dictionary
data_lock = threading.Lock()

# Function to parse a single line of incoming data
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

        # Initialize the node in the data dictionary
        with data_lock:  # Ensure thread-safe access
            _ = data[node]  # Trigger defaultdict initialization for the node
            print(f"Initialized data for node: {node}")  # Debug log

            # Only append data if the time_counter is not already present
            if time_counter not in data[node]["time"]:
                data[node]["time"].append(time_counter)
                data[node]["memory_usage"].append(mem_used)
                data[node]["memory_max"].append(mem_max)
                data[node]["cpu_usage"].append(cpu_usage)
                data[node]["disk_io"].append(disk_io)
                data[node]["net_rx"].append(net_rx)
                data[node]["net_tx"].append(net_tx)
                print(f"Updated data for {node}: {data[node]}")  # Debug log

    except ValueError as e:
        # Handle any parsing errors
        print(f"Error parsing line: {line}, Error: {e}")

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
                            data_chunk = client_socket.recv(1024).decode("utf-8")
                            if not data_chunk:
                                break
                            for line in data_chunk.splitlines():
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

# Start the listener in a separate thread
listener_thread = threading.Thread(target=listen_for_data, daemon=True)
listener_thread.start()

# Dash App Setup
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("System Metrics Dashboard", style={'textAlign': 'center'}),
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

    memory_fig = go.Figure()
    cpu_fig = go.Figure()
    disk_fig = go.Figure()
    network_fig = go.Figure()

    with data_lock:  # Ensure thread-safe access
        print(f"Data keys in update_plots: {list(data.keys())}")  # Debug log
        for node in data.keys():
            values = data[node]
            time_to_plot = values["time"][-200:] if len(values["time"]) > 200 else values["time"]

            # Memory Usage Subplot
            memory_fig.add_trace(go.Scatter(
                x=time_to_plot, y=values["memory_usage"][-200:],
                mode='lines', name=f"{node} Memory Usage (KB)"
            ))
            memory_fig.add_trace(go.Scatter(
                x=time_to_plot, y=values["memory_max"][-200:],
                mode='lines', name=f"{node} Memory Max (KB)", line=dict(dash='dash')
            ))

            # CPU Usage Subplot
            cpu_fig.add_trace(go.Scatter(
                x=time_to_plot, y=values["cpu_usage"][-200:],
                mode='lines', name=f"{node} CPU Usage (%)"
            ))

            # Disk I/O Subplot
            disk_fig.add_trace(go.Scatter(
                x=time_to_plot, y=values["disk_io"][-200:],
                mode='lines', name=f"{node} Disk I/O (KB/s)"
            ))

            # Network Metrics Subplot
            network_fig.add_trace(go.Scatter(
                x=time_to_plot, y=values["net_rx"][-200:],
                mode='lines', name=f"{node} Network RX (Bytes)"
            ))
            network_fig.add_trace(go.Scatter(
                x=time_to_plot, y=values["net_tx"][-200:],
                mode='lines', name=f"{node} Network TX (Bytes)"
            ))

    # Update layout for each subplot
    memory_fig.update_layout(
        title="Memory Usage Over Time",
        xaxis_title="Time (seconds)",
        yaxis_title="Memory Usage (KB)",
        height=400,
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
