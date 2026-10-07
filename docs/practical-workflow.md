# Practical workflow: the monthly capacity check

How one implementation professional uses R2 once a month. The same twelve steps work for a solo implementer (Starter Mode) and for a mature delivery organization (Mature Mode); only the number of roles, people, and forecast rows changes. Nothing in this workflow decides staffing, budget, or anyone's performance: every output is an input to a conversation a named person leads.

## Trigger

The first working day of each month, after R3's monthly Capacity Inputs export. Run it again whenever a large project is signed, a launch date moves in R1, or someone joins or leaves.

## Inputs

| Input | Owner | File |
|---|---|---|
| Capacity Inputs (task, request, handoff, and phase hours) | R3 | `upstream/r3/exports/csv/capacity-inputs.csv` (pinned) |
| Forecast projects and complexity tiers | The implementation professional | `projects` in `data/synthetic/universe.yaml` |
| People, roles, scheduled hours, allowances | The implementation professional or lead | `people` in `data/synthetic/universe.yaml` |
| Ramp factors and mentoring | R4 (interface fixtures until R4 exists) | `people` overrides in `data/synthetic/universe.yaml` |
| Training demand | R4 (interface fixtures until R4 exists) | `training_demand` in `data/synthetic/universe.yaml` |
| Launch-support plans | The implementation professional, from R1 launch dates | `golive_support` in `data/synthetic/universe.yaml` |
| Thresholds, curves, drivers, defaults | The team (each a user-configurable parameter) | `config/`, `profiles/` |

## Steps

### Step 1: Export Capacity Inputs from R3

- **Input:** The R3 tracker with this month's task, request, and handoff hours.
- **File or entity:** R3 `exports/csv/capacity-inputs.csv` (CPI rows); in this repository the pinned copy is `upstream/r3/exports/csv/capacity-inputs.csv`.
- **Deterministic rule:** R3 assigns each row one `capacity_inclusion_method`; R2 imports every row inside the planning horizon unchanged and never redefines its meaning.
- **Output:** `bottom_up` demand records in `data/synthetic/phase-demand.csv` with `precedence_rank` 1.
- **Human decision:** Confirm the export is this month's and that every active project's tasks are in it.
- **Downstream consumer:** Step 6 (demand calculation) and the source-precedence check.

### Step 2: Add future project forecast

- **Input:** Signed or likely projects that have no task plan yet, each with a complexity tier and the month its effort curve starts.
- **File or entity:** `projects` in `data/synthetic/universe.yaml`; tiers in `config/demand-drivers.yaml`; curves in `config/phase-effort-curves.yaml`.
- **Deterministic rule:** `top_down_hours = effort_hours_by_role x effort_share / duration_months` for each month of the curve.
- **Output:** `top_down` demand records with `precedence_rank` 3 and `value_basis` forecast.
- **Human decision:** Which pipeline projects to include and which tier fits each one. The forecast is a judgment; the arithmetic is not.
- **Downstream consumer:** Step 6, and the "validate forecast assumptions" question in the operating review.

### Step 3: Update availability

- **Input:** Planned leave, holidays, joiners and leavers, recurring non-project work, and other named reductions for each person and role.
- **File or entity:** `people` allocations and overrides in `data/synthetic/universe.yaml` (SUP records after calculation).
- **Deterministic rule:** `gross_available_hours = scheduled_work_hours - unavailable_hours`; `project_available_hours = gross_available_hours - non_project_hours - training_hours - other_capacity_reduction_hours`.
- **Output:** Supply records in `data/synthetic/supply-records.csv`.
- **Human decision:** Which reductions are real and approved. R2 uses hours, never a productive percentage.
- **Downstream consumer:** Step 7.

### Step 4: Update ramp factors

- **Input:** Each new person's ramp factor for the month and who mentors them.
- **File or entity:** `ramp_factor`, `mentor`, and `mentor_hours` overrides in `data/synthetic/universe.yaml`. Ramp is owned by R4; until R4 exists these are interface fixtures.
- **Deterministic rule:** `ramp_adjusted_hours = project_available_hours x ramp_factor`; ramp loss stays on the ramping person; mentoring hours reduce only the mentor; a mentor's record and the mentee's record must name each other.
- **Output:** `ramp_loss_hours` and `mentor_hours` on the supply records.
- **Human decision:** The ramp factor and mentoring time for each new person.
- **Downstream consumer:** Step 7, and later R4 ramp milestones.

### Step 5: Import training and launch-support demand

- **Input:** Upcoming training tracks (learners, class size, track hours, session length, preparation) and launch-support plans (people, hours per day, days).
- **File or entity:** `training_demand` (TRD) and `golive_support` (GLS) in `data/synthetic/universe.yaml`.
- **Deterministic rule:** Training already counted by an R1 task or R3 row is `excluded_to_prevent_double_count` and names the covering record; launch support is workload only and carries no readiness or decision.
- **Output:** `training-demand.csv`, `training-capacity.csv`, and `golive-support.csv` after calculation.
- **Human decision:** Whether each training or launch-support line is new work or already in the task plan.
- **Downstream consumer:** Step 6.

### Step 6: Calculate demand

- **Input:** Steps 1, 2, and 5.
- **File or entity:** `python tools/capacity_calc.py`.
- **Deterministic rule:** `demand_hours = authoritative project hours + authoritative trainer hours + authoritative launch-support hours`; one authoritative method per project and month; informational and excluded rows never count.
- **Output:** `project_demand_hours`, `training_demand_hours`, `golive_support_hours`, and `demand_hours` on each capacity snapshot.
- **Human decision:** None; the calculation is fixed.
- **Downstream consumer:** Steps 8 to 10.

### Step 7: Calculate effective capacity

- **Input:** Steps 3 and 4.
- **File or entity:** `python tools/capacity_calc.py` (same run).
- **Deterministic rule:** `effective_capacity_hours = ramp_adjusted_hours - mentor_hours`, summed by role into role capacity (RCP). A record that would go negative is rejected, not clipped.
- **Output:** `data/synthetic/role-capacity.csv` and `effective_capacity_hours` on each snapshot.
- **Human decision:** None; the calculation is fixed.
- **Downstream consumer:** Steps 8 to 10.

### Step 8: Review the gap

- **Input:** `capacity_gap_hours` by role and month.
- **File or entity:** `reports/executive-pack/capacity-summary.md`.
- **Deterministic rule:** `capacity_gap_hours = demand_hours - effective_capacity_hours`; above 0 means more work than capacity.
- **Output:** The list of role-months where demand is greater than supply.
- **Human decision:** Whether each gap is real or a forecast artifact, and whether to rebalance work across people or months.
- **Downstream consumer:** Step 12 and R5 workload context (later).

### Step 9: Review the load ratio

- **Input:** `load_ratio` and `load_ratio_state` by role and month.
- **File or entity:** `reports/executive-pack/capacity-summary.md` and `demand-vs-supply.md`.
- **Deterministic rule:** `load_ratio = demand_hours / effective_capacity_hours`; zero capacity gives `undefined_no_capacity`, never a number.
- **Output:** Role-months near balance, above the configured threshold, or with no capacity.
- **Human decision:** What a ratio means for this team. R2 asserts no ideal value.
- **Downstream consumer:** Step 10.

### Step 10: Review staffing triggers

- **Input:** Trigger states, firings, clearings, and proposed staffing recommendations.
- **File or entity:** `reports/executive-pack/staffing-signals.md`; `data/synthetic/staffing-recommendations.csv` (STR).
- **Deterministic rule:** Fire after the configured consecutive months above the upper threshold; clear after the configured months at or below the lower threshold; `latest_staffing_start_date = projected_gap_date - hiring_lead_time - ramp_duration`.
- **Output:** Proposed recommendations, each with a timing window that is open or has passed.
- **Human decision:** Whether to begin a staffing review, change the role mix, rebalance work, or change nothing. A named person decides; R2 records no decision.
- **Downstream consumer:** Step 12, the manager conversation, and R5 and R6 (later).

### Step 11: Review source and double-count warnings

- **Input:** The source-precedence check and validator output.
- **File or entity:** `verification/source-precedence-check.md`; `python tools/validate.py`.
- **Deterministic rule:** At most one authoritative method per project and month; each workload component authoritative at most once per month; every excluded row names a reason.
- **Output:** Zero problems, or a list of rows to fix upstream.
- **Human decision:** Fix the upstream record in R1 or R3 rather than editing R2's copy.
- **Downstream consumer:** Step 12.

### Step 12: Prepare the operating-review summary

- **Input:** The four reports above.
- **File or entity:** `reports/executive-pack/operating-review.md`.
- **Deterministic rule:** Counts and values only, copied from the calculation; no AI narrative is authoritative.
- **Output:** A one-page agenda for the monthly capacity conversation.
- **Human decision:** Every decision in the review, recorded by the named person outside R2.
- **Downstream consumer:** The monthly capacity conversation with a manager; R5 and R6 later read the aggregates.

## Deterministic rules

All in `tools/capacity_calc.py`, documented with worked examples in `formulas/`: one authoritative demand method per project and month; supply from named allowances; `capacity_gap_hours = demand_hours - effective_capacity_hours`; `load_ratio = demand_hours / effective_capacity_hours` or `undefined_no_capacity`; training and launch-support formulas; trigger persistence and hysteresis; staffing timing. The same inputs always give byte-identical outputs.

## Outputs

Demand, supply, role capacity, training capacity, launch support, capacity snapshots, and proposed staffing recommendations in `data/synthetic/`; the operating-review pack in `reports/executive-pack/`; the source-precedence check, the formula audit, and the synthetic dataset check in `verification/`.

## Events

Registered R2 events only, in `data/synthetic/events.jsonl`: `org_profile.selected` (when a person selects the stage), `capacity.snapshot_computed`, `training_capacity.computed`, `golive_support.computed`, `staffing_trigger.fired`, and `staffing_recommendation.recorded`. No cost-to-serve event in v0.1.

## Human decisions

Which projects to forecast and at what tier; which allowances and ramp factors are real; whether a gap is real; what to do about each proposed recommendation; whether to review the organization stage. R2 records none of these decisions; a named person records them where the team records decisions.

## Downstream integrations

R5 reads workload context per role and month and the selected stage (later). R6 reads snapshots and events read only, to draft narratives a person reviews (later). R1 consumes `golive_support.computed` and `org_profile.selected`. The analytics track reads the event contract and synthetic data.

## Verification

`python tools/capacity_calc.py --check`, `python tools/validate.py` (48 checks, recomputing every formula), and `python -m unittest discover -s tests -v`. A failed check means the outputs are not used until it is fixed.

## Solo use (Starter Mode)

For one implementation professional, or a team of two or three. Target: under one hour a month, which is a proposed design value, not a measured result.

Starter Mode needs only five inputs:

1. The project forecast (step 2): each upcoming project and its tier.
2. Task or workload hours (step 1): the R3 Capacity Inputs export, or the forecast alone if there is no task plan yet.
3. Available hours (step 3): scheduled hours per role you hold.
4. Major non-project load (step 3): recurring internal work and planned leave.
5. Upcoming training and launch support (step 5).

Skip ramp, mentoring, multiple people, and concurrency until they matter. Scenario A in the synthetic data is a Starter Mode example: one person holds four roles, and the model shows that the technical-specialist work across two projects is more than the hours that person has for it, which is a role-mix conversation rather than a hiring decision.

## Early-scale use

A small team adds one supply record per person and role, ramp factors and mentoring for each joiner, and reads the role-level view: who is above the threshold, where a ramp leaves a gap, and whether a watch month persists. Scenario B in the synthetic data is an early-scale example.

## Structured-growth use

Specialized roles each get their own snapshots; training and launch support become visible as their own demand; the horizon reaches past the hiring lead time so staffing timing matters. Scenario C in the synthetic data is a structured-growth example.

## Mature use (Mature Mode)

The same files and the same calculator, with more rows: several people per role, specialized roles, ramping joiners with mentors, a horizon long enough to see past the hiring lead time, and the full executive pack. There is no separate architecture. Scenario D in the synthetic data is a Mature Mode example. Cost-to-serve joins this mode in a later version.
