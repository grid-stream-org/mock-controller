# mock-controller - Simulator for Controller via MQTT

This Python script simulates a controller by generating mock data and publishing it to an MQTT broker. The data represents values that any connected DER would produce like current output and time and is transmitted at 1 second intervals.

## Features

- Publishes data to a HIVEMQ MQTT broker at 1 second intervals
- Publishes DER data between 1 and 5 times to simulate multiple connected DERs

## Data Format 

```json
{
    "derId": "12",
    "type": "solar",
    "isOnline": true,
    "Timestamp": "2024-10-23T11:51:39.233518",
    "currentOutput": 7,
    "units": "kW",
    "projectId": "project1234",
    "utilityId": "utility1234",
    "isStandalone": false,
    "currentSoc": 0
}


