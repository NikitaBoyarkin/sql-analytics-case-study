# Application log — measuring whether the portfolio converts

This turns the job search into a measurable experiment: does sending the live
report link change the interview rate? It closes audit risk #2 ("просмотр не
конвертит в интервью").

## File

`applications.csv` — one row per application. Schema:

| Column | Type | Values | Meaning |
|--------|------|--------|---------|
| `date` | date | `YYYY-MM-DD` | Date the application was sent |
| `segment` | string | `saas`, `ecommerce`, `other` | Target segment (PRD segments 1–2) |
| `link_used` | bool | `true` / `false` | Was the live report link included? |
| `opened` | bool | `true` / `false` | Was the tracking link opened (REQ-005)? `false` if no link |
| `response` | bool | `true` / `false` | Did the company reply at all? |
| `outcome` | enum | `none`, `screen`, `interview`, `offer`, `reject` | Furthest stage reached |

`date` and `segment` are copied from the application; `outcome` is filled in
when known. Leave `response`/`outcome` empty until the result lands.

## Protocol

1. Log every application on the day it is sent (blank `response`/`outcome`).
2. Mark `link_used` — this is the A/B label. Alternate coverage naturally; do
   **not** send the link only to "good" applications, or the comparison is biased.
3. Check the tracking link weekly; set `opened` for rows with `link_used = true`.
   For `link_used = false`, `opened` is meaningless — leave it `false`.
4. When a result arrives, set `response` and `outcome`.
5. Run the lift report weekly (below).

## Computing the lift

`interview` counts as `outcome` in `screen`, `interview`, or `offer` (a screen is
a positive conversion relative to no response).

```bash
uv run python log/lift.py
```

The script prints, per arm (link vs no-link): applications, interview rate,
and the difference. Decision rule (REQ-008):

- **lift ≥ 0 and ≥ +20% relative:** keep the link in every application; the
  delivery works — invest further in cases (dbt, real-data).
- **lift < 0:** the problem is *delivery, not the cases* — change how the link is
  presented (teaser, portfolio card REQ-007) before adding more cases.

## Minimum sample

Directional from ~20 rows; treat the number as a signal, not proof. At 40
applications (PRD Goal 1) the with/without comparison is the headline finding.
