from random import uniform, randint
import datetime
import os
import time
import paho.mqtt.client as mqtt
import json
import threading
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv('URL')
PORT = int(os.getenv('PORT'))
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')

# Configuration
MAX_MESSAGES = 0  # 0 for unlimited, or set a number

# Shared message counting
total_messages = 0
messages_lock = threading.Lock()

# Mode switching every 60 seconds
last_switch_time = datetime.datetime.now()
is_violation_mode = False
SWITCH_INTERVAL = 120  # seconds

# Value tracking for smooth transitions
current_values = {
    'power_meter': 18.0,  # Start close to baseline
    'last_update': datetime.datetime.now()
}

CONTROLLERS = [
    {
        'project_id': '492e323a-b7c5-48ff-bcf7-36ffd170f409',
        'utility_id': 'utility1234',
        'baseline': 18,     # kW - NB home with electric heat
        'contract_threshold': 10,  # kW - Threshold
        'ders': [
            {'der_id': '11', 'type': 'battery', 'nameplate_capacity': 10},
            {'der_id': '12', 'type': 'solar', 'nameplate_capacity': 8},
            {'der_id': '13', 'type': 'battery', 'nameplate_capacity': 5}
        ]
    }
]


def check_mode():
    """Check if it's time to switch modes"""
    global last_switch_time, is_violation_mode

    now = datetime.datetime.now()
    if (now - last_switch_time).total_seconds() >= SWITCH_INTERVAL:
        is_violation_mode = not is_violation_mode
        last_switch_time = now
        print(
            f"\n--- Switching to {'VIOLATION' if is_violation_mode else 'NON-VIOLATION'} mode ---\n")

    return is_violation_mode


def get_smooth_transition(current, target):
    """Transition values smoothly without spikes"""
    # Move 15% of the way to target each time
    return current + (target - current) * 0.15


def generate_data(controller_index):
    """Generate data with proper energy reduction calculation"""
    controller = CONTROLLERS[controller_index]
    baseline = controller['baseline']
    contract = controller['contract_threshold']
    data = []
    current_time = datetime.datetime.now(datetime.timezone.utc)

    # Check mode
    is_violation = check_mode()

    # Get current power meter value
    current_power = current_values.get('power_meter', baseline)

    # Target power meter value (close to baseline with small variation)
    target_power = baseline * uniform(0.80, 1)

    # Smooth transition for power meter
    power_meter = get_smooth_transition(current_power, target_power)

    # Store updated value
    current_values['power_meter'] = power_meter
    current_values['last_update'] = datetime.datetime.now()

    # Total DER output
    total_der_output = 0

    # Calculate what DER output should be to achieve desired reduction based on mode
    if is_violation:
        # In violation: reduction < contract threshold
        target_reduction = contract * uniform(0.7, 0.9)  # 70-90% of threshold
    else:
        # Normal: reduction > contract threshold
        target_reduction = contract * \
            uniform(1.1, 1.3)  # 110-130% of threshold

    # Using the formula: reduction = baseline - (power_meter - total_der_output)
    # Rearrange to: total_der_output = power_meter - (baseline - reduction)
    required_der_output = power_meter - (baseline - target_reduction)

    # Generate DER data
    for der in controller['ders']:
        # Generate SOC for batteries
        current_soc = uniform(40, 70) if der['type'] == 'battery' else 0

        # Base DER output on total required output, distributed proportionally by capacity
        capacity_ratio = der['nameplate_capacity'] / \
            sum(d['nameplate_capacity'] for d in controller['ders'])
        current_output = required_der_output * capacity_ratio * \
            uniform(0.95, 1.05)  # Small variation

        # Ensure reasonable bounds (0-80% of capacity)
        current_output = max(
            0, min(current_output, der['nameplate_capacity'] * 0.8))

        total_der_output += current_output

        # Add to data
        der_data = {
            "der_id": der['der_id'],
            "is_online": True,
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "current_output": round(current_output, 2),
            "power_meter_measurement": round(power_meter, 2),
            "current_soc": round(current_soc),
            "type": der['type'],
            "nameplate_capacity": der['nameplate_capacity'],
            "baseline": baseline,
            "contract_threshold": contract,
            "units": "kW",
            "project_id": controller['project_id'],
            "is_standalone": False,
            "connection_start_at": "2024-10-10T01:27:09.057Z",
        }
        data.append(der_data)

    # Calculate actual results
    consumption = power_meter - total_der_output
    reduction = baseline - consumption

    return data, reduction, consumption, power_meter, total_der_output


def should_continue(stop_event):
    global total_messages
    with messages_lock:
        if MAX_MESSAGES > 0 and total_messages >= MAX_MESSAGES:
            return False
    return not stop_event.is_set()


def run_controller(controller_index, stop_event):
    controller = CONTROLLERS[controller_index]
    client = mqtt.Client(client_id=f"controller-{controller['project_id']}")
    client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
    client.username_pw_set(USERNAME, PASSWORD)

    if client.connect(URL, PORT) != 0:
        print(f"Controller {controller['project_id']} failed to connect")
        return

    client.loop_start()
    print(f"Controller {controller['project_id']} connected")

    try:
        while should_continue(stop_event):
            data, reduction, consumption, power_meter, der_output = generate_data(
                controller_index)
            payload = json.dumps(data, indent=4)
            topic = f"projects/{controller['project_id']}"

            if client.publish(topic, payload=payload, qos=0).rc == 0:
                with messages_lock:
                    global total_messages
                    total_messages += 1
                    progress = f"({total_messages}/{MAX_MESSAGES})" if MAX_MESSAGES > 0 else total_messages

                    threshold = controller['contract_threshold']
                    status = "VIOLATION" if reduction < threshold else "COMPLIANT"

                    print(f"Meter: {power_meter:.2f} kW, DERs: {der_output:.2f} kW, "
                          f"Consumption: {consumption:.2f} kW, Reduction: {reduction:.2f} kW, "
                          f"Threshold: {threshold} kW - {status} [Msgs: {progress}]")

            # Sleep 1 second between publications
            time.sleep(randint(1, 3))

    except Exception as e:
        print(f"Error: {e}")
    finally:
        print(f"Controller disconnecting...")
        client.loop_stop()
        client.disconnect()


def main():
    stop_event = threading.Event()
    threads = []

    print(f"\nStarting Corrected NB Energy IoT Simulator:")
    print(f"Auto-switching every {SWITCH_INTERVAL} seconds")
    print(
        f"Current mode: {'VIOLATION' if is_violation_mode else 'NON-VIOLATION'}\n")

    for i in range(len(CONTROLLERS)):
        thread = threading.Thread(
            target=run_controller,
            args=(i, stop_event),
            daemon=True
        )
        thread.start()
        threads.append(thread)

    try:
        # Run until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        stop_event.set()

    for thread in threads:
        thread.join(timeout=5)
    print("All controllers shut down")


if __name__ == "__main__":
    main()
