"""
src/monte_carlo.py
==================
Monte Carlo simulation engine for the UK Mortgage Stress Platform.

Core model
----------
Monthly house price returns are drawn from a Normal distribution:

    r_t ~ N(μ, σ²)

Prices evolve multiplicatively (geometric Brownian motion, discrete):

    P_t = P_{t-1} × exp(r_t)

This ensures prices are always positive and the final-month distribution is
right-skewed (approximately log-normal) — as required by the validation check.

The mortgage balance is amortised deterministically month-by-month at the
prevailing mortgage rate (no stochastic interest rates within a scenario;
rate scenarios are handled at the run level in Phase 6).

Negative equity is flagged whenever P_t < outstanding_balance_t at any point
in the 60-month horizon. Probability is the fraction of paths that triggered
the event across N_SIMS simulations.

Known limitations (documented, not hidden)
------------------------------------------
1. Returns are modelled as Normal. Real UK house prices exhibit fat tails and
   negative skewness during crashes. The 2008–2009 London peak-to-trough was
   ~18% (HPI); our simulated 5th-percentile 5-year path for London is checked
   against this as a sanity check.
2. Correlation between regions is ignored (each region simulated independently).
3. Deposit is fixed at 10% (90% LTV) throughout — no dynamic LTV adjustment.
4. The model ignores transaction costs, stamp duty, and second-charge debt.
"""

import numpy as np
import pandas as pd
from typing import Tuple


# ── Defaults ──────────────────────────────────────────────────────────────────
N_SIMS       = 10_000   # number of price paths per region
HORIZON      = 60       # months (5 years)
TERM_MONTHS  = 300      # mortgage term (25 years)
LTV          = 0.90     # loan-to-value ratio for median buyer persona
RANDOM_SEED  = 42


def _amortise_schedule(principal: float, annual_rate_pct: float,
                        term_months: int = TERM_MONTHS) -> np.ndarray:
    """
    Return array of outstanding balance at end of each month (length = term_months).
    Vectorised — no Python loop.
    """
    r = (annual_rate_pct / 100.0) / 12.0
    if r == 0:
        n = np.arange(1, term_months + 1)
        return principal * (1 - n / term_months)
    n      = np.arange(term_months)
    factor = (1 + r) ** n
    M      = principal * r * (1 + r) ** term_months / ((1 + r) ** term_months - 1)
    return np.maximum(principal * factor - M * (factor - 1) / r, 0.0)


def simulate_region(
    current_price:    float,
    monthly_drift:    float,
    monthly_vol:      float,
    mortgage_rate_pct:float,
    ltv:              float = LTV,
    n_sims:           int   = N_SIMS,
    horizon:          int   = HORIZON,
    term_months:      int   = TERM_MONTHS,
    seed:             int   = RANDOM_SEED,
) -> dict:
    """
    Simulate n_sims house-price paths over `horizon` months for one region.

    Parameters
    ----------
    current_price     : float — observed average price at simulation start (£)
    monthly_drift     : float — calibrated monthly trend growth rate (from STL)
    monthly_vol       : float — calibrated monthly residual std as fraction of price
    mortgage_rate_pct : float — annual mortgage rate at 90% LTV (%)
    ltv               : float — loan-to-value ratio (default 0.90)
    n_sims            : int   — number of Monte Carlo paths
    horizon           : int   — forecast horizon in months
    term_months       : int   — mortgage amortisation term
    seed              : int   — random seed for reproducibility

    Returns
    -------
    dict with keys:
        prob_negative_equity  : float in [0, 1]
        paths                 : np.ndarray shape (n_sims, horizon) — price paths
        balance_schedule      : np.ndarray shape (horizon,) — mortgage balances
        params_used           : dict — inputs echo for traceability
    """
    rng = np.random.default_rng(seed)

    # ── Mortgage amortisation (deterministic) ─────────────────────────────────
    principal       = current_price * ltv
    full_schedule   = _amortise_schedule(principal, mortgage_rate_pct, term_months)
    balance_horizon = full_schedule[:horizon]   # first 60 months

    # ── Price simulation ──────────────────────────────────────────────────────
    # Draw returns: shape (n_sims, horizon)
    # Each monthly return r_t ~ N(monthly_drift, monthly_vol^2)
    returns = rng.normal(loc=monthly_drift, scale=monthly_vol, size=(n_sims, horizon))

    # Cumulative sum of log-returns, then exponentiate for multiplicative compounding
    log_price_changes = np.cumsum(returns, axis=1)          # (n_sims, horizon)
    paths = current_price * np.exp(log_price_changes)       # (n_sims, horizon)

    # ── Negative equity detection ─────────────────────────────────────────────
    # Flag a path if simulated price < outstanding balance at ANY point in horizon
    # balance_horizon broadcast: (1, horizon) vs (n_sims, horizon)
    neg_equity_mask = paths < balance_horizon[np.newaxis, :]  # (n_sims, horizon)
    any_neg_equity  = neg_equity_mask.any(axis=1)              # (n_sims,) bool
    prob_neg_equity = float(any_neg_equity.mean())

    return {
        "prob_negative_equity": prob_neg_equity,
        "paths":                paths,
        "balance_schedule":     balance_horizon,
        "params_used": {
            "current_price":     current_price,
            "monthly_drift":     monthly_drift,
            "monthly_vol":       monthly_vol,
            "mortgage_rate_pct": mortgage_rate_pct,
            "ltv":               ltv,
            "n_sims":            n_sims,
            "horizon":           horizon,
        },
    }


def run_all_regions(
    ab:               pd.DataFrame,
    stl_params:       pd.DataFrame,
    mortgage_rate_pct:float,
    scenario_label:   str,
    ltv:              float = LTV,
    n_sims:           int   = N_SIMS,
    horizon:          int   = HORIZON,
) -> pd.DataFrame:
    """
    Run simulate_region() for every LAD in the analytical_base.

    For LADs not in stl_params, fall back to their region's mean drift/vol.
    """
    # Use Jun 2024 snapshot
    latest = ab[ab["month_date"] == ab["month_date"].max()].copy()

    # Build region fallback params from stl_params regional averages
    stl_params_copy = stl_params.copy()
    # If stl_params has lad-level data use it; else compute regional means
    region_means = (latest.merge(stl_params_copy[["lad_code","monthly_drift","residual_monthly_vol"]],
                                  on="lad_code", how="left")
                    .groupby("region")[["monthly_drift","residual_monthly_vol"]]
                    .transform("mean"))

    merged = latest.merge(stl_params_copy[["lad_code","monthly_drift","residual_monthly_vol"]],
                           on="lad_code", how="left")
    merged["monthly_drift"]         = merged["monthly_drift"].fillna(region_means["monthly_drift"])
    merged["residual_monthly_vol"]  = merged["residual_monthly_vol"].fillna(
        region_means["residual_monthly_vol"])

    results = []
    for _, row in merged.iterrows():
        price = row["average_price"]
        drift = row["monthly_drift"]
        vol   = row["residual_monthly_vol"]

        if pd.isna(price) or pd.isna(drift) or pd.isna(vol):
            continue

        sim = simulate_region(
            current_price=price,
            monthly_drift=drift,
            monthly_vol=vol,
            mortgage_rate_pct=mortgage_rate_pct,
            ltv=ltv,
            n_sims=n_sims,
            horizon=horizon,
            seed=RANDOM_SEED,
        )
        results.append({
            "lad_code":             row["lad_code"],
            "lad_name":             row["lad_name"],
            "region":               row["region"],
            "nation":               row["nation"],
            "current_price":        price,
            "median_annual_earnings": row.get("median_annual_earnings", np.nan),
            "price_to_income_ratio": row.get("price_to_income_ratio", np.nan),
            "mortgage_balance":     price * ltv,
            "mortgage_rate_pct":    mortgage_rate_pct,
            "scenario":             scenario_label,
            "prob_negative_equity": sim["prob_negative_equity"],
            "monthly_drift":        drift,
            "monthly_vol":          vol,
        })

    return pd.DataFrame(results)
