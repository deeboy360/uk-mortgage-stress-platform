# Data Sources

**Last verified:** 2026-06-21

All datasets used in this project are published under the Open Government Licence v3.0 unless otherwise noted. The `data/raw/` directory in this repo contains **calibrated representative data** generated from the published statistics listed below, so that the full analysis pipeline runs out of the box on a fresh clone. To substitute the real source files, run `scripts/download_data.sh` (requires internet access) after cloning.

---

## 1. HM Land Registry UK House Price Index (UK HPI) — Average Prices

| Field | Value |
|---|---|
| **Publisher** | HM Land Registry |
| **Licence** | Open Government Licence v3.0 |
| **Download page** | https://www.gov.uk/government/statistical-data-sets/uk-house-price-index-data-downloads-june-2024 |
| **Direct CSV URL** | https://publicdata.landregistry.gov.uk/market-trend-data/house-price-index-data/Average-prices-2024-06.csv |
| **File** | `Average-prices-2024-06.csv` (9.4 MB) |
| **Coverage** | All local authority districts (England, Wales, Scotland, Northern Ireland), monthly from Jan 1995 to Jun 2024 |
| **Key columns** | `Date`, `Region_Name`, `Area_Code`, `Average_Price` |
| **Substitution note** | Download and rename to `data/raw/UK_HPI_Average_Prices_2024-06.csv`. The schema auto-detected by `src/data_loader.py`; re-run `scripts/ingest.sh` to reload. |

**SPARQL endpoint** (for custom queries): https://landregistry.data.gov.uk/app/qonsole

---

## 2. ONS Annual Survey of Hours and Earnings (ASHE) Table 8 — Earnings by Local Authority (Place of Residence)

| Field | Value |
|---|---|
| **Publisher** | Office for National Statistics (ONS) |
| **Licence** | Open Government Licence v3.0 |
| **Dataset page** | https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/datasets/placeofresidencebylocalauthorityashetable8 |
| **Direct ZIP URL (2024 revised)** | https://www.ons.gov.uk/file?uri=/employmentandlabourmarket/peopleinwork/earningsandworkinghours/datasets/placeofresidencebylocalauthorityashetable8/2024revised/ashetable82024revised.zip |
| **File** | `ashetable82024revised.zip` (8.0 MB) → extract Sheet 7a (median gross annual pay, full-time, residence-based) |
| **Coverage** | All UK local authority districts, annual survey year 2024 (reference date April 2024). Historical editions available from 2002. |
| **Key sheet** | `Table 7.7a` — Median gross annual earnings (£), full-time employees, place of residence, by local authority |
| **Substitution note** | Download ZIP, extract, identify the `7a` tab, and run `scripts/parse_ashe.py` to produce `data/raw/ASHE_Table8_Earnings_by_LAD.csv`. |

---

## 3. Bank of England Official Bank Rate History

| Field | Value |
|---|---|
| **Publisher** | Bank of England |
| **Licence** | Open Government Licence v3.0 |
| **Page** | https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp |
| **Series code** | `IUDBEDR` |
| **IADB CSV export** | https://www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp?Travel=NIxSTxSUx&FromSeries=1&ToSeries=50&DAT=RNG&FD=1&FM=Jan&FY=1990&TD=31&TM=Dec&TY=2025&VPD=Y&C=IUDBEDR&Filter=N&excel=1 |
| **Coverage** | Daily effective Bank Rate from 1694 (available); project uses 1995–2024 monthly series |
| **Current rate** | 3.75% (effective 18 December 2025) |
| **Note** | The IADB CSV export requires a browser session (CSRF token). The full change history was scraped from the page above on 2026-06-21 and hardcoded in `scripts/generate_calibrated_data.py`. |

---

## 4. Bank of England Mortgage Rate Series (2-Year Fixed, 75% and 90% LTV)

| Field | Value |
|---|---|
| **Publisher** | Bank of England (PSD — Product Sales Data) |
| **Licence** | Open Government Licence v3.0 |
| **Series codes** | `IUMBV34` (2yr fixed, 75% LTV), `IUMBV42` (2yr fixed, 90% LTV) |
| **IADB page** | https://www.bankofengland.co.uk/boeapps/database/ |
| **Coverage** | Monthly effective mortgage rates, Jan 1995 – latest |
| **Substitution note** | Same session-cookie issue as the Bank Rate above. Series can be manually exported from the IADB search interface. A calibrated proxy series is included in `data/raw/BoE_mortgage_rates.csv`, derived from the historical Bank Rate + empirically estimated LTV spread (see `notebooks/01_data_exploration.ipynb`, Section 3). |
| **Pass-through note** | Analysis in Phase 6 uses OLS regression of `mortgage_rate_90ltv ~ bank_rate` on the 2009–2024 window to estimate the spread; it is **not** assumed to be 1:1 (estimated β ≈ 0.92, intercept ≈ +0.95pp for 90% LTV). |

---

## 5. FCA Mortgage Lending Statistics — LTV Distribution

| Field | Value |
|---|---|
| **Publisher** | Financial Conduct Authority (FCA) |
| **Licence** | Open Government Licence v3.0 |
| **Page** | https://www.fca.org.uk/data/mortgage-lending-statistics |
| **File** | `mortgage-lending-statistics-2024-q2.xlsx` |
| **Coverage** | Q2 2024 (April–June 2024). Key tables: new mortgage lending by LTV band, buyer type (first-time buyer vs homemover), property type. |
| **Key finding** | First-time buyers: 29.3% at 86–90% LTV; weighted mean FTB LTV ≈ 79.9%. This grounds the project's "median buyer persona" at 90% LTV (top of the dominant FTB band) as a conservative, stress-relevant assumption. |
| **Substitution note** | Download the Excel from the FCA page and place at `data/raw/FCA_mortgage_LTV_distribution.xlsx`. Run `scripts/parse_fca.py` to extract the distribution table. |
| **UK Finance note** | The brief noted that UK Finance detailed lending data may be gated. FCA Mortgage Lending Statistics are the appropriate free public substitute and are explicitly referenced in the brief. |

---

## 6. ONS Open Geography Portal — Local Authority District Boundaries (December 2023, BGC)

| Field | Value |
|---|---|
| **Publisher** | ONS / Ordnance Survey |
| **Licence** | Open Government Licence v3.0 |
| **Portal page** | https://geoportal.statistics.gov.uk/datasets/ons::local-authority-districts-december-2023-boundaries-uk-bgc/about |
| **ArcGIS item ID** | `de420de4545f4e82b4e26b89424ede53` |
| **GeoJSON direct download** | https://opendata.arcgis.com/api/v3/datasets/de420de4545f4e82b4e26b89424ede53_0/downloads/data?format=geojson&spatialRefId=4326&where=1=1 |
| **Coverage** | 361 local authority districts and unitary authorities, UK, as of December 2023 |
| **Projection** | WGS84 (EPSG:4326) for GeoJSON export |
| **Note** | BGC = "Generalised, coastline-clipped" — reduced precision boundary, suitable for web choropleth. File is ~25 MB. The repo includes a lightweight placeholder GeoJSON (`data/raw/LAD_Dec2023_UK_BGC.geojson`) with approximate bounding polygons for each LAD centroid — sufficient to test all code paths. Replace with the real download for production maps. |
| **ArcGIS REST API** | https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/Local_Authority_Districts_December_2023_Boundaries_UK_BGC/FeatureServer/0 |
| **LAD code field** | `LAD23CD` (9-character ONS code, e.g. `E09000033`) |
| **Name field** | `LAD23NM` |

---

## Data Reproducibility Notes

### Local Authority Code Harmonisation

ONS periodically merges, splits, or renames local authorities. The UK HPI uses codes current at time of publication; ASHE Table 8 uses the same ONS codes. Key changes affecting 2020–2024 data:

- E06000060 (Buckinghamshire UA) replaced E07000004–E07000007 (Aylesbury Vale, Chiltern, South Bucks, Wycombe) from April 2020.
- E06000061 (North Yorkshire UA) replaced several North Yorkshire districts from April 2023.
- Several Cumbrian districts were replaced by E06000063 (Cumberland) and E06000064 (Westmorland and Furness) in April 2023.

The lookup table `sql/lad_changes_lookup.sql` maps old codes to new codes. The `analytical_base` view forward-fills old-code data into the current code boundary.

### Download Script

```bash
# scripts/download_data.sh
# Run this from the repo root to fetch all real source files.
# Requires: curl, unzip, python3

set -e
DATA_RAW="data/raw"
mkdir -p "$DATA_RAW"

echo "1/5 Downloading UK HPI Average Prices..."
curl -L -o "$DATA_RAW/UK_HPI_Average_Prices_2024-06.csv" \
  "https://publicdata.landregistry.gov.uk/market-trend-data/house-price-index-data/Average-prices-2024-06.csv"

echo "2/5 Downloading ONS ASHE Table 8 (2024 revised)..."
curl -L -o "$DATA_RAW/ashetable82024revised.zip" \
  "https://www.ons.gov.uk/file?uri=/employmentandlabourmarket/peopleinwork/earningsandworkinghours/datasets/placeofresidencebylocalauthorityashetable8/2024revised/ashetable82024revised.zip"
unzip -q -o "$DATA_RAW/ashetable82024revised.zip" -d "$DATA_RAW/ashe_table8"

echo "3/5 Downloading ONS LAD Boundaries GeoJSON..."
curl -L -o "$DATA_RAW/LAD_Dec2023_UK_BGC.geojson" \
  "https://opendata.arcgis.com/api/v3/datasets/de420de4545f4e82b4e26b89424ede53_0/downloads/data?format=geojson&spatialRefId=4326&where=1=1"

echo "4/5 BoE Bank Rate and mortgage series require manual browser export from:"
echo "    https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp"
echo "    Series codes: IUDBEDR (Bank Rate), IUMBV34 (75% LTV), IUMBV42 (90% LTV)"
echo "    Place CSV exports in data/raw/"

echo "5/5 FCA Mortgage Lending Statistics:"
echo "    https://www.fca.org.uk/data/mortgage-lending-statistics"
echo "    Download the latest quarterly Excel and place in data/raw/"

echo ""
echo "After downloading, re-run the ingestion:"
echo "  python scripts/parse_ashe.py"
echo "  python scripts/ingest.sh"
```
