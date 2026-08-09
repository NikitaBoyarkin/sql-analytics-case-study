-- 01. Funnel: session-level conversion.
-- Question: For each funnel step, how many sessions reached it, and what is
--   the step-to-step and overall (vs app_open) conversion?
-- Approach: count distinct sessions per event step (cumulative by funnel order),
--   step_pct = this/prev via LAG, overall_pct = this/app_open via FIRST_VALUE.
WITH step_counts AS (
    SELECT event_name, COUNT(DISTINCT session_id) AS sessions
    FROM events
    WHERE event_name IN ('app_open','view_item','add_to_cart','checkout','purchase')
    GROUP BY event_name
),
ordered AS (
    SELECT event_name, sessions,
           ROW_NUMBER() OVER (ORDER BY CASE event_name
             WHEN 'app_open' THEN 1 WHEN 'view_item' THEN 2
             WHEN 'add_to_cart' THEN 3 WHEN 'checkout' THEN 4 WHEN 'purchase' THEN 5 END) AS pos
    FROM step_counts
)
SELECT event_name, sessions,
       ROUND(sessions * 100.0 / FIRST_VALUE(sessions) OVER (ORDER BY pos), 2) AS overall_pct,
       ROUND(sessions * 100.0 / LAG(sessions) OVER (ORDER BY pos), 2) AS step_pct
FROM ordered
ORDER BY pos;
