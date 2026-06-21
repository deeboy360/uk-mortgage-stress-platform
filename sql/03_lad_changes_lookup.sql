-- =============================================================================
-- UK Mortgage Stress Platform — LAD boundary change harmonisation
-- Sources: ONS Open Geography Portal "Local Authority District Changes"
--          https://geoportal.statistics.gov.uk/
-- =============================================================================
-- Key changes 2020-2023:
--   Apr 2020: Buckinghamshire UA (E06000060) absorbed Aylesbury Vale, Chiltern,
--             South Bucks, Wycombe
--   Apr 2023: North Yorkshire UA (E06000065) absorbed several districts
--   Apr 2023: Cumbrian restructure → Cumberland (E06000063) +
--             Westmorland and Furness (E06000064)
-- =============================================================================

-- Example: mark Aylesbury Vale as superseded
UPDATE lad_lookup
SET    successor_code = 'E06000060',
       effective_to   = '2020-04-01'
WHERE  lad_code IN ('E07000004','E07000005','E07000006','E07000007');

-- Buckinghamshire UA row should already be in lad_lookup with no successor
UPDATE lad_lookup
SET    effective_from = '2020-04-01'
WHERE  lad_code = 'E06000060';

-- Note: For the project's 2010-2024 HPI series, district-level data is available
-- up to the boundary change date and UA-level data from that date forward.
-- The analytical_base view handles this transparently because:
--   (a) hpi_average_prices stores each LAD under its code at time of publication
--   (b) lad_lookup.successor_code routes old codes to new in aggregations
