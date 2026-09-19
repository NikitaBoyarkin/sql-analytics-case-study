# SQL Case Studies — Questions & Answers

Reference notes for each case. Numbers come from the deterministic dataset
(seed = 42); regenerate with `python data/generate_data.py` to reproduce.
`tests/test_golden_answers.py` pins the key numbers here to the live database,
so the two stay in sync.

## 01 · Funnel conversion

**Q:** For each funnel step, how many sessions reached it, and what is the
step-to-step and overall conversion?

**A:** 80,000 sessions opened the app; 65,739 viewed an item (82.2%);
29,641 added to cart (45.1% of viewers); 6,584 reached checkout (22.2% of
carts); 928 purchased (14.1% of checkouts, 1.16% overall).

**Signal:** the sharpest drop is add-to-cart → checkout (54% of carts never
proceed). That is the highest-leverage step to instrument and fix.

## 02 · N-day retention by cohort

**Q:** What share of each signup-month cohort returned on exactly day 1/7/30?

**A:** D1 retention is stable at ~18.6–20.7% across cohorts; D7 ~11–16%; D30
~4.6–5.3% (0 for the June cohort — not enough observation time).

**Signal:** the sharp D1→D7 drop points at the onboarding window as the
retention bottleneck, not long-term engagement.

## 03 · Rolling 30-day retention

**Q:** What % of each cohort was active in each 30-day window starting 7/14/30/60
days after signup?

**A:** Win-7d ~90–92% (early cohorts), decaying to ~54–56% by win-30d and
~11–18% by win-60d. June is censored (52% / 26% / 0% / 0%).

**Signal:** rolling (windowed) retention is a fairer lens than point retention
for products with sporadic usage — it does not punish users who return a few
days late.

## 04 · DAU / MAU / stickiness

**Q:** Daily active users, trailing-28d MAU, and stickiness (DAU/MAU).

**A:** Stickiness starts high (~100% on day 1, MAU window still filling) then
decays toward ~7% as the MAU window fills with the full user base.

**Signal:** stickiness ≈ DAU/MAU is a frequency metric, not a reach metric.
~7% stickiness means the average user is active ~2 days/month — a sporadic-use
product, which is why rolling retention (case 03) is the fairer lens.

## 05 · LTV by cohort

**Q:** Average revenue per user by signup cohort.

**A:** LTV per user is ~$0.72–$1.52 lifetime, modest because only ~4–5% of users
ever purchase (see case 09). Revenue is ~$2.3k–$5.3k per cohort.

**Signal:** cohort LTV must be compared at the *same age*, not calendar date —
younger cohorts look smaller simply because they have had less time to spend.

## 06 · Top-3 categories per country

**Q:** Which 3 product categories bring the most revenue in each country?

**A:** `ROW_NUMBER() OVER (PARTITION BY country ORDER BY SUM(amount) DESC)`
keeps the top 3. Electronics, clothing and home dominate most markets; RU is by
far the largest revenue market.

**Signal:** use `ROW_NUMBER` (not `RANK`/`DENSE_RANK`) when you want exactly N
rows per group regardless of ties.

## 07 · Cumulative revenue

**Q:** Daily revenue and the running total.

**A:** `SUM(amount) OVER (ORDER BY d ROWS UNBOUNDED PRECEDING)` — cumulative
reaches $25,194 at the last row (June 30).

**Signal:** `ROWS` vs `RANGE` framing matters when there are duplicate order
dates; `ROWS UNBOUNDED PRECEDING` is the safe default for running totals.

## 08 · Longest active-day streak (gaps-and-islands)

**Q:** For each user, the longest run of consecutive active days.

**A:** `ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY d)`, then
`epoch_day - rn` is a constant within each consecutive run (the island key).
Group by user + island key → run length; take the max. Top streaks are 6 days.

**Signal:** the `day - row_number` trick is the canonical gaps-and-islands
pattern — it converts "consecutive" into "same group" in one pass.

## 09 · A/B conversion by variant

**Q:** Purchase conversion for control vs treatment, and is the difference
statistically significant?

**A:** control 3.77%, treatment 5.18% → +1.41pp lift. Two-proportion z-test
(pooled variance) gives **z = 4.81, p = 0.000002** → significant at α = 0.05.
The generator embeds a real treatment effect (1.25× on checkout→purchase), so
the test correctly "finds" the signal.

**Signal:** user-level conversion (~4–5%) is much higher than session-level
(~1%, case 01) — pick the unit of analysis before reporting, and do not mix
them. The p-value is computed in pure SQL via the Abramowitz–Stegun normal-CDF
approximation — no statistical library needed.

## 10 · Revenue attribution

**Q:** Revenue by acquisition channel under lifetime vs first-touch models.

**A:** organic $8,000 / referral $4,863 / social $4,508 / paid_search $3,986 /
email $3,837 (lifetime). Referral over-indexes on revenue relative to its share
of users (high retention → repeat purchases); paid_search shows more divergence
between first-touch and lifetime.

**Signal:** the gap between first-touch and lifetime revenue is itself a signal
— large gaps mark channels with repeat-purchase potential worth investing in.

## 11 · 7-day moving average of DAU

**Q:** What is day-level DAU, and the 7-day moving average that reveals the trend?

**A:** DAU grows from ~25 (early Jan) to a ~460 plateau (Mar–Jun); the 7-day MA
smooths weekly noise. `AVG(dau) OVER (ORDER BY d ROWS BETWEEN 6 PRECEDING AND
CURRENT ROW)`.

**Signal:** the MA shows steady growth then saturation — a flat end is a trend
signal, not noise. Note the data is right-truncated (not clamped), so there is
no artificial end-of-window spike.

## 12 · Top-2 revenue users per country (QUALIFY)

**Q:** Who are the two highest-revenue users in each country?

**A:** `QUALIFY ROW_NUMBER() OVER (PARTITION BY country ORDER BY revenue DESC) <= 2`
keeps exactly 2 rows per country (10 rows total). Top spenders are $70–$131.

**Signal:** `QUALIFY` is DuckDB/Postgres-16 modern syntax — it filters on window
results in the same statement, removing the wrapping subquery.

## 13 · Monthly revenue by category (PIVOT)

**Q:** How does revenue split across categories month by month?

**A:** `PIVOT` turns (month, category) long-form into one column per category.
Revenue ramps through the year; June is up across every category (~$4,452 total
in June vs ~$2,069 in Jan).

**Signal:** pivot/unpivot is the standard move for making revenue mix readable
to stakeholders; column-per-category beats a tall table for eyeballing shifts.

## 14 · Subscription MRR (recursive CTE)

**Q:** What is monthly recurring revenue from subscriptions, and how does it grow?

**A:** A recursive CTE expands each subscription into one billing row per month
(monthly = full amount; annual = amount/12, i.e. ARR/12). MRR grows from
$170 (18 subs, Jan) to $2,500 (268 subs, Jun) — ~15× in six months.

**Signal:** recursion in SQL handles "expand one row into a time series" cleanly.
MRR compounding is the durable growth engine; flat MRR would be a churn alarm.

## 15 · Order amount distribution (median / p90 / p99)

**Q:** What is the spend distribution per product category?

**A:** Medians are tight ($21–$25) but p99 reaches $63–$93 — a fat tail.
Electronics has the highest total revenue ($4,805); beauty is the most
"average" (median $24, p99 $64).

**Signal:** median (not mean) is the honest central AOV; p99 guards against
outlier orders (fraud / bulk purchases). `MEDIAN` and `QUANTILE_CONT` are the
native idioms.

## 16 · Sessionization + session depth

**Q:** Can we reconstruct sessions from raw event timestamps alone (ignoring the
pre-assigned `session_id`), and how deep is the typical session?

**A:** Gaps-and-islands on `event_time` with a 30-minute inactivity gap
reconstructs 79,700 sessions vs the 80,000 pre-assigned — **99.6% fidelity**;
298 same-day back-to-back sessions closer than 30 min get merged, **none split**.
Median session = 2 events; 74% of sessions are 2–3 events, 18% are a single
event, median duration 0 min (sub-minute bursts).

**Signal:** a session definition is a business choice, not a data fact. The
30-min gap rule reproduces ground truth almost exactly — always validate a
derivation against known ids before trusting it. Sessions are shallow bursts:
depth (events), not duration, is the engagement signal.

## 17 · Weekly lifecycle composition

**Q:** What is the weekly mix of new / returning / resurrecting / dormant users,
and how does growth quality evolve?

**A:** New users fall from 100% of the base (week 1) to ~30% and stay there;
returning stabilizes at ~37%; resurrecting grows to ~33%; dormant climbs to
~60–66% of the active base.

**Signal:** after ramp, ~1/3 of the weekly active base is *resurrecting* lapsed
users and dormant equals ~60% of active — reactivation does as much work as
acquisition. Compare the new-vs-resurrecting split to judge whether "growth" is
real or recycled lapsed users.

## 18 · Cohort revenue retention (triangle)

**Q:** How does revenue from each signup cohort decay by months-since-signup, and
does it decay as fast as activity retention (cases 02/03)?

**A:** Month-1 revenue retention is strong (~67–88% of period-0), but month-2
collapses to ~10–20% and month-3 to ~4–6%. LTV accumulates to ~$1.2–1.5 per
user by the end of observation.

**Signal:** revenue retention decays *faster* than activity retention — one
purchase is effectively lifetime. A healthy month-1 NRR followed by a third-month
cliff means monetization is a single transaction, not a repeat engine.

## 19 · Repeat purchase & time between orders

**Q:** How repeatable is purchase behavior, and how quickly do repeat buyers come
back?

**A:** 896 buyers, only **31 (3.5%)** ever return — 30 buy twice, 1 buys three
times, none 4+. Median time between purchases is 9 days (p90 = 28).

**Signal:** an honest finding — this is a one-and-done purchase engine. A 3.5%
repeat rate is the single biggest monetization lever; with ~96% single-purchase
customers, growth is entirely acquisition-dependent.

## 20 · RFM segmentation (NTILE)

**Q:** Which buyer segments deserve the most attention, and where does revenue
concentrate?

**A:** `NTILE(5)` on recency (inverted), frequency and monetary → 1–5 scores,
then label rules. Segments split buyers nearly evenly (Champions 18.5%, Loyal
20.2%, Regular 20.0%, At Risk 19.6%, Hibernating 19.2%); Big Spenders and
Promising are ~1.2% each. Revenue tracks buyer share ~1:1 — no whale tier.

**Signal:** the frequency axis barely discriminates because repeat rate is ~3.5%
(case 19) — RFM here is mostly a *recency* story, so "Loyal" vs "At Risk" is
about last-purchase timing, not loyalty. Even revenue distribution: there is no
heavy-user backbone to double down on.

## 21 · Subscription churn (logo & MRR)

**Q:** What is monthly logo and MRR churn, and how fast does the sub base leak?

**A:** Logo churn grows from 5.6% (Feb) to ~15% (Jun) as the base matures; MRR
churn tracks it closely (5.9% → 14.8%, $10 → $210/month churned). 98 of 268
subscriptions (37%) cancel within the window by design.

**Signal:** MRR churn ≈ logo churn here because plans are flat-price — the two
diverge only when pricing is heterogeneous. A ~15%/month logo churn is a churn
alarm: it means MRR compounding (case 14) is hiding a fast-leaking bucket.

## 22 · Refunds & net revenue

**Q:** How much gross revenue is refunded, and where do refunds concentrate?

**A:** 53 refunds ($1,031 of $25,194 gross, ~4.1% overall). Monthly refund rate
runs 2.2–6.0%; February is the worst (6.03%).

**Signal:** report net, not gross — the refund rate is a revenue-quality number.
~4% is normal for e-commerce; a spiking month is a trigger to inspect
fulfilment/quality, not noise to ignore.

## 23 · Pareto / revenue concentration

**Q:** Where does revenue concentrate — is there a whale tier worth productizing?

**A:** Top decile of buyers = 22.3% of revenue; top 3 deciles = 50.2%; bottom
decile = 3.5%. The heaviest decile is ~2× the lightest. No 80/20.

**Signal:** concentration is moderate — the answer to "build a VIP tier?" is no,
there are no whales. Running the Pareto check *before* building a tier saves
building a product for a segment that doesn't exist.

## 24 · Daily revenue anomaly detection

**Q:** Which days deviate significantly from their own recent baseline?

**A:** A robust (median + MAD) z-score against a trailing-14-day baseline flags
exactly 4 days at |z| ≥ 3: Jan 25 (z = 5.3), Mar 23 (3.8), Apr 7 (3.2), Jun 14
(3.2) — each ~2–3× its recent median.

**Signal:** median/MAD beats mean/std for log-normal revenue — a mean baseline
would flag high-variance days instead. 4 isolated spikes over 6 months ≈ a
promo/holiday pattern to investigate, not noise.

## 25 · Purchase → subscription conversion

**Q:** Of purchasers, who converts to a paid subscription, and how fast?

**A:** 268 of 896 purchasers subscribe (29.9%); median 3 days from first order
(p90 = 6). 197 convert to monthly, 71 to annual (~26% of conversions).

**Signal:** the upsell window is one week — subscription marketing must hit
within days of first purchase. ~26% of converts choose annual despite the bigger
commitment: the annual pitch is working and worth scaling.

## 26 · Real data — repeat purchase & revenue concentration

**Q:** On a real two-year retail dataset, what share of customers repeat, and how
concentrated is revenue?

**A** (UCI Online Retail II, 1,067,371 invoice lines, 2009-12 → 2011-12): 5,878
customers, 36,969 invoices, £17.7M revenue. **72.4%** of customers buy more than
once. Order-count buckets:

| Orders | Customers | % of customers | % of revenue |
|--------|-----------|----------------|--------------|
| 1      | 1,623     | 27.6%          | 3.2%         |
| 2      | 944       | 16.1%          | 4.6%         |
| 3–5    | 1,510     | 25.7%          | 12.0%        |
| 6–10   | 925       | 15.7%          | 15.0%        |
| 11+    | 876       | 14.9%          | 65.2%        |

Top decile of customers = **63.9%** of revenue (top 20% = 77.3%).

**Signal:** the same SQL pattern that says "one-and-done" on the synthetic engine
says the opposite on real data — this retailer is repeat- and whale-driven (14.9%
of customers carry 65% of revenue). That contrast is the point: the pattern
transfers, and the business conclusion depends on the data, not the query.

**Source & license:** UCI ML Repository, dataset 502, CC BY 4.0 — see
`data/realdata/README.md`. Reproduce: `uv run python data/realdata/build_realdata.py`.