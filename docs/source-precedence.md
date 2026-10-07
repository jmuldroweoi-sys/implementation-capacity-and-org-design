# Source precedence

The same work can reach R2 from more than one place: a task in R1 tracked in R3, a training track from the enablement program, a launch-support plan, and a top-down forecast for the same project. Precedence decides which one counts, so each piece of work is counted once.

## Order

| Rank | Source | Records | When it counts |
|---|---|---|---|
| 1 | Valid explicit R1 task workload for an active period, exported by R3 | Bottom-up demand records imported from R3 Capacity Inputs | Always, when R3 marks the row `authoritative_workload` |
| 2 | An approved workload component supplied by an upstream repository | Training demand (R4 interface fixtures) and launch-support demand | When it is not already covered by a rank 1 record |
| 3 | Top-down configured forecast | Top-down demand records | Only for project-months with no rank 1 authoritative workload |

## Required fields on every workload record

| Field | Meaning |
|---|---|
| `workload_component_id` | The unit of work that may be authoritative at most once per period (R1 task ID for task rows; the record's own ID for forecast rows) |
| `source_entity_type` | task, request, handoff, phase, or project |
| `source_entity_id` | The R1 record or project the hours describe |
| `source_repo` | The repository that owns that record |
| `source_version` | The commit or configuration version the hours came from |
| `capacity_inclusion_method` | `authoritative_workload`, `informational_only`, or `excluded_to_prevent_double_count` |

Bottom-up rows also carry `import_source_repo` (the tracker workbook) and `import_record_id` (the R3 `CPI` row), so every imported hour traces back to one exported row.

## Inclusion values

- **`authoritative_workload`**: counts in demand.
- **`informational_only`**: context, for example an R3 phase summary that totals task rows already counted. Never demand.
- **`excluded_to_prevent_double_count`**: the same work is counted by another record, which the row names. Never demand.

Every non-authoritative row carries an `exclusion_reason`. An excluded training record names the R1 task that covers it in `covered_by`, and the validator checks that the task is an authoritative workload component in the same project and month.

## Refuse or flag

- The calculator raises an error, and writes nothing, if a project-month has authoritative rows from both demand methods or a workload component is authoritative twice in a period.
- The validator re-checks both rules (V11, V12, V13) on the committed files.
- `verification/source-precedence-check.md` is regenerated on every run and lists, for every project-month that has rows from both methods, which method stayed authoritative.
- A wrong source row is fixed upstream, in R1 or R3, then re-exported. R2's copies are never edited by hand.
