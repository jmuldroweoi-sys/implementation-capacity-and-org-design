# Capacity formulas

Every authoritative R2 capacity calculation, with a worked example from the synthetic data. Each `yaml worked-example` block is executed by validator check V48 and by the tests against `tools/capacity_calc.py`; if the calculator and this page ever disagree, the build fails. All examples are an illustrative example using synthetic data.

Rounding: hours use `hours_decimal_places` (2) and ratios `ratio_decimal_places` (4), half-up, both in `config/parameters.yaml`. Outputs are written without trailing zeros.

## 1. Top-down forecast hours

- **Purpose:** forecast one role's hours in one month for a project with no task plan.
- **Formula:** `top_down_hours = effort_hours_by_role x effort_share / duration_months`
- **Inputs:** the tier's effort for the role (`config/demand-drivers.yaml`); the curve segment's share and length (`config/phase-effort-curves.yaml`).
- **Units:** hours; share is a decimal ratio; duration in months.
- **Edge cases:** a segment shorter than one month, a negative effort, or a share outside 0 to 1 is rejected. A project-month that has bottom-up authoritative workload keeps its top-down rows only as `excluded_to_prevent_double_count`.
- **Implementation:** `capacity_calc.top_down_hours`.

Worked example: a standard-tier project's technical-specialist effort (480 hours) in one of the two build months (share 0.35).

```yaml worked-example
name: top-down hours, standard tier, technical specialist, build month
function: top_down_hours
inputs: {effort_hours: 480, effort_share: 0.35, duration_months: 2}
expected: {value: 84}
```

## 2. Demand aggregation

- **Purpose:** total the work a role must do in a month.
- **Formula:** `demand_hours = project_demand_hours + training_demand_hours + golive_support_hours`, where each term sums only `authoritative_workload` records for the scenario, role, and period.
- **Inputs:** demand records (`DMN`), training capacity (`TRC`, trainer hours only), launch-support demand (`GLS`).
- **Units:** hours.
- **Edge cases:** informational and excluded records never count; a project-month with authoritative rows from both methods, or a component authoritative twice, stops the calculation.
- **Implementation:** `capacity_calc.compute` (snapshot section) and `capacity_calc.double_count_problems`.

Worked example: snapshot `CAP-000001` (Scenario A, implementation lead, 2026-09) has 11 hours of bottom-up task demand imported from R3 and no training or launch support, so `demand_hours` is 11. The traced example in `verification/formula-audit.md` lists the exact records behind the largest gap.

## 3. Supply: gross, project-available, ramp, mentor, effective

- **Purpose:** the hours one person has for project work in one role and month.
- **Formula:**
  - `gross_available_hours = scheduled_work_hours - unavailable_hours`
  - `project_available_hours = gross_available_hours - non_project_hours - training_hours - other_capacity_reduction_hours`
  - `ramp_adjusted_hours = project_available_hours x ramp_factor`
  - `ramp_loss_hours = project_available_hours - ramp_adjusted_hours`
  - `effective_capacity_hours = ramp_adjusted_hours - mentor_hours`
- **Inputs:** a supply record's hours, ramp factor (R4 interface fixture below 1), and mentoring hours.
- **Units:** hours; ramp factor is a decimal ratio from 0 to 1.
- **Edge cases:** any negative input, allowances above scheduled hours, a ramp factor outside 0 to 1, or a negative effective capacity is rejected, never clipped. Mentoring is charged only to the mentor.
- **Implementation:** `capacity_calc.supply_breakdown` and `capacity_calc.gross_available_hours`.

Worked example (ramp): Person G joins mid-November 2026 (`SUP-000061`), with 80 unavailable hours, 8 non-project hours, 32 hours of their own onboarding, and a ramp factor of 0.25.

```yaml worked-example
name: ramping joiner, first month
function: supply_breakdown
inputs: {scheduled: 160, unavailable: 80, non_project: 8, training: 32, other: 0, ramp_factor: 0.25, mentor: 0}
expected: {gross_available_hours: 80, project_available_hours: 40, ramp_adjusted_hours: 10, ramp_loss_hours: 30, effective_capacity_hours: 10}
```

Worked example (mentor): Person F mentors Person G the same month (`SUP-000053`). Person F is fully ramped; 24 mentoring hours reduce only Person F's capacity.

```yaml worked-example
name: mentor, same month
function: supply_breakdown
inputs: {scheduled: 160, unavailable: 0, non_project: 16, training: 0, other: 0, ramp_factor: 1, mentor: 24}
expected: {gross_available_hours: 160, project_available_hours: 144, ramp_loss_hours: 0, effective_capacity_hours: 120}
```

## 4. Capacity gap

- **Purpose:** how far demand is above or below supply.
- **Formula:** `capacity_gap_hours = demand_hours - effective_capacity_hours` (shared standard 1.0.0; above 0 means more work than capacity).
- **Inputs:** a snapshot's demand and effective capacity.
- **Units:** hours; may be negative.
- **Edge cases:** with zero capacity the gap equals demand and is still recorded.
- **Implementation:** `capacity_calc.capacity_gap_hours`.

Worked example: Scenario D, technical specialist, 2027-06 (`CAP-000120`).

```yaml worked-example
name: demand above supply
function: capacity_gap_hours
inputs: {demand: 515.6, supply: 432}
expected: {value: 83.6}
```

## 5. Load ratio and zero capacity

- **Purpose:** demand relative to supply, as one comparable number.
- **Formula:** `load_ratio = demand_hours / effective_capacity_hours`
- **Inputs:** a snapshot's demand and effective capacity.
- **Units:** decimal ratio.
- **Edge cases:** when effective capacity is 0, no division happens and zero is never substituted: the state is `undefined_no_capacity` and the ratio is empty. R2 asserts no ideal ratio.
- **Implementation:** `capacity_calc.load_ratio`.

```yaml worked-example
name: load ratio, Scenario D technical specialist, 2027-06
function: load_ratio
inputs: {demand: 515.6, supply: 432}
expected: {value: 1.1935, state: defined}
```

Worked example (zero capacity): Scenario D, enablement lead, 2027-02 (`CAP-000126`). The only enablement lead is on leave for the whole month, and 24 trainer hours are planned.

```yaml worked-example
name: zero effective capacity
function: load_ratio
inputs: {demand: 24, supply: 0}
expected: {value: null, state: undefined_no_capacity}
```

## 6. Staffing timing

- **Purpose:** the latest date a staffing process could start for a new person to be fully ramped by the first month of a forecast gap.
- **Formula:** `latest_staffing_start_date = projected_gap_date - hiring_lead_time_days - ramp_duration_days`
- **Inputs:** `projected_gap_date` (the first day of the first month in the firing run); `hiring_lead_time_days` and `ramp_duration_days` from `config/parameters.yaml`.
- **Units:** dates and days.
- **Edge cases:** a date before `calculation_as_of_at` gives `timing_state: window_passed`. Planning logic only; it is not a decision or a promise to hire.
- **Implementation:** `capacity_calc.latest_staffing_start_date`.

Worked example: the load trigger for Scenario D's technical specialists first sees the gap in 2027-05.

```yaml worked-example
name: latest staffing start, gap from 2027-05
function: latest_staffing_start_date
inputs: {projected_gap_date: 2027-05-01, hiring_lead_time_days: 60, ramp_duration_days: 120}
expected: {value: "2026-11-02"}
```

## 7. Staffing trigger persistence and hysteresis

- **Purpose:** fire a staffing signal only when pressure persists, and clear it only when it has clearly eased.
- **Formula:** see [`docs/staffing-trigger-model.md`](../docs/staffing-trigger-model.md). Fire after `trigger_fire_after_periods` consecutive months with `load_ratio >= load_ratio_upper_threshold`; clear after `trigger_clear_after_periods` consecutive months with `load_ratio <= load_ratio_lower_threshold` or no demand.
- **Inputs:** a role's snapshots in month order; the parameters above.
- **Units:** months (counts) and decimal ratios.
- **Edge cases:** a single month above the threshold is `watch`; a month between the thresholds keeps a triggered rule triggered.
- **Implementation:** `capacity_calc.evaluate_trigger`.

Every threshold above is a user-configurable parameter and a proposed design value, not a measured result.
