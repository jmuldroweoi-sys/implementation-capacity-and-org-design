# Changelog

This file tracks the R2 repository version. The pinned R1 and R3 commits and the shared-standard version are stated in each entry and in `standard/standard-reference.yaml`.

## [0.1.0] Unreleased

Pinned R1 v0.1.0 at commit `5adf58a08f039f44b05e50c6ceb9750ed6fb5027` and R3 v0.1.0 at commit `dc498db3ca0263f6b9083e3a43cf9b247654b9ff`. Shared standard 1.0.0.

### Added

- `tools/capacity_calc.py`: deterministic reference calculator for demand (bottom-up and top-down, one authoritative method per project and month), source precedence and double-count prevention, supply with named allowances, ramp and mentoring, effective capacity, capacity gap, load ratio with explicit zero-capacity handling, concurrency, training capacity, launch-support hours, staffing triggers with persistence and hysteresis, proposed staffing recommendations with staffing timing, and registered R2 events. It also generates the five operating-review reports and three verification reports.
- Nine JSON Schemas (capacity snapshot, demand record, supply record, role capacity, staffing trigger, staffing recommendation, training demand, training capacity, launch-support demand), every numeric field with an explicit unit.
- Configuration: parameters, demand drivers, supply rules, phase-effort curves, staffing triggers, training capacity, launch support; four organization-stage profiles.
- Pinned upstream copies of 14 R1 and R3 files with a SHA-256 manifest, and `tools/sync_upstream.py` to change a pin only from an explicit full commit.
- One synthetic planning universe across four scenarios, with every output file generated from it.
- `tools/validate.py` (48 checks) and unit, output, and negative tests with deliberate negative fixtures.
- Documentation: README, architecture, practical workflow (12 steps, Starter Mode, Mature Mode), demand, supply, capacity, training, launch-support, staffing-trigger, and organization-design models, source precedence, portfolio integration, formulas with executable worked examples, and verification records.

### Changed (documentation, 2026-10-07 publication-readiness review)

- README opening no longer lists cost-to-serve as current modeling; it is stated as planned for a later version.
- README names how R4 fits beside R1 and R3, without a link that would not work before R4 is published.
- Status wording updated in the README and the practical-workflow, supply, training-capacity, and portfolio-integration documents: R4 v0.1 exists, and R2 v0.1 still reads interface fixtures in R4's shape rather than R4 records. Configuration and data comments are unchanged because their bytes feed the configuration digest.
- `tests/test_docs.py` guards these three wording fixes.
- `verification/release-gate.md` records the readiness review; the human release review is still unsigned.

### Not in this version

- Cost-to-serve (`CTS`) and builder capacity (`BLD`) are reserved and unused; no `cost_to_serve.computed` event is produced.
- Executive metric registrations, the organization-profile schema, a builder-model comparison, and a generated spreadsheet model.
- R4, R5, and R6 integrations beyond R4 interface fixtures.
