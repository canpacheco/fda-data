"""Rebuild the three county-level source files used in the FDA I combining week (Week 10):

    raw/census_popest_counties_2024.csv      Census Bureau county population estimates, vintage 2024
    raw/ers_unemployment_income_2023.xlsx    USDA ERS unemployment and median household income, 2000-2023
    raw/census_cbsa_delineation_2023.xlsx    Census Bureau list of core based statistical areas, July 2023

Each file is saved exactly as the publisher served it. The USDA server answers only requests that
look like a browser, so every request carries a browser User-Agent.
Run from the repository root: python scripts/fetch_county_sources.py
"""
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "raw"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130 Safari/537.36"
SOURCES = {
    "census_popest_counties_2024.csv":
        "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/totals/co-est2024-alldata.csv",
    "ers_unemployment_income_2023.xlsx":
        "https://ers.usda.gov/sites/default/files/_laserfiche/DataFiles/48747/Unemployment2023.xlsx",
    "census_cbsa_delineation_2023.xlsx":
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx",
}

for name, url in SOURCES.items():
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read()
    (RAW / name).write_bytes(data)
    print(f"{name}: {len(data):,} bytes", flush=True)
