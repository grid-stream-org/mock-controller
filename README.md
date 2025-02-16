# <p align="center">Mock Controller - Simulator for Controller via MQTT</p>

<p align="center"><img src="assets/logo.svg" width="350px"/></p>
<p align="center">This Python script simulates a controller by generating mock data and publishing it to an MQTT broker. The data represents values that any connected DER would produce and transmit at 1 second intervals.</p>

## 🧭 Table of Contents

- [Mock Controller - Simulator for Controller via MQTT](#mock-controller---simulator-for-controller-via-mqtt)
  - [Table of Contents](#-table-of-contents)
  - [Team](#-team)
  - [Directory Structure](#-directory-structure)
  - [Features](#features)
  - [Data Format](#data-format)
  - [Contributing](#-contributing)
  - [Local Run](#-local-run)
    - [Prerequisites](#prerequisites)
    - [Steps](#steps)

## 👥 Team

| Team Member     | Role Title                | Description                                                                                                                                             |
| --------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Matthew Collett | Technical Lead/Developer  | Focus on architecture design and solving complex problems, with a focus on the micro-batching process.                                                  |
| Cooper Dickson  | Project Manager/Developer | Ensure that the scope and timeline are feasible and overview project status, focus on UI and real-time transmission.                                    |
| Eric Cuenat     | Scrum Master/Developer    | In charge of agile methods for the team such as organizing meetings, removing blockers, and team communication, focus on UI and web socket interaction. |
| Sam Keays       | Product Owner/Developer   | Manager of product backlog and updating board to reflect scope changes and requirements, focus on database operations and schema design.                |

## 🏗️ Directory Structure
- `assets/`
  - Static global assets like images
- `src/`
  - `simulate_data.py`
    - Python script to simulate mock controller data
- `.env.example`
  - Example .env format. Please reach out to team for credentials
- `.gitignore`
  - Files or directories that git ignores
- `CONTRIBUTING.md`
  - Document outlining contribution guidelines
- `Makefile`
  - Makefile for this project
- `README.md`
  - This :-)
- `requirements.txt`
  - Dependencies for this project

## Features

- Publishes data to a HiveMQ MQTT broker at 1 second intervals
- Publishes DER data between 1 and 5 times to simulate multiple connected DERs

## Data Format 

```json
{
  "der_id": "DER_123456",
  "is_online": true,
  "timestamp": "2024-02-16T14:30:25.123Z",
  "current_output": 45.67,
  "power_meter_measurement": 46.12,
  "baseline": 50.00,
  "contract_threshold": 75.00,
  "units": "kW",
  "project_id": "PRJ_789012",
  "is_standalone": false,
  "connection_start_at": "2024-10-10T01:27:09.057Z",
  "current_soc": 85.5,
  "type": "battery_storage",
  "nameplate_capacity": 100.00
}
```

## ⛑️ Contributing

For guidlines and instructions on contributing, please refer to [CONTRIBUTING.md](https://github.com/grid-stream-org/mock-controller/blob/main/CONTRIBUTING.md)

## 🚀 Local Run

### Prerequisites
- Ensure you have python and pip installed
- Create a local `.env` file, and ensure it is populated with the correct credentials
```bash
cp .env.example .env
```

### Steps
1. First, start by cloning this repository to your local machine
```bash
git clone https://github.com/grid-stream-org/mock-controller.git
```
2. Run 
```bash
make run
```





