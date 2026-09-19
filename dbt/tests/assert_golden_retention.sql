-- Golden-answer test: pin the January and June retention cohorts.
select *
from {{ ref('fct_retention') }}
where (
        cast(cohort as date) = date '2024-01-01'
        and (d1_retention <> 20.69 or d7_retention <> 14.96 or d30_retention <> 5.15)
      )
   or (
        cast(cohort as date) = date '2024-06-01'
        and (d1_retention <> 19.47 or d30_retention <> 0.0)
      )
