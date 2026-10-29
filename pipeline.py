"""Pipeline integrasi dua DBMS: PostgreSQL (gempa) + SQLite (referensi provinsi)."""
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).parent


def _secret(name: str, default: str | None = None) -> str | None:
    """Ambil kredensial dari Streamlit secrets, lalu environment variable."""
    try:
        import streamlit as st

        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, default)


def get_pg_engine():
    url = _secret("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL belum diatur (gunakan secrets / env var).")
    # SQLAlchemy butuh driver eksplisit
    url = url.replace("postgres://", "postgresql+psycopg2://", 1).replace(
        "postgresql://", "postgresql+psycopg2://", 1
    )
    return create_engine(url, pool_pre_ping=True)


def get_sqlite_engine():
    path = _secret("SQLITE_PATH", str(BASE_DIR / "data" / "referensi.db"))
    return create_engine(f"sqlite:///{path}")


def load_gempa(engine, start, end, min_mag: float) -> pd.DataFrame:
    """DBMS 1 (PostgreSQL): data transaksi/kejadian gempa."""
    sql = text(
        """
        SELECT id, waktu, lat, lon, kedalaman_km, magnitudo, tempat, tsunami
        FROM gempa
        WHERE waktu >= :start AND waktu < :end AND magnitudo >= :min_mag
        """
    )
    return pd.read_sql(
        sql, engine, params={"start": start, "end": end, "min_mag": min_mag},
        parse_dates=["waktu"],
    )


def load_provinsi(engine) -> pd.DataFrame:
    """DBMS 2 (SQLite): referensi provinsi (pulau, centroid, penduduk)."""
    return pd.read_sql("SELECT * FROM provinsi", engine)


def _haversine_matrix(lat1, lon1, lat2, lon2):
    """Jarak (km) antara setiap titik gempa (N) dan setiap centroid (M) -> matriks N x M."""
    r = 6371.0
    p1, p2 = np.radians(lat1)[:, None], np.radians(lat2)[None, :]
    dphi = p2 - p1
    dl = np.radians(lon2)[None, :] - np.radians(lon1)[:, None]
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def join_gempa_provinsi(gempa: pd.DataFrame, prov: pd.DataFrame) -> pd.DataFrame:
    """Spatial join di tingkat aplikasi: tiap gempa dipetakan ke provinsi
    dengan centroid terdekat, lalu di-merge dengan atribut provinsi."""
    if gempa.empty:
        return gempa.assign(
            kode_provinsi=pd.Series(dtype="Int64"),
            jarak_ke_centroid_km=pd.Series(dtype=float),
            provinsi=pd.Series(dtype=str),
            pulau=pd.Series(dtype=str),
            penduduk_2020=pd.Series(dtype="Int64"),
        )
    dist = _haversine_matrix(
        gempa["lat"].to_numpy(), gempa["lon"].to_numpy(),
        prov["lat"].to_numpy(), prov["lon"].to_numpy(),
    )
    idx = dist.argmin(axis=1)
    out = gempa.copy()
    out["kode_provinsi"] = prov["kode"].to_numpy()[idx]
    out["jarak_ke_centroid_km"] = dist[np.arange(len(out)), idx]
    return out.merge(
        prov[["kode", "nama", "pulau", "penduduk_2020"]].rename(
            columns={"kode": "kode_provinsi", "nama": "provinsi"}
        ),
        on="kode_provinsi", how="left",
    )


def agregasi_provinsi(joined: pd.DataFrame, prov: pd.DataFrame) -> pd.DataFrame:
    """Ringkasan per provinsi + gempa per 1 juta penduduk (provinsi tanpa gempa = 0)."""
    agg = (
        joined.groupby("kode_provinsi")
        .agg(jumlah_gempa=("id", "count"), mag_maks=("magnitudo", "max"),
             mag_rata=("magnitudo", "mean"), kedalaman_rata=("kedalaman_km", "mean"))
        .reset_index()
    )
    res = prov.merge(agg, left_on="kode", right_on="kode_provinsi", how="left")
    res["jumlah_gempa"] = res["jumlah_gempa"].fillna(0).astype(int)
    res["gempa_per_juta"] = res["jumlah_gempa"] / (res["penduduk_2020"] / 1e6)
    return res.drop(columns=["kode_provinsi"])
