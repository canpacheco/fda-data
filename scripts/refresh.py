"""Pull every Week 8 source, save it unchanged under snapshots/<date>/, and write a manifest.

    python scripts/refresh.py            today's date (UTC)
    python scripts/refresh.py 2026-10-12 a named folder

Each file is saved exactly as the server sent it (the raw bytes), beside a manifest.csv that
records, for every file: the name, the URL, the time of the pull (UTC), the size in bytes, the
SHA-256 hash of the bytes, and the row count where the file is a table. The hash is a fingerprint:
two pulls with the same hash are the same file to the last byte, and a changed hash means the
publisher changed something. The manifest is the evidence bag of the pull.

The script never edits a raw file. The one derived file is arkansas_counties.csv, the county
table lifted out of the Wikipedia page, saved beside the page itself.
"""
import hashlib
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

# Servers disagree about who may ask. FRED answers the library's own header and hangs on a hand-set
# browser string; Freddie Mac refuses the library's header and wants a browser's. So each pull is
# tried plain first and, if that fails, with a browser header.
BROWSER = {"User-Agent": "Mozilla/5.0"}

SOURCES = {
    "fred_mortgage30us.csv": {
        "url": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US",
        "kind": "csv", "publisher": "FRED, Federal Reserve Bank of St. Louis",
    },
    "freddie_pmms_weekly.xlsx": {
        "url": "https://www.freddiemac.com/pmms/docs/historicalweeklydata.xlsx",
        "kind": "xlsx", "publisher": "Freddie Mac Primary Mortgage Market Survey",
        "read": {"sheet_name": "Full History", "skiprows": 6},
    },
    "zillow_zori_county.csv": {
        "url": "https://files.zillowstatic.com/research/public_csvs/zori/County_zori_uc_sfrcondomfr_sm_month.csv",
        "kind": "csv", "publisher": "Zillow Research, Observed Rent Index",
    },
    "census_gazetteer_counties_2025.zip": {
        "url": "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_counties_national.zip",
        "kind": "zip-pipe", "publisher": "Census Bureau, 2025 Gazetteer Files",
    },
    "fema_disaster_declarations.csv": {
        "url": ("https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries?$format=csv"
                "&$filter=declarationDate%20ge%20%272015-01-01%27"
                "&$select=disasterNumber,declarationType,declarationDate,incidentType,"
                "fipsStateCode,fipsCountyCode,declarationTitle&$allrecords=true"),
        "kind": "csv", "publisher": "OpenFEMA, Disaster Declarations Summaries v2",
    },
    "census_new_residential_sales.pdf": {
        "url": "https://www.census.gov/construction/nrs/pdf/newressales.pdf",
        "kind": "pdf", "publisher": "Census Bureau, Monthly New Residential Sales release",
    },
    "wikipedia_arkansas_counties.html": {
        "url": "https://en.wikipedia.org/wiki/List_of_counties_in_Arkansas",
        "kind": "html", "publisher": "Wikipedia, List of counties in Arkansas",
    },
}


def fetch(url):
    last_error = None
    for headers in ({}, BROWSER):
        try:
            response = requests.get(url, headers=headers, timeout=90)
            response.raise_for_status()
            return response.content
        except requests.RequestException as error:
            last_error = error
    raise last_error


def count_rows(name, spec, raw):
    """Rows of the table inside the file, or an empty string for a file that is not one table."""
    kind = spec["kind"]
    if kind == "csv":
        return len(pd.read_csv(io.BytesIO(raw)))
    if kind == "xlsx":
        return len(pd.read_excel(io.BytesIO(raw), **spec["read"]))
    if kind == "zip-pipe":
        return len(pd.read_csv(io.BytesIO(raw), sep="|", compression="zip"))
    return ""


def arkansas_counties(raw):
    """The county table on the Wikipedia page: the table whose first column is the county name."""
    tables = pd.read_html(io.StringIO(raw.decode("utf-8")))
    for table in tables:
        first = str(table.columns[0])
        if first.lower().startswith("county") and len(table) >= 75:
            return table
    raise SystemExit("county table not found on the Wikipedia page")


def main(folder_name):
    root = Path(__file__).resolve().parents[1]
    folder = root / "snapshots" / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, spec in SOURCES.items():
        pulled_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        raw = fetch(spec["url"])
        (folder / name).write_bytes(raw)
        n_rows = count_rows(name, spec, raw)
        if spec["kind"] == "html":
            table = arkansas_counties(raw)
            table.to_csv(folder / "arkansas_counties.csv", index=False)
            n_rows = len(table)
        rows.append({"file": name, "publisher": spec["publisher"], "url": spec["url"],
                     "pulled_at": pulled_at, "bytes": len(raw),
                     "sha256": hashlib.sha256(raw).hexdigest(), "rows": n_rows})
        print("%-38s %10d bytes  rows=%s" % (name, len(raw), n_rows), flush=True)
    manifest = pd.DataFrame(rows)
    manifest.to_csv(folder / "manifest.csv", index=False)
    print("manifest written:", folder / "manifest.csv")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else datetime.now(timezone.utc).strftime("%Y-%m-%d"))
