# New Brunswick Energy Data Generation

## Overview

This document describes the methodology used to generate mock energy data for distributed energy resources (DERs) in New Brunswick, Canada. The data simulates realistic energy patterns specifically calibrated for March conditions.

## Energy Components

### Solar Generation

Solar output is generated based on New Brunswick's March conditions:

- Daylight hours follow New Brunswick's March pattern (approximately 7 AM to 6 PM)
- Peak production occurs around 12:30 PM, reaching 75% of capacity in optimal conditions
- March solar generation is modeled at 60% of summer potential due to seasonal angle and intensity
- Cloud cover dynamically changes every 5-15 minutes with gradual transitions
- Generation follows a bell curve with gradual transitions between hours

The formula used:
```
solar_output = capacity × time_of_day_factor × seasonal_factor × weather_factor × small_variations
```

### Battery Systems

Battery behavior follows daily discharge/charge cycles:

- State of Charge (SOC) follows a predictable pattern:
  - Higher in morning (70-90%)
  - Depleting during morning peak hours (6-9 AM)
  - Potentially charging during solar production hours
  - Higher discharge during evening peak (5-8 PM)
  - SOC never drops below 10% (deep discharge protection)

Discharge rate is calculated based on time of day and current SOC:
```
battery_output = capacity × time_of_day_factor × soc_factor × minute_variation
```

### Electric Vehicles

EV interaction with the grid (V2G) is modeled with:

- Connection probability varies by hour (70-90% overnight, 20-30% during commute hours)
- Different patterns between weekdays and weekends
- V2G output is higher during peak demand periods (15-25% of capacity)
- V2G output is lower during off-peak hours (5-10% of capacity)

### Power Meter Readings

Power meter readings represent grid consumption after DER contribution:

- Base load is adjusted for time of day (morning/evening peaks)
- Regional variations between Fredericton, Saint John, and Moncton
- Weather impacts, appliance events, and consumption trends are incorporated

## Natural Variations

Several mechanisms create realistic variability:

### Weather Patterns
- Cloud cover simulation affects solar output
- Changes every 5-15 minutes using Gaussian distribution (mean 1.0, SD 0.2)
- Transitions gradually to simulate natural cloud movement

### Appliance Events
- Random energy-consuming events with different magnitudes:
  - Small events (1.1-1.3× multiplier): 70% probability
  - Medium events (1.4-1.8× multiplier): 25% probability
  - Large events (1.8-2.5× multiplier): 5% probability
- Events last 1-5 minutes
- Simulate real-world occurrences like appliances turning on

### Consumption Trends
- Slow-changing factors that shift every 10-30 minutes
- Small variations (±8%) representing ambient temperature changes
- Creates natural drift in baseline consumption

### Time-Based Patterns
- Morning peak (6-9 AM): Higher consumption for heating and morning routines
- Mid-day reduction (10 AM-3 PM): Lower consumption during typical work hours
- Evening peak (5-8 PM): Highest consumption (cooking, heating, lighting)
- Night reduction (10 PM-5 AM): Minimal consumption
- Weekend patterns feature flatter mornings and higher mid-day usage

## Contract Validation

The contract validation model works as follows:

1. Net consumption is calculated: `Power Meter Measurement - DER Output`
2. This is tracked in a 5-minute rolling window
3. Reduction from baseline is calculated: `Baseline - Net Consumption`
4. A contract violation occurs when this reduction is less than the contractually agreed threshold

When simulating violations, the model reduces the effective DER output in power meter calculations, resulting in higher net consumption and therefore smaller reductions from baseline.

## Data Source

This data generation methodology was developed by Claude at Anthropic (March 2025) based on typical energy patterns for New Brunswick, Canada. The time-of-day factors, solar generation curves, and consumption patterns are derived from typical residential and small commercial energy profiles adjusted for New Brunswick's climate and latitude.