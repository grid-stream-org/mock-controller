"""
New Brunswick Energy IoT Data Simulator
---------------------------------------
Author: Claude (Anthropic)
Date: March 2025
Description: Generates realistic energy consumption and production data for DERs in New Brunswick, 
             Canada with specific focus on March conditions. Includes support for simulating 
             contract validation violations.
"""
from random import randint, uniform, random, gauss
import datetime
import os
import time
import paho.mqtt.client as mqtt
import json
import threading
import collections
import argparse
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv('URL')
PORT = int(os.getenv('PORT'))
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')

# Parse command line arguments
parser = argparse.ArgumentParser(
    description='IoT Data Simulator with Contract Violation')
parser.add_argument('--violation', action='store_true',
                    help='Enable contract violation mode')
parser.add_argument('--multiplier', type=float, default=1.5,
                    help='Violation intensity multiplier (default: 1.5)')
parser.add_argument('--max-messages', type=int, default=0,
                    help='Maximum number of messages to send (0 for unlimited)')
args = parser.parse_args()

# Configuration
MAX_MESSAGES = args.max_messages

# Violation settings from command line
VIOLATION_MODE = {
    'enabled': args.violation,
    'multiplier': args.multiplier
}

# Shared message counting
total_messages = 0
messages_lock = threading.Lock()

# Track 5-minute window data for validation calculations
readings_history = {}  # Store readings by project_id to calculate 5-min averages

# Using original project IDs and comments, with NB-appropriate values
CONTROLLERS = [
    # matthew.collett12@gmail.com
    {
        'project_id': '492e323a-b7c5-48ff-bcf7-36ffd170f409',
        'utility_id': 'utility1234',
        # kW - typical New Brunswick home baseline (16-20kW peak periods)
        'baseline': 18,
        'contract_threshold': 15,  # 83% of baseline, typical NB Power DR program
        'location': 'Fredericton',
        'ders': [
            {'der_id': '11', 'type': 'battery',
                'nameplate_capacity': 10},  # Typical home battery
            # ~8kW residential solar
            {'der_id': '12', 'type': 'solar', 'nameplate_capacity': 8},
            {'der_id': '13', 'type': 'battery',
                'nameplate_capacity': 5}    # Secondary battery
        ]
    },
    # test@test.com
    {
        'project_id': '0b2a26cc-3573-40d6-a685-a025920bc700',
        'utility_id': 'utility1234',
        'baseline': 35,  # kW - small business consumption
        'contract_threshold': 29,  # ~83% of baseline
        'location': 'Saint John',
        'ders': [
            {'der_id': '14', 'type': 'battery',
                'nameplate_capacity': 20},  # Commercial battery
            {'der_id': '15', 'type': 'solar',
                'nameplate_capacity': 15},    # Commercial solar
        ]
    },
    # ericcuenat@gmail.com
    {
        'project_id': '8b434748-ff61-4e0f-9f24-654c3abf81fb',
        'utility_id': 'utility1234',
        'baseline': 22,  # kW - larger home with electric heating
        'contract_threshold': 18,  # ~82% of baseline
        'location': 'Moncton',
        'ders': [
            {'der_id': '16', 'type': 'solar',
                'nameplate_capacity': 10},    # Residential solar
            {'der_id': '17', 'type': 'ev',
                'nameplate_capacity': 11},       # EV charger
        ]
    }
]

# Initialize tracking data structures
for controller in CONTROLLERS:
    project_id = controller['project_id']
    readings_history[project_id] = collections.deque(
        maxlen=300)  # Store 5 minutes of readings at 1/sec

# Cache for weather patterns, appliance events, and other "slow changing" factors
weather_cache = {}
appliance_events = {}
last_appliance_check = {}
consumption_trends = {}

# Initialize caches for each controller
for controller in CONTROLLERS:
    project_id = controller['project_id']
    weather_cache[project_id] = {'last_update': None, 'pattern': 1.0}
    appliance_events[project_id] = {
        'active': False, 'end_time': None, 'magnitude': 1.0}
    last_appliance_check[project_id] = datetime.datetime.now()
    consumption_trends[project_id] = {
        'trend': 1.0, 'next_change': datetime.datetime.now()}


def get_nb_seasonal_factors(location='Fredericton'):
    """Get realistic time-of-day factors for New Brunswick in March"""
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute
    day_of_week = now.weekday()  # 0=Monday, 6=Sunday
    is_weekend = day_of_week >= 5

    # Realistic hourly factors for home energy use in NB during March
    # Morning peak (heating + activities), evening peak (heating, cooking, lights)
    # Values based on NB Power load curve data, adjusted for March
    base_hourly_factors = {
        0: 0.65, 1: 0.55, 2: 0.50, 3: 0.45, 4: 0.50, 5: 0.70,  # overnight to early morning
        6: 0.85, 7: 1.10, 8: 1.20, 9: 1.05, 10: 0.85, 11: 0.80,  # morning peak to mid-day
        12: 0.75, 13: 0.70, 14: 0.65, 15: 0.70, 16: 0.85, 17: 1.05,  # mid-day to evening
        18: 1.20, 19: 1.15, 20: 1.00, 21: 0.90, 22: 0.80, 23: 0.70   # evening peak to night
    }

    # Weekend adjustments - flatter morning peak, higher mid-day
    if is_weekend:
        weekend_adjustments = {
            # Later and smaller morning peak on weekends
            6: 0.70, 7: 0.80, 8: 0.90, 9: 1.00, 10: 1.05,
            # Higher and more sustained mid-day usage
            11: 0.95, 12: 0.90, 13: 0.85, 14: 0.80, 15: 0.85, 16: 0.95
        }
        # Apply weekend adjustments
        for h, factor in weekend_adjustments.items():
            if h in base_hourly_factors:
                base_hourly_factors[h] = factor

    # Location-specific adjustments (minor regional differences)
    location_factors = {
        'Fredericton': 1.0,     # Base reference
        'Saint John': 1.02,     # Slightly higher due to industrial area
        'Moncton': 0.98,        # Slightly lower
    }

    location_factor = location_factors.get(location, 1.0)

    # Get current hour's factor with location adjustment
    hour_factor = base_hourly_factors.get(hour, 0.75) * location_factor

    # Account for gradual transitions between hours
    if minute < 15 and hour > 0:  # First 15 minutes of hour - blend with previous hour
        prev_hour = hour - 1
        prev_factor = base_hourly_factors.get(
            prev_hour, 0.75) * location_factor
        blend_ratio = (15 - minute) / 15
        hour_factor = hour_factor * \
            (1 - blend_ratio) + prev_factor * blend_ratio
    elif minute > 45:  # Last 15 minutes of hour - blend with next hour
        next_hour = (hour + 1) % 24
        next_factor = base_hourly_factors.get(
            next_hour, 0.75) * location_factor
        blend_ratio = (minute - 45) / 15
        hour_factor = hour_factor * \
            (1 - blend_ratio) + next_factor * blend_ratio

    # Solar factors for March in New Brunswick (adjusted for latitude ~46°N)
    # Data from NB Power solar resource assessment - March averages
    base_solar_factors = {
        0: 0.00, 1: 0.00, 2: 0.00, 3: 0.00, 4: 0.00, 5: 0.00,  # No generation overnight
        6: 0.02, 7: 0.15, 8: 0.30, 9: 0.45, 10: 0.60, 11: 0.70,  # Morning ramp
        # Peak and afternoon decline
        12: 0.75, 13: 0.75, 14: 0.65, 15: 0.50, 16: 0.35, 17: 0.15,
        # No generation after sunset
        18: 0.02, 19: 0.00, 20: 0.00, 21: 0.00, 22: 0.00, 23: 0.00
    }

    # Get current solar factor with minute-based gradual transition
    solar_factor = base_solar_factors.get(hour, 0)
    if minute < 20 and hour > 0 and solar_factor > 0:
        prev_factor = base_solar_factors.get(hour - 1, 0)
        blend_ratio = (20 - minute) / 20
        solar_factor = solar_factor * \
            (1 - blend_ratio) + prev_factor * blend_ratio
    elif minute > 40 and solar_factor > 0:
        next_hour = (hour + 1) % 24
        next_factor = base_solar_factors.get(next_hour, 0)
        blend_ratio = (minute - 40) / 20
        solar_factor = solar_factor * \
            (1 - blend_ratio) + next_factor * blend_ratio

    # March in NB has variable cloud cover - apply a daily weather pattern
    # This will be further modified by the weather_cache in the solar function
    day_seed = now.day + now.month * 31
    base_weather_factor = ((day_seed * 9973) % 1000) / 1000.0  # 0-1 range
    daily_weather = 0.7 + base_weather_factor * 0.6  # 0.7-1.3 range

    # EV charging likelihood by hour for New Brunswick (based on survey data)
    ev_connection_factors = {
        0: 0.85, 1: 0.90, 2: 0.90, 3: 0.90, 4: 0.80, 5: 0.70,  # High overnight
        # Lower during commute & morning
        6: 0.50, 7: 0.30, 8: 0.20, 9: 0.30, 10: 0.35, 11: 0.35,
        12: 0.30, 13: 0.30, 14: 0.35, 15: 0.35, 16: 0.30, 17: 0.25,  # Workplace and errands
        18: 0.30, 19: 0.45, 20: 0.60, 21: 0.75, 22: 0.80, 23: 0.85   # Increasing at home
    }

    # Weekend pattern for EV is different
    if is_weekend:
        weekend_ev_adjustments = {
            # More home charging during day on weekends
            9: 0.40, 10: 0.45, 11: 0.45, 12: 0.40, 13: 0.40, 14: 0.45,
            15: 0.45, 16: 0.40
        }
        for h, factor in weekend_ev_adjustments.items():
            if h in ev_connection_factors:
                ev_connection_factors[h] = factor

    # Battery factors - when batteries typically discharge in NB homes
    # Higher during peak demand periods, lower during solar production
    battery_discharge_factors = {
        0: 0.15, 1: 0.10, 2: 0.05, 3: 0.05, 4: 0.10, 5: 0.20,  # Low overnight
        # High morning peak then drop
        6: 0.40, 7: 0.55, 8: 0.50, 9: 0.30, 10: 0.15, 11: 0.10,
        # Low mid-day, rising evening
        12: 0.05, 13: 0.05, 14: 0.10, 15: 0.20, 16: 0.35, 17: 0.60,
        # High evening peak, then declining
        18: 0.70, 19: 0.65, 20: 0.45, 21: 0.35, 22: 0.25, 23: 0.20
    }

    return {
        'usage': hour_factor,  # Overall electricity usage factor
        'solar': solar_factor * daily_weather,  # Solar generation potential
        'ev': ev_connection_factors.get(hour, 0.5),  # EV connection likelihood
        # Battery discharge factor
        'battery': battery_discharge_factors.get(hour, 0.2),
        'time_of_day': hour + minute/60.0,  # Decimal time of day for gradual calculations
        'is_weekend': is_weekend,  # Flag for weekend
    }


def update_weather_pattern(project_id):
    """Update weather pattern for a location - changes periodically to simulate cloud cover"""
    now = datetime.datetime.now()
    cache = weather_cache[project_id]

    # Update weather every 5-15 minutes (simulates changing cloud patterns)
    if cache['last_update'] is None or (now - cache['last_update']).total_seconds() > randint(300, 900):
        # Create new weather pattern - weighted toward middle values
        # Mean of 1.0, with SD of 0.2 gives typical values between 0.6-1.4
        new_pattern = min(1.5, max(0.6, gauss(1.0, 0.2)))

        # Gradual transition if previous pattern exists
        if cache['last_update'] is not None:
            # Blend based on time since last major change
            seconds_since = (now - cache['last_update']).total_seconds()
            # Transition over 3 minutes
            blend_ratio = min(1.0, seconds_since / 180)
            cache['pattern'] = cache['pattern'] * \
                (1-blend_ratio) + new_pattern * blend_ratio
        else:
            cache['pattern'] = new_pattern

        cache['last_update'] = now

    # Add minor fluctuations each time (small second-to-second variations)
    minor_fluctuation = 0.98 + random() * 0.04  # 0.98-1.02 small variations

    return cache['pattern'] * minor_fluctuation


def check_appliance_events(project_id):
    """Simulate random energy events like appliances turning on/off"""
    now = datetime.datetime.now()
    event = appliance_events[project_id]

    # Only check for new events every 30-60 seconds to avoid too much checking
    if (now - last_appliance_check[project_id]).total_seconds() < 30:
        # Return current event state without checking for new one
        return event['magnitude'] if event['active'] and event['end_time'] > now else 1.0

    # Update check time
    last_appliance_check[project_id] = now

    # If an active event has ended, clear it
    if event['active'] and event['end_time'] < now:
        event['active'] = False

    # Chance of a new event starting (about 15% chance every minute)
    if not event['active'] and random() < 0.15:
        # Event duration between 1-5 minutes
        duration_seconds = randint(60, 300)

        # Event magnitude - most common is 1.1-1.3 (small appliance)
        # Occasionally 1.4-1.8 (major appliance like dryer, oven)
        # Rarely 1.8-2.5 (multiple appliances or electric vehicle charging)
        r = random()
        if r < 0.7:  # 70% chance of small event
            magnitude = uniform(1.1, 1.3)
        elif r < 0.95:  # 25% chance of medium event
            magnitude = uniform(1.4, 1.8)
        else:  # 5% chance of large event
            magnitude = uniform(1.8, 2.5)

        # Set event
        event['active'] = True
        event['end_time'] = now + datetime.timedelta(seconds=duration_seconds)
        event['magnitude'] = magnitude

    return event['magnitude'] if event['active'] else 1.0


def update_consumption_trend(project_id):
    """Update slow-changing consumption trend"""
    now = datetime.datetime.now()
    trend = consumption_trends[project_id]

    # Check if it's time for a trend change
    if now >= trend['next_change']:
        # Small trend changes every 10-30 minutes
        next_change_minutes = randint(10, 30)
        trend['next_change'] = now + \
            datetime.timedelta(minutes=next_change_minutes)

        # Gradual trend changes - target is 0.92-1.08 (±8% variation)
        new_target = uniform(0.92, 1.08)

        # Move 30% of the way to the new target (gradual shifts)
        trend['trend'] = trend['trend'] * 0.7 + new_target * 0.3

    return trend['trend']


def generate_solar_output(capacity, controller_index):
    """Generate realistic solar output for New Brunswick in March"""
    controller = CONTROLLERS[controller_index]
    project_id = controller['project_id']
    factors = get_nb_seasonal_factors(controller['location'])

    # No output during night hours
    if factors['solar'] <= 0:
        return 0

    # Get/update weather pattern (cloud cover)
    weather_factor = update_weather_pattern(project_id)

    # Calculate base output from capacity and time of day
    base_output = capacity * factors['solar']

    # Apply weather factor (clouds, etc)
    weather_adjusted = base_output * weather_factor

    # Add small noise variation to make the output more natural
    noise = 0.97 + (datetime.datetime.now().second % 6) / 100

    return round(max(0, weather_adjusted * noise), 2)


def generate_battery_output(capacity, current_soc, controller_index):
    """Generate realistic battery output based on NB patterns"""
    controller = CONTROLLERS[controller_index]
    project_id = controller['project_id']
    factors = get_nb_seasonal_factors(controller['location'])

    # Batteries should only discharge when SOC permits
    if current_soc < 10:  # Protection against deep discharge
        return 0

    # Base discharge rate from time-of-day factors
    base_discharge_rate = factors['battery']

    # Adjust for SOC - higher SOC = willing to discharge more
    soc_factor = 0.5 + (current_soc / 200)  # 0.55-0.95 range based on SOC

    # Adjust discharge for current home needs and SOC
    discharge_rate = base_discharge_rate * soc_factor

    # Add small variations
    minute_variation = 0.95 + (datetime.datetime.now().minute % 10) / 100

    output = capacity * discharge_rate * minute_variation

    # Cap output at 80% of capacity
    return round(min(output, capacity * 0.8), 2)


def generate_ev_output(capacity, controller_index):
    """Generate realistic EV output based on NB patterns"""
    controller = CONTROLLERS[controller_index]
    project_id = controller['project_id']
    factors = get_nb_seasonal_factors(controller['location'])

    # Determine if EV is connected based on time of day
    # Use a weighted random function that's consistent for short periods
    minute_of_day = int(factors['time_of_day'] * 60)
    rand_seed = minute_of_day + datetime.datetime.now().day * 1440
    rand_val = ((rand_seed * 9973) % 1000) / \
        1000.0  # Pseudo-random but consistent

    is_connected = rand_val < factors['ev']

    if not is_connected:
        return 0

    # When connected, V2G output depends on time of day
    if 7 <= datetime.datetime.now().hour <= 9 or 17 <= datetime.datetime.now().hour <= 20:
        # Higher output during peak hours (morning/evening)
        v2g_factor = 0.15 + (rand_val * 0.1)  # 15-25% of capacity
    else:
        # Lower output during off-peak hours
        v2g_factor = 0.05 + (rand_val * 0.05)  # 5-10% of capacity

    return round(capacity * v2g_factor, 2)


def calculate_power_meter(base_load, der_output, controller_index, apply_violation=False):
    """Calculate realistic power meter reading with appropriate variations"""
    controller = CONTROLLERS[controller_index]
    project_id = controller['project_id']
    factors = get_nb_seasonal_factors(controller['location'])

    # Apply time-of-day factor to base load
    adjusted_load = base_load * factors['usage']

    # Apply consumption trend (slow-changing factor)
    trend_factor = update_consumption_trend(project_id)
    adjusted_load *= trend_factor

    # Apply appliance events (occasional spikes)
    event_factor = check_appliance_events(project_id)
    adjusted_load *= event_factor

    # Add small noise variations
    now = datetime.datetime.now()
    noise_seed = now.second + now.minute * 60
    noise_factor = 0.98 + ((noise_seed * 3) % 5) / 100  # 0.98-1.02 range

    # Calculate final value (can't go below 0)
    # In violation mode, we reduce DER output to create higher net consumption
    if apply_violation:
        # When in violation mode, we want to reduce the apparent effectiveness of DERs
        # This will make (power_meter - der_output) higher, potentially exceeding threshold
        effective_der_output = der_output / VIOLATION_MODE['multiplier']
    else:
        effective_der_output = der_output

    return round(max(0, adjusted_load * noise_factor - effective_der_output), 2)


def generate_data(controller_index):
    """Generate realistic data for a controller"""
    controller = CONTROLLERS[controller_index]
    project_id = controller['project_id']
    data = []
    current_time = datetime.datetime.now(datetime.timezone.utc)

    # Determine if we should apply violation
    apply_violation = VIOLATION_MODE['enabled']

    # Total DER output for this controller
    total_der_output = 0

    for der in controller['ders']:
        # Generate realistic SOC for batteries
        if der['type'] == 'battery':
            # Create time-appropriate SOC
            hour = current_time.hour

            # SOC pattern follows daily cycle (higher in morning, lower in evening)
            # With consistent day-to-day values
            day_seed = current_time.day + current_time.month * 31
            der_seed = int(der['der_id'])

            # Base SOC changes throughout day
            if hour < 6:  # Late night/early morning
                base_soc = 65 + (hour * 3)  # Slowly charging overnight
            elif 6 <= hour < 9:  # Morning peak - discharging
                # Discharging during morning peak
                base_soc = 80 - ((hour - 6) * 6)
            elif 9 <= hour < 15:  # Mid-day - may be charging from solar
                # Slowly charging when solar available
                base_soc = 62 + ((hour - 9) * 3)
            elif 15 <= hour < 21:  # Evening peak - discharging
                # Faster discharge during evening peak
                base_soc = 80 - ((hour - 15) * 5)
            else:  # Late evening - starting to charge
                base_soc = 50 + ((hour - 21) * 3)  # Beginning to charge

            # Add controller-specific variation
            controller_offset = ((der_seed + day_seed) % 10) - 5  # -5 to +5

            # Add some smaller variation based on minute (continuous changes)
            minute_variation = ((current_time.minute / 60) * 6) - 3  # -3 to +3

            current_soc = max(
                10, min(95, base_soc + controller_offset + minute_variation))
        else:
            current_soc = 0

        # Generate appropriate output based on DER type
        if der['type'] == 'solar':
            current_output = generate_solar_output(
                der['nameplate_capacity'], controller_index)
        elif der['type'] == 'battery':
            current_output = generate_battery_output(
                der['nameplate_capacity'], current_soc, controller_index)
        else:  # ev
            current_output = generate_ev_output(
                der['nameplate_capacity'], controller_index)

        # For display purposes (unchanged, actual output)
        original_current_output = current_output
        total_der_output += current_output

        # Calculate actual grid consumption with realistic variations
        base_load = controller['baseline']  # Use baseline from controller

        # For violation mode, we apply different logic in the power_meter calculation
        power_meter = calculate_power_meter(
            base_load, current_output, controller_index, apply_violation)

        der_data = {
            "der_id": der['der_id'],
            "is_online": True,
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            # Always show real output
            "current_output": round(original_current_output, 2),
            "power_meter_measurement": round(power_meter, 2),
            "baseline": controller['baseline'],
            "contract_threshold": controller['contract_threshold'],
            "units": "kW",
            "project_id": controller['project_id'],
            "is_standalone": False,
            "connection_start_at": "2024-10-10T01:27:09.057Z",
            "current_soc": round(current_soc),
            "type": der['type'],
            "nameplate_capacity": der['nameplate_capacity']
        }
        data.append(der_data)

    # Calculate net consumption using the formula:
    # Net = Power Meter Measurement - DER Output
    net_consumption = sum(
        [item["power_meter_measurement"] - item["current_output"] for item in data])

    # Track this reading in the 5-minute history
    readings_history[controller['project_id']].append(
        (current_time, net_consumption))

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

            # Realistic sleep time
            sleep_time = randint(1, 5)
            time.sleep(sleep_time)

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
