import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import socket
import struct
from collections import defaultdict
import threading
import libvirt

# Configuration
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 4444       # Port to listen on
RAM_INCREMENT_HIGH_MB = 100  # Amount of RAM to increase when usage > 80% (in MB)
RAM_INCREMENT_LOW_MB = 500   # Amount of RAM to decrease when usage < 20% (in MB)
RAM_INCREMENT_HIGH_KB = RAM_INCREMENT_HIGH_MB * 1024  # Convert to KB
RAM_INCREMENT_LOW_KB = RAM_INCREMENT_LOW_MB * 1024    # Convert to KB
THRESHOLD_HIGH_PERCENT = 80  # High memory usage threshold
THRESHOLD_LOW_PERCENT = 20   # Low memory usage threshold

# Mapping of node names to domain names
NODE_TO_DOMAIN = {
    "grs-node-1": "grs-project-1",
    "grs-node-2": "grs-project-2",
    "grs-node-3": "grs-project-3",
}

# Colors for each node
NODE_COLORS = {
    "grs-node-1": "blue",
    "grs-node-2": "green",
    "grs-node-3": "red",
}

# Initialize data storage
data = defaultdict(lambda: {"time": [], "usage": [], "max": []})
time_counter = 0  # Simulated time counter for x-axis

# Connect to libvirt (session-based)
conn = libvirt.open("qemu:///session")
if conn is None:
    print("Failed to open connection to qemu:///session")
    exit(1)
else:
    print("Successfully connected to libvirt")

# List all domains
domains = conn.listAllDomains()
print("List of all domains:")
for domain in domains:
    print(f"Name: {domain.name()}, ID: {domain.ID()}, State: {domain.state()[0]}")

# Function to parse a single line of incoming data
def parse_line(line):
    global time_counter
    parts = line.strip().split()
    if len(parts) != 3:
        return  # Skip malformed lines
    node, current_usage, max_usage = parts
    current_usage = int(current_usage)
    max_usage = int(max_usage)

    # Update the data for the node
    if time_counter not in data[node]["time"]:
        data[node]["time"].append(time_counter)
        data[node]["usage"].append(current_usage)
        data[node]["max"].append(max_usage)

    # Check if memory usage exceeds the high threshold
    if current_usage * 100 / max_usage > THRESHOLD_HIGH_PERCENT:
        print(f"Memory usage is high for {node} ({current_usage}/{max_usage} KB). Increasing RAM...")
        adjust_ram(node, increase=True, increment=RAM_INCREMENT_HIGH_KB)

    # Check if memory usage is below the low threshold
    elif current_usage * 100 / max_usage < THRESHOLD_LOW_PERCENT:
        print(f"Memory usage is low for {node} ({current_usage}/{max_usage} KB). Decreasing RAM...")
        adjust_ram(node, increase=False, increment=RAM_INCREMENT_LOW_KB)

# Function to adjust RAM for a domain
def adjust_ram(node, increase=True, increment=RAM_INCREMENT_HIGH_KB):
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

# Function to listen for incoming data on the specified port
def listen_for_data():
    global time_counter
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # Set socket options
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))

        print(f"Attempting to bind to {HOST}:{PORT}...")
        try:
            server_socket.bind((HOST, PORT))
            print(f"Successfully bound to {HOST}:{PORT}")
        except OSError as e:
            print(f"Error binding to {HOST}:{PORT}: {e}")
            return

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

# Start the listener in a separate thread
listener_thread = threading.Thread(target=listen_for_data, daemon=True)
listener_thread.start()

# Dash App Setup
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Memory Usage Over Time", style={'textAlign': 'center'}),
    dcc.Graph(id='memory-usage-graph'),
    dcc.Interval(
        id='interval-component',
        interval=1000,  # Update every 1 second
        n_intervals=0
    )
])

@app.callback(
    Output('memory-usage-graph', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_plot(n_intervals):
    fig = go.Figure()

    for node in ["grs-node-1", "grs-node-2", "grs-node-3"]:
        if node in data:
            values = data[node]
            color = NODE_COLORS[node]  # Use the same color for current and max usage
            # Plot only the last 200 entries if there are more than 200
            time_to_plot = values["time"][-200:] if len(values["time"]) > 200 else values["time"]
            usage_to_plot = values["usage"][-200:] if len(values["usage"]) > 200 else values["usage"]
            max_to_plot = values["max"][-200:] if len(values["max"]) > 200 else values["max"]

            # Add current usage line
            fig.add_trace(go.Scatter(
                x=time_to_plot, y=usage_to_plot, mode='lines', name=f"{node} Current Usage",
                line=dict(color=color)
            ))

            # Add max usage line
            fig.add_trace(go.Scatter(
                x=time_to_plot, y=max_to_plot, mode='lines', name=f"{node} Max Usage",
                line=dict(color=color, dash='dash'),
                fill='tonexty', fillpattern=dict(shape='x')  # Add cross-hatching
            ))

    fig.update_layout(
        title="Memory Usage Over Time",
        xaxis_title="Time (seconds)",
        yaxis_title="Memory Usage (KB)",
        legend_title="Nodes",
        height=800
    )

    return fig

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)
