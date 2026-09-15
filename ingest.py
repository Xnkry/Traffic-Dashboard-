import time
from datetime import datetime, timezone
from re import L

import pandas as pd
import requests as rq

import Constants

API_KEY = Constants.TOMTOM_API
URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
LOCATIONS = [
    {"name": "Centre Ville", "lat": 33.5731, "lon": -7.5898},
    {"name": "Ain Diab", "lat": 33.5928, "lon": -7.6511},
    {"name": "Sidi Bernoussi", "lat": 33.6086, "lon": -7.5013},
]


def fetch_traffic(lat: float, lon: float) -> dict | None:
    """Call the TomTom API for one point. Returns the flowSegmentData dict, or None on failure."""
    params = {"point": f"{lat},{lon}", "key": API_KEY}
    try:
        resp = rq.get(URL, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()["flowSegmentData"]
    except rq.exceptions.RequestException as e:
        print(f"  [FAILED] {lat},{lon} -> {e}")
        return None


def collect_all_locations() -> pd.DataFrame:
    """Loop over every location, flatten each response into a row."""
    rows = []
    timestamp = datetime.now(timezone.utc)

    for loc in LOCATIONS:
        print(f"Fetching: {loc['name']} ({loc['lat']}, {loc['lon']})...")
        flow = fetch_traffic(loc["lat"], loc["lon"])

        if flow is None:
            continue

        current_speed = flow["currentSpeed"]
        free_flow_speed = flow["freeFlowSpeed"]
        rows.append(
            {
                "timestamp": timestamp,
                "location": loc["name"],
                "lat": loc["lat"],
                "lon": loc["lon"],
                "current_speed": current_speed,
                "free_flow_speed": free_flow_speed,
                "congestion_ratio": round(current_speed / free_flow_speed, 3),
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = collect_all_locations()

    print("\n--- Result ---")
    if df.empty:
        print("No data collected — check your API key or network connection.")
    else:
        print(df.to_string(index=False))
        print(f"\n{len(df)} location(s) collected successfully.")
