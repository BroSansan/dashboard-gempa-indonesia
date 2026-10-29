-- DBMS 1: PostgreSQL (Neon / Supabase) - data kejadian gempa
CREATE TABLE IF NOT EXISTS gempa (
    id           TEXT PRIMARY KEY,          -- ID event USGS
    waktu        TIMESTAMPTZ NOT NULL,
    lat          DOUBLE PRECISION NOT NULL,
    lon          DOUBLE PRECISION NOT NULL,
    kedalaman_km DOUBLE PRECISION,
    magnitudo    DOUBLE PRECISION NOT NULL,
    tipe_mag     TEXT,
    tempat       TEXT,
    tsunami      SMALLINT DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_gempa_waktu ON gempa (waktu);
CREATE INDEX IF NOT EXISTS idx_gempa_mag ON gempa (magnitudo);
