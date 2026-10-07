# Training formulas

Trainer workload from one training-demand record. Training demand is an R4 interface fixture in v0.1. Each `yaml worked-example` block is executed by validator check V48 and the tests against `tools/capacity_calc.py`. All examples are an illustrative example using synthetic data.

Implementation reference for every formula on this page: `capacity_calc.training_capacity`.

## Formulas

| Name | Purpose | Formula | Units |
|---|---|---|---|
| `cohorts_required` | How many classes the learners need | `ceil(learner_count / class_size)` | cohorts |
| `sessions_per_cohort` | How many sessions one class needs | `ceil(track_hours / session_length_hours)` | sessions |
| `sessions_required` | Sessions across all classes | `cohorts_required x sessions_per_cohort` | sessions |
| `trainer_delivery_hours` | Trainer time in the room | `cohorts_required x track_hours` | hours |
| `trainer_preparation_hours` | Trainer time preparing | `sessions_required x prep_hours_per_session` | hours |
| `trainer_assessment_hours` | Trainer time assessing or remediating, where supplied | `cohorts_required x assessment_hours_per_cohort` | hours |
| `trainer_hours` | Trainer workload that can enter demand | delivery + preparation + assessment | hours |
| `learner_seat_hours` | Learners' time, for context only | `learner_count x track_hours` | learner_hours |

Inputs: `learner_count` (learners), `class_size` (learners), `track_hours` (hours), `session_length_hours` (hours), `prep_hours_per_session` (hours), `assessment_hours_per_cohort` (hours). Missing class size, session length, or preparation hours take `default_class_size`, `default_session_length_hours`, or `default_prep_hours_per_session`; each default is a user-configurable parameter and a proposed design value, not a measured result.

Edge cases:

- Both counts round up; there is no partial cohort or session.
- Zero learners gives zero cohorts and zero trainer hours.
- A class size or session length of zero or less, or any negative hours, is rejected.
- Learner seat-hours never enter demand, and a record excluded to prevent double counting contributes no trainer hours.

## Worked examples

Rounding up cohorts: `TRD-000007`, 25 learners in classes of 10, a 6-hour track in 3-hour sessions, 1.5 preparation hours per session, 1 assessment hour per cohort.

```yaml worked-example
name: cohorts round up
function: training_capacity
inputs: {learner_count: 25, class_size: 10, track_hours: 6, session_length_hours: 3, prep_hours_per_session: 1.5, assessment_hours_per_cohort: 1}
expected: {cohorts_required: 3, sessions_per_cohort: 2, sessions_required: 6, trainer_delivery_hours: 18, trainer_preparation_hours: 9, trainer_assessment_hours: 3, trainer_hours: 30, learner_seat_hours: 150}
```

Rounding up sessions and keeping learner hours apart: `TRD-000002`, an administrator refresher, 8 learners in classes of 10, a 3-hour track in 1.5-hour sessions.

```yaml worked-example
name: small refresher
function: training_capacity
inputs: {learner_count: 8, class_size: 10, track_hours: 3, session_length_hours: 1.5, prep_hours_per_session: 0.5, assessment_hours_per_cohort: 0.5}
expected: {cohorts_required: 1, sessions_per_cohort: 2, sessions_required: 2, trainer_delivery_hours: 3, trainer_preparation_hours: 1, trainer_assessment_hours: 0.5, trainer_hours: 4.5, learner_seat_hours: 24}
```

Larger rollout: `TRD-000003`, 45 learners in classes of 12, a 6-hour track in 2-hour sessions. The 270 learner seat-hours are learners' time; only the 40 trainer hours can enter demand.

```yaml worked-example
name: larger rollout
function: training_capacity
inputs: {learner_count: 45, class_size: 12, track_hours: 6, session_length_hours: 2, prep_hours_per_session: 1, assessment_hours_per_cohort: 1}
expected: {cohorts_required: 4, sessions_per_cohort: 3, sessions_required: 12, trainer_delivery_hours: 24, trainer_preparation_hours: 12, trainer_assessment_hours: 4, trainer_hours: 40, learner_seat_hours: 270}
```

Defaults applied: `TRD-000006` gives no class size, session length, or preparation hours, so the defaults (12 learners, 2 hours, 1 hour) apply.

```yaml worked-example
name: defaults applied
function: training_capacity
inputs: {learner_count: 10, class_size: 12, track_hours: 4, session_length_hours: 2, prep_hours_per_session: 1, assessment_hours_per_cohort: 0}
expected: {cohorts_required: 1, sessions_per_cohort: 2, sessions_required: 2, trainer_delivery_hours: 4, trainer_preparation_hours: 2, trainer_hours: 6, learner_seat_hours: 40}
```
