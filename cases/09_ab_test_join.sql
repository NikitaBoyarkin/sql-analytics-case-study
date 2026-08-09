-- 09. A/B test: purchase conversion by variant.
-- Question: For control vs treatment, what is the purchase-conversion rate and
--   the absolute lift in percentage points?
-- Approach: variant from users.ab_variant; purchased flag from orders;
--   conv_pct per variant; lift = treatment conv - control conv via LAG.
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
)
SELECT ab_variant, users, purchasers,
       ROUND(conv_pct, 2) AS conv_pct,
       ROUND(conv_pct - LAG(conv_pct) OVER (ORDER BY ab_variant), 2) AS lift_pp
FROM rates
ORDER BY ab_variant;
