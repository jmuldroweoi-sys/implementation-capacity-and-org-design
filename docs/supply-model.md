# Supply model

Supply is the hours a person has for implementation project work in one role and one month, after every named allowance. The shared standard calls it supply; R2 records it as `effective_capacity_hours`.

## Supply record (`SUP`)

One record per person, role, and month. A person who holds several roles, which is normal in a startup, has one record per role, each with its own share of scheduled hours.

| Step | Field | Formula |
|---|---|---|
| 1 | `gross_available_hours` | `scheduled_work_hours - unavailable_hours` |
| 2 | `project_available_hours` | `gross_available_hours - non_project_hours - training_hours - other_capacity_reduction_hours` |
| 3 | `ramp_adjusted_hours` | `project_available_hours x ramp_factor` |
| 4 | `ramp_loss_hours` | `project_available_hours - ramp_adjusted_hours` |
| 5 | `effective_capacity_hours` | `ramp_adjusted_hours - mentor_hours` |

## Allowances

| Field | Meaning |
|---|---|
| `unavailable_hours` | Planned leave, holidays, or the part of a month before a joiner starts |
| `non_project_hours` | Recurring internal work outside implementation projects |
| `training_hours` | The person's own learning time, for example new-hire onboarding. Never trainer workload |
| `other_capacity_reduction_hours` | Any other approved, named reduction |
| `mentor_hours` | Time this person spends mentoring someone else |

There is no universal productive percentage. Every reduction is an explicit allowance in hours, so a reader can see exactly why supply is lower than scheduled hours. Default scheduled hours (`standard_working_hours_per_period`) is a user-configurable parameter and a proposed design value, not a measured result.

## Ramp

A ramping person's `ramp_factor` is between 0 and 1; a fully ramped person's is 1. Ramp is owned by the enablement repository (R4): R2 reads factors and owns no ramp definition. Until R4 exists, factors below 1 are interface fixtures and are marked `ramp_source: r4_interface_fixture`. The lost hours are recorded once, as the ramping person's own `ramp_loss_hours`.

## Mentoring

Mentoring reduces only the mentor's capacity, through the mentor's own `mentor_hours`. The mentee's ramp loss and the mentor's mentoring time are different hours on different people, so the same hours are never counted twice. The mentor's record names the mentee and the mentee's record names the mentor for the same month; the validator rejects a one-sided pair.

## Rules

- Every hour field is non-negative. A record whose allowances exceed scheduled hours, or whose effective capacity would go negative, is rejected, not clipped.
- Roles come from R1. R2 models work allocation by role and prescribes no titles; an organization does not need every role.
- Supply in v0.1 is a forecast (`value_basis: forecast`). Actual available capacity is a later extension and will never overwrite the forecast.
- Supply measures available work time, not anyone's worth or performance. Low capacity never means poor performance, and R2 workload data must not be used to judge a person.

## Role capacity (`RCP`)

Supply records are summed by scenario, role, and month into role capacity, which keeps every allowance visible (`person_count`, scheduled, unavailable, non-project, own training, ramp loss, mentoring, effective). Each capacity snapshot points to its role capacity record.
