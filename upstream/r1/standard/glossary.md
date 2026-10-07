# Glossary

Standard version: 1.0.0

One canonical term per concept. Use these words, and only these words, in every repository that pins this standard. Where a concept's rules or calculations belong to another repository, the entry says so; the definition here is shared, the authority is not.

Repository names: R1 `implementation-operating-system`, R2 `implementation-capacity-and-org-design`, R3 `implementation-tracker-workbook`, R4 `implementation-enablement-program`, R5 `implementation-team-management-toolkit`, R6 `implementation-ai-agent-framework`.

| Term | Definition | ID prefix | Authority |
|---|---|---|---|
| customer | The organization that receives the implementation. Customers are referred to generically; no real customer is ever named. | none | R1 |
| implementation project | The time-bound effort to put a system into use for one customer. "Project" is the short form and means the same thing. | PRJ | R1 |
| phase | One of the ten reference lifecycle stages (Initiate to Review) as it occurs within one project. | PHS | R1 |
| milestone | A dated checkpoint within a project that is either achieved or missed. | MLS | R1 |
| task | A unit of work with an owner, a status, and usually a due date. | TSK | R1 |
| dependency | A relationship in which one task, milestone, or request cannot start or finish until another one does. A dependency is a link between records, not a record of its own. | none | R1 |
| request | An ask for input, approval, or action, from the customer or within the team, that moves through a defined state machine. | REQ | R1 |
| handoff | A transfer of responsibility for work from one role or team to another, with agreed information passed along. | HND | R1 |
| risk | Something that has not happened but could harm a project's scope, timeline, quality, or adoption. | RSK | R1 |
| issue | Something that is harming a project now. A risk that occurs becomes an issue. | ISS | R1 |
| SLA rule | A deterministic rule that sets a response or completion target and what happens when it is missed. Targets are user-configurable parameters. | RUL | R1 |
| gate | The checkpoint at the end of a phase where evidence is reviewed before the project moves on. | none (gates are defined in configuration) | R1 |
| gate assessment | The recorded result of a gate: pass, pass_with_conditions, or hold, decided by a named human. | GAT | R1 |
| configuration item | A versioned unit of system configuration delivered for a customer, such as a workflow, form, rule, or integration setting. | CFG | R1 |
| environment | A copy of the system used for a purpose, such as building, testing, training, or live use. | ENV | R1 |
| readiness | The degree to which a project is prepared to launch across six categories: people, process, technology, data, training, support. Scored deterministically. | RDS, RDE | R1 |
| event | An immutable record of something that happened, in the shared event contract. Audit records are events. | EVT | R1 standard |
| recommendation | A proposal from a person, a deterministic rule, or an AI agent. It has no authority until a named human approves it. | REC | Schema: R1 standard. AI workflow: R6 |
| approval | A named human's recorded decision to approve or reject a subject. AI is never the approver. | APR | R1 standard |
| metric definition | The description of a metric: meaning, owner, grain, unit, and where its deterministic rule lives. | MTR | R1 standard; each metric's owner computes it |
| metric value | One computed value of a metric for one grain. | MTV (reserved) | The repository that owns the metric |
| role | A named set of responsibilities that people hold and work is assigned to. | ROL | R1 |
| person | An individual, recorded by ID and role label only. Synthetic data never uses human-style names. | PER | R1 |
| profile | A saved configuration that describes an organization stage, complexity tier, service tier, or segment. | PRF | R1 |
| scenario | A labeled synthetic context (Scenario A to E) used only in examples and optional packs. | SCN | R1 |
| demand | Hours of work required in a period, from one demand method per project and period. | DMN | Shared definition; authoritative calculation belongs to R2 |
| supply | Hours people have available for project work in a period after allowances. | SUP | Shared definition; authoritative calculation belongs to R2 |
| capacity | Supply that can be applied to demand in a period, by role or team. | CAP, RCP | Shared definition; authoritative calculation belongs to R2 |
| capacity gap | Demand minus capacity for a period. Positive means more work than capacity. | none (a field of a capacity snapshot) | Shared definition; authoritative calculation belongs to R2 |
| load ratio | Demand hours divided by supply hours. It can exceed 1. It is not utilization, which is reserved for actual hours worked divided by available hours. | none (a field of a capacity snapshot) | Shared definition; authoritative calculation belongs to R2 |
| proficiency | A person's demonstrated ability against learning objectives, recorded deterministically as pass or not_yet. | PFR | Shared definition; authority belongs to R4 |
| competency | An observable capability with behavioral anchors by level, used for development and review. | CMP | Shared definition; authority belongs to R5, human judgments only |
| credential | A human-granted recognition that a person may perform a defined role, such as delivering a course. R4 records the learning requirements; R5 records the review and the grant. | CRQ (requirement), CDR (review), CDG (grant) | Requirements: R4. Review and grant: R5 |

## Rules

- Use the canonical term. Do not introduce synonyms such as "client", "account", "engagement", "ticket", or "user" for these concepts.
- Use generic wording only: no employer, vendor, product, or industry-specific terms.
- A repository may add terms for concepts it alone owns, in its own documentation. It may not redefine a term listed here.
