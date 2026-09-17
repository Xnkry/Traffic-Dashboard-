-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Fixed monitoring points
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    geom GEOMETRY(Point, 4326)
);

-- Time-series traffic readings
CREATE TABLE IF NOT EXISTS traffic_readings (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    current_speed FLOAT,
    free_flow_speed FLOAT,
    congestion_ratio FLOAT
);

CREATE INDEX IF NOT EXISTS idx_readings_time ON traffic_readings (recorded_at);
CREATE INDEX IF NOT EXISTS idx_locations_geom ON locations USING GIST (geom);

-- Seed the fixed Casablanca locations
INSERT INTO locations (name, lat, lon, geom) VALUES
('Centre Ville',   33.5731, -7.5898, ST_SetSRID(ST_MakePoint(-7.5898, 33.5731), 4326)),
('Ain Diab',       33.5928, -7.6511, ST_SetSRID(ST_MakePoint(-7.6511, 33.5928), 4326)),
('Sidi Bernoussi', 33.6086, -7.5013, ST_SetSRID(ST_MakePoint(-7.5013, 33.6086), 4326))
ON CONFLICT DO NOTHING;
