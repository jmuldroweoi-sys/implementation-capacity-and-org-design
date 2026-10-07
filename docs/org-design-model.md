# Organization-stage model

Implementation organizations change shape as they grow. R2 describes four stages so a team can choose planning settings that fit, and so a capacity review can ask whether the current shape still fits the work. The stages are descriptive, not universal benchmarks.

## The four stages

Exactly the four shared-standard stages, each with a profile in `profiles/`:

| Stage | Profile | Typical operating model | Signals that suggest reviewing the stage |
|---|---|---|---|
| `startup` | `ORG-000001` | One person may implement, train, support, and coordinate; minimal formal specialization; a lightweight capacity review | Concurrency rises and work competes across customers; one person is the bottleneck for every launch |
| `early_scale` | `ORG-000002` | A small team; some role separation; new hires ramping beside experienced people | Concurrency increases; work competes across customers; inconsistency appears; new-hire ramp consumes experienced capacity |
| `structured_growth` | `ORG-000003` | Specialization begins; enablement, operations, or lead functions appear | Demand forecasts matter before the hiring lead time; coaching and management overhead becomes material |
| `mature` | `ORG-000004` | Segmented delivery; dedicated operations, enablement, and portfolio planning | Formal portfolio planning, cost-to-serve, and continuous improvement become more important |

Each profile also sets `max_active_projects_per_role`, a concurrency observation threshold that is a user-configurable parameter and a proposed design value, not a measured result.

## Human selection

- A named person selects the stage. R2 records the selection with an `org_profile.selected` event whose actor is that person (`actor_type: human`).
- R2 never determines the stage from headcount and never changes it: not from startup to early_scale, not from early_scale to structured_growth, nor any other move.
- R2 may calculate signals that suggest reviewing the stage, such as concurrency above the configured maximum or repeated coverage gaps. They appear in the operating review as questions.
- The validator (V27) fails if a selection event has a non-human actor or if any snapshot's stage differs from its scenario's selected stage.

## Role mix

R2 plans by role and does not require every organization to have every role. In the synthetic data, Scenario A's one person holds four roles; Scenario D separates implementation lead, technical specialist, enablement, and support. R2 models how work is allocated across roles; it prescribes no titles and no reporting lines.

## People-data boundary

R2 uses only the operational planning fields capacity needs: a person ID, a neutral label, roles, scheduled and available hours, ramp state, and capacity parameters. It is not an HR system and holds no demographic or protected-class data, no salary or compensation, no performance ratings, and no private one-to-one notes. Later management-workload inputs from the team management toolkit (R5) enter only as aggregated hours where approved.

**Capacity measures available work, not employee worth.** R2 workload data must never be used to conclude that someone is inefficient, underperforming, or ready for promotion, and low capacity never means poor performance.
