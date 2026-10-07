# Capacity model

A capacity snapshot (`CAP`) compares demand with supply for one scenario, role, and monthly period. It is the record the monthly review reads.

## Fields

| Field | Formula or source | Unit |
|---|---|---|
| `demand_hours` | `project_demand_hours + training_demand_hours + golive_support_hours` (authoritative records only) | hours |
| `effective_capacity_hours` | Sum of the role's supply-record `effective_capacity_hours` (the shared standard's supply) | hours |
| `capacity_gap_hours` | `demand_hours - effective_capacity_hours` | hours |
| `load_ratio` | `demand_hours / effective_capacity_hours`, rounded to `ratio_decimal_places` | decimal ratio |
| `load_ratio_state` | `defined`, or `undefined_no_capacity` when effective capacity is zero | state |
| `active_project_count` and counts by tier | Distinct projects with authoritative demand for the role and month | projects |
| `trigger_state` | Combined staffing-trigger state (see the staffing trigger model) | state |
| `source_version`, `config_digest`, `inputs_digest`, `calculation_version`, `calculated_at`, `standard_version`, `schema_version` | Reproducibility | text |

## Gap sign

R2 follows shared standard 1.0.0, which defines capacity gap as demand minus capacity:

- above 0: demand exceeds supply by that many hours;
- 0: demand equals supply;
- below 0: that many hours remain available.

The event `capacity.snapshot_computed` carries the same values, with `supply_hours` equal to the snapshot's `effective_capacity_hours`.

## Load ratio

`load_ratio` is the shared canonical term (V4 retired `utilization_rate` for this quantity). If effective capacity is zero, R2 does not divide and does not substitute zero: `load_ratio` is left empty, `load_ratio_state` is `undefined_no_capacity`, and the raw demand and supply hours stay on the record. A zero-capacity role with demand is what staffing trigger `STG-000002` watches for.

R2 does not treat any load ratio as good or bad for every team. A ratio means only what demand and supply say about one role in one month. Each threshold the staffing triggers use is a user-configurable parameter and a proposed design value, not a measured result, and none is a benchmark for any organization.

## Concurrency

Each snapshot counts the distinct projects a role has authoritative work on in the month, in total and by complexity tier, and compares the total with `max_active_projects_per_role` from the selected organization profile. `concurrency_state` is `within_configured_maximum` or `above_configured_maximum`. The maximum is a user-configurable parameter and a proposed design value, not a measured result. It is an observation threshold for a person to discuss; it fires no trigger and is not a benchmark.

## Reproducibility

Every snapshot can be rebuilt from its inputs:

- `inputs_digest` is the SHA-256 of the exact authoritative demand, training, launch-support, and supply record IDs and hours that produced it, plus the configuration digest, calculation version, and standard version.
- `config_digest` is the SHA-256 of every configuration and profile file.
- `source_version` names the pinned R3 commit and the synthetic universe version.

A reviewer asking "why did this snapshot show this gap?" can list the records behind it and recompute the digest; `verification/formula-audit.md` shows one traced example and the validator (V45) recomputes every digest.

## Role mix

Snapshots exist for every role a scenario has supply or demand for. An organization does not need every role, and one person may hold several. A role with demand and no supply is shown, not hidden, because that is a coverage question.
