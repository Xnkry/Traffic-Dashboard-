"""
ingest.py

Fetches live traffic data for each monitored Casablanca location,
flattens the response, and prints the resulting DataFrame.

No database involved yet — that's the next step once this prints
a clean table correctly.

Run with:
    python ingest.py
"""

from datetime import datetime, timezone

import pandas as pd
import requests
from sqlalchemy import create_engine

from Constants import TOMTOM_API  # your key, kept out of git via .gitignore

API_KEY = TOMTOM_API

DATABASE_URL = "postgresql://traffic_user:traffic_pass@localhost:5432/traffic_db"
engine = create_engine(DATABASE_URL)

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
        resp = requests.get(URL, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()["flowSegmentData"]
    except requests.exceptions.RequestException as e:
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


def save_to_db(df: pd.DataFrame) -> None:
    """Insert collected rows into traffic_readings, matching each location to its ID."""
    # Get the location_id for each location name from the locations table
    locations_df = pd.read_sql("SELECT id, name FROM locations", engine)
    name_to_id = dict(zip(locations_df["name"], locations_df["id"]))

    df = df.copy()
    df["location_id"] = df["location"].map(name_to_id)

    if df["location_id"].isna().any():
        missing = df[df["location_id"].isna()]["location"].unique()
        print(f"  [WARNING] No matching location_id for: {missing}")
        df = df.dropna(subset=["location_id"])

    insert_df = df.rename(columns={"timestamp": "recorded_at"})[
        [
            "location_id",
            "recorded_at",
            "current_speed",
            "free_flow_speed",
            "congestion_ratio",
        ]
    ]

    insert_df.to_sql("traffic_readings", engine, if_exists="append", index=False)
    print(f"  Inserted {len(insert_df)} row(s) into traffic_readings.")


if __name__ == "__main__":
    df = collect_all_locations()

    print("\n--- Result ---")
    if df.empty:
        print("No data collected — check your API key or network connection.")
    else:
        print(df.to_string(index=False))
        print(f"\n{len(df)} location(s) collected successfully.")

        save_to_db(df)
