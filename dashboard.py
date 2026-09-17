"""
dashboard.py

Streamlit dashboard for the Casablanca Traffic Project.
Reads data from PostgreSQL (populated by ingest.py) and displays:
- A KPI for current congestion
- An interactive line chart of congestion over time
- A map of monitored locations colored by current congestion

Run with:
    streamlit run dashboard.py
"""

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine
from streamlit_folium import st_folium

# --- Setup ---
st.set_page_config(page_title="Casablanca Traffic Dashboard", layout="wide")

DATABASE_URL = "postgresql://traffic_user:traffic_pass@localhost:5432/traffic_db"
engine = create_engine(DATABASE_URL)


@st.cache_data(ttl=300)  # refresh cached data every 5 minutes
def load_data() -> pd.DataFrame:
    query = """
        SELECT
            l.name AS location,
            l.lat,
            l.lon,
            r.recorded_at,
            r.current_speed,
            r.free_flow_speed,
            r.congestion_ratio
        FROM traffic_readings r
        JOIN locations l ON l.id = r.location_id
        ORDER BY r.recorded_at ASC
    """
    df = pd.read_sql(query, engine)
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])
    return df


# --- Load data ---
df = load_data()

st.title("🚦 Casablanca Traffic Dashboard")

if df.empty:
    st.warning("No data yet. Run ingest.py a few times first, then refresh this page.")
    st.stop()

# --- Sidebar filters ---
st.sidebar.header("Filters")
all_locations = sorted(df["location"].unique())
selected_locations = st.sidebar.multiselect(
    "Locations", options=all_locations, default=all_locations
)

filtered_df = df[df["location"].isin(selected_locations)]

# --- KPIs ---
latest = (
    filtered_df.sort_values("recorded_at")
    .groupby("location")
    .tail(1)
    .sort_values("congestion_ratio")
)

cols = st.columns(len(latest)) if len(latest) > 0 else [st]
for col, (_, row) in zip(cols, latest.iterrows()):
    col.metric(
        label=row["location"],
        value=f"{row['congestion_ratio']:.2f}",
        help=f"current: {row['current_speed']} km/h | free flow: {row['free_flow_speed']} km/h",
    )

st.divider()

# --- Layout: chart on the left, map on the right ---
left, right = st.columns([2, 1])

with left:
    st.subheader("Congestion over time")
    fig = px.line(
        filtered_df,
        x="recorded_at",
        y="congestion_ratio",
        color="location",
        markers=True,
        labels={"recorded_at": "Time", "congestion_ratio": "Congestion ratio"},
    )
    fig.update_layout(yaxis_range=[0, 1.1])
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Live map")
    center_lat = filtered_df["lat"].mean()
    center_lon = filtered_df["lon"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    for _, row in latest.iterrows():
        color = (
            "green"
            if row["congestion_ratio"] >= 0.7
            else ("orange" if row["congestion_ratio"] >= 0.4 else "red")
        )
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=12,
            color=color,
            fill=True,
            fill_opacity=0.8,
            popup=f"{row['location']}: {row['congestion_ratio']:.2f}",
        ).add_to(m)

    st_folium(m, width=400, height=400)

st.divider()

# --- Raw data table (optional, collapsible) ---
with st.expander("Show raw data"):
    st.dataframe(filtered_df.sort_values("recorded_at", ascending=False))
