# Synthetic data

All files in this folder are synthetic data generated for illustration. No record describes a real person, team, customer, employer, or organization, and no number is a measured result. People appear only as `PER` IDs with neutral labels such as Person A. There is no branded fictional company.

## How the files are made

`universe.yaml` is the only hand-authored file here. `tools/capacity_calc.py` reads it, the pinned R3 Capacity Inputs (`upstream/r3/exports/csv/capacity-inputs.csv`), and the configuration, and writes every other file. Calculated values are never typed by hand. Exact row counts are in [`verification/synthetic-data-check.md`](../../verification/synthetic-data-check.md) and are locked by the tests.

## Scenarios

| Scenario | Stage | What it shows |
|---|---|---|
| Scenario A (`SCN-000001`) | startup | One person (Person A) holds four roles. R1 project `PRJ-000001` uses bottom-up task hours from R3 in September and October and a top-down forecast afterwards; a forecast project joins in January. The technical-specialist role fires a sustained-load trigger and later clears it: a role-mix conversation for a solo implementer. Starter Mode example. |
| Scenario B (`SCN-000002`) | early_scale | A new technical specialist (Person G) joins mid-November and ramps (R4 interface fixtures) while Person F mentors them; mentoring reduces only Person F's capacity. The implementation lead has single months above the threshold that stay on watch without firing. |
| Scenario C (`SCN-000003`) | structured_growth | Specialized roles. R1 project `PRJ-000003` launches in October with rehearsal, cutover, command-center, and hypercare support. One training record is excluded because R1 task `TSK-000024` already counts it. The technical specialists see sustained pressure from two forecast projects. |
| Scenario D (`SCN-000004`) | mature | A larger forecast pipeline across several people per role. The only enablement lead is on leave for a whole month with training planned, so capacity is zero and the coverage trigger fires and clears. Late-horizon pressure fires load triggers whose staffing timing window is still open. Mature Mode example. |

Each scenario's organization stage was selected by a named person (an `org_profile.selected` event); the calculation never changes it.

## Files

| File | Records | Purpose |
|---|---|---|
| `universe.yaml` | inputs | Scenarios, people and allocations, forecast projects, training demand (R4 interface fixtures), launch-support plans |
| `scenarios.csv` | scenarios | Scenario, selected stage, profile, who selected it and when |
| `people.csv` | person-role allocations | Planning fields only: ID, neutral label, role, scheduled and non-project hours, first period, ramp state, mentoring |
| `projects.csv` | project-months | For each project and month: curve phases, tier, and the one authoritative demand method. No project status |
| `phase-demand.csv` | demand records (`DMN`) | Bottom-up rows imported from R3 and top-down forecast rows, with inclusion method and precedence |
| `training-demand.csv` | training demand (`TRD`) | R4 interface fixtures |
| `training-capacity.csv` | training capacity (`TRC`) | Cohorts, sessions, trainer delivery, preparation, assessment hours, and learner seat-hours |
| `golive-support.csv` | launch-support demand (`GLS`) | Rehearsal, cutover, command-center, and hypercare hours |
| `supply-records.csv` | supply records (`SUP`) | Every allowance from scheduled to effective hours, per person, role, and month |
| `role-capacity.csv` | role capacity (`RCP`) | Supply summed by scenario, role, and month |
| `capacity-snapshots.csv` | capacity snapshots (`CAP`) | Demand, effective capacity, gap, load ratio, concurrency, trigger states, digests |
| `staffing-recommendations.csv` | staffing recommendations (`STR`) | Proposed recommendations from fired triggers, with staffing timing |
| `events.jsonl` | events (`EVT`) | Registered R2 events in the shared event contract |

## Periods and horizon

Monthly periods `YYYY-MM`, from `planning_horizon_start` to `planning_horizon_end` in `config/parameters.yaml`. Every calculated value uses the fixed `calculation_as_of_at` time.
