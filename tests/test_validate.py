"""Negative tests for tools/validate.py.

Each test copies the repository into a temporary folder, breaks exactly one thing (often by
injecting a deliberate negative fixture from tests/fixtures/negative/), and confirms the
matching check fails. The committed repository is never modified."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import FIXTURES, ROOT, Sandbox, V

EM_DASH = chr(0x2014)
NEG = FIXTURES / "negative"


class RealRepository(unittest.TestCase):
    def test_real_repository_passes_every_check(self) -> None:
        res = V.validate(ROOT)
        self.assertEqual([(c, n) for c, ok, n in res.rows if not ok], [])
        self.assertEqual(len(res.rows), 48)

    def test_vendor_matcher(self) -> None:
        self.assertFalse(V.names_listed_vendor("A generic tracker and a generic spreadsheet."))


class Negative(unittest.TestCase):
    def setUp(self) -> None:
        self.box = Sandbox()

    def tearDown(self) -> None:
        self.box.close()

    def assertFails(self, check: str, contains: str | None = None, blocklist=None) -> None:
        results = self.box.run(blocklist)
        ok, note = results[check]
        self.assertFalse(ok, f"{check} should fail")
        if contains:
            self.assertIn(contains, note)

    def demand_rows_from(self, fixture: str) -> None:
        lines = (NEG / fixture).read_text(encoding="utf-8").splitlines()[1:]
        self.box.append("data/synthetic/phase-demand.csv", "\n".join(lines) + "\n")

    # Pins
    def test_altered_upstream_copy(self) -> None:
        self.box.replace("upstream/r1/standard/glossary.md", "Demand", "Demand ")
        self.assertFails("V03", "SHA-256")

    def test_unpinned_commit(self) -> None:
        self.box.replace("standard/standard-reference.yaml", "r1_commit: 5adf58a08f039f44b05e50c6ceb9750ed6fb5027", "r1_commit: main")
        self.assertFails("V02")

    # IDs and events
    def test_invalid_prefix(self) -> None:
        self.box.replace("data/synthetic/supply-records.csv", "SUP-000001,", "SPL-000001,")
        self.assertFails("V04")

    def test_reserved_prefix_used(self) -> None:
        self.box.append("data/synthetic/universe.yaml", "# BLD-000001\n")
        self.assertFails("V04", "BLD")

    def test_unregistered_event(self) -> None:
        self.box.append("data/synthetic/events.jsonl", (NEG / "unregistered-event.jsonl").read_text(encoding="utf-8"))
        self.assertFails("V05", "unregistered")

    def test_cost_to_serve_event_rejected(self) -> None:
        self.box.append("data/synthetic/events.jsonl", (NEG / "cost-to-serve-event.jsonl").read_text(encoding="utf-8"))
        self.assertFails("V05", "cost_to_serve")

    def test_event_extra_payload_field(self) -> None:
        self.box.replace("data/synthetic/events.jsonl", '"payload":{"org_stage":"startup"}', '"payload":{"org_stage":"startup","headcount":3}')
        self.assertFails("V31", "extra")

    # Schemas, units, periods
    def test_invalid_period(self) -> None:
        self.box.replace("data/synthetic/golive-support.csv", ",2026-10,rehearsal,", ",2026-13,rehearsal,")
        self.assertFails("V09", "invalid period")

    def test_weekly_period_rejected(self) -> None:
        self.box.replace("data/synthetic/golive-support.csv", ",2026-10,rehearsal,", ",2026-W42,rehearsal,")
        self.assertFails("V09")

    def test_invalid_unit_column(self) -> None:
        self.box.replace("data/synthetic/supply-records.csv", ",forecast,hours,", ",forecast,learner_hours,")
        self.assertFails("V08", "unit")

    def test_missing_schema_unit(self) -> None:
        self.box.replace("schemas/golive-support-demand.schema.json", '"x-unit": "days"', '"x-unit": "weeks"')
        self.assertFails("V08", "x-unit")

    def test_learner_hours_unit_elsewhere(self) -> None:
        self.box.replace("schemas/capacity-snapshot.schema.json", '"x-unit": "hours",\n      "description": "Authoritative trainer hours.',
                         '"x-unit": "learner_hours",\n      "description": "Authoritative trainer hours.')
        self.assertFails("V08", "learner_hours")

    def test_record_fails_schema(self) -> None:
        self.box.replace("data/synthetic/golive-support.csv", ",hypercare_support,", ",go_no_go,")
        self.assertFails("V06")

    # Demand, precedence, double counting
    def test_mixed_method_double_count(self) -> None:
        self.demand_rows_from("mixed-method-demand.csv")
        self.assertFails("V12", "more than one method")

    def test_duplicate_component(self) -> None:
        self.demand_rows_from("duplicate-component-demand.csv")
        self.assertFails("V12", "authoritative")

    def test_top_down_not_yielding(self) -> None:
        text = self.box.read("data/synthetic/phase-demand.csv")
        line = next(ln for ln in text.splitlines() if ",top_down," in ln and "excluded_to_prevent_double_count" in ln)
        fixed = line.replace("excluded_to_prevent_double_count", "authoritative_workload")
        self.box.replace("data/synthetic/phase-demand.csv", line, fixed)
        self.assertFails("V11", "precedence")

    def test_r3_row_redefined(self) -> None:
        self.box.replace("data/synthetic/phase-demand.csv", ",CPI-000034,informational_only,", ",CPI-000034,authoritative_workload,")
        self.assertFails("V11", "redefine")

    def test_unknown_demand_method(self) -> None:
        self.box.replace("data/synthetic/phase-demand.csv", ",top_down,", ",middle_out,")
        self.assertFails("V10")

    def test_excluded_training_without_cover(self) -> None:
        self.box.replace("data/synthetic/training-demand.csv", "TSK-000024", "TSK-000001")
        self.assertFails("V13", "covered_by")

    # Formulas
    def test_demand_aggregation_tampered(self) -> None:
        self.box.replace("data/synthetic/capacity-snapshots.csv", "CAP-000001,SCN-000001,startup,ROL-000001,2026-09,RCP-000001,11,0,0,11,",
                         "CAP-000001,SCN-000001,startup,ROL-000001,2026-09,RCP-000001,11,0,0,12,")
        self.assertFails("V14")

    def test_effective_capacity_tampered(self) -> None:
        self.box.replace("data/synthetic/supply-records.csv", ",96,1,96,0,0,96,,,", ",96,1,96,0,0,90,,,")
        self.assertFails("V15")

    def test_gap_sign_reversed(self) -> None:
        self.box.replace("data/synthetic/capacity-snapshots.csv", ",11,96,-85,", ",11,96,85,")
        self.assertFails("V16")

    def test_load_ratio_wrong(self) -> None:
        self.box.replace("data/synthetic/capacity-snapshots.csv", ",-85,0.1146,", ",-85,0.2,")
        self.assertFails("V17")

    def test_zero_capacity_substituted_zero(self) -> None:
        self.box.replace("data/synthetic/capacity-snapshots.csv", ",24,0,24,,undefined_no_capacity,", ",24,0,24,0,undefined_no_capacity,")
        self.assertFails("V18")

    def test_ramp_tampered(self) -> None:
        self.box.replace("data/synthetic/supply-records.csv", ",0.25,10,30,", ",0.25,10,20,")
        self.assertFails("V19")

    def test_one_sided_mentor(self) -> None:
        self.box.replace("data/synthetic/supply-records.csv", ",PER-000006,,r4_interface_fixture,", ",,,r4_interface_fixture,", 3)
        self.assertFails("V20", "mentor")

    def test_cohorts_rounded_down(self) -> None:
        self.box.replace("data/synthetic/training-capacity.csv", "TRC-000007,TRD-000007,SCN-000002,PRJ-000002,2026-11,ROL-000001,25,10,record,6,3,record,1.5,record,1,3,",
                         "TRC-000007,TRD-000007,SCN-000002,PRJ-000002,2026-11,ROL-000001,25,10,record,6,3,record,1.5,record,1,2,")
        self.assertFails("V21")

    def test_sessions_wrong(self) -> None:
        self.box.replace("data/synthetic/training-capacity.csv", ",record,1,3,2,6,18,", ",record,1,3,2,5,18,")
        self.assertFails("V22")

    def test_learner_hours_as_trainer_hours(self) -> None:
        self.box.replace("data/synthetic/training-capacity.csv", ",18,9,3,30,150,", ",18,9,3,150,150,")
        self.assertFails("V23")

    def test_golive_math_wrong(self) -> None:
        self.box.replace("data/synthetic/golive-support.csv", ",2,8,1,16,", ",2,8,1,18,")
        self.assertFails("V24")

    def test_trigger_fired_too_early(self) -> None:
        self.box.replace("config/parameters.yaml", "value: 2  # proposed design value, not a measured result\n    labels: [user-configurable parameter, \"proposed design value, not a measured result\"]\n    source: R2 design choice\n    effective_version: \"1.0.0\"\n  - parameter_id: trigger_clear_after_periods",
                         "value: 1  # proposed design value, not a measured result\n    labels: [user-configurable parameter, \"proposed design value, not a measured result\"]\n    source: R2 design choice\n    effective_version: \"1.0.0\"\n  - parameter_id: trigger_clear_after_periods")
        self.assertFails("V25")

    def test_staffing_timing_wrong(self) -> None:
        self.box.replace("data/synthetic/staffing-recommendations.csv", ",2026-11-02,window_open,", ",2026-12-02,window_open,")
        self.assertFails("V44")

    # Governance
    def test_recommendation_approved_by_r2(self) -> None:
        self.box.replace("data/synthetic/staffing-recommendations.csv", ",proposed,2026-10-06T12:00:00Z,", ",approved,2026-10-06T12:00:00Z,")
        self.assertFails("V26")

    def test_recommendation_names_a_person(self) -> None:
        self.box.replace("config/staffing-triggers.yaml", "Begin a staffing review for this role:", "Hire Person B now; begin a staffing review for this role:")
        self.assertFails("V26", "people decision")

    def test_org_stage_selected_by_system(self) -> None:
        self.box.replace("data/synthetic/events.jsonl", '"actor_id":"PER-000001","actor_type":"human","subject_type":"org_profile"',
                         '"actor_id":"CAP-000001","actor_type":"system","subject_type":"org_profile"')
        self.assertFails("V27", "human")

    def test_unsupported_benchmark_claim(self) -> None:
        self.box.write("docs/benchmark-note.md", (NEG / "benchmark-claim.md").read_text(encoding="utf-8"))
        self.assertFails("V28")

    def test_label_near_variant(self) -> None:
        self.box.append("docs/capacity-model.md", "\nThis threshold is a proposed design value.\n")
        self.assertFails("V29", "near-variant")

    def test_config_number_without_label(self) -> None:
        self.box.replace("config/phase-effort-curves.yaml", "user-configurable parameter", "adjustable", 10)
        self.assertFails("V29")

    def test_data_folder_without_label(self) -> None:
        self.box.path("data/synthetic/README.md").unlink()
        self.assertFails("V30")

    def test_orphan_reference(self) -> None:
        self.box.replace("data/synthetic/golive-support.csv", "GLS-000001,SCN-000003,PRJ-000003,", "GLS-000001,SCN-000003,PRJ-000999,")
        self.assertFails("V32", "orphan")

    def test_vendor_name(self) -> None:
        hashed_name = "Sales" + "force"  # assembled so this file never spells out a listed name
        self.box.append("docs/architecture.md", f"\nImport from {hashed_name}.\n")
        self.assertFails("V33")

    def test_private_blocklist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            block = Path(tmp) / "blocklist.txt"
            block.write_text("Synthetic Organization Zeta\n", encoding="utf-8")
            self.box.append("docs/architecture.md", "\nSynthetic Organization Zeta\n")
            self.assertFails("V34", "private term", blocklist=[str(block)])

    def test_secret(self) -> None:
        self.box.append("docs/architecture.md", "\ntoken = \"" + "abcd" * 6 + "\"\n")
        self.assertFails("V35")

    def test_em_dash(self) -> None:
        self.box.append("docs/architecture.md", f"\nCapacity {EM_DASH} demand.\n")
        self.assertFails("V36")

    def test_readme_sections(self) -> None:
        self.box.replace("README.md", "## Limitations", "## Known gaps")
        self.assertFails("V37")

    def test_readme_ai_disclosure(self) -> None:
        self.box.replace("README.md", "Deterministic code, not AI, performs every calculation", "Code performs every calculation")
        self.assertFails("V37", "deterministic")

    def test_workflow_step_missing_field(self) -> None:
        self.box.replace("docs/practical-workflow.md", "- **Human decision:** None; the calculation is fixed.\n", "", 1)
        self.assertFails("V38", "Human decision")

    def test_stale_generated_output(self) -> None:
        self.box.replace("reports/executive-pack/operating-review.md", "Questions for the review", "Questions")
        self.assertFails("V39")

    def test_parameter_missing_unit(self) -> None:
        self.box.replace("config/parameters.yaml", "    unit: days\n", "", 1)
        self.assertFails("V40", "unit")

    def test_curve_shares_wrong(self) -> None:
        self.box.replace("config/phase-effort-curves.yaml", "effort_share: 0.40}", "effort_share: 0.45}")
        self.assertFails("V41", "sum to 1")

    def test_people_forbidden_field(self) -> None:
        self.box.replace("data/synthetic/people.csv", ",unit,schema_version", ",unit,schema_version,performance_rating", 1)
        self.assertFails("V42")

    def test_upstream_authority_field(self) -> None:
        self.box.replace("data/synthetic/projects.csv", ",schema_version\n", ",schema_version,project_status\n", 1)
        self.assertFails("V46")

    def test_forecast_row_with_actuals(self) -> None:
        text = self.box.read("data/synthetic/phase-demand.csv")
        line = next(ln for ln in text.splitlines() if ",top_down," in ln and ",authoritative_workload,3,84,," in ln)
        self.box.replace("data/synthetic/phase-demand.csv", line, line.replace(",authoritative_workload,3,84,,", ",authoritative_workload,3,84,80,"))
        self.assertFails("V47")

    def test_worked_example_disagrees(self) -> None:
        self.box.replace("formulas/golive-support-formulas.md", "expected: {value: 16}", "expected: {value: 17}")
        self.assertFails("V48", "expected 17")

    def test_digest_tampered(self) -> None:
        text = self.box.read("data/synthetic/capacity-snapshots.csv")
        digest = text.splitlines()[1].split(",")[-6]
        self.box.replace("data/synthetic/capacity-snapshots.csv", digest, "0" * 64)
        self.assertFails("V45")


class Events(unittest.TestCase):
    def test_every_event_uses_the_ten_fields(self) -> None:
        for ln in (ROOT / "data/synthetic/events.jsonl").read_text(encoding="utf-8").splitlines():
            e = json.loads(ln)
            self.assertEqual(list(e), ["event_id", "event_type", "occurred_at", "actor_id", "actor_type", "subject_type", "subject_id",
                                       "payload", "source_repo", "schema_version"])


if __name__ == "__main__":
    unittest.main()
