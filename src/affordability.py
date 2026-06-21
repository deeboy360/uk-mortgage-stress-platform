"""
src/affordability.py
====================
Affordability ratio modelling for the UK Mortgage Stress Platform.

Median-Buyer Persona Assumptions (documented here, referenced in README):
  - Income:   Regional median gross annual earnings (ONS ASHE Table 8, place of residence)
  - Deposit:  10% of purchase price (→ 90% LTV)
               Rationale: FCA Mortgage Lending Statistics Q2 2024 show 29.3% of FTBs
               at 86-90% LTV; weighted mean FTB LTV ≈ 79.9% but 90% is the conservative
               stress assumption (top of the dominant FTB LTV band).
  - Property: Regional average house price (HM Land Registry UK HPI)
  - Term:     25 years (300 months), capital repayment mortgage
  - Rate:     Prevailing 2yr fixed, 90% LTV (BoE IADB series IUMBV42 equivalent)
"""

import numpy as np
import pandas as pd


# ── Constants ─────────────────────────────────────────────────────────────────
LTV               = 0.90    # loan-to-value ratio
DEPOSIT_PCT       = 1 - LTV # 10% deposit
TERM_MONTHS       = 300     # 25 years × 12 months


def monthly_repayment(principal: float, annual_rate_pct: float, term_months: int = TERM_MONTHS) -> float:
    """
    Standard amortising mortgage repayment formula.

    M = P × [r(1+r)^n] / [(1+r)^n - 1]

    Parameters
    ----------
    principal        : float — initial loan amount (£)
    annual_rate_pct  : float — annual interest rate as percentage (e.g. 5.5 for 5.5%)
    term_months      : int   — mortgage term in months (default 300 = 25 years)

    Returns
    -------
    float — monthly repayment (£)
    """
    r = (annual_rate_pct / 100.0) / 12.0   # monthly rate
    if r == 0:
        return principal / term_months
    n = term_months
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def amortise_balance(principal: float, annual_rate_pct: float,
                     term_months: int = TERM_MONTHS) -> np.ndarray:
    """
    Return the outstanding balance at the end of each month.

    Parameters
    ----------
    principal        : float — initial loan amount (£)
    annual_rate_pct  : float — annual interest rate as percentage
    term_months      : int   — total term in months

    Returns
    -------
    np.ndarray shape (term_months,) — outstanding balance at end of each period
    """
    r = (annual_rate_pct / 100.0) / 12.0
    M = monthly_repayment(principal, annual_rate_pct, term_months)
    balances = np.zeros(term_months)
    bal = principal
    for t in range(term_months):
        interest   = bal * r
        repaid     = M - interest
        bal       -= repaid
        balances[t] = max(bal, 0.0)
    return balances


def compute_affordability(row: pd.Series) -> pd.Series:
    """
    Compute all affordability metrics for a single analytical_base row.

    Returns a Series with additional columns:
        deposit, mortgage_balance, monthly_repayment, repayment_pct_income
    """
    price    = row["average_price"]
    earnings = row["median_annual_earnings"]
    rate_pct = row["rate_2yr_90ltv"]

    deposit          = price * DEPOSIT_PCT
    mortgage_balance = price * LTV
    M                = monthly_repayment(mortgage_balance, rate_pct)
    monthly_income   = earnings / 12.0
    repayment_pct    = (M / monthly_income * 100.0) if monthly_income > 0 else np.nan

    return pd.Series({
        "deposit":              round(deposit, 2),
        "mortgage_balance":     round(mortgage_balance, 2),
        "monthly_repayment":    round(M, 2),
        "repayment_pct_income": round(repayment_pct, 2),
    })


def build_affordability_table(ab: pd.DataFrame) -> pd.DataFrame:
    """
    Apply affordability calculations to the full analytical_base DataFrame.
    Drops rows with missing price, earnings, or mortgage rate.
    """
    cols_needed = ["average_price", "median_annual_earnings", "rate_2yr_90ltv"]
    df = ab.dropna(subset=cols_needed).copy()

    aff = df.apply(compute_affordability, axis=1)
    return pd.concat([df, aff], axis=1)
