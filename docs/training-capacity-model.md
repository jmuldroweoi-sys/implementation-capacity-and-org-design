# Training capacity model

How training work becomes trainer workload, and how R2 keeps learner time out of it.

## Where training demand comes from

Training demand (`TRD`) reaches R2 only from the enablement repository (R4, V4 decision D10). R1 does not export training fields, so training hours are never counted from two places. R4 is not built yet: every v0.1 training-demand record is an **interface fixture** in the planned R4 shape, marked `source: r4_interface_fixture`. R2 defines no curriculum, course, or track; it only reads the numbers it needs.

| Field | Meaning | Unit |
|---|---|---|
| `learner_count` | Learners to train | learners |
| `class_size` | Learners per cohort (or `default_class_size`) | learners |
| `track_hours` | Contact hours of the track per cohort | hours |
| `session_length_hours` | Length of one session (or `default_session_length_hours`) | hours |
| `prep_hours_per_session` | Trainer preparation per delivered session (or `default_prep_hours_per_session`) | hours |
| `assessment_hours_per_cohort` | Trainer assessment or remediation hours per cohort, where supplied | hours |
| `trainer_role_id` | The role whose capacity the delivery consumes | role |

Defaults are in `config/parameters.yaml`; each is a user-configurable parameter and a proposed design value, not a measured result. The training capacity record says whether each value came from the record or a default.

## Formulas (training capacity, `TRC`)

| Output | Formula | Unit |
|---|---|---|
| `cohorts_required` | `ceil(learner_count / class_size)` | cohorts |
| `sessions_per_cohort` | `ceil(track_hours / session_length_hours)` | sessions |
| `sessions_required` | `cohorts_required x sessions_per_cohort` | sessions |
| `trainer_delivery_hours` | `cohorts_required x track_hours` | hours |
| `trainer_preparation_hours` | `sessions_required x prep_hours_per_session` | hours |
| `trainer_assessment_hours` | `cohorts_required x assessment_hours_per_cohort` | hours |
| `trainer_hours` | delivery + preparation + assessment | hours |
| `learner_seat_hours` | `learner_count x track_hours` | learner_hours |

Delivery uses the track's real contact time per cohort, not sessions times session length, because the last session of a cohort can be shorter. Both counts round up: 25 learners in classes of 10 need 3 cohorts.

## Four kinds of hours, never mixed

- **Learner seat-hours** are learners' time. They carry the unit `learner_hours`, appear only on the training capacity record, and never enter demand.
- **Trainer delivery hours** are the trainer's time in the room.
- **Trainer preparation hours** are the trainer's time preparing each session.
- **Assessment or remediation hours** are the trainer's time checking or supporting learners, where supplied.

Only `trainer_hours` of authoritative records enter demand, under the trainer's role. The validator fails if `learner_hours` appears on any other field or if snapshot training demand differs from the sum of authoritative trainer hours.

## Double-count boundary

Training delivery may already be planned as an R1 task and exported by R3, or represented in future R4 data. Such a record is `excluded_to_prevent_double_count` and names the covering task in `covered_by`; the validator checks that the named task is an authoritative workload component in the same project and month. In the synthetic data, `TRD-000001` is excluded because R1 task `TSK-000024` already counts the same end-user training.

## Events

Each training capacity record emits `training_capacity.computed` with `period` and `trainer_hours`.
