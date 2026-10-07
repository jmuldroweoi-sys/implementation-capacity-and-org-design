# Contributing

R2 consumes R1 and R3 and owns capacity planning only. It never redefines what R1 or R3 owns. Every change is reviewed by a human before it merges.

## What may change here

- Formulas in `tools/capacity_calc.py`, provided the schemas, worked examples, validator, and tests change with them.
- Configuration in `config/` and `profiles/`, keeping the labels on every number.
- The synthetic universe in `data/synthetic/universe.yaml`.
- R2 schemas in `schemas/`.

## What may never change here

- Anything under `upstream/`. These are byte-identical copies of pinned R1 and R3 commits. Change R1 or R3 first, then run `python tools/sync_upstream.py --r1-repo PATH --r1-commit FULL_SHA --r3-repo PATH --r3-commit FULL_SHA`, regenerate, and revalidate.
- Shared vocabulary, ID prefixes, or event types. They come from shared standard 1.0.0 in R1. R2 adds no prefix and no event.
- The meaning of an R3 Capacity Inputs row.
- Project, task, or request status, readiness, launch decisions, training completion, proficiency, or any people decision.
- Any generated file by hand. Edit the inputs and run `python tools/capacity_calc.py`.

## Change process

1. Change the inputs, configuration, or calculator.
2. Regenerate: `python tools/capacity_calc.py`.
3. If a computed value quoted in documentation changed, update the worked example or prose and the test that locks it, and say why in the change.
4. Run every check: `python tools/capacity_calc.py --check`, `python tools/validate.py`, `python -m unittest discover -s tests -v`.
5. Record the change in `CHANGELOG.md`.

## Public-safety requirements

- Write everything freshly. Never copy wording, structure, ratios, or numbers from any organization's documents, plans, or systems.
- Never include real names of people, customers, employers, vendors, products, or internal tools, and never include real headcount, salaries, margins, utilization, staffing plans, ratios, or workloads.
- Run the validator with the private blocklist (`--blocklist FILE`, kept outside this repository) before any change intended for publication.
- Never state an outcome the model does not show. Use "designed to", "illustrates", "reference implementation", "can help surface", and "supports a staffing conversation".

## Labels

Synthetic records are labeled synthetic data; examples are labeled illustrative example; adjustable values are labeled user-configurable parameter; design numbers are labeled proposed design value, not a measured result. Use the exact wording on one line; the validator rejects near-variants.
