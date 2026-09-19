-- Golden-answer test (cases.md / tests/test_golden_answers.py): pin the funnel.
-- Any returned row means a dbt number drifted from the SQL case.
select *
from {{ ref('fct_funnel') }}
where (event_name = 'app_open'    and sessions <> 80000)
   or (event_name = 'view_item'   and sessions <> 65739)
   or (event_name = 'add_to_cart' and sessions <> 29641)
   or (event_name = 'checkout'    and sessions <> 6584)
   or (event_name = 'purchase'    and sessions <> 928)
