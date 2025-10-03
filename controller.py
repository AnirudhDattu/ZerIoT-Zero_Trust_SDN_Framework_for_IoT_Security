import matplotlib
matplotlib.use('Agg')
from flask import Flask, request, render_template, send_file, jsonify
import json
import matplotlib.pyplot as plt
import io
import time
import uuid
from datetime import datetime
import random

app = Flask(__name__)

# Device authorization (static for now, can be dynamic)
authorized_devices = {
    "ESP32_2": True,
    "ESP32_3": True,
    "ESP32_4": False
}
device_data = {"ESP32_2": [], "ESP32_3": [], "ESP32_4": []}
timestamps = []
last_seen = {"ESP32_2": 0, "ESP32_3": 0, "ESP32_4": 0}
device_tokens = {}  # {device_id: {"token": token, "last_activity": timestamp}}
packet_counts = {"ESP32_2": [], "ESP32_3": [], "ESP32_4": []}  # For rate limiting
SESSION_TIMEOUT = 300  # 5 minutes
RATE_LIMIT = 60  # Max 60 packets per minute per device

# Store MAC addresses dynamically
mac_addresses = {
    "ESP32_Gateway": "A0:B1:C2:D3:E4:F5"  # Hardcoded for gateway
    # ESP32 devices will be populated dynamically
}

# SDN Policies
sdn_policies = {
    "packet_inspection": False,
    "traffic_shaping": False,
    "dynamic_routing": False
}

# Simulated policy logs
policy_logs = []

# Simulated SDN metrics
sdn_metrics = {
    "control_plane_latency": 0,  # ms
    "data_plane_throughput": 0,  # Mbps
    "policy_enforcement_rate": 0  # %
}

def is_maintenance_window():
    current_hour = datetime.now().hour
    return 2 <= current_hour < 3  # Simulated maintenance window

def simulate_policy_enforcement(device_id):
    if sdn_policies["packet_inspection"] and random.random() > 0.8:
        policy_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Blocked packet from {device_id} due to packet inspection policy")
        return False
    if sdn_policies["traffic_shaping"] and random.random() > 0.9:
        policy_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Delayed packet from {device_id} due to traffic shaping policy")
        time.sleep(0.1)  # Simulate delay
    if sdn_policies["dynamic_routing"]:
        policy_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Rerouted packet from {device_id} via dynamic routing policy")
    return True

def update_sdn_metrics():
    sdn_metrics["control_plane_latency"] = random.randint(5, 50)
    sdn_metrics["data_plane_throughput"] = random.randint(100, 1000)
    sdn_metrics["policy_enforcement_rate"] = random.randint(80, 100)

@app.route('/get_token', methods=['POST'])
def get_token():
    data = request.json
    device_id = data.get('device_id')
    mac_address = data.get('mac_address')  # Get MAC address from request
    if not device_id:
        return json.dumps({'error': 'Missing device_id'}), 400
    if not authorized_devices.get(device_id, False):
        return json.dumps({'error': 'Device not authorized'}), 403
    token = str(uuid.uuid4())
    device_tokens[device_id] = {"token": token, "last_activity": time.time()}
    if mac_address:  # Store the MAC address if provided
        mac_addresses[device_id] = mac_address
    return json.dumps({'token': token})

@app.route('/auth', methods=['POST'])
def auth():
    data = request.json
    device_id = data.get('device_id')
    token = data.get('token')
    if not device_id or not token:
        return json.dumps({'error': 'Missing device_id or token'}), 400

    if device_id not in device_tokens or device_tokens[device_id]["token"] != token:
        return json.dumps({'device_id': device_id, 'authorized': False})

    current_time = time.time()
    last_activity = device_tokens[device_id]["last_activity"]
    if current_time - last_activity > SESSION_TIMEOUT:
        device_tokens.pop(device_id)
        return json.dumps({'device_id': device_id, 'authorized': False})

    device_tokens[device_id]["last_activity"] = current_time
    return json.dumps({'device_id': device_id, 'authorized': True})

@app.route('/data', methods=['POST'])
def data():
    data = request.json
    device_id = data.get('device_id')
    token = data.get('token')
    packet_time = data.get('timestamp')
    data_value = data.get('data', 0)

    if not device_id or not token or not packet_time:
        return json.dumps({'status': 'rejected'})

    if device_id not in device_tokens or device_tokens[device_id]["token"] != token:
        return json.dumps({'status': 'rejected'})

    current_time = time.time()
    last_activity = device_tokens[device_id]["last_activity"]
    if current_time - last_activity > SESSION_TIMEOUT:
        device_tokens.pop(device_id)
        return json.dumps({'status': 'rejected'})

    if is_maintenance_window():
        return json.dumps({'status': 'rejected', 'reason': 'Maintenance window'})

    packet_counts[device_id].append(current_time)
    packet_counts[device_id] = [t for t in packet_counts[device_id] if current_time - t <= 60]
    if len(packet_counts[device_id]) > RATE_LIMIT:
        return json.dumps({'status': 'rejected', 'reason': 'Rate limit exceeded'})

    # Apply SDN policies
    if not simulate_policy_enforcement(device_id):
        return json.dumps({'status': 'rejected', 'reason': 'SDN policy violation'})

    device_tokens[device_id]["last_activity"] = current_time
    last_seen[device_id] = current_time
    device_data[device_id].append(1)
    if len(timestamps) == 0 or current_time - timestamps[-1] > 1:
        timestamps.append(current_time)
    return json.dumps({'status': 'accepted'})

def generate_graph():
    plt.figure(figsize=(8, 4))
    has_data = False
    for device in device_data:
        if len(device_data[device]) > 0:
            plt.plot(timestamps[-len(device_data[device]):], device_data[device], label=device)
            has_data = True
    if has_data:
        plt.xlabel('Time (s)')
        plt.ylabel('Packets Received')
        plt.legend()
        plt.grid(True)
    else:
        plt.text(0.5, 0.5, 'No data to display', horizontalalignment='center', verticalalignment='center')
        plt.axis('off')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

@app.route('/')
def dashboard():
    return render_template('dashboard.html', devices=authorized_devices, data={k: sum(v) for k, v in device_data.items()})

@app.route('/graph')
def graph():
    return send_file(generate_graph(), mimetype='image/png')

@app.route('/get_data')
def get_data():
    current_time = time.time()
    data = {}
    for device in device_data:
        packet_count = sum(device_data[device])
        device_packet_counts = [t for t in packet_counts[device] if current_time - t <= 60]
        rate_limit_status = f"{len(device_packet_counts)}/{RATE_LIMIT}"
        blocked_reason = "Maintenance window" if is_maintenance_window() else None
        data[device] = {
            "packets": packet_count,
            "rate_limit_status": rate_limit_status,
            "blocked_reason": blocked_reason
        }
    return json.dumps(data)

@app.route('/update', methods=['POST'])
def update_auth():
    device_id = request.form['device_id']
    action = request.form['action']
    authorized_devices[device_id] = (action == 'authorize')
    if action == 'revoke' and device_id in device_tokens:
        device_tokens.pop(device_id)
    return dashboard()

@app.route('/update_policy', methods=['POST'])
def update_policy():
    policy = request.form['policy']
    action = request.form['action']
    sdn_policies[policy] = (action == 'enable')
    policy_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {policy.replace('_', ' ').title()} policy {'enabled' if action == 'enable' else 'disabled'}")
    return dashboard()

@app.route('/get_topology')
def get_topology():
    return json.dumps(last_seen)

@app.route('/get_topology_with_mac')
def get_topology_with_mac():
    current_time = time.time()
    topology = {
        "nodes": [],
        "edges": []
    }
    
    # Add gateway node
    topology["nodes"].append({
        "id": "ESP32_Gateway",
        "label": "Gateway",
        "mac": mac_addresses["ESP32_Gateway"],
        "online": True,
        "last_seen": current_time,
        "packets": 0
    })
    
    # Add ESP32 device nodes and edges to gateway
    for device, last_seen_time in last_seen.items():
        online = (current_time - last_seen_time) < 10
        topology["nodes"].append({
            "id": device,
            "label": device,
            "mac": mac_addresses.get(device, "Unknown"),
            "online": online,
            "last_seen": last_seen_time,
            "packets": sum(device_data.get(device, []))
        })
        topology["edges"].append({
            "from": device,
            "to": "ESP32_Gateway"
        })
    
    return json.dumps(topology)

@app.route('/get_health_metrics')
def get_health_metrics():
    current_time = time.time()
    health_data = {}
    for device in device_data:
        online = (current_time - last_seen.get(device, 0)) < 10
        if online:
            health_data[device] = {
                "cpu_usage": random.randint(20, 80),
                "memory_usage": random.randint(30, 90),
                "uptime": int(current_time - last_seen.get(device, current_time))
            }
        else:
            health_data[device] = {
                "cpu_usage": 0,
                "memory_usage": 0,
                "uptime": 0
            }
    return json.dumps(health_data)

@app.route('/get_policy_logs')
def get_policy_logs():
    return json.dumps(policy_logs[-10:])  # Return last 10 logs

@app.route('/get_sdn_metrics')
def get_sdn_metrics():
    update_sdn_metrics()
    return json.dumps(sdn_metrics)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)