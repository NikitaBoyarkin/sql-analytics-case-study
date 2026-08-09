-- 04. DAU, trailing-28d MAU, and stickiness (DAU/MAU) by day.
-- Question: For each active day, how many users were active, how many were
--   active in the trailing 28 days, and the stickiness ratio?
-- Approach: DAU = distinct users per date; MAU = distinct users active in the
--   [d-27, d] window (range join over calendar); stickiness = DAU/MAU*100.
WITH calendar AS (
    SELECT DATE(event_time) AS d FROM events GROUP BY d
),
dau AS (
    SELECT DATE(event_time) AS d, COUNT(DISTINCT user_id) AS dau
    FROM events GROUP BY d
),
mau AS (
    SELECT c.d,
           COUNT(DISTINCT e.user_id) AS mau
    FROM calendar c
    JOIN events e
      ON DATE(e.event_time) BETWEEN c.d - 27 AND c.d
    GROUP BY c.d
)
SELECT d.d, d.dau, m.mau,
       ROUND(d.dau * 100.0 / m.mau, 2) AS stickiness_pct
FROM dau d JOIN mau m ON d.d = m.d
ORDER BY d.d;
