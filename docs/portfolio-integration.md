# Portfolio integration

R2 is one repository in a six-repository implementation portfolio that shares one standard (1.0.0, published in R1). This page says what R2 reads, what it publishes, and what it never owns.

## Inputs

| From | What | How | Status in v0.1 |
|---|---|---|---|
| R1 `implementation-operating-system` | Shared standard (IDs, events, labels, lifecycle phases, recommendation and event contracts), R1 projects, tasks, and roles | Pinned copies in `upstream/r1/` at v0.1.0 | Live |
| R3 `implementation-tracker-workbook` | Capacity Inputs: task, request, handoff, and phase hours with inclusion methods | Pinned copy in `upstream/r3/` at v0.1.0 | Live |
| R4 `implementation-enablement-program` | Training demand, session hours, ramp factors and duration | Interface fixtures in the planned R4 shape | Not built; fixtures only |
| R5 `implementation-team-management-toolkit` | Aggregated management workload hours | Not read in v0.1 | Later |
| R6 `implementation-ai-agent-framework` | AI review workload hours | Not read in v0.1 | Later |

## Outputs

| To | What |
|---|---|
| R5 | Workload context per role and month (capacity snapshots) and the selected organization stage |
| R6 | Capacity events and snapshots, read only, as inputs to drafted narratives that a person reviews |
| R1 | `golive_support.computed` and `org_profile.selected` events (R1 is a registered consumer) |
| Analytics track | The event contract and synthetic data |

## Authority boundary

| R2 owns | R2 never owns |
|---|---|
| Demand modeling, supply modeling, effective capacity, load ratio, capacity gap | Project, phase, task, and request status (R1) |
| Training capacity and launch-support capacity | Readiness and go or no-go decisions (R1) |
| Staffing triggers and staffing recommendations (proposed only) | Training completion, proficiency, credentials, ramp definitions (R4) |
| Organization-stage planning and role-mix planning | People ratings and one-to-ones (R5, humans only) |
| Ramp-capacity loss (as hours, from R4 factors) | Hiring, budget, compensation, and reorganization decisions (humans) |
| Cost-to-serve and executive-operational reporting (later versions) | AI narratives (R6, never authoritative) |

## Changing a pin

Pins change only from an explicit full commit: `python tools/sync_upstream.py --r1-repo PATH --r1-commit FULL_SHA --r3-repo PATH --r3-commit FULL_SHA`, then rerun the calculator and every check. If R2 ever needs the shared standard, R1, or R3 to change, that change is made in the owning repository first; R2 never patches its copies.
