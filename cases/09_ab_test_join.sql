-- 09. A/B test: purchase conversion by variant + statistical significance.
-- Question: Does the treatment variant lift purchase conversion, and is the
--   difference statistically significant (alpha = 0.05)?
-- Approach: per-variant user-level conversion; two-proportion z-test with
--   pooled variance; two-sided p-value from the standard normal CDF via the
--   Abramowitz-Stegun 26.2.17 approximation (|error| < 7.5e-8); verdict column.
--   (numpy/scipy-free on purpose: every case stays pure SQL.)
WITH conv AS (
    SELECT u.ab_variant,
           COUNT(DISTINCT u.user_id) AS users,
           COUNT(DISTINCT o.user_id) AS purchasers
    FROM users u
    LEFT JOIN orders o ON o.user_id = u.user_id
    GROUP BY u.ab_variant
),
rates AS (
    SELECT ab_variant, users, purchasers,
           purchasers * 100.0 / users AS conv_pct
    FROM conv
),
totals AS (
    SELECT (SELECT users      FROM rates WHERE ab_variant = 'treatment') AS n1,
           (SELECT purchasers FROM rates WHERE ab_variant = 'treatment') AS k1,
           (SELECT users      FROM rates WHERE ab_variant = 'control')  AS n0,
           (SELECT purchasers FROM rates WHERE ab_variant = 'control')  AS k0
),
test AS (
    SELECT n1, k1, n0, k0,
           k1 * 1.0 / n1 AS p1,
           k0 * 1.0 / n0 AS p0,
           (k1 + k0) * 1.0 / (n1 + n0) AS p_pool
    FROM totals
),
stats AS (
    SELECT *, (p1 - p0) / SQRT(p_pool * (1 - p_pool) * (1.0 / n1 + 1.0 / n0)) AS z
    FROM test
),
cdf AS (
    SELECT *,
           ABS(z) AS az,
           1 / (1 + 0.2316419 * ABS(z)) AS t
    FROM stats
),
phi AS (
    SELECT *,
           1 - 0.3989422804014327 * EXP(-az * az / 2)
               * (0.319381530*t - 0.356563782*t*t + 1.781477937*t*t*t
                  - 1.821255978*t*t*t*t + 1.330274429*t*t*t*t*t) AS phi_pos
    FROM cdf
)
SELECT r.ab_variant, r.users, r.purchasers,
       ROUND(r.conv_pct, 2)                AS conv_pct,
       ROUND(r.conv_pct - LAG(r.conv_pct) OVER (ORDER BY r.ab_variant), 2) AS lift_pp,
       ROUND(p.z, 2)                        AS z_score,
       ROUND(2 * (1 - p.phi_pos), 6)        AS p_value,
       CASE WHEN 2 * (1 - p.phi_pos) < 0.05 THEN 'YES' ELSE 'no' END AS significant_005
FROM rates r
CROSS JOIN phi p
ORDER BY r.ab_variant;