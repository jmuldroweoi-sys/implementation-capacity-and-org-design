"""Validator for implementation-capacity-and-org-design (R2).

Reads files only; never publishes, pushes, or changes anything. Formula checks recompute
each value from the record's own raw fields, independently of tools/capacity_calc.py;
V39 then confirms the committed outputs are exactly what the calculator produces.

Checks (each prints PASS or FAIL):
  V01 required files                      V25 staffing trigger persistence
  V02 standard pin                        V26 staffing recommendations non-authoritative
  V03 R1 and R3 upstream copies           V27 organization profile human-selected
  V04 registered ID prefixes              V28 no universal ratio or outcome claim
  V05 registered event types              V29 required labels
  V06 JSON Schemas and records            V30 synthetic-data labels
  V07 YAML                                V31 event schema
  V08 units                               V32 referential integrity
  V09 monthly period format               V33 genericity (no vendor names)
  V10 demand method                       V34 private blocklist (when supplied)
  V11 source precedence                   V35 no secrets
  V12 no double-counted workload          V36 no em dashes
  V13 capacity inclusion method           V37 README sections and AI assistance
  V14 demand aggregation                  V38 practical workflow
  V15 effective capacity                  V39 generated outputs current
  V16 gap formula                         V40 parameters complete
  V17 load-ratio formula                  V41 phase-effort curves
  V18 zero-capacity handling              V42 people data boundary
  V19 ramp math                           V43 concurrency
  V20 mentor-load math                    V44 staffing timing
  V21 training cohort math                V45 reproducibility digests
  V22 session math                        V46 no duplicated upstream authority
  V23 trainer-hour math                   V47 forecast and actual kept distinct
  V24 launch-support math                 V48 formula worked examples

Private blocklist: --blocklist FILE ... or PORTFOLIO_GATE_BLOCKLIST (os.pathsep-separated),
outside this repository. Matched terms are never printed; only counts are.

Usage:
    python tools/validate.py [--root PATH] [--blocklist FILE ...]
Exit codes: 0 pass, 1 one or more failures.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402
from jsonschema import Draft202012Validator, FormatChecker  # noqa: E402

D = Decimal
BLOCKLIST_ENV = "PORTFOLIO_GATE_BLOCKLIST"
EM_DASH = chr(0x2014)
REPO = "implementation-capacity-and-org-design"
R2_PREFIXES = ("CAP", "DMN", "SUP", "RCP", "STG", "STR", "ORG", "TRD", "TRC", "GLS", "BLD", "CTS")
R2_UNUSED_IN_V01 = ("BLD", "CTS")
STAGES = ("startup", "early_scale", "structured_growth", "mature")
UNITS = {"hours", "ratio", "people", "projects", "learners", "learner_hours", "sessions", "cohorts", "days", "months", "rank"}
SCHEMAS = {  # schema file -> (data file, id field, parse JSON columns)
    "demand-record": ("data/synthetic/phase-demand.csv", "demand_record_id"),
    "supply-record": ("data/synthetic/supply-records.csv", "supply_record_id"),
    "role-capacity": ("data/synthetic/role-capacity.csv", "role_capacity_id"),
    "capacity-snapshot": ("data/synthetic/capacity-snapshots.csv", "capacity_snapshot_id"),
    "staffing-recommendation": ("data/synthetic/staffing-recommendations.csv", "staffing_recommendation_id"),
    "training-demand": ("data/synthetic/training-demand.csv", "training_demand_id"),
    "training-capacity": ("data/synthetic/training-capacity.csv", "training_capacity_id"),
    "golive-support-demand": ("data/synthetic/golive-support.csv", "golive_support_demand_id"),
    "staffing-trigger": (None, "staffing_trigger_id"),
}
REQUIRED_FILES = (
    "README.md", "LICENSE", "CHANGELOG.md", "CONTRIBUTING.md", ".gitignore", ".github/workflows/validate.yml", "requirements.txt",
    "standard/standard-reference.yaml", "upstream/manifest.yaml",
    "docs/architecture.md", "docs/practical-workflow.md", "docs/demand-model.md", "docs/supply-model.md", "docs/capacity-model.md",
    "docs/training-capacity-model.md", "docs/golive-support-model.md", "docs/staffing-trigger-model.md", "docs/org-design-model.md",
    "docs/source-precedence.md", "docs/portfolio-integration.md",
    "formulas/capacity-formulas.md", "formulas/training-formulas.md", "formulas/golive-support-formulas.md",
    "config/parameters.yaml", "config/demand-drivers.yaml", "config/supply-rules.yaml", "config/phase-effort-curves.yaml",
    "config/staffing-triggers.yaml", "config/training-capacity.yaml", "config/golive-support.yaml",
    "profiles/startup.yaml", "profiles/early-scale.yaml", "profiles/structured-growth.yaml", "profiles/mature.yaml",
    *(f"schemas/{s}.schema.json" for s in SCHEMAS),
    "data/synthetic/README.md", "data/synthetic/universe.yaml", "data/synthetic/scenarios.csv", "data/synthetic/people.csv",
    "data/synthetic/projects.csv", "data/synthetic/phase-demand.csv", "data/synthetic/training-demand.csv",
    "data/synthetic/training-capacity.csv", "data/synthetic/golive-support.csv", "data/synthetic/supply-records.csv",
    "data/synthetic/role-capacity.csv", "data/synthetic/capacity-snapshots.csv", "data/synthetic/staffing-recommendations.csv",
    "data/synthetic/events.jsonl",
    "reports/executive-pack/README.md", "reports/executive-pack/capacity-summary.md", "reports/executive-pack/demand-vs-supply.md",
    "reports/executive-pack/staffing-signals.md", "reports/executive-pack/training-support.md", "reports/executive-pack/operating-review.md",
    "tools/capacity_calc.py", "tools/validate.py", "tools/sync_upstream.py",
    "verification/R2-V0.1-CHECKLIST.md", "verification/formula-audit.md", "verification/source-precedence-check.md",
    "verification/synthetic-data-check.md", "verification/release-gate.md",
)
LABELS = ("proposed design value, not a measured result", "synthetic data", "illustrative example", "user-configurable parameter")
LABEL_VARIANTS = (
    re.compile(r"proposed\s+design\s+value(?!,\s+not\s+a\s+measured\s+result)", re.I),
    re.compile(r"\buser configurable parameter\b", re.I),
    re.compile(r"\billustrative-example\b(?!-[a-z0-9])", re.I),
    re.compile(r"\bsynthetic-data\b(?!-[a-z0-9])", re.I),
    # A label must sit on one line; a label broken across lines (for example in a wrapped
    # comment) is not the exact label.
    re.compile(r"\b(?:proposed|proposed design|design value,|value, not|not a|a measured|user-|user-configurable|illustrative)[ \t]*\n[ \t#>*-]*"
               r"(?:design|value|not a|measured|result|configurable|parameter|example)\b", re.I),
)
# Benchmark and outcome claims R2 must never make. Matched case-insensitively in every
# text file except this one and the tests (which hold deliberate negative fixtures).
CLAIM_PATTERNS = (
    re.compile(r"\b\d{1,3}\s?(?:%|percent)\s+(?:load|utili[sz]ation|capacity)?\s*(?:is|means|=)\s+(?:healthy|optimal|ideal|safe|hire|sustainable)", re.I),
    re.compile(r"\b(?:optimal|ideal|healthy|target)\s+(?:load ratio|utili[sz]ation)\b", re.I),
    re.compile(r"\bbest[- ]practice\s+(?:threshold|ratio|target|load)", re.I),
    re.compile(r"\bindustry\s+(?:benchmark|standard)\s+(?:ratio|threshold|load|utili[sz]ation)", re.I),
    re.compile(r"\bone\s+(?:implementation\s+)?(?:manager|lead|consultant)\s+should\s+(?:handle|manage|run)\s+\d", re.I),
    re.compile(r"\b(?:improves|increases)\s+utili[sz]ation\b", re.I),
    re.compile(r"\breduces\s+headcount\b", re.I),
    re.compile(r"\bincreases\s+margin\b", re.I),
    re.compile(r"\bprevents\s+burnout\b", re.I),
    re.compile(r"\boptimi[sz]es\s+staffing\b", re.I),
    re.compile(r"\bproven\s+forecasting\s+model\b", re.I),
)
FORBIDDEN_RECOMMENDATION = (
    re.compile(r"\b(?:hire|fire|release|promote|demote|reassign|terminate)\s+(?:Person\s+[A-Z]\b|PER-\d{6})", re.I),
    re.compile(r"\bbudget\s+(?:is\s+)?approved\b", re.I),
    re.compile(r"\bmust\s+(?:be\s+)?(?:restructured|reorgani[sz]ed)\b", re.I),
    re.compile(r"\b(?:underperform|inefficien|low performer|performance rating)", re.I),
)
PEOPLE_FIELDS_ALLOWED = {"person_id", "person_label", "scenario_id", "role_id", "scheduled_work_hours", "non_project_hours",
                         "first_period", "ramp_state", "mentor_of", "unit", "schema_version"}
FORBIDDEN_HEADER = re.compile(r"(salary|compensation|wage|bonus|rating|performance|gender|(?:^|_)age(?:_|$)|birth|ethnic|race|religio|disabil|"
                              r"nationality|marital|1on1|one_on_one|note_private|review_score|utilization_rate)", re.I)
UPSTREAM_AUTHORITY_FIELDS = ("project_status", "task_status", "request_status", "phase_status", "readiness_score", "gate_outcome",
                             "golive_decision", "go_no_go", "proficiency", "credential", "hire_decision", "approved_budget")
# Vendor and product names that must not appear, stored as SHA-256 hashes of the exact
# name so this public file never spells out the products it guards against. Names of
# one to three words are matched case-sensitively as whole words.
GENERICITY_TERM_HASHES = frozenset({
    "12e5f2025ea19bfe8f8eb2f2219e69af38260f1951f516a35e7390cd81e3f1d9",
    "33a7935db79df2a3bf5ac7ff9f2421015ff61623e005da1cf0cc9e1352c98069",
    "5a06b98b21528d307de51a5b5ab38d9650147fa5c022187dac64956cb5e74d9e",
    "5f5f6ddd5dbf171077a052fe33f2d349f2b3ee91a732c461fb380d801a482d3e",
    "61a463ae2530e7960c35f1ac06b8bf310d3b587de79ef9da386289ed3782089d",
    "73bcfe98830b53a1cabd2fa68c6ba8819adcfb9b0566f7ed5d455582d47973ed",
    "8b9b0b3f792de8a6ad54ee531bd8f2efba7a64189029519237d882b3724dbcfd",
    "a11413b0a4a315c2819e264b40f0ed5161a7b1cd1a2c1726661b7a25575fec6b",
    "b27fb38ba323745c91fe7fd9021605430d43bdb7d3be765266e29364d103e26f",
    "bbc323fb4c8234bba43e21ad21d450c9f059826ac4cbccabe423adaac7cab666",
    "ca96ecb62e7bfb333671f467cd2b0f8dccbc211153e41f6aa7c47ac391c62d6e",
    "dc7620ebfc35d54ef34e32b9eb6f69f1bfe93f294370c2798d91147e34e7ad56",
    "e35c40edf9819dd4f14de7dd4c038d3529312744942e49b7ac63ee165705057c",
    "ff8fdf4e47f0b0957ee901813bc6e5f24d862b6ac4c43d401b3f0f196e40a2b4",
})
VENDOR_TOKEN = re.compile(r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*")
SECRET_PATTERNS = (
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_\w{40,})"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b[\"']?\s*[:=]\s*[\"'][^\"'\s]{16,}[\"']"),
)
SECRET_FILES = re.compile(r"(?:^|/)(?:\.env(?:\..+)?|id_rsa|id_ed25519|.+\.pem|.+\.key)$")
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".jsonl", ".csv", ".py", ".txt", ".toml", ".cfg", ""}
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "dist", ".pytest_cache"}
SCAN_EXEMPT = {"tools/validate.py"}
README_SECTIONS = (
    "Purpose", "Who this is for", "What questions R2 answers", "Relationship to R1", "Relationship to R3", "Demand model",
    "Supply model", "Capacity and load", "Training capacity", "Launch-support capacity", "Staffing triggers",
    "Organization-stage model", "Practical workflow", "Synthetic data", "Deterministic calculations", "Verification",
    "Limitations", "AI assistance", "Versioning", "License",
)
WORKFLOW_STEPS = (
    "Export Capacity Inputs from R3", "Add future project forecast", "Update availability", "Update ramp factors",
    "Import training and launch-support demand", "Calculate demand", "Calculate effective capacity", "Review the gap",
    "Review the load ratio", "Review staffing triggers", "Review source and double-count warnings", "Prepare the operating-review summary",
)
WORKFLOW_FIELDS = ("Input", "File or entity", "Deterministic rule", "Output", "Human decision", "Downstream consumer")
PERIOD_RE = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def names_listed_vendor(text: str) -> bool:
    """True when any run of one to three words in text, compared case-sensitively, hashes
    to a listed vendor or product name."""
    words = VENDOR_TOKEN.findall(text)
    for n in (1, 2, 3):
        for i in range(len(words) - n + 1):
            if _sha256(" ".join(words[i:i + n])) in GENERICITY_TERM_HASHES:
                return True
    return False


class Result:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []

    def add(self, check: str, problems: list[str], ok_note: str) -> None:
        self.rows.append((check, not problems, "; ".join(problems[:8]) if problems else ok_note))

    @property
    def failed(self) -> bool:
        return any(not ok for _, ok, _ in self.rows)

    def status(self, code: str) -> bool:
        return next(ok for c, ok, _ in self.rows if c.startswith(code))


def repo_files(root: Path) -> list[Path]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        out += [Path(dirpath, n) for n in filenames]
    return sorted(out)


def rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix()


def text_of(path: Path) -> str | None:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def load_blocklist(given, root: Path) -> tuple[list[str], list[str]]:
    names = list(given or [])
    if not names and os.environ.get(BLOCKLIST_ENV):
        names = [p for p in os.environ[BLOCKLIST_ENV].split(os.pathsep) if p]
    terms, problems = [], []
    for name in names:
        path = Path(name).expanduser().resolve()
        if not path.is_file():
            problems.append("blocklist file not found")
            continue
        try:
            path.relative_to(root)
            problems.append("blocklist file must live outside this repository")
            continue
        except ValueError:
            pass
        terms += [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.strip().startswith("#")]
    return terms, problems


def guard(res: Result, check: str, fn) -> None:
    try:
        problems, ok = fn()
    except Exception as exc:  # noqa: BLE001
        problems, ok = [f"check could not run: {exc.__class__.__name__}: {exc}"], ""
    res.add(check, problems, ok)


def dnum(v) -> Decimal:
    return D(str(v)) if v not in (None, "") else D(0)


def q(x: Decimal, places: int) -> Decimal:
    return x.quantize(D(1).scaleb(-places), rounding=ROUND_HALF_UP)


def read_typed_csv(path: Path, schema: dict | None) -> list[dict]:
    props = (schema or {}).get("properties", {})
    out = []
    with path.open(encoding="utf-8", newline="") as h:
        for raw in csv.DictReader(h):
            rec = {}
            for k, v in raw.items():
                if v == "" or v is None:
                    continue
                t = props.get(k, {}).get("type", "string")
                if t == "integer":
                    rec[k] = int(v) if re.fullmatch(r"-?\d+", v) else v
                elif t == "number":
                    try:
                        rec[k] = float(v)
                    except ValueError:
                        rec[k] = v
                elif t == "array":
                    rec[k] = json.loads(v)
                else:
                    rec[k] = v
            out.append(rec)
    return out


def read_raw_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8", newline="") as h:
        r = csv.DictReader(h)
        rows = list(r)
        return list(r.fieldnames or []), rows


def validate(root: Path, blocklist: list[str] | None = None) -> Result:
    res = Result()
    cache: dict = {}

    def y(relpath):
        if relpath not in cache:
            cache[relpath] = yaml.safe_load((root / relpath).read_text(encoding="utf-8"))
        return cache[relpath]

    def schema(name):
        return json.loads((root / f"schemas/{name}.schema.json").read_text(encoding="utf-8"))

    def raw(name):
        key = ("raw", name)
        if key not in cache:
            cache[key] = read_raw_csv(root / f"data/synthetic/{name}")[1]
        return cache[key]

    def events():
        if "events" not in cache:
            cache["events"] = [json.loads(ln) for ln in (root / "data/synthetic/events.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
        return cache["events"]

    def params():
        return {p["parameter_id"]: p["value"] for p in y("config/parameters.yaml")["parameters"]}

    def registry():
        return y("upstream/r1/standard/id-registry.yaml")

    def catalog():
        return {e["event_type"]: e for e in y("upstream/r1/standard/event-catalog.yaml")["events"]}

    def text_files():
        for p in repo_files(root):
            r = rel(root, p)
            if r in SCAN_EXEMPT or r.startswith("tests/"):
                continue
            t = text_of(p)
            if t is not None:
                yield r, t

    # V01 ------------------------------------------------------------------------------
    def v01():
        missing = [f for f in REQUIRED_FILES if not (root / f).is_file()]
        return [f"missing {m}" for m in missing], f"{len(REQUIRED_FILES)} required files present"
    guard(res, "V01 required files", v01)

    # V02 ------------------------------------------------------------------------------
    def v02():
        ref = y("standard/standard-reference.yaml")
        man = y("upstream/manifest.yaml")
        problems = []
        if str(ref.get("shared_standard_version")) != "1.0.0":
            problems.append("shared_standard_version is not 1.0.0")
        for key in ("r1_commit", "r3_commit"):
            if not re.fullmatch(r"[0-9a-f]{40}", str(ref.get(key, ""))):
                problems.append(f"{key} is not a full commit SHA")
        commits = {(f["source_repo"], f["source_commit"]) for f in man["files"]}
        if ("implementation-operating-system", ref.get("r1_commit")) not in commits or ("implementation-tracker-workbook", ref.get("r3_commit")) not in commits:
            problems.append("manifest commits differ from standard-reference.yaml")
        if len(commits) != 2:
            problems.append("manifest mixes more than one commit per repository")
        if int(ref.get("pinned_files", -1)) != len(man["files"]):
            problems.append("pinned_files count differs from the manifest")
        if str(y("upstream/r1/standard/id-registry.yaml").get("standard_version")) != "1.0.0":
            problems.append("pinned id-registry is not standard 1.0.0")
        return problems, f"standard 1.0.0; R1 {ref.get('r1_version')} at {str(ref.get('r1_commit'))[:7]}; R3 {ref.get('r3_version')} at {str(ref.get('r3_commit'))[:7]}"
    guard(res, "V02 standard pin", v02)

    # V03 ------------------------------------------------------------------------------
    def v03():
        man = y("upstream/manifest.yaml")
        problems = []
        for f in man["files"]:
            p = root / f["local_path"]
            if not p.is_file():
                problems.append(f"missing pinned copy {f['local_path']}")
            elif hashlib.sha256(p.read_bytes()).hexdigest() != f["sha256"]:
                problems.append(f"{f['local_path']}: SHA-256 differs from the pinned source")
        on_disk = {rel(root, p) for p in repo_files(root / "upstream")} - {"upstream/manifest.yaml"} if (root / "upstream").is_dir() else set()
        on_disk = {("upstream/" + x if not x.startswith("upstream/") else x) for x in on_disk}
        listed = {f["local_path"] for f in man["files"]}
        problems += [f"unlisted file in upstream/: {x}" for x in sorted(on_disk - listed)]
        return problems, f"{len(man['files'])} pinned copies match their SHA-256"
    guard(res, "V03 R1 and R3 upstream copies", v03)

    # V04 ------------------------------------------------------------------------------
    def v04():
        reg = registry()
        active = {e["prefix"]: e for e in reg["prefixes"] if e["status"] == "active"}
        problems = []
        for pre in R2_PREFIXES:
            if active.get(pre, {}).get("owning_repo") != REPO:
                problems.append(f"{pre} is not an active R2 prefix in the registry")
        id_re = re.compile(r"\b([A-Z]{3})-\d{6}\b")
        used = defaultdict(set)
        for p in sorted((root / "data/synthetic").glob("*")):
            if p.suffix in (".csv", ".jsonl", ".yaml"):
                for m in id_re.finditer(p.read_text(encoding="utf-8")):
                    used[m.group(1)].add(p.name)
        for pre, files in sorted(used.items()):
            if pre not in active:
                problems.append(f"{pre} used in {sorted(files)[0]} but not an active registered prefix")
        for pre in R2_UNUSED_IN_V01:
            if pre in used:
                problems.append(f"{pre} is reserved and unused in v0.1 but appears in data")
        own = {"phase-demand.csv": "DMN", "supply-records.csv": "SUP", "role-capacity.csv": "RCP", "capacity-snapshots.csv": "CAP",
               "staffing-recommendations.csv": "STR", "training-demand.csv": "TRD", "training-capacity.csv": "TRC", "golive-support.csv": "GLS"}
        for name, pre in own.items():
            for r in raw(name):
                if not re.fullmatch(pre + r"-\d{6}", next(iter(r.values()))):
                    problems.append(f"{name}: first column is not a {pre} ID")
                    break
        return problems, f"{len(used)} prefixes used, all registered; R2 creates only {', '.join(p for p in R2_PREFIXES if p not in R2_UNUSED_IN_V01)}; BLD and CTS unused"
    guard(res, "V04 registered ID prefixes", v04)

    # V05 ------------------------------------------------------------------------------
    def v05():
        cat = catalog()
        problems = []
        types = defaultdict(int)
        for e in events():
            types[e.get("event_type")] += 1
            entry = cat.get(e.get("event_type"))
            if entry is None:
                problems.append(f"{e.get('event_id')}: unregistered event type")
            elif entry["producer_repo"] != REPO:
                problems.append(f"{e.get('event_id')}: {e['event_type']} is not produced by R2")
        if types.get("cost_to_serve.computed"):
            problems.append("cost_to_serve.computed events present; cost-to-serve is not implemented in v0.1")
        return problems, f"{sum(types.values())} events of {len(types)} registered R2 types; no cost_to_serve.computed"
    guard(res, "V05 registered event types", v05)

    # V06 ------------------------------------------------------------------------------
    def v06():
        problems, n = [], 0
        for name, (data, idf) in SCHEMAS.items():
            sc = schema(name)
            Draft202012Validator.check_schema(sc)
            v = Draft202012Validator(sc, format_checker=FormatChecker())
            rows = read_typed_csv(root / data, sc) if data else y("config/staffing-triggers.yaml")["triggers"]
            for r in rows:
                n += 1
                errs = sorted(v.iter_errors(r), key=lambda e: list(e.path))
                if errs:
                    problems.append(f"{r.get(idf)}: {errs[0].message[:120]}")
            for ex in sc.get("examples", []):
                if list(v.iter_errors(ex)):
                    problems.append(f"{name}: example does not validate")
            if data:
                with (root / data).open(encoding="utf-8", newline="") as h:
                    header = next(csv.reader(h))
                extra = [c for c in header if c not in sc["properties"]]
                if extra:
                    problems.append(f"{data}: columns not in schema {extra}")
        return problems, f"{len(SCHEMAS)} schemas valid; {n} records validate"
    guard(res, "V06 JSON Schemas and records", v06)

    # V07 ------------------------------------------------------------------------------
    def v07():
        problems, n = [], 0
        for p in repo_files(root):
            if p.suffix in (".yaml", ".yml"):
                n += 1
                try:
                    yaml.safe_load(p.read_text(encoding="utf-8"))
                except yaml.YAMLError as exc:
                    problems.append(f"{rel(root, p)}: {str(exc).splitlines()[0]}")
        return problems, f"{n} YAML files parse"
    guard(res, "V07 YAML", v07)

    # V08 ------------------------------------------------------------------------------
    def v08():
        problems = []
        learner_fields = set()
        for name in SCHEMAS:
            for prop, spec in schema(name)["properties"].items():
                if spec.get("type") in ("number", "integer"):
                    unit = spec.get("x-unit")
                    if unit not in UNITS:
                        problems.append(f"{name}.{prop}: missing or unknown x-unit {unit!r}")
                    if unit == "learner_hours":
                        learner_fields.add(f"{name}.{prop}")
        if learner_fields != {"training-capacity.learner_seat_hours"}:
            problems.append(f"learner_hours unit must appear only on training-capacity.learner_seat_hours, found {sorted(learner_fields)}")
        cap = schema("capacity-snapshot")["properties"]
        for f in ("project_demand_hours", "training_demand_hours", "golive_support_hours", "demand_hours", "effective_capacity_hours", "capacity_gap_hours"):
            if cap[f].get("x-unit") != "hours":
                problems.append(f"capacity-snapshot.{f} must be in hours")
        for name in ("phase-demand.csv", "supply-records.csv", "people.csv"):
            for r in raw(name):
                if r.get("unit") != "hours":
                    problems.append(f"{name}: unit {r.get('unit')!r} is not hours")
                    break
        for p in y("config/parameters.yaml")["parameters"]:
            if not p.get("unit"):
                problems.append(f"parameter {p.get('parameter_id')} has no unit")
        return problems, "every numeric schema field has an explicit unit; learner-hours isolated from trainer and project hours"
    guard(res, "V08 units", v08)

    # V09 ------------------------------------------------------------------------------
    def v09():
        P = params()
        start, end = P["planning_horizon_start"], P["planning_horizon_end"]
        problems, n = [], 0
        for name in ("phase-demand.csv", "supply-records.csv", "role-capacity.csv", "capacity-snapshots.csv", "training-demand.csv",
                     "training-capacity.csv", "golive-support.csv", "projects.csv"):
            for r in raw(name):
                n += 1
                p = r.get("period", "")
                if not PERIOD_RE.match(p):
                    problems.append(f"{name}: invalid period {p!r}")
                elif not (start <= p <= end):
                    problems.append(f"{name}: period {p} outside the planning horizon")
        for e in events():
            p = e.get("payload", {}).get("period")
            if p is not None and (not PERIOD_RE.match(str(p)) or not (start <= p <= end)):
                problems.append(f"{e.get('event_id')}: invalid payload period {p!r}")
        for key in ("planning_horizon_start", "planning_horizon_end"):
            if not PERIOD_RE.match(str(P[key])):
                problems.append(f"{key} is not YYYY-MM")
        return problems, f"{n} record periods are YYYY-MM inside {start} to {end}; monthly only"
    guard(res, "V09 monthly period format", v09)

    # V10 ------------------------------------------------------------------------------
    def v10():
        problems = []
        curves = {c["curve_id"] for c in y("config/phase-effort-curves.yaml")["curves"]}
        for r in raw("phase-demand.csv"):
            m = r["demand_method"]
            if m not in ("bottom_up", "top_down"):
                problems.append(f"{r['demand_record_id']}: demand_method {m!r}")
            if m == "top_down" and r["curve_id"] not in curves:
                problems.append(f"{r['demand_record_id']}: unknown curve {r['curve_id']}")
            if m == "bottom_up" and r["import_source_repo"] != "implementation-tracker-workbook":
                problems.append(f"{r['demand_record_id']}: bottom_up row not imported from R3")
        counts = defaultdict(int)
        for r in raw("phase-demand.csv"):
            counts[r["demand_method"]] += 1
        if not counts["bottom_up"] or not counts["top_down"]:
            problems.append("both demand methods must be demonstrated")
        return problems, f"bottom_up {counts['bottom_up']}, top_down {counts['top_down']}; only the two allowed methods"
    guard(res, "V10 demand method", v10)

    # V11 ------------------------------------------------------------------------------
    def v11():
        P = params()
        problems = []
        r3 = {r["capacity_input_id"]: r for r in read_raw_csv(root / "upstream/r3/exports/csv/capacity-inputs.csv")[1]}
        dem = raw("phase-demand.csv")
        imported = {r["import_record_id"]: r for r in dem if r["demand_method"] == "bottom_up"}
        for cid, src in r3.items():
            in_h = P["planning_horizon_start"] <= src["period"] <= P["planning_horizon_end"]
            row = imported.get(cid)
            if in_h and row is None:
                problems.append(f"{cid}: R3 row in the horizon was not imported")
                continue
            if not in_h:
                if row is not None:
                    problems.append(f"{cid}: R3 row outside the horizon was imported")
                continue
            for a, b in (("project_id", "project_id"), ("period", "period"), ("role_id", "role_id"), ("workload_component_id", "workload_component_id"),
                         ("workload_type", "workload_type"), ("capacity_inclusion_method", "capacity_inclusion_method"),
                         ("source_entity_id", "source_entity_id"), ("source_repo", "source_repo"), ("source_version", "source_version")):
                if row[a] != src[b]:
                    problems.append(f"{row['demand_record_id']}: {a} differs from R3 {cid} (R2 may not redefine R3 meaning)")
            if dnum(row["hours"]) != dnum(src["planned_hours"]) or dnum(row["actual_hours"]) != dnum(src["actual_hours"]):
                problems.append(f"{row['demand_record_id']}: hours differ from R3 {cid}")
        auth_bu = {(r["project_id"], r["period"]) for r in dem if r["demand_method"] == "bottom_up" and r["capacity_inclusion_method"] == "authoritative_workload"}
        for r in dem:
            if r["demand_method"] == "top_down":
                want = "excluded_to_prevent_double_count" if (r["project_id"], r["period"]) in auth_bu else "authoritative_workload"
                if r["capacity_inclusion_method"] != want:
                    problems.append(f"{r['demand_record_id']}: top_down inclusion should be {want} (precedence)")
            want_rank = "1" if r["demand_method"] == "bottom_up" else "3"
            if r["precedence_rank"] != want_rank:
                problems.append(f"{r['demand_record_id']}: precedence_rank {r['precedence_rank']} should be {want_rank}")
        for name in ("training-capacity.csv", "golive-support.csv"):
            for r in raw(name):
                if r["precedence_rank"] != "2":
                    problems.append(f"{name}: precedence_rank must be 2")
        return problems, f"{len(imported)} R3 rows imported unchanged; top_down yields to bottom_up on {len(auth_bu)} project-periods"
    guard(res, "V11 source precedence", v11)

    # V12 ------------------------------------------------------------------------------
    def v12():
        import capacity_calc as C  # noqa: PLC0415
        dem = raw("phase-demand.csv")
        problems = C.double_count_problems(dem)
        # Independent restatement of the same rule.
        seen_m, seen_c = defaultdict(set), defaultdict(int)
        for r in dem:
            if r["capacity_inclusion_method"] == "authoritative_workload":
                seen_m[(r["project_id"], r["period"])].add(r["demand_method"])
                seen_c[(r["workload_component_id"], r["period"])] += 1
        problems += [f"{k}: mixed authoritative methods" for k, v in seen_m.items() if len(v) > 1]
        problems += [f"{k}: component authoritative {v} times" for k, v in seen_c.items() if v > 1]
        return sorted(set(problems)), f"{len(seen_m)} project-periods with one authoritative method each; {len(seen_c)} components counted once"
    guard(res, "V12 no double-counted workload", v12)

    # V13 ------------------------------------------------------------------------------
    def v13():
        allowed = {"authoritative_workload", "informational_only", "excluded_to_prevent_double_count"}
        problems = []
        dem = raw("phase-demand.csv")
        for name in ("phase-demand.csv", "training-demand.csv", "training-capacity.csv", "golive-support.csv"):
            for r in raw(name):
                if r["capacity_inclusion_method"] not in allowed:
                    problems.append(f"{name}: {r['capacity_inclusion_method']!r} not allowed")
        auth_components = {(r["workload_component_id"], r["project_id"], r["period"]) for r in dem if r["capacity_inclusion_method"] == "authoritative_workload"}
        for t in raw("training-demand.csv"):
            if t["capacity_inclusion_method"] == "excluded_to_prevent_double_count":
                if (t["covered_by"], t["project_id"], t["period"]) not in auth_components:
                    problems.append(f"{t['training_demand_id']}: covered_by {t['covered_by']} is not an authoritative component in the same project and period")
            elif t["covered_by"]:
                problems.append(f"{t['training_demand_id']}: covered_by set on a record that is not excluded")
        for r in dem:
            if r["capacity_inclusion_method"] != "authoritative_workload" and not r["exclusion_reason"]:
                problems.append(f"{r['demand_record_id']}: excluded or informational without a reason")
        counts = defaultdict(int)
        for r in dem:
            counts[r["capacity_inclusion_method"]] += 1
        return problems, ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + "; excluded training names its covering component"
    guard(res, "V13 capacity inclusion method", v13)

    # V14 ------------------------------------------------------------------------------
    def v14():
        problems = []
        proj, trn, gls = defaultdict(lambda: D(0)), defaultdict(lambda: D(0)), defaultdict(lambda: D(0))
        for r in raw("phase-demand.csv"):
            if r["capacity_inclusion_method"] == "authoritative_workload":
                proj[(r["scenario_id"], r["role_id"], r["period"])] += dnum(r["hours"])
        for r in raw("training-capacity.csv"):
            if r["capacity_inclusion_method"] == "authoritative_workload":
                trn[(r["scenario_id"], r["trainer_role_id"], r["period"])] += dnum(r["trainer_hours"])
        for r in raw("golive-support.csv"):
            if r["capacity_inclusion_method"] == "authoritative_workload":
                gls[(r["scenario_id"], r["role_id"], r["period"])] += dnum(r["support_hours"])
        keys = set()
        for s in raw("capacity-snapshots.csv"):
            k = (s["scenario_id"], s["role_id"], s["period"])
            keys.add(k)
            parts = (dnum(s["project_demand_hours"]), dnum(s["training_demand_hours"]), dnum(s["golive_support_hours"]))
            if parts != (proj[k], trn[k], gls[k]):
                problems.append(f"{s['capacity_snapshot_id']}: demand components differ from authoritative records")
            if dnum(s["demand_hours"]) != sum(parts):
                problems.append(f"{s['capacity_snapshot_id']}: demand_hours is not the sum of its components")
        orphan = [k for k in set(proj) | set(trn) | set(gls) if k not in keys]
        problems += [f"authoritative demand {k} has no snapshot" for k in orphan]
        total = sum(proj.values()) + sum(trn.values()) + sum(gls.values())
        return problems, f"{len(keys)} snapshots; total demand {total} hours equals authoritative project, trainer, and launch-support hours"
    guard(res, "V14 demand aggregation", v14)

    # V15 ------------------------------------------------------------------------------
    def v15():
        P = params()
        hp = int(P["hours_decimal_places"])
        problems = []
        sums = defaultdict(lambda: defaultdict(lambda: D(0)))
        people = defaultdict(set)
        for s in raw("supply-records.csv"):
            sid = s["supply_record_id"]
            n = {k: dnum(s[k]) for k in ("scheduled_work_hours", "unavailable_hours", "non_project_hours", "training_hours",
                                         "other_capacity_reduction_hours", "ramp_factor", "mentor_hours")}
            gross = n["scheduled_work_hours"] - n["unavailable_hours"]
            pav = gross - n["non_project_hours"] - n["training_hours"] - n["other_capacity_reduction_hours"]
            radj = q(pav * n["ramp_factor"], hp)
            eff = radj - n["mentor_hours"]
            for f, want in (("gross_available_hours", gross), ("project_available_hours", pav), ("ramp_adjusted_hours", radj),
                            ("ramp_loss_hours", pav - radj), ("effective_capacity_hours", eff)):
                if dnum(s[f]) != want:
                    problems.append(f"{sid}: {f} {s[f]} should be {want}")
            if eff < 0 or any(v < 0 for v in n.values()):
                problems.append(f"{sid}: negative hours")
            k = (s["scenario_id"], s["role_id"], s["period"])
            people[k].add(s["person_id"])
            for f in ("scheduled_work_hours", "unavailable_hours", "gross_available_hours", "non_project_hours", "training_hours",
                      "other_capacity_reduction_hours", "project_available_hours", "ramp_loss_hours", "mentor_hours", "effective_capacity_hours"):
                sums[k][f] += dnum(s[f])
        rcp = {}
        for r in raw("role-capacity.csv"):
            k = (r["scenario_id"], r["role_id"], r["period"])
            rcp[r["role_capacity_id"]] = r
            for f, v in sums[k].items():
                if dnum(r[f]) != v:
                    problems.append(f"{r['role_capacity_id']}: {f} is not the sum of its supply records")
            if int(r["person_count"]) != len(people[k]):
                problems.append(f"{r['role_capacity_id']}: person_count differs")
        for s in raw("capacity-snapshots.csv"):
            r = rcp.get(s["role_capacity_id"])
            if r is None or (r["scenario_id"], r["role_id"], r["period"]) != (s["scenario_id"], s["role_id"], s["period"]):
                problems.append(f"{s['capacity_snapshot_id']}: role_capacity_id does not match")
            elif dnum(s["effective_capacity_hours"]) != dnum(r["effective_capacity_hours"]):
                problems.append(f"{s['capacity_snapshot_id']}: effective_capacity_hours differs from its role capacity")
        return problems, f"{len(raw('supply-records.csv'))} supply records recomputed; {len(rcp)} role capacities and snapshots match"
    guard(res, "V15 effective capacity", v15)

    # V16 ------------------------------------------------------------------------------
    def v16():
        problems = []
        for s in raw("capacity-snapshots.csv"):
            if dnum(s["capacity_gap_hours"]) != dnum(s["demand_hours"]) - dnum(s["effective_capacity_hours"]):
                problems.append(f"{s['capacity_snapshot_id']}: gap is not demand minus effective capacity")
        signs = defaultdict(int)
        for s in raw("capacity-snapshots.csv"):
            g = dnum(s["capacity_gap_hours"])
            signs["positive" if g > 0 else "zero" if g == 0 else "negative"] += 1
        return problems, "capacity_gap_hours = demand_hours - effective_capacity_hours (standard 1.0.0 sign); " + ", ".join(f"{k} {v}" for k, v in sorted(signs.items()))
    guard(res, "V16 gap formula", v16)

    # V17 ------------------------------------------------------------------------------
    def v17():
        rp = int(params()["ratio_decimal_places"])
        problems, n = [], 0
        for s in raw("capacity-snapshots.csv"):
            sup = dnum(s["effective_capacity_hours"])
            if sup != 0:
                n += 1
                want = q(dnum(s["demand_hours"]) / sup, rp)
                if s["load_ratio_state"] != "defined" or dnum(s["load_ratio"]) != want:
                    problems.append(f"{s['capacity_snapshot_id']}: load_ratio {s['load_ratio']} should be {want}")
        for name in SCHEMAS:
            if "utilization_rate" in schema(name)["properties"]:
                problems.append(f"{name}: utilization_rate is retired; use load_ratio")
        return problems, f"{n} defined load ratios = demand_hours / effective_capacity_hours, {rp} decimal places"
    guard(res, "V17 load-ratio formula", v17)

    # V18 ------------------------------------------------------------------------------
    def v18():
        problems, n = [], 0
        for s in raw("capacity-snapshots.csv"):
            if dnum(s["effective_capacity_hours"]) == 0:
                n += 1
                if s["load_ratio_state"] != "undefined_no_capacity" or s["load_ratio"] != "":
                    problems.append(f"{s['capacity_snapshot_id']}: zero capacity must give undefined_no_capacity and no ratio")
            elif s["load_ratio_state"] == "undefined_no_capacity":
                problems.append(f"{s['capacity_snapshot_id']}: undefined state with non-zero capacity")
        for e in events():
            if e.get("event_type") == "capacity.snapshot_computed" and e["payload"].get("supply_hours") == 0 and e["payload"].get("load_ratio") is not None:
                problems.append(f"{e['event_id']}: zero supply with a numeric load_ratio")
        if n == 0:
            problems.append("no zero-capacity snapshot demonstrated")
        return problems, f"{n} zero-capacity snapshot(s): no division, no substituted zero, raw demand and supply kept"
    guard(res, "V18 zero-capacity handling", v18)

    # V19 ------------------------------------------------------------------------------
    def v19():
        problems, n = [], 0
        for s in raw("supply-records.csv"):
            rf = dnum(s["ramp_factor"])
            if not (D(0) <= rf <= D(1)):
                problems.append(f"{s['supply_record_id']}: ramp_factor outside 0 to 1")
            if rf < 1:
                n += 1
                if s["ramp_source"] != "r4_interface_fixture":
                    problems.append(f"{s['supply_record_id']}: ramp below 1 must be an R4 interface fixture")
                if dnum(s["ramp_loss_hours"]) != dnum(s["project_available_hours"]) - dnum(s["ramp_adjusted_hours"]):
                    problems.append(f"{s['supply_record_id']}: ramp loss mismatch")
            elif dnum(s["ramp_loss_hours"]) != 0 or s["ramp_source"] != "fully_ramped_default":
                problems.append(f"{s['supply_record_id']}: ramped record with ramp loss")
        if n == 0:
            problems.append("no ramp effect demonstrated")
        return problems, f"{n} ramping supply records; ramp loss = project_available - project_available x ramp_factor"
    guard(res, "V19 ramp math", v19)

    # V20 ------------------------------------------------------------------------------
    def v20():
        problems, n = [], 0
        sup = raw("supply-records.csv")
        by = {(s["person_id"], s["period"]): s for s in sup}
        for s in sup:
            if dnum(s["mentor_hours"]) > 0:
                n += 1
                mentee = by.get((s["mentee_person_id"], s["period"]))
                if mentee is None or mentee["mentor_person_id"] != s["person_id"]:
                    problems.append(f"{s['supply_record_id']}: mentor record not matched by the mentee's record")
                if mentee is not None and dnum(mentee["mentor_hours"]) != 0:
                    problems.append(f"{s['supply_record_id']}: mentoring hours also charged to the mentee")
            if s["mentor_person_id"]:
                mentor = by.get((s["mentor_person_id"], s["period"]))
                if mentor is None or mentor["mentee_person_id"] != s["person_id"]:
                    problems.append(f"{s['supply_record_id']}: mentee names a mentor whose record does not name them")
        if n == 0:
            problems.append("no mentor load demonstrated")
        return problems, f"{n} mentor records reduce only the mentor's capacity; every mentor and mentee pair matches"
    guard(res, "V20 mentor-load math", v20)

    # V21 to V23 ---------------------------------------------------------------------------
    def trc_rows():
        P = params()
        out = []
        trd = {t["training_demand_id"]: t for t in raw("training-demand.csv")}
        for t in raw("training-capacity.csv"):
            d = trd.get(t["training_demand_id"], {})
            size = int(d.get("class_size") or P["default_class_size"])
            sess = dnum(d.get("session_length_hours") or P["default_session_length_hours"])
            prep = dnum(d.get("prep_hours_per_session") or P["default_prep_hours_per_session"])
            out.append((t, d, size, sess, prep))
        return out

    def v21():
        problems = []
        for t, d, size, _, _ in trc_rows():
            learners = int(d.get("learner_count", -1))
            if int(t["learner_count"]) != learners or int(t["class_size"]) != size:
                problems.append(f"{t['training_capacity_id']}: inputs differ from {t['training_demand_id']}")
            if int(t["cohorts_required"]) != -(-learners // size):
                problems.append(f"{t['training_capacity_id']}: cohorts_required is not ceil(learners / class_size)")
        return problems, f"{len(raw('training-capacity.csv'))} records: cohorts = ceil(learner_count / class_size)"
    guard(res, "V21 training cohort math", v21)

    def v22():
        problems = []
        for t, d, _, sess, _ in trc_rows():
            per = math.ceil(dnum(d.get("track_hours")) / sess)
            if int(t["sessions_per_cohort"]) != per or int(t["sessions_required"]) != per * int(t["cohorts_required"]):
                problems.append(f"{t['training_capacity_id']}: session math differs")
        return problems, "sessions_per_cohort = ceil(track_hours / session_length_hours); sessions_required = cohorts x sessions_per_cohort"
    guard(res, "V22 session math", v22)

    def v23():
        problems = []
        for t, d, _, _, prep in trc_rows():
            cohorts, sessions = int(t["cohorts_required"]), int(t["sessions_required"])
            delivery = cohorts * dnum(d.get("track_hours"))
            prep_h = sessions * prep
            assess = cohorts * dnum(d.get("assessment_hours_per_cohort"))
            for f, want in (("trainer_delivery_hours", delivery), ("trainer_preparation_hours", prep_h),
                            ("trainer_assessment_hours", assess), ("trainer_hours", delivery + prep_h + assess),
                            ("learner_seat_hours", int(d.get("learner_count", 0)) * dnum(d.get("track_hours")))):
                if dnum(t[f]) != want:
                    problems.append(f"{t['training_capacity_id']}: {f} should be {want}")
        seat = sum(dnum(t["learner_seat_hours"]) for t in raw("training-capacity.csv"))
        trn = sum(dnum(s["training_demand_hours"]) for s in raw("capacity-snapshots.csv"))
        auth = sum(dnum(t["trainer_hours"]) for t in raw("training-capacity.csv") if t["capacity_inclusion_method"] == "authoritative_workload")
        if trn != auth:
            problems.append("snapshot training demand is not the sum of authoritative trainer hours")
        return problems, f"trainer hours = delivery + preparation + assessment; {auth} trainer hours in demand, {seat} learner seat-hours never in demand"
    guard(res, "V23 trainer-hour math", v23)

    # V24 ------------------------------------------------------------------------------
    def v24():
        problems = []
        types = set()
        for g in raw("golive-support.csv"):
            types.add(g["support_type"])
            want = int(g["people_count"]) * dnum(g["hours_per_person_per_day"]) * dnum(g["days"])
            if dnum(g["support_hours"]) != want:
                problems.append(f"{g['golive_support_demand_id']}: support_hours should be {want}")
        for need in ("rehearsal", "hypercare_support"):
            if need not in types:
                problems.append(f"{need} not demonstrated")
        if not types & {"cutover_support", "command_center_support"}:
            problems.append("launch-window support not demonstrated")
        return problems, f"{len(raw('golive-support.csv'))} records: support_hours = people_count x hours_per_person_per_day x days; types {', '.join(sorted(types))}"
    guard(res, "V24 launch-support math", v24)

    # V25 ------------------------------------------------------------------------------
    def v25():
        P = params()
        upper, lower = dnum(P["load_ratio_upper_threshold"]), dnum(P["load_ratio_lower_threshold"])
        rules = {t["staffing_trigger_id"]: t for t in y("config/staffing-triggers.yaml")["triggers"]}
        problems = []
        series = defaultdict(list)
        for s in raw("capacity-snapshots.csv"):
            series[(s["scenario_id"], s["role_id"])].append(s)
        fired = []

        def run(above, below, fire_n, clear_n):
            # Independent restatement of persistence and hysteresis.
            st, up, down, out = "not_triggered", 0, 0, []
            for a, b in zip(above, below):
                ev = None
                if st in ("not_triggered", "watch"):
                    up = up + 1 if a else 0
                    st, ev = (("triggered", "fired") if a and up >= fire_n else (("watch" if a else "not_triggered"), None))
                    down = 0
                else:
                    down = down + 1 if b else 0
                    st, ev = (("not_triggered", "cleared") if b and down >= clear_n else (("clearing" if b else "triggered"), None))
                    if ev:
                        up = 0
                out.append((st, ev))
            return out
        for key, snaps in series.items():
            snaps.sort(key=lambda s: s["period"])
            defined = [s["load_ratio_state"] == "defined" for s in snaps]
            ratio = [dnum(s["load_ratio"]) if d else None for s, d in zip(snaps, defined)]
            demand = [dnum(s["demand_hours"]) for s in snaps]
            supply = [dnum(s["effective_capacity_hours"]) for s in snaps]
            la = [d and r >= upper for d, r in zip(defined, ratio)]
            lb = [(d and r <= lower) or dm == 0 for d, r, dm in zip(defined, ratio, demand)]
            ca = [(not d) and dm > 0 for d, dm in zip(defined, demand)]
            cb = [sp > 0 or dm == 0 for sp, dm in zip(supply, demand)]
            r1 = run(la, lb, int(P[rules["STG-000001"]["fire_after_parameter"]]), int(P[rules["STG-000001"]["clear_after_parameter"]]))
            r2 = run(ca, cb, int(P[rules["STG-000002"]["fire_after_parameter"]]), int(P[rules["STG-000002"]["clear_after_parameter"]]))
            order = ["triggered", "clearing", "watch", "not_triggered"]
            for s, (s1, e1), (s2, e2) in zip(snaps, r1, r2):
                if (s["load_trigger_state"], s["coverage_trigger_state"]) != (s1, s2):
                    problems.append(f"{s['capacity_snapshot_id']}: trigger states should be {s1}, {s2}")
                if s["trigger_state"] != min((s1, s2), key=order.index):
                    problems.append(f"{s['capacity_snapshot_id']}: combined trigger_state wrong")
                evs = ";".join(x for x in (f"STG-000001:{e1}" if e1 else "", f"STG-000002:{e2}" if e2 else "") if x)
                if s["trigger_events"] != evs:
                    problems.append(f"{s['capacity_snapshot_id']}: trigger events should be {evs or 'none'}")
                for rid, e in (("STG-000001", e1), ("STG-000002", e2)):
                    if e == "fired":
                        fired.append((rid, s["capacity_snapshot_id"]))
        strs = {(r["staffing_trigger_id"], r["subject_id"]) for r in raw("staffing-recommendations.csv")}
        if set(fired) != strs:
            problems.append("staffing recommendations do not match fired triggers one to one")
        fired_events = sorted((e["payload"]["rule_id"], e["payload"]["period"]) for e in events() if e.get("event_type") == "staffing_trigger.fired")
        snap_period = {s["capacity_snapshot_id"]: s["period"] for s in raw("capacity-snapshots.csv")}
        if fired_events != sorted((r, snap_period[c]) for r, c in fired):
            problems.append("staffing_trigger.fired events do not match fired triggers")
        for k in ("trigger_fire_after_periods", "trigger_clear_after_periods"):
            if int(P[k]) < 1:
                problems.append(f"{k} must be at least 1")
        if dnum(P["load_ratio_lower_threshold"]) >= dnum(P["load_ratio_upper_threshold"]):
            problems.append("lower threshold must sit below the upper threshold (hysteresis band)")
        return problems, f"{len(fired)} firings after the configured persistence; clearing only after the lower threshold holds"
    guard(res, "V25 staffing trigger persistence", v25)

    # V26 ------------------------------------------------------------------------------
    def v26():
        problems = []
        recs = read_typed_csv(root / "data/synthetic/staffing-recommendations.csv", schema("staffing-recommendation"))
        for r in recs:
            rid = r["staffing_recommendation_id"]
            if r.get("status") != "proposed" or "approval_id" in r:
                problems.append(f"{rid}: R2 records recommendations as proposed only, with no approval")
            if r.get("origin_type") != "system" or not str(r.get("origin_id", "")).startswith("STG-"):
                problems.append(f"{rid}: origin must be the firing STG rule")
            if r.get("decision_owner") != "named_human":
                problems.append(f"{rid}: decision owner must be a named human")
            if any(p.search(r.get("content", "")) for p in FORBIDDEN_RECOMMENDATION):
                problems.append(f"{rid}: content reads as a people decision")
        for e in events():
            if e.get("event_type") == "staffing_recommendation.recorded" and e["payload"].get("status") != "proposed":
                problems.append(f"{e['event_id']}: recommendation event status must be proposed")
        trig = y("config/staffing-triggers.yaml")
        for t in trig["recommendation_types"]:
            if any(p.search(t["content"]) for p in FORBIDDEN_RECOMMENDATION):
                problems.append(f"recommendation type {t['type']} reads as a people decision")
        return problems, f"{len(recs)} recommendations, all proposed, system-originated, decided by a named human; none names a person or a decision"
    guard(res, "V26 staffing recommendations non-authoritative", v26)

    # V27 ------------------------------------------------------------------------------
    def v27():
        problems = []
        scen = {s["scenario_id"]: s for s in raw("scenarios.csv")}
        stages = {}
        for name in ("startup", "early-scale", "structured-growth", "mature"):
            p = y(f"profiles/{name}.yaml")
            stages[p["org_profile_id"]] = p["org_stage"]
            if "Selected by a named person" not in p.get("selection_rule", ""):
                problems.append(f"profiles/{name}.yaml: selection_rule must state human selection")
        if sorted(stages.values()) != sorted(STAGES):
            problems.append("profiles must cover exactly the four standard stages")
        sel = [e for e in events() if e.get("event_type") == "org_profile.selected"]
        for e in sel:
            if e["actor_type"] != "human" or not e["actor_id"].startswith("PER-"):
                problems.append(f"{e['event_id']}: org_profile.selected must be recorded by a human")
            if stages.get(e["subject_id"]) != e["payload"].get("org_stage"):
                problems.append(f"{e['event_id']}: payload stage differs from the profile")
        by_profile = {e["subject_id"]: e for e in sel}
        for s in scen.values():
            e = by_profile.get(s["org_profile_id"])
            if e is None or e["actor_id"] != s["selected_by"] or e["occurred_at"] != s["selected_at"]:
                problems.append(f"{s['scenario_id']}: no matching human selection event")
            if stages.get(s["org_profile_id"]) != s["org_stage"]:
                problems.append(f"{s['scenario_id']}: stage differs from its profile")
        for s in raw("capacity-snapshots.csv"):
            if scen[s["scenario_id"]]["org_stage"] != s["org_stage"]:
                problems.append(f"{s['capacity_snapshot_id']}: stage changed by calculation")
                break
        return problems, f"{len(sel)} human selections; no calculated stage change"
    guard(res, "V27 organization profile human-selected", v27)

    # V28 ------------------------------------------------------------------------------
    def v28():
        hits = [r for r, t in text_files() if any(p.search(t) for p in CLAIM_PATTERNS)]
        return [f"{h}: universal ratio, benchmark, or unsupported outcome claim" for h in hits], f"{len(CLAIM_PATTERNS)} claim patterns; 0 hits"
    guard(res, "V28 no universal ratio or outcome claim", v28)

    # V29 ------------------------------------------------------------------------------
    def v29():
        problems = []
        num_re = re.compile(r":\s*-?\d+(?:\.\d+)?\s*(?:[#,}\]]|$)", re.M)
        for p in sorted(list((root / "config").glob("*.yaml")) + list((root / "profiles").glob("*.yaml"))):
            t = p.read_text(encoding="utf-8")
            if num_re.search(t) or re.search(r"value:\s*\"?\d", t):
                for label in (LABELS[0], LABELS[3]):
                    if label not in t:
                        problems.append(f"{rel(root, p)}: numeric values without '{label}'")
        for f in ("config/phase-effort-curves.yaml", "config/demand-drivers.yaml") + tuple(f"profiles/{n}.yaml" for n in ("startup", "early-scale", "structured-growth", "mature")):
            if LABELS[2] not in (root / f).read_text(encoding="utf-8"):
                problems.append(f"{f}: lacks '{LABELS[2]}'")
        for pr in y("config/parameters.yaml")["parameters"]:
            if isinstance(pr["value"], (int, float)) and pr["parameter_id"] not in ("hours_decimal_places", "ratio_decimal_places"):
                if LABELS[0] not in pr.get("labels", []) or LABELS[3] not in pr.get("labels", []):
                    problems.append(f"parameter {pr['parameter_id']} lacks a required label")
        for r, t in text_files():
            if r.startswith("upstream/"):
                continue
            if any(pat.search(t) for pat in LABEL_VARIANTS):
                problems.append(f"{r}: label near-variant")
        return problems, "config and profile numbers carry both value labels; curves, drivers, and profiles are illustrative examples; no near-variants"
    guard(res, "V29 required labels", v29)

    # V30 ------------------------------------------------------------------------------
    def v30():
        problems = []
        folders = {p.parent for p in repo_files(root) if p.suffix in (".csv", ".jsonl") and not rel(root, p).startswith(("upstream/", "tests/"))}
        for f in folders:
            readme = f / "README.md"
            if not readme.is_file() or LABELS[1] not in readme.read_text(encoding="utf-8").lower():
                problems.append(f"{rel(root, f)}: no README.md with the synthetic data label")
        for p in sorted((root / "reports/executive-pack").glob("*.md")):
            if LABELS[1] not in p.read_text(encoding="utf-8"):
                problems.append(f"{rel(root, p)}: lacks the synthetic data label")
        if LABELS[1] not in (root / "data/synthetic/universe.yaml").read_text(encoding="utf-8").splitlines()[0] + (root / "data/synthetic/universe.yaml").read_text(encoding="utf-8")[:400]:
            problems.append("universe.yaml header lacks the synthetic data label")
        return problems, f"{len(folders)} data folder(s) and every report carry the synthetic data label"
    guard(res, "V30 synthetic-data labels", v30)

    # V31 ------------------------------------------------------------------------------
    def v31():
        sc = json.loads((root / "upstream/r1/standard/schemas/event.schema.json").read_text(encoding="utf-8"))
        v = Draft202012Validator(sc, format_checker=FormatChecker())
        cat = catalog()
        reg = {e["prefix"]: e["entity"] for e in registry()["prefixes"]}
        problems, ids = [], set()
        prev = None
        for i, e in enumerate(events(), 1):
            eid = e.get("event_id")
            errs = list(v.iter_errors(e))
            if errs:
                problems.append(f"{eid}: {errs[0].message[:100]}")
                continue
            if eid != f"EVT-{i:06d}" or eid in ids:
                problems.append(f"{eid}: event IDs must be unique and sequential")
            ids.add(eid)
            entry = cat.get(e["event_type"])
            if entry is None:
                continue
            allowed = set(entry["required_payload_fields"]) | set(entry.get("optional_payload_fields") or [])
            missing = [f for f in entry["required_payload_fields"] if f not in e["payload"]]
            extra = [f for f in e["payload"] if f not in allowed]
            if missing or extra:
                problems.append(f"{eid}: payload missing {missing} or extra {extra}")
            if e["subject_type"] != entry["subject_type"] or reg.get(e["subject_id"][:3]) != entry["subject_type"]:
                problems.append(f"{eid}: subject does not match the catalog")
            if e["source_repo"] != REPO or e["schema_version"] != "1.0.0":
                problems.append(f"{eid}: source_repo or schema_version wrong")
            if e["actor_type"] == "system" and e["actor_id"][:3] not in R2_PREFIXES:
                problems.append(f"{eid}: system actor must be the R2 rule or record that produced it")
            if prev and e["occurred_at"] < prev:
                problems.append(f"{eid}: events out of time order")
            prev = e["occurred_at"]
        return problems, f"{len(events())} events validate against the pinned event contract and catalog payloads"
    guard(res, "V31 event schema", v31)

    # V32 ------------------------------------------------------------------------------
    def v32():
        problems = []
        u = y("data/synthetic/universe.yaml")
        roles = set(re.findall(r"`(ROL-\d{6})`", (root / "upstream/r1/data/synthetic/README.md").read_text(encoding="utf-8")))
        r1_projects = {r["project_id"]: r for r in read_raw_csv(root / "upstream/r1/data/synthetic/projects.csv")[1]}
        r1_tasks = {r["task_id"] for r in read_raw_csv(root / "upstream/r1/data/synthetic/tasks.csv")[1]}
        scen = {s["scenario_id"] for s in raw("scenarios.csv")}
        projects = {p["project_id"]: p for p in u["projects"]}
        persons = {p["person_id"] for p in u["people"]}
        ids = {"CAP": {s["capacity_snapshot_id"] for s in raw("capacity-snapshots.csv")}, "STG": {t["staffing_trigger_id"] for t in y("config/staffing-triggers.yaml")["triggers"]}}
        for name in ("phase-demand.csv", "supply-records.csv", "role-capacity.csv", "capacity-snapshots.csv", "training-demand.csv",
                     "training-capacity.csv", "golive-support.csv", "projects.csv", "people.csv", "staffing-recommendations.csv"):
            for r in raw(name):
                if r.get("scenario_id") and r["scenario_id"] not in scen:
                    problems.append(f"{name}: unknown scenario {r['scenario_id']}")
                for f in ("role_id", "trainer_role_id"):
                    if r.get(f) and r[f] not in roles:
                        problems.append(f"{name}: role {r[f]} is not an R1 role")
                if r.get("project_id"):
                    p = projects.get(r["project_id"])
                    if p is None:
                        problems.append(f"{name}: orphan project {r['project_id']}")
                    elif r.get("scenario_id") and p["scenario_id"] != r["scenario_id"]:
                        problems.append(f"{name}: {r['project_id']} belongs to another scenario")
                for f in ("person_id", "mentor_person_id", "mentee_person_id", "selected_by"):
                    if r.get(f) and r[f] not in persons:
                        problems.append(f"{name}: orphan person {r[f]}")
        for p in u["projects"]:
            if p["source"] == "r1":
                r1 = r1_projects.get(p["project_id"])
                if r1 is None:
                    problems.append(f"{p['project_id']}: not an R1 project")
                    continue
                if r1["org_stage"] != next(s["org_stage"] for s in u["scenarios"] if s["scenario_id"] == p["scenario_id"]):
                    problems.append(f"{p['project_id']}: R1 org_stage differs from the scenario")
                launch = [r for r in raw("projects.csv") if r["project_id"] == p["project_id"] and "launch" in r["curve_phase_keys"].split("+")]
                if launch and launch[0]["period"] != r1["target_launch_date"][:7]:
                    problems.append(f"{p['project_id']}: curve launch period {launch[0]['period']} differs from the R1 target launch month")
            elif p["project_id"] in r1_projects:
                problems.append(f"{p['project_id']}: forecast project reuses an R1 project ID")
        for t in raw("training-demand.csv"):
            if t["covered_by"] and t["covered_by"] not in r1_tasks:
                problems.append(f"{t['training_demand_id']}: covered_by {t['covered_by']} is not an R1 task")
        for r in read_typed_csv(root / "data/synthetic/staffing-recommendations.csv", schema("staffing-recommendation")):
            for ref in r["source_references"] + [{"source_id": r["subject_id"]}, {"source_id": r["staffing_trigger_id"]}]:
                if ref["source_id"] not in ids[ref["source_id"][:3]]:
                    problems.append(f"{r['staffing_recommendation_id']}: orphan reference {ref['source_id']}")
        trd = {t["training_demand_id"] for t in raw("training-demand.csv")}
        problems += [f"{t['training_capacity_id']}: orphan {t['training_demand_id']}" for t in raw("training-capacity.csv") if t["training_demand_id"] not in trd]
        sup_ids = {s["supply_record_id"] for s in raw("supply-records.csv")}
        for r in raw("role-capacity.csv"):
            for sid in filter(None, r["supply_record_ids"].split(";")):
                if sid not in sup_ids:
                    problems.append(f"{r['role_capacity_id']}: orphan {sid}")
        subject_ids = {"CAP": ids["CAP"], "STG": ids["STG"], "STR": {r["staffing_recommendation_id"] for r in raw("staffing-recommendations.csv")},
                       "TRC": {t["training_capacity_id"] for t in raw("training-capacity.csv")}, "GLS": {g["golive_support_demand_id"] for g in raw("golive-support.csv")},
                       "ORG": {s["org_profile_id"] for s in raw("scenarios.csv")}}
        for e in events():
            if e["subject_id"] not in subject_ids.get(e["subject_id"][:3], set()):
                problems.append(f"{e['event_id']}: orphan subject {e['subject_id']}")
        return problems, "scenarios, R1 projects and roles, people, R1 tasks, records, and event subjects all resolve; R1 launch months align"
    guard(res, "V32 referential integrity", v32)

    # V33 to V36 -----------------------------------------------------------------------
    guard(res, "V33 genericity", lambda: (
        [f"{r}: names a listed vendor or product" for r, t in text_files() if names_listed_vendor(t)],
        f"no listed vendor or product names ({len(GENERICITY_TERM_HASHES)} checked)"))

    def v34():
        terms, probs = load_blocklist(blocklist, root)
        if probs:
            return probs, ""
        if not terms:
            return [], "no private blocklist supplied; check skipped (supply one before publication)"
        pats = [re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", re.I) for t in terms]
        hits = {r for r, t in text_files() if any(p.search(t) for p in pats)}
        hits |= {rel(root, p) for p in repo_files(root) if any(pt.search(rel(root, p)) for pt in pats)}
        return ([f"{len(hits)} file(s) contain a private term"] if hits else []), f"{len(terms)} private terms loaded; 0 hits"
    guard(res, "V34 private blocklist", v34)

    def v35():
        problems = [f"{rel(root, p)}: secret-bearing file name" for p in repo_files(root) if SECRET_FILES.search(rel(root, p))]
        problems += [f"{r}: credential pattern" for r, t in text_files() if any(p.search(t) for p in SECRET_PATTERNS)]
        return problems, "none"
    guard(res, "V35 no secrets", v35)

    def v36():
        hits = [rel(root, p) for p in repo_files(root) if (t := text_of(p)) and EM_DASH in t]
        return [f"em dash in {h}" for h in hits], "0 em dashes"
    guard(res, "V36 no em dashes", v36)

    # V37 ------------------------------------------------------------------------------
    def v37():
        text = (root / "README.md").read_text(encoding="utf-8")
        heads = re.findall(r"^## (.+)$", text, re.M)
        problems = []
        if tuple(heads) != README_SECTIONS:
            problems.append(f"README ## sections must be exactly the 20 required sections in order (found {len(heads)})")
        ai = text.split("## AI assistance", 1)[-1].split("\n## ", 1)[0].lower()
        for need in ("ai", "deterministic", "human review"):
            if need not in ai:
                problems.append(f"AI assistance section does not mention '{need}'")
        if re.search(r"\bai\b[^.\n]*\bapprov", ai) and "never approves" not in ai and "does not approve" not in ai:
            problems.append("AI assistance section implies AI approval")
        top = text.split("## Purpose", 1)[-1].split("\n## ", 1)[0]
        for need in ("R1", "R3"):
            if need not in top:
                problems.append(f"the R1, R3, R2 story is not near the top (missing {need} in Purpose)")
        return problems, "20 sections in order; AI assistance discloses AI help, deterministic code, and human release review"
    guard(res, "V37 README sections and AI assistance", v37)

    # V38 ------------------------------------------------------------------------------
    def v38():
        text = (root / "docs/practical-workflow.md").read_text(encoding="utf-8")
        problems = []
        steps = re.findall(r"^### Step (\d+): (.+)$", text, re.M)
        if [s[1] for s in steps] != list(WORKFLOW_STEPS) or [int(s[0]) for s in steps] != list(range(1, 13)):
            problems.append("practical workflow must have the 12 required steps in order")
        blocks = re.split(r"^### Step \d+: .+$", text, flags=re.M)[1:]
        for i, b in enumerate(blocks, 1):
            b = b.split("\n## ", 1)[0]
            for f in WORKFLOW_FIELDS:
                if not re.search(rf"^- \*\*{re.escape(f)}:\*\* \S", b, re.M):
                    problems.append(f"step {i} lacks '{f}'")
        heads = re.findall(r"^## (.+)$", text, re.M)
        for need in ("Starter Mode", "Mature Mode"):
            if not any(need in h for h in heads):
                problems.append(f"practical workflow lacks a '{need}' section")
        for need in (LABELS[0],):
            if need not in text:
                problems.append(f"practical workflow lacks '{need}'")
        return problems, "12 steps, each with input, file or entity, rule, output, human decision, and consumer; Starter and Mature Modes"
    guard(res, "V38 practical workflow", v38)

    # V39 ------------------------------------------------------------------------------
    def v39():
        import capacity_calc as C  # noqa: PLC0415
        model = C.compute(C.load_inputs(root))
        outputs = C.build_outputs(model)
        stale = [r for r, t in outputs.items() if not (root / r).is_file() or (root / r).read_text(encoding="utf-8") != t]
        return [f"{s} differs from tools/capacity_calc.py output" for s in stale], f"{len(outputs)} generated files equal a fresh deterministic run"
    guard(res, "V39 generated outputs current", v39)

    # V40 ------------------------------------------------------------------------------
    def v40():
        problems = []
        need = ("parameter_id", "description", "unit", "value", "labels", "source", "effective_version")
        ps = y("config/parameters.yaml")["parameters"]
        ids = [p.get("parameter_id") for p in ps]
        if len(ids) != len(set(ids)):
            problems.append("duplicate parameter_id")
        for p in ps:
            miss = [k for k in need if k not in p or p[k] in (None, "")]
            if miss:
                problems.append(f"{p.get('parameter_id')}: missing {miss}")
            if LABELS[3] not in p.get("labels", []):
                problems.append(f"{p.get('parameter_id')}: not marked user-configurable parameter")
        refs = set()
        for t in y("config/staffing-triggers.yaml")["triggers"]:
            refs |= {t["fire_after_parameter"], t["clear_after_parameter"]}
        problems += [f"trigger references unknown parameter {r}" for r in refs if r not in ids]
        return problems, f"{len(ps)} parameters with id, description, unit, value, labels, source, and effective version"
    guard(res, "V40 parameters complete", v40)

    # V41 ------------------------------------------------------------------------------
    def v41():
        phases = [p["phase_key"] for p in y("upstream/r1/standard/lifecycle-terms.yaml")["phases"]]
        problems = []
        curves = y("config/phase-effort-curves.yaml")["curves"]
        for c in curves:
            keys = [k for s in c["segments"] for k in s["phase_keys"]]
            if keys != phases:
                problems.append(f"{c['curve_id']}: must cover the ten R1 phases once, in order")
            if sum(dnum(s["effort_share"]) for s in c["segments"]) != 1:
                problems.append(f"{c['curve_id']}: effort shares do not sum to 1")
            if any(int(s["duration_months"]) < 1 for s in c["segments"]):
                problems.append(f"{c['curve_id']}: a segment shorter than one month")
        tiers = y("config/demand-drivers.yaml")["tiers"]
        cids = {c["curve_id"] for c in curves}
        problems += [f"tier {t['tier_key']}: unknown curve" for t in tiers if t["curve_id"] not in cids]
        prf = {e["prefix"] for e in registry()["prefixes"]}
        problems += [f"tier {t['tier_key']}: bad R1 profile" for t in tiers if t.get("r1_complexity_profile_id") and t["r1_complexity_profile_id"][:3] not in prf]
        return problems, f"{len(curves)} curves cover the ten R1 phases once and sum to 1"
    guard(res, "V41 phase-effort curves", v41)

    # V42 ------------------------------------------------------------------------------
    def v42():
        problems = []
        header = read_raw_csv(root / "data/synthetic/people.csv")[0]
        extra = [h for h in header if h not in PEOPLE_FIELDS_ALLOWED]
        if extra:
            problems.append(f"people.csv carries fields outside the planning boundary: {extra}")
        for p in sorted((root / "data/synthetic").glob("*.csv")):
            for h in read_raw_csv(p)[0]:
                if FORBIDDEN_HEADER.search(h):
                    problems.append(f"{p.name}: field {h} is outside the people-data boundary")
        u = y("data/synthetic/universe.yaml")
        for p in u["people"]:
            if not re.fullmatch(r"Person [A-Z]", p["label"]):
                problems.append(f"{p['person_id']}: label must be a neutral 'Person X'")
            extra = set(p) - {"person_id", "label", "scenario_id", "note", "first_period", "allocations", "overrides"}
            if extra:
                problems.append(f"{p['person_id']}: unexpected fields {sorted(extra)}")
        return problems, "people data limited to IDs, neutral labels, roles, hours, and ramp state; no HR, demographic, pay, or rating fields"
    guard(res, "V42 people data boundary", v42)

    # V43 ------------------------------------------------------------------------------
    def v43():
        problems = []
        u = y("data/synthetic/universe.yaml")
        tiers = {p["project_id"]: p["complexity_tier"] for p in u["projects"]}
        maxes = {}
        for name in ("startup", "early-scale", "structured-growth", "mature"):
            p = y(f"profiles/{name}.yaml")
            maxes[p["org_profile_id"]] = int(p["planning_settings"]["max_active_projects_per_role"])
        prof = {s["scenario_id"]: s["org_profile_id"] for s in raw("scenarios.csv")}
        active = defaultdict(set)
        for r in raw("phase-demand.csv"):
            if r["capacity_inclusion_method"] == "authoritative_workload" and dnum(r["hours"]) > 0:
                active[(r["scenario_id"], r["role_id"], r["period"])].add(r["project_id"])
        for r in raw("training-capacity.csv"):
            if r["capacity_inclusion_method"] == "authoritative_workload" and r["project_id"]:
                active[(r["scenario_id"], r["trainer_role_id"], r["period"])].add(r["project_id"])
        for r in raw("golive-support.csv"):
            active[(r["scenario_id"], r["role_id"], r["period"])].add(r["project_id"])
        for s in raw("capacity-snapshots.csv"):
            a = active[(s["scenario_id"], s["role_id"], s["period"])]
            mx = maxes[prof[s["scenario_id"]]]
            t = [tiers[x] for x in a]
            if (int(s["active_project_count"]), int(s["active_simple_count"]), int(s["active_standard_count"]), int(s["active_complex_count"])) != (len(a), t.count("simple"), t.count("standard"), t.count("complex")):
                problems.append(f"{s['capacity_snapshot_id']}: active project counts differ")
            if int(s["max_active_projects_per_role"]) != mx or s["concurrency_state"] != ("above_configured_maximum" if len(a) > mx else "within_configured_maximum"):
                problems.append(f"{s['capacity_snapshot_id']}: concurrency state differs")
        return problems, "active projects by role and tier recomputed; maximum read from the selected profile"
    guard(res, "V43 concurrency", v43)

    # V44 ------------------------------------------------------------------------------
    def v44():
        P = params()
        as_of = dt.date.fromisoformat(P["calculation_as_of_at"][:10])
        problems = []
        snap = {s["capacity_snapshot_id"]: s for s in raw("capacity-snapshots.csv")}
        for r in raw("staffing-recommendations.csv"):
            gap = dt.date.fromisoformat(r["projected_gap_date"])
            want = gap - dt.timedelta(days=int(P["hiring_lead_time_days"])) - dt.timedelta(days=int(P["ramp_duration_days"]))
            if r["latest_staffing_start_date"] != want.isoformat():
                problems.append(f"{r['staffing_recommendation_id']}: latest start should be {want}")
            if r["projected_gap_date"] != r["first_affected_period"] + "-01":
                problems.append(f"{r['staffing_recommendation_id']}: projected gap date is not the first day of the first affected period")
            if r["timing_state"] != ("window_open" if want >= as_of else "window_passed"):
                problems.append(f"{r['staffing_recommendation_id']}: timing_state wrong")
            s = snap.get(r["subject_id"])
            if s is None or s["period"] != r["fired_period"] or dnum(s["capacity_gap_hours"]) != dnum(r["capacity_gap_hours"]):
                problems.append(f"{r['staffing_recommendation_id']}: subject snapshot does not match")
            if int(r["hiring_lead_time_days"]) != int(P["hiring_lead_time_days"]) or int(r["ramp_duration_days"]) != int(P["ramp_duration_days"]):
                problems.append(f"{r['staffing_recommendation_id']}: timing parameters differ from parameters.yaml")
        return problems, "latest_staffing_start_date = projected_gap_date - hiring_lead_time - ramp_duration on every recommendation"
    guard(res, "V44 staffing timing", v44)

    # V45 ------------------------------------------------------------------------------
    def v45():
        import capacity_calc as C  # noqa: PLC0415
        problems = []
        cd = C.config_digest(root)
        std = str(y("standard/standard-reference.yaml")["shared_standard_version"])
        dem, trc, gls, sup = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
        for r in raw("phase-demand.csv"):
            if r["capacity_inclusion_method"] == "authoritative_workload":
                dem[(r["scenario_id"], r["role_id"], r["period"])].append([r["demand_record_id"], r["hours"]])
        for r in raw("training-capacity.csv"):
            if r["capacity_inclusion_method"] == "authoritative_workload":
                trc[(r["scenario_id"], r["trainer_role_id"], r["period"])].append([r["training_capacity_id"], r["trainer_hours"]])
        for r in raw("golive-support.csv"):
            if r["capacity_inclusion_method"] == "authoritative_workload":
                gls[(r["scenario_id"], r["role_id"], r["period"])].append([r["golive_support_demand_id"], r["support_hours"]])
        for r in raw("supply-records.csv"):
            sup[(r["scenario_id"], r["role_id"], r["period"])].append([r["supply_record_id"], r["effective_capacity_hours"]])
        for s in raw("capacity-snapshots.csv"):
            k = (s["scenario_id"], s["role_id"], s["period"])
            src = {"demand_records": dem[k], "training_capacity": trc[k], "golive_support": gls[k], "supply_records": sup[k],
                   "config_digest": cd, "calculation_version": s["calculation_version"], "standard_version": std}
            if s["config_digest"] != cd:
                problems.append(f"{s['capacity_snapshot_id']}: config_digest differs from the current configuration")
            if s["inputs_digest"] != _sha256(json.dumps(src, sort_keys=True, separators=(",", ":"))):
                problems.append(f"{s['capacity_snapshot_id']}: inputs_digest does not reproduce from its records")
            if s["standard_version"] != std or s["calculation_version"] != C.CALCULATION_VERSION:
                problems.append(f"{s['capacity_snapshot_id']}: version fields differ")
        return problems, f"{len(raw('capacity-snapshots.csv'))} snapshots reproduce from their input records, config digest, calculation version, and standard version"
    guard(res, "V45 reproducibility digests", v45)

    # V46 ------------------------------------------------------------------------------
    def v46():
        problems = []
        for name in SCHEMAS:
            for prop in schema(name)["properties"]:
                if prop in UPSTREAM_AUTHORITY_FIELDS:
                    problems.append(f"{name}.{prop}: field owned by another repository or a human")
        for p in sorted((root / "data/synthetic").glob("*.csv")):
            for h in read_raw_csv(p)[0]:
                if h in UPSTREAM_AUTHORITY_FIELDS:
                    problems.append(f"{p.name}: column {h} is owned elsewhere")
        u = y("data/synthetic/universe.yaml")
        for g in u["golive_support"]:
            if set(g) & {"decision", "go_no_go", "readiness", "gate"}:
                problems.append(f"{g['golive_support_demand_id']}: launch decision fields are R1's")
        if any(e.get("event_type", "").startswith(("project.", "golive.", "task.", "request.")) for e in events()):
            problems.append("R2 emits an R1-owned event")
        return problems, "no project, task, request, readiness, launch-decision, proficiency, or hiring fields in R2"
    guard(res, "V46 no duplicated upstream authority", v46)

    # V47 ------------------------------------------------------------------------------
    def v47():
        problems = []
        for r in raw("phase-demand.csv"):
            if r["demand_method"] == "top_down" and r["actual_hours"]:
                problems.append(f"{r['demand_record_id']}: forecast row carries actual hours")
            if r["value_basis"] not in ("planned", "forecast"):
                problems.append(f"{r['demand_record_id']}: demand must be planned or forecast")
        for name in ("supply-records.csv", "capacity-snapshots.csv", "golive-support.csv"):
            for r in raw(name):
                if r["value_basis"] != "forecast":
                    problems.append(f"{name}: v0.1 supply and snapshots are forecast only")
                    break
        bu = [r for r in raw("phase-demand.csv") if r["demand_method"] == "bottom_up"]
        differ = sum(1 for r in bu if r["hours"] != r["actual_hours"])
        return problems, f"demand uses planned or forecast hours only; {differ} bottom-up rows keep a different actual value alongside, never in demand"
    guard(res, "V47 forecast and actual kept distinct", v47)

    # V48 ------------------------------------------------------------------------------
    def v48():
        import capacity_calc as C  # noqa: PLC0415
        problems, n = [], 0
        for f in ("formulas/capacity-formulas.md", "formulas/training-formulas.md", "formulas/golive-support-formulas.md"):
            text = (root / f).read_text(encoding="utf-8")
            for block in re.findall(r"```yaml worked-example\n(.*?)```", text, re.S):
                n += 1
                ex = yaml.safe_load(block)
                fn = getattr(C, ex["function"], None)
                if fn is None:
                    problems.append(f"{f}: unknown function {ex['function']}")
                    continue
                got = fn(**ex["inputs"])
                want = ex["expected"]
                if isinstance(got, tuple):
                    got = {"value": got[0], "state": got[1]}
                elif not isinstance(got, dict):
                    got = {"value": got}
                for k, v in want.items():
                    g = got.get(k)
                    g = g.isoformat() if isinstance(g, dt.date) else g
                    if (None if g is None else str(C.fmt(g) if not isinstance(g, str) else g)) != (None if v is None else str(v)):
                        problems.append(f"{f}: {ex['name']} {k} expected {v}, calculator gives {g}")
            if "```yaml worked-example" not in text:
                problems.append(f"{f}: no worked example")
        return problems, f"{n} worked examples in formulas/ reproduce exactly with tools/capacity_calc.py"
    guard(res, "V48 formula worked examples", v48)

    res.rows.sort(key=lambda r: r[0])
    return res


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="Validate the capacity and org-design repository.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--blocklist", nargs="*")
    args = parser.parse_args(argv)
    res = validate(Path(args.root).resolve(), args.blocklist)
    for check, ok, note in res.rows:
        print(f"{'PASS' if ok else 'FAIL'} {check}: {note}")
    failed = sum(1 for _, ok, _ in res.rows if not ok)
    print(f"RESULT: {'FAIL' if failed else 'PASS'} ({len(res.rows) - failed} passed, {failed} failed)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
