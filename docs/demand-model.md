# Demand model

Demand is the implementation work a role is expected to do in a monthly period, in hours. R2 builds it from three kinds of records and counts each piece of work once.

| Source | Record | Enters demand as |
|---|---|---|
| Project work | Demand record (`DMN`), `data/synthetic/phase-demand.csv` | `project_demand_hours` |
| Training delivery | Training capacity (`TRC`), from training demand (`TRD`) | `training_demand_hours` (trainer hours only) |
| Launch support | Launch-support demand (`GLS`) | `golive_support_hours` |

`demand_hours = project_demand_hours + training_demand_hours + golive_support_hours`, segmented by scenario, role, and period. Within project work, every record also carries the project, complexity tier where applicable, and workload type.

## Two demand methods (V4 decision D9)

Every demand record has `demand_method`, and only two values exist.

### `bottom_up`: task demand

For projects with real task detail in R1, tracked in R3.

- Source: the pinned R3 Capacity Inputs export (`upstream/r3/exports/csv/capacity-inputs.csv`).
- Hours: R3 `planned_hours`, by the task's owner role and the period R3 allocated it to.
- Actual hours: R3 `actual_hours` are copied to `actual_hours` for retrospective comparison. They never replace planned hours and never enter demand.
- Inclusion: R3's `capacity_inclusion_method`, unchanged. R2 does not redefine what R3 rows mean.
- `precedence_rank` 1, `value_basis` planned.

### `top_down`: forecast demand

For future or insufficiently tasked work.

- Source: a project's complexity tier (`config/demand-drivers.yaml`), the tier's phase-effort curve (`config/phase-effort-curves.yaml`), and the project's `curve_start_period`.
- Hours: `effort_hours_by_role x effort_share / duration_months` for each month of each curve segment, rounded to `hours_decimal_places`.
- Phases: each month records the R1 phase keys its curve segment covers, for example `validate+enable`.
- `precedence_rank` 3, `value_basis` forecast, `workload_type` forecast_project_effort, and the record's own DMN ID as its workload component.

Project count enters through the number of forecast projects; complexity through the tier; phase and configured effort through the curve. The tiers, efforts, and curves are an illustrative example, and every value in them is a user-configurable parameter and a proposed design value, not a measured result. No curve is a universal effort distribution.

Only the implementation lead and technical specialist roles carry tier effort. Training and launch support enter through their own records, so the same hours are never counted through a tier as well.

## One authoritative method per project and period

A project in a given period contributes through one authoritative method only. If bottom-up authoritative workload exists for a project and month, every top-down row for that project and month is kept for transparency but marked `excluded_to_prevent_double_count` with the reason. The rule applies to the whole project-month, not role by role: a partly tasked month uses its task plan, and the gap between plan and forecast is a question for the review, not something R2 fills in.

The calculator refuses to produce output if any project-month has authoritative rows from both methods, or if any workload component is authoritative more than once in a period. The validator (V11, V12) and tests restate both rules independently. See [`source-precedence.md`](source-precedence.md).

## Forecast and actual

Demand is always planned (bottom-up) or forecast (top-down). Actual task hours are carried alongside planned hours but are never written over them and never become demand. A later version may add actual-based analysis; it will be a separate field, not a replacement.

## Periods

v0.1 plans in calendar months written `YYYY-MM`. The horizon is `planning_horizon_start` to `planning_horizon_end` in `config/parameters.yaml`. R3 rows outside the horizon are not imported, and the source-precedence check reports how many. Weekly planning is not part of v0.1; a later version could add a `period_grain` field without changing monthly records.
