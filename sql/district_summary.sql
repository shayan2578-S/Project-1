-- Each LSOA remains one row. Ratios of sums use the indicator's own universe.
-- The population-weighted access mean describes residents' area scores;
-- it does not measure an individual's actual travel experience.
SELECT district_code, district_name, study_role,
       COUNT(*) AS neighbourhoods,
       COUNT(access_pt) AS access_observed,
       SUM(CAST(priority_eligible AS INTEGER)) AS priority_eligible,
       SUM(CAST(triple_priority AS INTEGER)) AS triple_priority_count,
       SUM(population_total) AS census_population,
       AVG(access_pt) AS unweighted_mean_access,
       MEDIAN(access_pt) AS median_access,
       QUANTILE_CONT(access_pt, 0.1) AS p10_access,
       QUANTILE_CONT(access_pt, 0.9) AS p90_access,
       SUM(access_pt * population_total) FILTER (WHERE access_pt IS NOT NULL AND population_total > 0)
         / NULLIF(SUM(population_total) FILTER (WHERE access_pt IS NOT NULL AND population_total > 0), 0)
         AS population_weighted_mean_access,
       SUM(population_total) FILTER (WHERE access_pt IS NOT NULL AND population_total > 0)
         / NULLIF(SUM(population_total) FILTER (WHERE population_total > 0), 0) AS access_population_coverage,
       AVG(no_car_pct) AS mean_neighbourhood_no_car_pct,
       100.0 * SUM(households_no_car) FILTER (WHERE households_no_car IS NOT NULL AND households_total > 0)
         / NULLIF(SUM(households_total) FILTER (WHERE households_no_car IS NOT NULL AND households_total > 0), 0)
         AS household_no_car_pct,
       AVG(income_pct) AS mean_neighbourhood_income_pct,
       SUM(income_rate * income_population) FILTER (WHERE income_rate IS NOT NULL AND income_population > 0)
         / NULLIF(SUM(income_population) FILTER (WHERE income_rate IS NOT NULL AND income_population > 0), 0) * 100
         AS income_denominator_weighted_pct,
       100.0 * SUM(unemployed_16plus) FILTER (WHERE unemployed_16plus IS NOT NULL AND active_16plus > 0)
         / NULLIF(SUM(active_16plus) FILTER (WHERE unemployed_16plus IS NOT NULL AND active_16plus > 0), 0)
         AS unemployment_pct
FROM neighbourhoods
GROUP BY district_code, district_name, study_role
ORDER BY study_role DESC, district_name;
