"""Rebuild raw/hmda_lar_nwa_2020_2024.csv.gz and raw/hmda_filers_nwa_2020_2024.csv
from the FFIEC HMDA Data Browser API (Benton and Washington counties, Arkansas, 2020-2024).

The API takes ONE year per request: `years=2020,2021` returns 2020 only, with an HTTP 200
and no warning, so the file is built by looping over the years and concatenating. The
columns are checked to be identical across years before the parts are joined.
Run from the repository root: python scripts/fetch_hmda_nwa.py
"""
import gzip
import json
import urllib.request
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "raw"
COUNTIES = "05007,05143"
YEARS = (2020, 2021, 2022, 2023, 2024)
BASE = "https://ffiec.cfpb.gov/v2/data-browser-api/view"

parts, filers = [], []
for y in YEARS:
    url = f"{BASE}/csv?counties={COUNTIES}&years={y}"
    with urllib.request.urlopen(url, timeout=900) as r:
        df = pd.read_csv(r, dtype=str, keep_default_na=False, low_memory=False)
    parts.append(df)
    with urllib.request.urlopen(f"{BASE}/filers?counties={COUNTIES}&years={y}", timeout=300) as r:
        filers += json.load(r)["institutions"]
    print(f"{y}: {len(df)} rows, {df.shape[1]} columns", flush=True)

cols = list(parts[0].columns)
for y, p in zip(YEARS, parts):
    assert list(p.columns) == cols, f"schema drift in {y}"
lar = pd.concat(parts, ignore_index=True)
with gzip.open(RAW / "hmda_lar_nwa_2020_2024.csv.gz", "wt", newline="", compresslevel=9) as f:
    lar.to_csv(f, index=False)

f = pd.DataFrame(filers).rename(columns={"period": "activity_year"})
f[["activity_year", "lei", "name", "count"]].to_csv(RAW / "hmda_filers_nwa_2020_2024.csv", index=False)
print(f"LAR {len(lar)} rows, filers {len(f)} rows")
