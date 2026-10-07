# Launch-support model

How much implementation-team capacity a launch consumes, as plain workload.

## Support types

| `support_type` | Meaning |
|---|---|
| `rehearsal` | Rehearsing the launch steps before the launch date |
| `cutover_support` | Implementation-team hours during the cutover window |
| `command_center_support` | Implementation-team hours staffing a launch command center |
| `hypercare_support` | Heightened support hours after launch, before normal support takes over |

## Formula

`support_hours = people_count x hours_per_person_per_day x days`, in hours, for one project, period, support type, and role.

Each launch-support record (`GLS`) names the role whose capacity it consumes. Records are `authoritative_workload` with `precedence_rank` 2 unless an R1 task already covers the same hours, in which case they would be excluded exactly as training is. Every staffing pattern in the synthetic data is an illustrative example, and every number is a proposed design value, not a measured result.

## What R2 never does here

These are workload calculations only. R1 owns launch readiness, cutover logic, command-center definitions, and the go or no-go decision. R2 plans support hours on the assumption that a launch proceeds as planned in R1, and records no readiness score, gate outcome, or decision. A launch-support record has no field for any of them, and the validator (V46) fails if one appears.

R1 projects' launch-support months line up with R1 target launch dates: the validator checks that each R1 project's curve places its launch segment in the month of the R1 target launch date.

## Events

Each record emits `golive_support.computed` with `period`, `project_id`, and `support_hours`.
