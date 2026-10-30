"""Dashboard Gempa Indonesia - Multi-DBMS (PostgreSQL + SQLite) | Streamlit + Plotly."""
from datetime import date

import plotly.express as px
import streamlit as st

import pipeline as pl

st.set_page_config(page_title="Dashboard Gempa Indonesia", page_icon="🌋", layout="wide")


@st.cache_data(ttl=3600, show_spinner="Mengambil data dari PostgreSQL...")
def get_gempa(start, end, min_mag):
    return pl.load_gempa(pl.get_pg_engine(), start, end, min_mag)


@st.cache_data(show_spinner=False)
def get_prov():
    return pl.load_provinsi(pl.get_sqlite_engine())


st.title("🌋 Dashboard Gempa Bumi Indonesia")
st.caption(
    "Data kejadian gempa (USGS) di **PostgreSQL** digabung dengan referensi provinsi "
    "(BPS) di **SQLite** menggunakan Pandas."
)

prov = get_prov()

# ---------- Sidebar: filter interaktif ----------
st.sidebar.header("Filter")
rentang = st.sidebar.date_input(
    "Rentang tanggal", value=(date(2020, 1, 1), date.today()),
    min_value=date(2020, 1, 1), max_value=date.today(),
)
if not isinstance(rentang, tuple) or len(rentang) != 2:
    st.info("Pilih tanggal awal dan akhir.")
    st.stop()
min_mag = st.sidebar.slider("Magnitudo minimum", 4.5, 8.0, 5.0, 0.1)
pulau_opsi = sorted(prov["pulau"].unique())
pulau_pilih = st.sidebar.multiselect("Kelompok pulau", pulau_opsi, default=pulau_opsi)
kedalaman = st.sidebar.slider("Kedalaman (km)", 0, 700, (0, 700))

try:
    gempa = get_gempa(rentang[0], rentang[1], min_mag)
except Exception as e:  # koneksi gagal
    st.error(f"Gagal terhubung ke PostgreSQL: {e}")
    st.stop()

joined = pl.join_gempa_provinsi(gempa, prov)
joined = joined[
    joined["pulau"].isin(pulau_pilih)
    & joined["kedalaman_km"].between(kedalaman[0], kedalaman[1])
]
if joined.empty:
    st.warning("Tidak ada data untuk filter ini.")
    st.stop()

ringkas = pl.agregasi_provinsi(joined, prov[prov["pulau"].isin(pulau_pilih)])

# ---------- KPI ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Jumlah gempa", f"{len(joined):,}")
c2.metric("Magnitudo maks", f"{joined['magnitudo'].max():.1f}")
c3.metric("Kedalaman rata-rata", f"{joined['kedalaman_km'].mean():.0f} km")
top = ringkas.sort_values("jumlah_gempa", ascending=False).iloc[0]
c4.metric("Provinsi terbanyak", top["nama"], f"{int(top['jumlah_gempa'])} gempa")

tab1, tab2, tab3, tab4 = st.tabs(["Peta", "Per Provinsi", "Tren & Sebaran", "Data"])

with tab1:
    sample = joined.sort_values("magnitudo", ascending=False).head(5000)
    fig = px.scatter_map(
        sample, lat="lat", lon="lon", color="magnitudo", size="magnitudo",
        size_max=14, hover_name="tempat",
        hover_data={"waktu": True, "kedalaman_km": ":.0f", "provinsi": True,
                    "lat": False, "lon": False},
        color_continuous_scale="YlOrRd", zoom=3.3, center={"lat": -2.5, "lon": 118},
        height=620,
    )
    fig.update_layout(map_style="open-street-map", margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)
    if len(joined) > 5000:
        st.caption("Peta menampilkan 5.000 gempa dengan magnitudo tertinggi.")

with tab2:
    a, b = st.columns(2)
    metrik = a.radio("Urutkan berdasarkan", ["jumlah_gempa", "gempa_per_juta"],
                     format_func=lambda x: "Jumlah gempa" if x == "jumlah_gempa"
                     else "Gempa per 1 juta penduduk", horizontal=True)
    n = b.slider("Tampilkan N provinsi teratas", 5, 34, 15)
    d = ringkas.sort_values(metrik, ascending=False).head(n)
    fig = px.bar(d, x=metrik, y="nama", orientation="h", color="pulau",
                 labels={"nama": "", "jumlah_gempa": "Jumlah gempa",
                         "gempa_per_juta": "Gempa per 1 juta penduduk"})
    fig.update_layout(yaxis=dict(autorange="reversed"), height=520)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Provinsi dipetakan dari centroid terdekat; gempa lepas pantai ikut "
               "dihitung ke provinsi terdekat.")

with tab3:
    a, b = st.columns(2)
    bulanan = (joined.set_index("waktu").resample("MS").size().rename("jumlah").reset_index())
    a.plotly_chart(px.line(bulanan, x="waktu", y="jumlah", title="Jumlah gempa per bulan"),
                   use_container_width=True)
    b.plotly_chart(px.histogram(joined, x="magnitudo", nbins=30, title="Distribusi magnitudo"),
                   use_container_width=True)
    st.plotly_chart(
        px.scatter(joined.sample(min(len(joined), 4000), random_state=1), x="kedalaman_km",
                   y="magnitudo", color="pulau", opacity=0.5,
                   title="Kedalaman vs magnitudo"),
        use_container_width=True,
    )

with tab4:
    st.dataframe(ringkas.sort_values("jumlah_gempa", ascending=False), use_container_width=True)
    st.download_button("Unduh data gabungan (CSV)",
                       joined.to_csv(index=False).encode("utf-8"), "gempa_gabungan.csv")

st.divider()
st.caption(
    "Sumber: USGS Earthquake Catalog (earthquake.usgs.gov) · "
    "BPS Sensus Penduduk 2020 · Kode: lihat README repositori."
)
