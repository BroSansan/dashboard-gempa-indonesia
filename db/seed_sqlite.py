"""Seed DBMS 2 (SQLite) dari data/provinsi.csv -> data/referensi.db"""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "referensi.db"

con = sqlite3.connect(DB)
con.executescript((ROOT / "db" / "schema_sqlite.sql").read_text())
con.execute("DELETE FROM provinsi")
df = pd.read_csv(ROOT / "data" / "provinsi.csv")
df.to_sql("provinsi", con, if_exists="append", index=False)
con.commit()
print(f"SQLite: {len(df)} provinsi dimuat ke {DB}")
con.close()
