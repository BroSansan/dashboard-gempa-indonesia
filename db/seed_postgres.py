"""Seed DBMS 1 (PostgreSQL) dengan katalog gempa USGS untuk wilayah Indonesia.

Penggunaan:
    export DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"
    python db/seed_postgres.py --start 2015 --end 2026 --min-mag 4.5
"""
import argparse
import io
import os
from pathlib import Path

import pandas as pd
import requests
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
API = "https://earthquake.usgs.gov/fdsnws/event/1/query"
# Bounding box Indonesia (perkiraan)
BBOX = dict(minlatitude=-11.5, maxlatitude=6.5, minlongitude=94.5, maxlongitude=141.5)
KOLOM = ["id", "time", "latitude", "longitude", "depth", "mag", "magType", "place", "tsunami"]


def fetch_year(year: int, min_mag: float) -> pd.DataFrame:
    params = dict(format="csv", orderby="time-asc", minmagnitude=min_mag,
                  starttime=f"{year}-01-01", endtime=f"{year + 1}-01-01", **BBOX)
    r = requests.get(API, params=params, timeout=120)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2015)
    ap.add_argument("--end", type=int, default=2026)
    ap.add_argument("--min-mag", type=float, default=4.5)
    a = ap.parse_args()

    url = os.environ["DATABASE_URL"].replace("postgres://", "postgresql+psycopg2://", 1)
    url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    engine = create_engine(url)
    with engine.begin() as con:
        con.exec_driver_sql((ROOT / "db" / "schema_postgres.sql").read_text())

    total = 0
    for year in range(a.start, a.end + 1):
        df = fetch_year(year, a.min_mag)
        if df.empty:
            print(f"{year}: kosong")
            continue
        # kolom yang tidak ada diisi kosong agar tidak error
        df = df.reindex(columns=KOLOM)
        rows = pd.DataFrame({
            "id": df["id"], "waktu": pd.to_datetime(df["time"], utc=True),
            "lat": df["latitude"], "lon": df["longitude"],
            "kedalaman_km": df["depth"], "magnitudo": df["mag"],
            "tipe_mag": df["magType"], "tempat": df["place"],
            "tsunami": df["tsunami"].fillna(0).astype(int),
        }).dropna(subset=["id", "magnitudo"])
        rows = rows.astype(object).where(rows.notna(), None)
        with engine.begin() as con:
            con.execute(text("""
                INSERT INTO gempa (id, waktu, lat, lon, kedalaman_km, magnitudo, tipe_mag, tempat, tsunami)
                VALUES (:id, :waktu, :lat, :lon, :kedalaman_km, :magnitudo, :tipe_mag, :tempat, :tsunami)
                ON CONFLICT (id) DO NOTHING"""), rows.to_dict("records"))
        total += len(rows)
        print(f"{year}: {len(rows)} baris")
    print(f"Selesai. Total diproses: {total}")


if __name__ == "__main__":
    main()