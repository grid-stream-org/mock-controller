from random import randint, randrange, uniform, random
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
MAX_MESSAGES = 1000  # 0 for unlimited, or set a number

# Shared message counting
total_messages = 0
messages_lock = threading.Lock()

CONTROLLERS = [
    {
        'project_id': 'adsf1234dfgr1234',
        'utility_id': 'utility1234',
        'baseline': 150,
        'contract_threshold': 120,
        'ders': [
            {'der_id': '11', 'type': 'battery', 'capacity': 50},
            {'der_id': '12', 'type': 'solar', 'capacity': 75},
            {'der_id': '13', 'type': 'battery', 'capacity': 25}
        ]
    },
    {
        'project_id': 'proj5678dfgr5678',
        'utility_id': 'utility5678',
        'baseline': 180,
        'contract_threshold': 150,
        'ders': [
            {'der_id': '21', 'type': 'solar', 'capacity': 100},
            {'der_id': '22', 'type': 'battery', 'capacity': 80}
        ]
    },
    {
        'project_id': 'proj9012dfgr9012',
        'utility_id': 'utility9012',
        'baseline': 200,
        'contract_threshold': 170,
        'ders': [
            {'der_id': '31', 'type': 'solar', 'capacity': 150},
            {'der_id': '32', 'type': 'battery', 'capacity': 50},
            {'der_id': '33', 'type': 'ev', 'capacity': 75},
            {'der_id': '34', 'type': 'solar', 'capacity': 100}
        ]
    },
    {
        'project_id': 'ctrl3456dfgr3456',
        'utility_id': 'utility3456',
        'baseline': 300,
        'contract_threshold': 250,
        'ders': [
            {'der_id': '41', 'type': 'solar', 'capacity': 200},
            {'der_id': '42', 'type': 'solar', 'capacity': 150},
            {'der_id': '43', 'type': 'battery', 'capacity': 100},
            {'der_id': '44', 'type': 'battery', 'capacity': 100},
            {'der_id': '45', 'type': 'ev', 'capacity': 50}
        ]
    },
    {
        'project_id': 'home7890dfgr7890',
        'utility_id': 'utility7890',
        'baseline': 90,
        'contract_threshold': 75,
        'ders': [
            {'der_id': '51', 'type': 'solar', 'capacity': 50},
            {'der_id': '52', 'type': 'battery', 'capacity': 30},
            {'der_id': '53', 'type': 'ev', 'capacity': 40}
        ]
    },
    {
        'project_id': 'site2345dfgr2345',
        'utility_id': 'utility2345',
        'baseline': 250,
        'contract_threshold': 200,
        'ders': [
            {'der_id': '61', 'type': 'solar', 'capacity': 175},
            {'der_id': '62', 'type': 'solar', 'capacity': 125},
            {'der_id': '63', 'type': 'battery', 'capacity': 80}
        ]
    },
    {
        'project_id': 'grid6789dfgr6789',
        'utility_id': 'utility6789',
        'baseline': 400,
        'contract_threshold': 350,
        'ders': [
            {'der_id': '71', 'type': 'solar', 'capacity': 250},
            {'der_id': '72', 'type': 'solar', 'capacity': 200},
            {'der_id': '73', 'type': 'battery', 'capacity': 150},
            {'der_id': '74', 'type': 'battery', 'capacity': 100},
            {'der_id': '75', 'type': 'ev', 'capacity': 75},
            {'der_id': '76', 'type': 'ev', 'capacity': 75}
        ]
    },
    {
        'project_id': 'node1357dfgr1357',
        'utility_id': 'utility1357',
        'baseline': 140,
        'contract_threshold': 110,
        'ders': [
            {'der_id': '81', 'type': 'solar', 'capacity': 80},
            {'der_id': '82', 'type': 'battery', 'capacity': 60}
        ]
    },
    {
        'project_id': 'unit2468dfgr2468',
        'utility_id': 'utility2468',
        'baseline': 220,
        'contract_threshold': 180,
        'ders': [
            {'der_id': '91', 'type': 'solar', 'capacity': 120},
            {'der_id': '92', 'type': 'solar', 'capacity': 100},
            {'der_id': '93', 'type': 'battery', 'capacity': 75},
            {'der_id': '94', 'type': 'ev', 'capacity': 50}
        ]
    },
    {
        'project_id': 'base9876dfgr9876',
        'utility_id': 'utility9876',
        'baseline': 160,
        'contract_threshold': 130,
        'ders': [
            {'der_id': '101', 'type': 'solar', 'capacity': 100},
            {'der_id': '102', 'type': 'battery', 'capacity': 60},
            {'der_id': '103', 'type': 'ev', 'capacity': 40}
        ]
    }
]


def generate_solar_output(capacity, time_of_day=None):
    # Simulate solar output based on time of day
    if not time_of_day:
        time_of_day = datetime.datetime.now().hour

    # Peak hours are between 10 AM and 4 PM
    if 10 <= time_of_day <= 16:
        return uniform(capacity * 0.6, capacity * 0.9)
    elif 6 <= time_of_day <= 9 or 17 <= time_of_day <= 19:
        return uniform(capacity * 0.2, capacity * 0.5)
    else:
        return 0


def generate_battery_output(capacity, current_soc):
    # Batteries can discharge at different rates based on SOC
    if current_soc > 80:
        return uniform(capacity * 0.7, capacity * 0.9)
    elif current_soc > 20:
        return uniform(capacity * 0.4, capacity * 0.7)
    else:
        return uniform(capacity * 0.1, capacity * 0.3)


def generate_ev_output(capacity):
    # EVs are typically either charging (negative output) or providing power
    if random() < 0.7:  # 70% chance of charging
        return -uniform(capacity * 0.1, capacity * 0.3)
    else:
        return uniform(capacity * 0.1, capacity * 0.4)


def generate_data(controller_index):
    controller = CONTROLLERS[controller_index]
    data = []

    for der in controller['ders']:
        current_soc = randrange(0, 101) if der['type'] == 'battery' else 0

        if der['type'] == 'solar':
            current_output = generate_solar_output(der['capacity'])
        elif der['type'] == 'battery':
            current_output = generate_battery_output(
                der['capacity'], current_soc)
        else:  # ev
            current_output = generate_ev_output(der['capacity'])

        power_meter = max(0, current_output + uniform(-5, 5))  # Add some noise

        der_data = {
            "der_id": der['der_id'],
            "is_online": True,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "current_output": round(current_output, 2),
            "power_meter_measurement": round(power_meter, 2),
            "baseline": controller['baseline'],
            "contract_threshold": controller['contract_threshold'],
            "units": "kW",
            "project_id": controller['project_id'],
            "is_standalone": False,  # Most DERs in a project aren't standalone
            "connection_start_at": "2024-10-10T01:27:09.057Z",
            "current_soc": current_soc,
            "der_type": der['type'],
            "capacity": der['capacity']
        }
        data.append(der_data)

    return data


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
            data = generate_data(controller_index)
            payload = json.dumps(data, indent=4)
            topic = f"projects/{controller['project_id']}"

            if client.publish(topic, payload=payload, qos=0).rc == 0:
                with messages_lock:
                    global total_messages
                    total_messages += 1
                    progress = f"({total_messages}/{MAX_MESSAGES})" if MAX_MESSAGES > 0 else total_messages
                    print(
                        f"Project {controller['project_id']} published {len(data)} DERs [Total messages: {progress}]")

            time.sleep(randint(1, 5))

    except Exception as e:
        print(f"Controller {controller['project_id']} error: {e}")
    finally:
        print(f"Controller {controller['project_id']} disconnecting...")
        client.loop_stop()
        client.disconnect()


def main():
    stop_event = threading.Event()
    threads = []

    print(f"\nStarting with:")
    print(
        f"Max messages: {'unlimited' if MAX_MESSAGES == 0 else MAX_MESSAGES}")
    print(f"Number of controllers: {len(CONTROLLERS)}\n")

    for i in range(len(CONTROLLERS)):
        thread = threading.Thread(
            target=run_controller,
            args=(i, stop_event),
            daemon=True
        )
        thread.start()
        threads.append(thread)

    try:
        # If we have a message limit, wait for completion
        if MAX_MESSAGES > 0:
            while total_messages < MAX_MESSAGES:
                time.sleep(0.1)
            stop_event.set()
        else:
            # For unlimited messages, run until interrupted
            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down controllers...")
        stop_event.set()

    for thread in threads:
        thread.join(timeout=5)
    print("All controllers shut down")


if __name__ == "__main__":
    main()
