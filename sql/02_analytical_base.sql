-- =============================================================================
-- UK Mortgage Stress Platform — analytical_base VIEW
-- Engine: PostgreSQL 14+
-- =============================================================================
-- Grain: local_authority_code × month
-- Strategy:
--   • Generate a monthly date spine using generate_series()
--   • Join HPI prices (already monthly) directly
--   • Forward-fill ASHE earnings (annual) onto the monthly spine using
--     the most recent available survey_year for each month via LAG/LAST_VALUE
--   • Join BoE mortgage rates (already monthly) directly
-- =============================================================================

DROP VIEW IF EXISTS analytical_base CASCADE;

CREATE OR REPLACE VIEW analytical_base AS

WITH

-- 1. Date spine: one row per month, Jan 2010 – Jun 2024
date_spine AS (
    SELECT generate_series(
               '2010-01-01'::DATE,
               '2024-06-01'::DATE,
               '1 month'::INTERVAL
           )::DATE AS month_date
),

-- 2. LAD × month cross-join (all active LADs)
lad_spine AS (
    SELECT
        l.lad_code,
        l.lad_name,
        l.region,
        l.nation,
        d.month_date
    FROM   lad_lookup l
    CROSS JOIN date_spine d
    WHERE  l.successor_code IS NULL   -- active LADs only
),

-- 3. ASHE earnings: forward-fill annual data onto monthly spine
--    For each (lad_code, month_date), take earnings from the most recent
--    survey year that is <= that month's year
ashe_filled AS (
    SELECT
        ls.lad_code,
        ls.month_date,
        -- LAST_VALUE over the ordered window gives us the most recent annual value
        LAST_VALUE(ae.median_gross_annual_earnings IGNORE NULLS)
            OVER (
                PARTITION BY ls.lad_code
                ORDER BY ls.month_date
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS median_annual_earnings
    FROM   lad_spine ls
    LEFT JOIN ashe_earnings ae
           ON ae.lad_code   = ls.lad_code
          AND ae.survey_year = EXTRACT(YEAR FROM ls.month_date)::SMALLINT
),

-- 4. Assemble final base table
base AS (
    SELECT
        ls.lad_code,
        ls.lad_name,
        ls.region,
        ls.nation,
        ls.month_date,

        -- HPI
        h.average_price,

        -- Earnings (forward-filled annual → monthly)
        af.median_annual_earnings,
        af.median_annual_earnings / 12.0    AS median_monthly_earnings,

        -- Bank rate & mortgage rate
        mr.bank_rate,
        mr.rate_2yr_90ltv                   AS mortgage_rate_90ltv,
        mr.rate_2yr_75ltv                   AS mortgage_rate_75ltv,

        -- Derived: house price-to-earnings ratio (PTI)
        CASE
            WHEN af.median_annual_earnings > 0
            THEN h.average_price / af.median_annual_earnings
        END AS price_to_income_ratio

    FROM   lad_spine          ls
    JOIN   hpi_average_prices h  ON h.lad_code   = ls.lad_code
                                 AND h.date        = ls.month_date
    JOIN   ashe_filled        af ON af.lad_code   = ls.lad_code
                                 AND af.month_date = ls.month_date
    LEFT JOIN boe_mortgage_rates mr ON mr.date = ls.month_date
)

SELECT * FROM base
ORDER BY lad_code, month_date;

-- Row-count guard query (run manually after CREATE VIEW):
-- SELECT COUNT(*) FROM analytical_base;
-- Expected ≈ 342 LADs × 174 months = 59,508 rows (no duplication)
-- SELECT lad_code, month_date, COUNT(*) cnt
-- FROM analytical_base
-- GROUP BY 1,2 HAVING COUNT(*) > 1;  -- should return 0 rows

COMMENT ON VIEW analytical_base IS
    'Monthly grain (lad_code × month_date). Annual ASHE earnings forward-filled via LAST_VALUE window. '
    'No duplication guaranteed by UNIQUE constraints on source tables. '
    'Expected row count: ~59,508 (342 LADs × 174 months Jan-2010 to Jun-2024).';
