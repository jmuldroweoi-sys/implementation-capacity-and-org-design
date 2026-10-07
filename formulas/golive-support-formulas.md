# Launch-support formulas

Implementation-team hours consumed around a launch. Workload only: R1 owns readiness, cutover logic, and the go or no-go decision. Each `yaml worked-example` block is executed by validator check V48 and the tests against `tools/capacity_calc.py`. All examples are an illustrative example using synthetic data.

## Launch-support hours

- **Name:** `support_hours`
- **Purpose:** the hours one role spends on one kind of launch support for one project in one month.
- **Formula:** `support_hours = people_count x hours_per_person_per_day x days`
- **Inputs:** `people_count` (people), `hours_per_person_per_day` (hours), `days` (days), plus the project, period, `support_type` (rehearsal, cutover_support, command_center_support, hypercare_support), and role.
- **Units:** hours.
- **Edge cases:** any negative input is rejected; zero days gives zero hours. A record already covered by an R1 task would be `excluded_to_prevent_double_count` and contribute nothing. No field records readiness, a gate, or a decision.
- **Implementation:** `capacity_calc.golive_support_hours`.

## Worked examples

Cutover: `GLS-000008`, two technical specialists, 8 hours each, one day.

```yaml worked-example
name: cutover support
function: golive_support_hours
inputs: {people_count: 2, hours_per_person_per_day: 8, days: 1}
expected: {value: 16}
```

Command center: `GLS-000012`, two implementation leads, 6 hours each, three days.

```yaml worked-example
name: command-center support
function: golive_support_hours
inputs: {people_count: 2, hours_per_person_per_day: 6, days: 3}
expected: {value: 36}
```

Hypercare: `GLS-000005`, one support owner, 3 hours a day for eight days.

```yaml worked-example
name: hypercare support
function: golive_support_hours
inputs: {people_count: 1, hours_per_person_per_day: 3, days: 8}
expected: {value: 24}
```

Every staffing pattern above is a proposed design value, not a measured result.
