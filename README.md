# Multi-DBMS Data Pipeline & Web Visualization — Gempa Bumi Indonesia

Tugas Mandiri Terstruktur · Visualisasi Data dan Informasi · Informatika

| | |
|---|---|
| **Nama / NIM** | Sansan Maulana Anugrah / 230660121104 |
| **Live App** | https://dashboard-gempa-indonesia-sansan-spzmh486biybbxyvje2uorz.streamlit.app |
| **Repositori** | https://github.com/BroSansan/dashboard-gempa-indonesia |

## Studi kasus

Dashboard interaktif kejadian gempa bumi di wilayah Indonesia (2020 – 2026, magnitudo ≥ 4,5)
yang dikaitkan dengan provinsi terdekat dan jumlah penduduknya. Pertanyaan yang dijawab:
provinsi mana yang paling sering diguncang gempa, dan bagaimana angkanya bila dibandingkan
dengan jumlah penduduk?

Dua DBMS dipakai karena sifat datanya berbeda:

- **Data kejadian** (ribuan baris, terus bertambah, hasil pengamatan USGS) → DBMS relasional server (PostgreSQL).
- **Data referensi** (34 provinsi: pulau, titik pusat, penduduk; kecil, statis, hanya dibaca) → DBMS embedded (SQLite) yang ikut di repositori.

## Ringkasan arsitektur

| | Engine | Fungsi | Tabel |
|---|---|---|---|
| **DBMS 1** | PostgreSQL (Neon) | Data kejadian gempa | `gempa` |
| **DBMS 2** | SQLite (`data/referensi.db`) | Referensi provinsi | `provinsi` (34 baris) |

```
USGS API ──seed_postgres.py──► PostgreSQL: gempa ───────────┐
CSV BPS ───seed_sqlite.py────► SQLite:     provinsi ────────┴─► Pandas (haversine + merge + groupby) ─► Streamlit + Plotly
```

**Alur pipeline** (`pipeline.py`):
1. *Extract*: `SELECT` terparameter (tanggal dan magnitudo) dari PostgreSQL, dan seluruh tabel `provinsi` dari SQLite, lewat SQLAlchemy.
2. *Integrate*: jarak haversine dari tiap gempa ke titik pusat setiap provinsi dihitung dengan NumPy; provinsi terdekat dipilih lalu digabung dengan `DataFrame.merge()` berdasarkan kode provinsi.
3. *Transform*: agregasi per provinsi (jumlah, magnitudo maksimum dan rata-rata, kedalaman rata-rata) serta gempa per 1 juta penduduk.
4. *Serve*: hasil di-cache (`st.cache_data`, TTL 1 jam) lalu divisualisasikan dengan Plotly.

**Pengolahan data saat seed** (`db/`):
- `seed_postgres.py` mengunduh katalog USGS per tahun untuk kotak koordinat Indonesia, mengisi kolom yang hilang, dan memakai `ON CONFLICT DO NOTHING` agar aman dijalankan ulang.
- `seed_sqlite.py` membuat tabel `provinsi` dari `data/provinsi.csv`.

## Fitur interaktif

- Filter rentang tanggal, magnitudo minimum, kelompok pulau, dan kedalaman.
- KPI: jumlah gempa, magnitudo maksimum, kedalaman rata-rata, provinsi dengan gempa terbanyak.
- Peta sebaran (warna dan ukuran mengikuti magnitudo, hover untuk detail).
- Peringkat provinsi (urut jumlah atau per 1 juta penduduk, jumlah provinsi dapat diatur).
- Tren bulanan, histogram magnitudo, dan scatter kedalaman vs magnitudo.
- Tabel hasil gabungan dan unduh CSV.

## Hasil utama

Dengan filter bawaan (1 Jan 2020 – 29 Okt 2026, magnitudo ≥ 4,5, seluruh pulau, kedalaman 0–700 km):

| Indikator | Nilai |
|---|---|
| Jumlah gempa | 6.733 |
| Magnitudo maksimum | 7,8 |
| Kedalaman rata-rata | 68 km |
| Provinsi dengan gempa terbanyak | Maluku Utara (1.601 gempa) |

Pada magnitudo ≥ 5,0, Maluku Utara (296), Maluku (210), dan Sulawesi Utara (205) tercatat
terbanyak; per 1 juta penduduk, Maluku Utara (±231) dan Maluku (±114) juga tertinggi.
Kawasan timur Indonesia lebih sering diguncang gempa dibanding Jawa, sejalan dengan
zona tumbukan lempeng di sekitar Laut Maluku.

## Keterbatasan

- Pemetaan gempa ke provinsi memakai **titik pusat terdekat**, bukan batas wilayah, sehingga gempa
  lepas pantai ikut dihitung ke provinsi terdekat dan provinsi luas seperti Papua bisa terhitung lebih sedikit.
- Referensi memakai 34 provinsi (basis Sensus Penduduk 2020); pemekaran Papua 2022 belum dipisah.
- Titik pusat provinsi disusun manual (perkiraan).

## Sumber data

- **Data primer**: USGS Earthquake Catalog — https://earthquake.usgs.gov/fdsnws/event/1/
- **Data referensi**: jumlah penduduk provinsi, BPS Sensus Penduduk 2020 — https://sensus.bps.go.id/ ;
  titik pusat provinsi dan pengelompokan pulau disusun manual (`data/provinsi.csv`).

## Referensi kode / inspirasi

**Repositori publik yang dipelajari:**
- SeismoStream (Aditya-Ramachandran) — https://github.com/Aditya-Ramachandran/SiesmoStream
  Dipelajari untuk teknik peta sebaran gempa interaktif (Streamlit + Plotly) dan pengambilan data dari API USGS.
- streamlit-tutorial (fneum) — https://github.com/fneum/streamlit-tutorial
  Dipelajari untuk struktur dasar `app.py` dan `requirements.txt` pada dashboard Streamlit + Plotly.

**Yang dikembangkan sendiri:** penyimpanan data pada dua DBMS (PostgreSQL dan SQLite), skrip seed, pemetaan gempa ke
provinsi dengan jarak haversine, join dan agregasi Pandas, serta seluruh filter dan visualisasi per provinsi.

**Dokumentasi teknis:**
- Streamlit — Connect to PostgreSQL: https://docs.streamlit.io/develop/tutorials/databases/postgresql
- Streamlit — Secrets management: https://docs.streamlit.io/develop/concepts/connections/secrets-management
- SQLAlchemy — Engine configuration: https://docs.sqlalchemy.org/en/20/core/engines.html
- Plotly — Scatter plots on tile maps: https://plotly.com/python/tile-scatter-maps/

## Menjalankan secara lokal

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 1) Siapkan PostgreSQL (mis. Neon), lalu isi .streamlit/secrets.toml:
#    DATABASE_URL = "postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require"

# 2) Seed kedua database (DATABASE_URL harus terpasang di terminal untuk seed Postgres)
python db/seed_sqlite.py
python db/seed_postgres.py --start 2020 --end 2026 --min-mag 4.5

# 3) Jalankan aplikasi
streamlit run app.py
```

## Deploy (Streamlit Community Cloud)

1. Push repositori ke GitHub (publik); `data/referensi.db` ikut di-commit.
2. share.streamlit.io → *Create app* → pilih repo, branch `main`, file `app.py`.
3. *Advanced settings → Secrets*, isi `DATABASE_URL = "postgresql://..."`.
4. Jangan pernah meng-commit password; `.env` dan `.streamlit/secrets.toml` sudah ada di `.gitignore`.
5. Setelah deploy, buka aplikasi dan pastikan KPI serta peta terisi (berarti kedua DBMS terbaca).
   Jika aplikasi "tertidur" karena lama tidak dikunjungi, klik **Yes, get this app back up!** dan tunggu sekitar 1 menit.

## Struktur repositori

```
app.py                    # UI Streamlit + visualisasi Plotly
pipeline.py               # extract dari 2 DBMS, join haversine + merge Pandas, agregasi
requirements.txt          # dependensi Python
.env.example              # contoh variabel lingkungan (tanpa kredensial asli)
.gitignore                # .env, secrets.toml, .venv tidak ikut di-commit
db/
  schema_postgres.sql     # DDL DBMS 1 (tabel gempa)
  schema_sqlite.sql       # DDL DBMS 2 (tabel provinsi)
  seed_postgres.py        # unduh katalog USGS dan isi PostgreSQL
  seed_sqlite.py          # isi SQLite dari data/provinsi.csv
data/
  provinsi.csv            # data mentah referensi provinsi
  referensi.db            # DBMS 2 (SQLite)
```