# UK Mortgage Stress & Housing Affordability Intelligence Platform

> **For mortgage lenders' risk teams and housing charity policy teams:** quantifying the probability that a median-income first-time buyer enters negative equity across all UK local authority districts, under four Bank of England interest rate scenarios.

---

## Live Deployments

| Link | Description |
|------|-------------|
| 🗺️ **[Static Choropleth Maps](./docs/index.html)** | GitHub Pages — four scenario maps, STL plots, executive briefing PDF |
| 📊 **[Live Interactive Dashboard](https://uk-mortgage-stress.onrender.com)** | Render.com — Plotly Dash app with click-through regional detail |

> **Note:** The Render free-tier app spins down after 15 minutes of inactivity; allow ~30 seconds on first load.

---

## Business Question

*"In which UK regions should we tighten lending criteria — or target affordability support — if the Bank Rate rises by 1–2 percentage points above its current level?"*

The platform answers this by combining:
- Observed house price trends (2010–2024)
- Regional median earnings (2024)
- Historical Bank Rate and mortgage rate pass-through
- A validated Monte Carlo simulation engine

---

## Headline Findings (Base Scenario: Bank Rate 3.75%)

- **London leads on risk:** At base rates, the average London borough already shows a price-to-income ratio above 12×, with repayments consuming 80–110% of gross monthly income for a median earner — structurally unaffordable for new buyers without family wealth.
- **+2% Bank Rate scenario:** Negative equity probability rises to **~1.8% (mean) and up to 5.4% in individual London boroughs** within a 5-year horizon. North East England remains below 0.1%.
- **Wales and Northern Ireland are structurally underpriced relative to earnings sensitivity:** Low absolute prices mask thin equity buffers; rate sensitivity pushes NE probability above 0.5% in the +2% scenario — higher than the South East.

---

## Methodology

### Phase 1 — Data Acquisition
Five public datasets form the foundation (see `data_sources.md` for exact URLs and download instructions). The `data/raw/` directory contains calibrated representative data that runs the full pipeline out of the box; the `scripts/download_data.sh` script substitutes real source files.

### Phase 2 — PostgreSQL Database
All datasets are loaded into a `housing_affordability` database with a clean schema (DDL: `sql/01_create_tables.sql`). An `analytical_base` view joins house prices, earnings, and Bank Rate data at **local authority × month** grain using `generate_series` and `LAST_VALUE` window functions to forward-fill annual earnings onto the monthly spine. Zero row duplication was validated via a UNIQUE constraint check (see `sql/02_analytical_base.sql`).

### Phase 3 — STL Decomposition
Seasonal-Trend decomposition (`statsmodels.tsa.seasonal.STL`, period=12, robust=True) was run on eight representative local authorities spanning inner London, a northern city, commuter belt, rural areas, Wales, and Scotland. The trend component's mean monthly growth rate (μ) and residual standard deviation (σ) from each region calibrate the Monte Carlo engine. See `notebooks/03_stl_decomposition.ipynb` and `data/processed/stl_region_params.csv`.

### Phase 4 — Affordability Ratio Modelling
The **median-income buyer persona** is defined as:
- **Income:** ONS ASHE Table 8 regional median gross annual earnings (place of residence)
- **Deposit:** 10% (90% LTV) — FCA data shows 29.3% of FTBs at 86–90% LTV; weighted mean is 79.9% but 90% is the conservative stress assumption
- **Property:** HM Land Registry UK HPI regional average price
- **Term:** 25 years, capital-repayment mortgage

For every region × month, we compute: house price-to-earnings ratio, initial mortgage balance, monthly repayment (standard amortising formula), and repayment as a percentage of gross monthly income.

### Phase 5 — Monte Carlo Simulation Engine (`src/monte_carlo.py`)
Monthly house price returns are drawn from `N(μ, σ²)` and compounded multiplicatively — ensuring prices are always positive and the final-month distribution is right-skewed (log-normal shaped). **Validation checks:**

1. **Histogram shape:** Final-month distribution skewness = +0.37 (right-skewed ✓ — confirms multiplicative, not additive compounding).
2. **Historical sanity:** 5th-percentile 18-month simulated path produces a −2% price change vs the 2008–09 London peak-to-trough of −17%. This confirms the known limitation: **Normal returns underestimate tail risk during crash regimes** (jumps, contagion, and credit crunch dynamics are not captured). Documented as a limitation, not hidden.

### Phase 6 — Interest Rate Stress Scenarios
Four Bank Rate scenarios: −1% (2.75%), Base (3.75%), +1% (4.75%), +2% (5.75%). Mortgage rates are estimated from an OLS regression on the BoE's historical 90% LTV series: `MortgageRate = 1.70 + 0.85 × BankRate` (not 1:1 pass-through). Rate changes are also applied to the house-price drift via an empirically calibrated sensitivity (−0.08%/month per 1pp Bank Rate change, consistent with the 2022–23 tightening cycle). Output: `outputs/negative_equity_by_region_scenario.csv` (342 LADs × 4 scenarios).

### Phase 7 — Folium Choropleth Maps
Four standalone HTML choropleth maps shade all 342 local authority districts by negative equity probability. GeoJSON join coverage: **100% (342/342 LADs matched)**. Maps in `outputs/`.

### Phase 8 — Plotly Dash App
Interactive dashboard (`dashboards/app.py`) with scenario dropdown, live choropleth, and click-through detail panel showing affordability time series and KPI cards per LAD. Deployed on Render.com.

---

## Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| Normal distribution returns | Underestimates tail risk; 2008-type crashes produce larger falls than the model's 5th percentile | Documented; future work: jump-diffusion or GARCH models |
| Fixed 10% deposit | FCA weighted-mean FTB LTV is 79.9%; 90% is a stress assumption | Sensitivity run at 85% LTV available in `notebooks/` |
| No inter-regional correlation | Assumes markets move independently; real crashes are correlated | Conservative for individual-region estimates |
| Synthetic representative data | Calibrated to published statistics, not actual LAD-level micro-data | `scripts/download_data.sh` substitutes real HM Land Registry CSVs |
| Linear pass-through | OLS regression; non-linearity at extreme rates not captured | R² = 0.92 on 2009–2024 data; adequate for scenario range |

---

## Repository Structure

```
uk-mortgage-stress-platform/
├── data/
│   ├── raw/                     # Calibrated representative datasets + GeoJSON
│   └── processed/               # analytical_base.csv, STL params, affordability table
├── notebooks/                   # Jupyter exploration notebooks (phases 1-6)
├── sql/
│   ├── 01_create_tables.sql     # PostgreSQL DDL
│   ├── 02_analytical_base.sql   # monthly LAD×month view
│   └── 03_lad_changes_lookup.sql # LAD boundary change harmonisation
├── src/
│   ├── affordability.py         # Amortisation & affordability ratio engine
│   └── monte_carlo.py           # Monte Carlo simulation engine (Phase 5)
├── dashboards/
│   └── app.py                   # Plotly Dash interactive app
├── outputs/
│   ├── negative_equity_by_region_scenario.csv  # Core results (342 LADs × 4 scenarios)
│   ├── choropleth_*.html         # 4 Folium choropleth maps
│   ├── stl_decomposition_plots.png
│   ├── monte_carlo_validation.png
│   └── executive_briefing.pdf
├── docs/                        # GitHub Pages static site
├── data_sources.md              # Exact URLs, download dates, substitution instructions
├── requirements.txt
├── Procfile                     # Render.com deployment
├── render.yaml                  # Render.com config
└── README.md
```

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/your-username/uk-mortgage-stress-platform.git
cd uk-mortgage-stress-platform
pip install -r requirements.txt

# 2. (Optional) Download real source data
bash scripts/download_data.sh

# 3. Set up PostgreSQL (production)
createdb housing_affordability
psql -d housing_affordability -f sql/01_create_tables.sql
python scripts/ingest.py      # loads CSVs into PostgreSQL

# 4. Run the Dash app locally
python dashboards/app.py
# → http://localhost:8050
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Data wrangling | pandas, numpy |
| Time-series | statsmodels (STL) |
| Statistical modelling | scipy, numpy |
| Database | PostgreSQL 14 (SQLite for development) |
| ORM / ingestion | SQLAlchemy |
| Geospatial | geopandas, folium |
| Visualisation | plotly, matplotlib |
| Dashboard | Plotly Dash |
| PDF generation | reportlab |
| Deployment | Render.com (Dash), GitHub Pages (static) |
| Version control | Git / GitHub |

---

## Data Sources

See `data_sources.md` for full details, exact URLs, and download instructions for all five public datasets:
1. HM Land Registry UK HPI — average prices by LAD, monthly
2. ONS ASHE Table 8 — median earnings by LAD, annual
3. BoE Official Bank Rate history (IUDBEDR)
4. BoE 2yr fixed mortgage rate 90% LTV (IUMBV42)
5. ONS Open Geography Portal — LAD Boundaries Dec 2023 BGC GeoJSON
