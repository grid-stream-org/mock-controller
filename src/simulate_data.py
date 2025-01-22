from random import randint, randrange, choice
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
        'utility_id': 'utility1234'
    },
    {
        'project_id': 'proj5678dfgr5678',
        'utility_id': 'utility5678'
    },
    {
        'project_id': 'proj9012dfgr9012',
        'utility_id': 'utility9012'
    },
    {
        'project_id': 'ctrl3456dfgr3456',
        'utility_id': 'utility3456'
    },
    {
        'project_id': 'home7890dfgr7890',
        'utility_id': 'utility7890'
    },
    {
        'project_id': 'site2345dfgr2345',
        'utility_id': 'utility2345'
    },
    {
        'project_id': 'grid6789dfgr6789',
        'utility_id': 'utility6789'
    },
    {
        'project_id': 'node1357dfgr1357',
        'utility_id': 'utility1357'
    },
    {
        'project_id': 'unit2468dfgr2468',
        'utility_id': 'utility2468'
    },
    {
        'project_id': 'base9876dfgr9876',
        'utility_id': 'utility9876'
    }
]


def generate_data(controller_index):
    controller = CONTROLLERS[controller_index]
    data = []
    for _ in range(randint(1, 5)):
        der = {
            "der_id": str(randrange(10, 100)),
            "is_online": True,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "current_output": randrange(1, 100),
            "contract_threshold": randrange(1, 100),
            "power_meter_measurement": randrange(1, 100),
            "units": "kW",
            "project_id": controller['project_id'],
            "isStandalone": choice([True, False]),
            "connection_start_at": "2024-10-10T01:27:09.057Z",
            "current_soc": randrange(0, 101) if choice(['solar', 'battery', 'ev']) == "battery" else 0
        }
        data.append(der)
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
            topic = f"projects/{controller['project_id']}/data"

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
