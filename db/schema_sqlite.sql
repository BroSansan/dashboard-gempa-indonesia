-- DBMS 2: SQLite (embedded) - referensi provinsi
CREATE TABLE IF NOT EXISTS provinsi (
    kode          INTEGER PRIMARY KEY,
    nama          TEXT NOT NULL,
    pulau         TEXT NOT NULL,
    lat           REAL NOT NULL,   -- centroid perkiraan
    lon           REAL NOT NULL,
    penduduk_2020 INTEGER NOT NULL
);
