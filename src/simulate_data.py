from random import randrange
import datetime
import os
import time
import paho.mqtt.client as mqtt
import json
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv('URL')
PORT = int(os.getenv('PORT'))
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')


def generate_data():
    data = []
    for i in range(randrange(1, 5)):
        der = {
            "derId": "12",
            "type": "solar",
            "isOnline": True,
            "Timestamp": datetime.datetime.now().isoformat(),
            "currentOutput": 7,
            "units": "kW",
            "projectId": "adsf1234dfgr1234",
            "utilityId": "utility1234",
            "isStandalone": False,
            "connectionStartAt": "",
            "currentSoc": 0
        }
        data.append(der)
    return data


def create_client(username, password):
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id="gridstream")
    client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
    client.user_data_set([])
    client.username_pw_set(username, password)
    return client


def connect(client):
    response = client.connect(URL, PORT)
    if response == 0:
        print("Connected to broker successfully")
    else:
        print(f"Failed to connect. Error code: {response}")


def publish(client, data):
    project_id = data[0]['projectId']
    payload = json.dumps(data, indent=4)
    response = client.publish(f"projects/{project_id}", payload=payload, qos=0)
    if response.rc == 0:
        print(f"Published to Topic: projects/{project_id}\n{payload}")
    else:
        print(f"Failed to publish message. Error: {response.rc}")


def main():
    client = create_client(USERNAME, PASSWORD)
    connect(client)

    client.loop_start()
    try:
        while True:
            data = generate_data()
            publish(client, data)
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nDisconnecting from broker...")
        client.loop_stop()
        client.disconnect()
        print("Disconnected successfully.")


if __name__ == "__main__":
    main()