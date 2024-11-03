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
2. Install the project dependencies
```bash
pip install -r requirements.txt
```
3. Navigate into the source directory
```bash
cd src
```
4. Run the python script
```
python simulate_data.py
```






