# SQL Case Studies — Questions & Answers

Reference notes for each case. Numbers come from the deterministic dataset
(seed = 42); regenerate with `python data/generate_data.py` to reproduce.

## 01 · Funnel conversion

**Q:** For each funnel step, how many sessions reached it, and what is the
step-to-step and overall conversion?

**A:** 80,000 sessions opened the app; 65,700 viewed an item (82.1%);
29,805 added to cart (45.4% of viewers); 6,544 reached checkout (21.9% of
carts); 807 purchased (12.3% of checkouts, 1.0% overall).

**Signal:** the sharpest drop is add-to-cart → checkout (54% of carts never
proceed). That is the highest-leverage step to instrument and fix.

## 02 · N-day retention by cohort

**Q:** What share of each signup-month cohort returned on exactly day 1/7/30?

**A:** D1 retention is stable at ~17–20% across cohorts; D7 ~13–14%; D30
~4–6% (0 for the June cohort — not enough observation time).

**Signal:** the sharp D1→D7 drop points at the onboarding window as the
retention bottleneck, not long-term engagement.

## 03 · Rolling 30-day retention

**Q:** What % of each cohort was active in each 30-day window starting 7/14/30/60
days after signup?

**A:** Win-7d ~88–90% (early cohorts), decaying to ~0–16% by win-60d.

**Signal:** rolling (windowed) retention is a fairer lens than point retention
for products with sporadic usage — it does not punish users who return a few
days late.

## 04 · DAU / MAU / stickiness

**Q:** Daily active users, trailing-28d MAU, and stickiness (DAU/MAU).

**A:** Stickiness climbs from ~35–45% as the MAU window fills with history,
then stabilizes.

**Signal:** stickiness ≈ DAU/MAU is a frequency metric, not a reach metric.
~40% stickiness means the average user is active ~12 days/month.

## 05 · LTV by cohort

**Q:** Average revenue per user by signup cohort.

**A:** LTV per user is ~$0.90–$1.23 lifetime, modest because only ~4% of users
ever purchase (see case 09).

**Signal:** cohort LTV must be compared at the *same age*, not calendar date —
younger cohorts look smaller simply because they have had less time to spend.

## 06 · Top-3 categories per country

**Q:** Which 3 product categories bring the most revenue in each country?

**A:** `ROW_NUMBER() OVER (PARTITION BY country ORDER BY SUM(amount) DESC)`
keeps the top 3. Electronics and clothing dominate most markets.

**Signal:** use `ROW_NUMBER` (not `RANK`/`DENSE_RANK`) when you want exactly N
rows per group regardless of ties.

## 07 · Cumulative revenue

**Q:** Daily revenue and the running total.

**A:** `SUM(amount) OVER (ORDER BY d ROWS UNBOUNDED PRECEDING)` — cumulative
equals total revenue at the last row.

**Signal:** `ROWS` vs `RANGE` framing matters when there are duplicate order
dates; `ROWS UNBOUNDED PRECEDING` is the safe default for running totals.

## 08 · Longest active-day streak (gaps-and-islands)

**Q:** For each user, the longest run of consecutive active days.

**A:** `ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY d)`, then
`epoch_day - rn` is a constant within each consecutive run (the island key).
Group by user + island key → run length; take the max.

**Signal:** the `day - row_number` trick is the canonical gaps-and-islands
pattern — it converts "consecutive" into "same group" in one pass.

## 09 · A/B conversion by variant

**Q:** Purchase conversion for control vs treatment, and the lift.

**A:** control 4.00%, treatment 3.94% → −0.07pp (no positive lift on this
sample). `LAG` over the two-row result gives the diff.

**Signal:** user-level conversion (4%) is much higher than session-level
(1%, case 01) — pick the unit of analysis before reporting, and do not mix them.

## 10 · Revenue attribution

**Q:** Revenue by acquisition channel under lifetime vs first-touch models.

**A:** Referral over-indexes on revenue relative to its share of users (high
retention → repeat purchases), so first-touch and lifetime are close for it;
paid_search shows more divergence (one-and-done purchasers).

**Signal:** the gap between first-touch and lifetime revenue is itself a signal
— large gaps mark channels with repeat-purchase potential worth investing in.
