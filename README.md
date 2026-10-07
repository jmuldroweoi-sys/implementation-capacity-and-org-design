# implementation-capacity-and-org-design

Deterministic workload, capacity, staffing, and organization-stage modeling for implementation teams (cost-to-serve is planned for a later version). A Python reference calculator turns implementation workload into demand, effective capacity, capacity gaps, load ratios, training and launch-support hours, and staffing signals that support a staffing conversation. It never makes the decision.

> **Status: version 0.1.0, released 2026-10-07 (tag `v0.1.0`).** Reference implementation built on shared standard 1.0.0 and pinned to R1 [`implementation-operating-system`](https://github.com/jmuldroweoi-sys/implementation-operating-system) v0.1.0 and R3 [`implementation-tracker-workbook`](https://github.com/jmuldroweoi-sys/implementation-tracker-workbook) v0.1.0 ([`standard/standard-reference.yaml`](standard/standard-reference.yaml)). It has not been historically deployed as this exact model. Every number in the bundled data is synthetic data, and nothing here reports a measured result. Cost-to-serve is planned for a later version; v0.1 does not calculate it.

**How the three repositories fit:** R1 defines how implementation work operates (lifecycle, records, rules, events). R3 is the working tracker where one implementation professional runs that work and exports Capacity Inputs once a month. R2, this repository, consumes that workload and translates it into capacity and staffing-planning signals. R4 `implementation-enablement-program`, the companion enablement repository (published under the same account after R2), owns training demand and ramp, which R2 reads as inputs. R2 does not replace R1, R3, or R4 and never changes their records.

## Purpose

Answer, with arithmetic anyone can check, the monthly question every implementation team eventually asks: *can we take this on?* R2 reads workload that R1 defines and R3 exports, adds a forecast for work that is not tasked yet, subtracts every named allowance from scheduled hours, and shows where demand is greater than supply, when a staffing conversation is due, and how much capacity training and launch support consume.

Designed and maintained by Jared Muldrow, an implementation and onboarding professional who runs delivery work hands-on and designs the systems, controls, and tooling around it. That experience informed the design as inspiration only: no employer document, data, ratio, or wording is used here.

## Who this is for

- **One implementation professional working alone**, who wants a personal "can I take this project?" check in under an hour a month (Starter Mode).
- **An implementation lead in a small team**, who needs a role-level view: who is over-committed, where a new hire's ramp leaves a gap, and when to raise staffing timing.
- **A growing or mature delivery organization**, which needs the same model at more roles, more people, and a longer horizon, with an operating-review pack for a monthly capacity conversation.

## What questions R2 answers

| Question | Where the answer is |
|---|---|
| How much implementation work is coming? | Demand records (`data/synthetic/phase-demand.csv`), by method, project, role, and month |
| How much usable delivery capacity exists? | Supply records and role capacity (`supply-records.csv`, `role-capacity.csv`) |
| Where is demand greater than supply? | Capacity snapshots: `capacity_gap_hours` above 0 and `load_ratio` |
| When should staffing be discussed? | Staffing triggers, proposed recommendations, and the latest staffing start date |
| How much capacity do training and launch support consume? | `training-capacity.csv` (trainer hours) and `golive-support.csv` |
| What happens to capacity while new people ramp? | `ramp_loss_hours` on the ramping person and `mentor_hours` on the mentor |
| When does specialization become worth considering? | Concurrency observations and organization-stage signals, for a person to judge |
| What does the workload cost to serve? | Planned for a later version (`CTS` is reserved); v0.1 does not calculate cost |
| How should these signals be summarized for an operational review? | `reports/executive-pack/` |

## Relationship to R1

R1 and shared standard 1.0.0 are authoritative for shared vocabulary, IDs, events, projects, tasks, roles, lifecycle phases, readiness, and launch decisions. R2 pins R1 v0.1.0 at commit `5adf58a` and copies the files it reads into `upstream/r1/` with SHA-256 hashes; the validator fails if a copy drifts. R2 uses R1 project, task, and role IDs, R1's ten phase keys in its effort curves, and only the R2 prefixes and events that standard 1.0.0 registers. R2 never writes a project status, task status, readiness score, or go or no-go decision.

## Relationship to R3

R3 is authoritative for its Capacity Inputs export shape and meaning. R2 pins R3 v0.1.0 at commit `dc498db`, imports every Capacity Inputs row inside the planning horizon unchanged (hours, role, workload component, inclusion method), and never redefines what a row means. Rows R3 marks `informational_only` or `excluded_to_prevent_double_count` stay out of demand exactly as R3 says.

## Demand model

Every demand record uses exactly one of two methods (V4 decision D9):

- **`bottom_up`**: planned task hours from R3 Capacity Inputs, for projects with real task detail. Actual hours are kept beside them for retrospective comparison and never become demand.
- **`top_down`**: a complexity tier's configured effort per role, spread across the months of an illustrative phase-effort curve, for forecast or untasked work.

A project contributes through one authoritative method per month. When bottom-up task workload exists for a project and month, the top-down rows for that project and month are kept but marked `excluded_to_prevent_double_count`. See [`docs/demand-model.md`](docs/demand-model.md) and [`docs/source-precedence.md`](docs/source-precedence.md).

## Supply model

For each person, role, and month: scheduled hours minus unavailable hours gives gross available hours; minus non-project, own-training, and other named reductions gives project-available hours; times the ramp factor gives ramp-adjusted hours; minus mentoring hours gives effective capacity. There is no universal productive percentage: every reduction is a named allowance in hours. Ramp loss is charged only to the ramping person and mentoring only to the mentor. See [`docs/supply-model.md`](docs/supply-model.md).

## Capacity and load

For each scenario, role, and month, `capacity_gap_hours = demand_hours - effective_capacity_hours`, following the shared standard's definition (positive means more work than capacity). `load_ratio = demand_hours / effective_capacity_hours`. When effective capacity is zero, R2 does not divide and does not substitute zero: the snapshot records `undefined_no_capacity` and keeps the raw hours. R2 does not treat any load ratio as good or bad for every team; every threshold is a user-configurable parameter. See [`docs/capacity-model.md`](docs/capacity-model.md).

## Training capacity

Training demand reaches R2 only from the enablement repository (R4, V4 decision D10). R2 v0.1 does not read R4 directly: it reads interface fixtures in R4's training-demand shape, and R4 v0.1 documents how its own records map to that shape. Cohorts and sessions round up; trainer hours are delivery plus preparation plus assessment; learner seat-hours are reported for context and are never trainer workload. See [`docs/training-capacity-model.md`](docs/training-capacity-model.md).

## Launch-support capacity

Rehearsal, cutover, command-center, and hypercare support hours are `people_count x hours_per_person_per_day x days`. They are workload only: R1 owns readiness, cutover logic, and the go or no-go decision. See [`docs/golive-support-model.md`](docs/golive-support-model.md).

## Staffing triggers

A trigger means operational conditions justify a staffing conversation; it never means hire someone. `STG-000001` fires after the load ratio stays at or above the upper threshold for the configured number of consecutive months and clears only after it stays at or below a lower threshold (hysteresis). `STG-000002` fires when a role has demand and zero capacity. Each firing records a staffing recommendation with status `proposed` and a latest staffing start date (`projected_gap_date - hiring_lead_time - ramp_duration`). A named person decides. See [`docs/staffing-trigger-model.md`](docs/staffing-trigger-model.md).

## Organization-stage model

Four stages from the shared standard: `startup`, `early_scale`, `structured_growth`, `mature`. A named person selects the stage and R2 records it with an `org_profile.selected` event. R2 may surface signals that suggest reviewing the stage; it never changes the stage and never infers it from headcount. Capacity measures available work time, not anyone's worth or performance. See [`docs/org-design-model.md`](docs/org-design-model.md).

## Practical workflow

Once a month, one implementation professional exports Capacity Inputs from R3, adds forecast projects, updates availability and ramp, imports training and launch-support demand, runs `python tools/capacity_calc.py`, reviews gaps, load ratios, triggers, and source warnings, and brings the operating-review summary to a staffing conversation. Twelve steps, each with its input, file, rule, output, human decision, and consumer: [`docs/practical-workflow.md`](docs/practical-workflow.md). Starter Mode needs only five inputs.

## Synthetic data

One coherent synthetic planning universe ([`data/synthetic/`](data/synthetic/README.md)) across four scenarios with neutral labels: Scenario A (startup), Scenario B (early scale), Scenario C (structured growth), Scenario D (mature). People appear only as IDs with labels such as Person A. R1 projects keep their R1 IDs; forecast projects use new IDs. The only hand-authored input is `data/synthetic/universe.yaml`; every other file is generated. Exact row counts: [`verification/synthetic-data-check.md`](verification/synthetic-data-check.md).

## Deterministic calculations

`tools/capacity_calc.py` implements every v0.1 formula with decimal arithmetic, a fixed calculation time, and no network, clock, randomness, or language model. The same inputs always produce byte-identical outputs. Each capacity snapshot carries an `inputs_digest` (SHA-256 of its exact input record IDs and hours), a `config_digest`, the calculation version, and the standard version, so a reviewer can trace any gap back to its inputs. Formulas with worked examples: [`formulas/`](formulas/capacity-formulas.md).

## Verification

```
pip install -r requirements.txt
python tools/capacity_calc.py --check
python tools/validate.py
python -m unittest discover -s tests -v
```

The validator runs 48 checks, recomputing every formula from raw record fields; the tests include deliberate negative fixtures. CI runs both plus a secret scan. Evidence: [`verification/`](verification/R2-V0.1-CHECKLIST.md).

## Limitations

- Monthly periods only (`YYYY-MM`); weekly planning is not modeled.
- Demand and supply are forecasts. Actual hours are carried for comparison but v0.1 has no actual-supply records.
- Training demand and ramp factors are interface fixtures in R4's shape; R2 v0.1 does not read R4 records directly.
- Cost-to-serve, builder capacity, executive metric registrations, and a spreadsheet version of the model are planned for later versions.
- Thresholds, curves, and effort drivers are illustrative examples; a team must set its own.
- The model can help surface a staffing conversation. It cannot say whether to hire, budget, reorganize, or reassign anyone.

## AI assistance

AI assisted with this repository: Claude (Anthropic) helped structure the documentation, draft portions of the implementation (the calculator, validator, schemas, and tests), and plan the implementation steps, under the author's direction. Deterministic code, not AI, performs every calculation: demand, supply, capacity, load ratio, gap, trigger state, and staffing timing. AI never approves staffing and never calculates headcount. Every release receives human review and approval by the author before publication, recorded in [`verification/release-gate.md`](verification/release-gate.md).

## Versioning

| Version | Value |
|---|---|
| Repository (R2) | 0.1.0, released 2026-10-07, tag `v0.1.0` (`CHANGELOG.md`) |
| Calculation version | 0.1.0 |
| R2 record schemas | 0.1.0 |
| Shared standard | 1.0.0 |
| Pinned R1 | v0.1.0, commit `5adf58a08f039f44b05e50c6ceb9750ed6fb5027` |
| Pinned R3 | v0.1.0, commit `dc498db3ca0263f6b9083e3a43cf9b247654b9ff` |

## License

MIT. See [`LICENSE`](LICENSE).
