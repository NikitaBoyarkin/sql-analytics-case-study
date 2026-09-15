-- 17. Weekly user lifecycle composition.
-- Question: What is the weekly mix of new / returning / resurrecting / dormant
--   users, and how does growth quality evolve?
-- Approach: weekly grain (Monday-start). A user-week is: new = first-ever
--   activity; returning = active this week and last week; resurrecting = active
--   this week, inactive last week, active before; dormant = active last week
--   but not this week. These are the standard product-analytics states.

WITH active AS (
    SELECT DISTINCT user_id, DATE_TRUNC('week', event_time) AS wk
    FROM events
),
first_seen AS (
    SELECT user_id, MIN(wk) AS first_wk FROM active GROUP BY user_id
),
flagged AS (
    SELECT a.user_id, a.wk, f.first_wk,
           LAG(a.wk) OVER (PARTITION BY a.user_id ORDER BY a.wk) AS prev_wk,
           LEAD(a.wk) OVER (PARTITION BY a.user_id ORDER BY a.wk) AS next_wk
    FROM active a
    JOIN first_seen f ON f.user_id = a.user_id
),
states AS (
    SELECT wk,
           COUNT(*) FILTER (WHERE wk = first_wk)                                  AS new_users,
           COUNT(*) FILTER (WHERE prev_wk = wk - INTERVAL 7 DAY)                  AS returning_users,
           COUNT(*) FILTER (WHERE wk > first_wk
                             AND (prev_wk IS NULL OR prev_wk < wk - INTERVAL 7 DAY)) AS resurrecting_users
    FROM flagged
    GROUP BY wk
),
dormant AS (
    SELECT wk + INTERVAL 7 DAY AS wk, COUNT(*) AS dormant_users
    FROM flagged
    WHERE next_wk IS DISTINCT FROM wk + INTERVAL 7 DAY
    GROUP BY wk + INTERVAL 7 DAY
)
SELECT s.wk,
       s.new_users,
       s.returning_users,
       s.resurrecting_users,
       COALESCE(d.dormant_users, 0) AS dormant_users,
       s.new_users + s.returning_users + s.resurrecting_users AS active_users,
       ROUND(100.0 * s.new_users        / (s.new_users + s.returning_users + s.resurrecting_users), 1) AS new_pct,
       ROUND(100.0 * s.returning_users  / (s.new_users + s.returning_users + s.resurrecting_users), 1) AS returning_pct,
       ROUND(100.0 * s.resurrecting_users / (s.new_users + s.returning_users + s.resurrecting_users), 1) AS resurrecting_pct,
       ROUND(100.0 * COALESCE(d.dormant_users, 0) / (s.new_users + s.returning_users + s.resurrecting_users), 1) AS dormant_pct
FROM states s
LEFT JOIN dormant d ON d.wk = s.wk
ORDER BY s.wk;