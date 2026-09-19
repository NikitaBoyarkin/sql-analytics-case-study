-- Golden-answer test: pin the first and last MRR months (Jan $170 → Jun $2,500).
select *
from {{ ref('fct_mrr') }}
where (month = date '2024-01-01' and (mrr <> 169.86 or active_subs <> 18))
   or (month = date '2024-06-01' and (mrr <> 2500.47 or active_subs <> 268))
