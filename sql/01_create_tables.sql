-- =============================================================================
-- UK Mortgage Stress Platform — Schema DDL
-- Engine: PostgreSQL 14+
-- Run:    psql -U postgres -d housing_affordability -f sql/01_create_tables.sql
-- =============================================================================

-- Drop and recreate (idempotent)
DROP TABLE IF EXISTS hpi_average_prices CASCADE;
DROP TABLE IF EXISTS ashe_earnings CASCADE;
DROP TABLE IF EXISTS boe_bank_rate CASCADE;
DROP TABLE IF EXISTS boe_mortgage_rates CASCADE;
DROP TABLE IF EXISTS fca_ltv_distribution CASCADE;
DROP TABLE IF EXISTS lad_lookup CASCADE;
DROP VIEW  IF EXISTS analytical_base CASCADE;

-- LAD lookup / harmonisation table
CREATE TABLE lad_lookup (
    lad_code        CHAR(9)      NOT NULL PRIMARY KEY,
    lad_name        VARCHAR(100) NOT NULL,
    region          VARCHAR(60),
    nation          CHAR(1),          -- E / W / S / N
    successor_code  CHAR(9),          -- NULL if still active; else points to merged successor
    effective_from  DATE,
    effective_to    DATE
);

-- UK HPI average prices (monthly, by LAD)
CREATE TABLE hpi_average_prices (
    id              BIGSERIAL    PRIMARY KEY,
    date            DATE         NOT NULL,
    lad_code        CHAR(9)      NOT NULL REFERENCES lad_lookup(lad_code),
    lad_name        VARCHAR(100),
    region          VARCHAR(60),
    nation          CHAR(1),
    average_price   NUMERIC(12,2) NOT NULL,
    UNIQUE (date, lad_code)
);
CREATE INDEX idx_hpi_date     ON hpi_average_prices(date);
CREATE INDEX idx_hpi_ladcode  ON hpi_average_prices(lad_code);

-- ASHE Table 8 — median gross annual earnings by LAD (annual, survey year)
CREATE TABLE ashe_earnings (
    id              SERIAL       PRIMARY KEY,
    survey_year     SMALLINT     NOT NULL,
    lad_code        CHAR(9)      NOT NULL REFERENCES lad_lookup(lad_code),
    lad_name        VARCHAR(100),
    region          VARCHAR(60),
    nation          CHAR(1),
    median_gross_annual_earnings  NUMERIC(10,2),
    UNIQUE (survey_year, lad_code)
);
CREATE INDEX idx_ashe_year    ON ashe_earnings(survey_year);
CREATE INDEX idx_ashe_lad     ON ashe_earnings(lad_code);

-- Bank of England official Bank Rate (monthly)
CREATE TABLE boe_bank_rate (
    date            DATE         PRIMARY KEY,
    bank_rate       NUMERIC(6,4) NOT NULL
);

-- Bank of England mortgage rates (monthly)
CREATE TABLE boe_mortgage_rates (
    date            DATE         PRIMARY KEY,
    bank_rate       NUMERIC(6,4),
    rate_2yr_90ltv  NUMERIC(6,4),   -- 2yr fixed, 90% LTV (IUMBV42 equivalent)
    rate_2yr_75ltv  NUMERIC(6,4)    -- 2yr fixed, 75% LTV (IUMBV34 equivalent)
);

-- FCA Mortgage Lending Statistics — LTV distribution
CREATE TABLE fca_ltv_distribution (
    ltv_band        VARCHAR(10)  PRIMARY KEY,
    ftb_pct         NUMERIC(5,2),        -- % of first-time buyer completions
    homemover_pct   NUMERIC(5,2)
);

COMMENT ON TABLE hpi_average_prices    IS 'HM Land Registry UK HPI Average Prices, Jun 2024 edition';
COMMENT ON TABLE ashe_earnings         IS 'ONS ASHE Table 8 median gross earnings by LAD, 2024 revised';
COMMENT ON TABLE boe_bank_rate         IS 'BoE official Bank Rate history (series IUDBEDR), monthly';
COMMENT ON TABLE boe_mortgage_rates    IS 'BoE 2yr fixed mortgage rates 75/90 LTV (IUMBV34/IUMBV42), monthly';
COMMENT ON TABLE fca_ltv_distribution  IS 'FCA Mortgage Lending Stats Q2 2024 — FTB LTV distribution';
