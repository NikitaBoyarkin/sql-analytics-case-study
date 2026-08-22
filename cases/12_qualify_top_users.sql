-- 12. Top-2 revenue users per country via QUALIFY (modern DuckDB syntax).
-- Question: Who are the two highest-revenue users in each country?
-- Approach: aggregate revenue per (country, user); QUALIFY keeps only the
--   rows whose ROW_NUMBER() partition rank is <= 2, in the same statement
--   (no extra wrapping SELECT). COALESCE treats never-purchasing users as $0.
WITH user_rev AS (
    SELECT u.country, u.user_id,
           COALESCE(SUM(o.amount), 0) AS revenue
    FROM users u
    LEFT JOIN orders o ON o.user_id = u.user_id
    GROUP BY u.country, u.user_id
)
SELECT country, user_id, ROUND(revenue, 2) AS revenue
FROM user_rev
QUALIFY ROW_NUMBER() OVER (PARTITION BY country ORDER BY revenue DESC) <= 2
ORDER BY country, revenue DESC;