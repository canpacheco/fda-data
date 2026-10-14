# FDA course data

Public data files for the Financial Data Analytics courses (University of Arkansas, Cathy Pacheco).
Each file is read straight from this repository by URL, for example:

```python
import pandas as pd

counties = pd.read_csv("https://raw.githubusercontent.com/canpacheco/fda-data/main/student/counties.csv")
```

## student/ (the course county dataset)

| File | What it is |
|---|---|
| `counties.csv` | 795 US counties: FIPS code, name, state, metro label, latest typical home value, state finance salary, cost of living, years-to-buy |
| `home_values_long.csv` | the same counties, one row per county per month, January 2015 to December 2025 (Zillow ZHVI) |
| `states.csv` | one row per state: Census region, population, net domestic migration, unemployment rate, salary, cost of living |
| `rents.csv` | one row per county with a Zillow rent figure (fewer counties than `counties.csv`) |
| `disasters.csv` | one row per county per federal disaster declaration, 2015 to 2025 |
| `state_economics.csv` | the state salary and cost-of-living values used in `counties.csv` |
| `course_data.duckdb` | the same county data as a DuckDB database (tables counties, home_values, state_economics), the one the SQL weeks query |

Home values and rents are Zillow research data. Salary and cost of living are representative
state-level values calibrated to public sources (BLS Occupational Employment Statistics, BEA Regional
Price Parities); they are teaching values, not official statistics.

## raw/ (snapshots of public sources, as downloaded)

| File | Source | Snapshot |
|---|---|---|
| `zillow_zori_county.csv` | Zillow Observed Rent Index, county, smoothed, all homes plus multifamily | through August 2026 |
| `census_state_population.csv` | Census Bureau Vintage 2025 state population estimates (NST-EST2025-ALLDATA) | October 2026 |
| `fema_disaster_declarations.csv` | OpenFEMA Disaster Declarations Summaries v2, declared 2015 or later | October 2026 |
| `bls_state_unemployment.csv` | BLS state unemployment rates, seasonally adjusted, via FRED | October 2026 |
| `fred_mortgage30us.csv` | FRED series MORTGAGE30US, 30-year fixed mortgage rate, weekly | 1 October 2026 |
| `hmda_lar_nwa_2020_2024.csv.gz` | HMDA loan application register for Benton and Washington counties, Arkansas, 2020 to 2024, from the FFIEC Data Browser API (179,193 rows, 99 columns; gzip of the CSV the API returned, one year per request, joined) | 20 August 2026 |
| `hmda_filers_nwa_2020_2024.csv` | the lenders behind those rows, one row per lender per year (LEI, name, row count), from the same API | 20 August 2026 |
| `hmda_codes.csv` | labels for the coded HMDA fields (loan type, loan purpose, action taken, lien status, occupancy, purchaser, first denial reason), from the FFIEC LAR data-field documentation | 20 August 2026 |

`scripts/fetch_hmda_nwa.py` rebuilds the two HMDA files. The public HMDA file reports loan amounts
and property values as the midpoint of a $10,000 interval, income in thousands of dollars, ages in
buckets, and the word Exempt in fields a small lender need not report.

The raw files are kept exactly as the sources served them, so a live download in class can be
compared with the snapshot. Files here are not updated during a semester.

## snapshots/ (the weekly refresh)

`scripts/refresh.py` pulls every source again and saves the files, unchanged, under
`snapshots/<date>/` with a `manifest.csv` (file, publisher, URL, time of the pull, size, SHA-256
hash, rows). `scripts/change_report.py` then writes `CHANGES.md` in the new folder: which files
changed since the previous snapshot, how many rows each table gained, and whether Zillow revised
past months. The GitHub Actions workflow in `.github/workflows/refresh.yml` runs both every Monday
and commits the result, so the folder is a dated record of what each source said each week.
