# Staffing trigger model

A staffing trigger means: **operational conditions justify a staffing conversation.** It never means hire someone. Nothing in R2 decides staffing, budget, compensation, reorganization, or anyone's performance.

## Triggers (`STG`)

Defined in `config/staffing-triggers.yaml`, evaluated for every scenario and role, month by month across the horizon.

| ID | Name | Above condition | Below condition | Fires after | Clears after |
|---|---|---|---|---|---|
| `STG-000001` | sustained_load_pressure | load ratio defined and at or above `load_ratio_upper_threshold` | load ratio defined and at or below `load_ratio_lower_threshold`, or no demand | `trigger_fire_after_periods` consecutive months | `trigger_clear_after_periods` consecutive months |
| `STG-000002` | role_coverage_gap | demand above 0 and zero effective capacity | effective capacity above 0, or no demand | `coverage_fire_after_periods` | `coverage_clear_after_periods` |

Inputs a trigger draws on: the forecast capacity gap and load ratio, the number of consecutive affected months, the configured hiring lead time and ramp duration (for timing), and critical role coverage. Concurrency pressure is reported as an observation beside the triggers for a person to weigh; it fires nothing in v0.1.

Every threshold and count is a user-configurable parameter and a proposed design value, not a measured result. None is presented as a norm for any organization.

## Persistence and hysteresis

So that a small change near a boundary does not switch a signal on and off:

| State | Meaning |
|---|---|
| `not_triggered` | The above condition is not met, or it was met and has since cleared |
| `watch` | The above condition is met, but not yet for enough consecutive months to fire |
| `triggered` | The rule fired this month or earlier and has not cleared |
| `clearing` | Triggered, and the below condition is met, but not yet for enough consecutive months to clear |

- A rule fires only after the above condition holds for the fire-after count in a row. A single month above the threshold is `watch`, and a month that is not above resets the count.
- A triggered rule clears only after the below condition holds for the clear-after count in a row. A month between the two thresholds keeps it `triggered` and resets the clearing count.
- The lower threshold must sit below the upper threshold; the validator checks it.
- A snapshot's combined `trigger_state` takes the most serious rule state, in the order triggered, clearing, watch, not_triggered.

## Staffing recommendation (`STR`)

Each firing records one staffing recommendation that follows the shared recommendation contract (standard 1.0.0):

- `status` is `proposed`. R2 never sets approved or rejected; that needs an approval record made by a named person, outside R2.
- `origin_type` is `system` and `origin_id` is the firing rule.
- `subject` is the capacity snapshot in the month it fired; `source_references` list every snapshot in the firing run and the rule.
- `recommendation_type` comes from the rule: begin a staffing review, or review role coverage. The configured vocabulary also includes investigate role mix, consider workload rebalance, review hiring timing, and validate forecast assumptions.
- `decision_owner` is `named_human`.

A recommendation may suggest a review, a role-mix question, a rebalance, a timing check, or a forecast check. It never names a person to hire, release, promote, or reassign, never states that budget is approved, and never states that the organization must be restructured. The validator (V26) checks the content of every recommendation and every configured recommendation type.

## Staffing timing

If a gap is forecast:

`latest_staffing_start_date = projected_gap_date - hiring_lead_time_days - ramp_duration_days`

- `projected_gap_date` is the first day of the first month in the firing run.
- `hiring_lead_time_days` and `ramp_duration_days` come from `config/parameters.yaml`. Ramp duration is an R4 interface default until R4 supplies it.
- `timing_state` is `window_open` if the latest start date is on or after `calculation_as_of_at`, otherwise `window_passed`.

This is planning logic only. It is not a promise or a recommendation that the organization should or will hire. Its assumptions are the two parameters above and the forecast behind the gap; a passed window means the configured lead time no longer fits, which is itself a reason to discuss rebalancing, role mix, or launch timing with R1's owners.

## Events

- `staffing_trigger.fired` (subject: the rule) with `period`, `rule_id`, and `capacity_gap_hours`.
- `staffing_recommendation.recorded` (subject: the recommendation) with `staffing_trigger_id` and `status: proposed`.

Clearing is visible in the snapshot's `trigger_events` field; standard 1.0.0 registers no clearing event, and R2 adds none.
