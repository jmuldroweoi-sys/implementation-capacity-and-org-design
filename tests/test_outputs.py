"""Locks the generated synthetic universe: exact row counts, determinism, the states each
scenario must demonstrate, and every computed number quoted in prose documentation.
All values are synthetic data and an illustrative example."""

from __future__ import annotations

import csv
import json
import unittest
from decimal import Decimal as D

from support import ROOT, C, Sandbox

ROW_COUNTS = {
    "scenarios.csv": 4, "people.csv": 18, "projects.csv": 82, "phase-demand.csv": 193, "training-demand.csv": 7,
    "training-capacity.csv": 7, "golive-support.csv": 13, "supply-records.csv": 178, "role-capacity.csv": 140,
    "capacity-snapshots.csv": 140, "staffing-recommendations.csv": 5,
}
EVENT_COUNTS = {"org_profile.selected": 4, "training_capacity.computed": 7, "golive_support.computed": 13,
                "capacity.snapshot_computed": 140, "staffing_trigger.fired": 5, "staffing_recommendation.recorded": 5}


def rows(name: str) -> list[dict]:
    with (ROOT / "data/synthetic" / name).open(encoding="utf-8", newline="") as h:
        return list(csv.DictReader(h))


def snap(scenario: str, role: str, period: str) -> dict:
    return next(s for s in rows("capacity-snapshots.csv") if (s["scenario_id"], s["role_id"], s["period"]) == (scenario, role, period))


class Counts(unittest.TestCase):
    def test_exact_row_counts(self) -> None:
        self.assertEqual({n: len(rows(n)) for n in ROW_COUNTS}, ROW_COUNTS)

    def test_exact_event_counts(self) -> None:
        events = [json.loads(ln) for ln in (ROOT / "data/synthetic/events.jsonl").read_text(encoding="utf-8").splitlines()]
        got = {}
        for e in events:
            got[e["event_type"]] = got.get(e["event_type"], 0) + 1
        self.assertEqual(got, EVENT_COUNTS)
        self.assertEqual(len(events), 174)

    def test_synthetic_check_matches(self) -> None:
        text = (ROOT / "verification/synthetic-data-check.md").read_text(encoding="utf-8")
        for name, n in ROW_COUNTS.items():
            self.assertIn(f"| `data/synthetic/{name}` | {n} |", text)
        self.assertIn("| `data/synthetic/events.jsonl` | 174 |", text)


class Determinism(unittest.TestCase):
    def test_two_runs_identical(self) -> None:
        a = C.build_outputs(C.compute(C.load_inputs(ROOT)))
        b = C.build_outputs(C.compute(C.load_inputs(ROOT)))
        self.assertEqual(a, b)

    def test_committed_outputs_current(self) -> None:
        self.assertEqual(C.run(ROOT, check=True), 0)

    def test_regeneration_in_a_copy_is_byte_identical(self) -> None:
        box = Sandbox()
        try:
            before = {p: box.path(p).read_bytes() for p in C.build_outputs(C.compute(C.load_inputs(box.root)))}
            for p in before:
                box.path(p).unlink()
            box.regenerate()
            self.assertEqual({p: box.path(p).read_bytes() for p in before}, before)
        finally:
            box.close()

    def test_changed_parameter_changes_digest(self) -> None:
        box = Sandbox()
        try:
            box.replace("config/parameters.yaml", "value: 1.10", "value: 1.20")
            m = C.compute(C.load_inputs(box.root))
            self.assertNotEqual(m["snapshots"][0]["config_digest"], rows("capacity-snapshots.csv")[0]["config_digest"])
        finally:
            box.close()


class Demonstrations(unittest.TestCase):
    def test_spare_near_balance_negative_and_zero(self) -> None:
        snaps = rows("capacity-snapshots.csv")
        self.assertTrue(any(D(s["capacity_gap_hours"]) < 0 for s in snaps))
        self.assertTrue(any(D(s["capacity_gap_hours"]) > 0 for s in snaps))
        self.assertTrue(any(s["load_ratio"] and D("0.95") <= D(s["load_ratio"]) <= D("1.05") for s in snaps))
        zero = [s for s in snaps if s["effective_capacity_hours"] == "0"]
        self.assertEqual([(z["scenario_id"], z["role_id"], z["period"]) for z in zero], [("SCN-000004", "ROL-000005", "2027-02")])

    def test_ramp_and_mentor_effects(self) -> None:
        sup = rows("supply-records.csv")
        self.assertEqual(sorted((s["person_id"], s["period"]) for s in sup if D(s["ramp_loss_hours"]) > 0),
                         [("PER-000007", "2026-11"), ("PER-000007", "2026-12"), ("PER-000007", "2027-01")])
        self.assertEqual(sorted((s["person_id"], s["period"]) for s in sup if D(s["mentor_hours"]) > 0),
                         [("PER-000006", "2026-11"), ("PER-000006", "2026-12"), ("PER-000006", "2027-01")])

    def test_scenario_stories(self) -> None:
        recs = rows("staffing-recommendations.csv")
        story = sorted((r["scenario_id"], r["role_id"], r["staffing_trigger_id"], r["first_affected_period"], r["fired_period"], r["timing_state"]) for r in recs)
        self.assertEqual(story, [
            ("SCN-000001", "ROL-000004", "STG-000001", "2026-11", "2026-12", "window_passed"),
            ("SCN-000003", "ROL-000004", "STG-000001", "2027-01", "2027-02", "window_passed"),
            ("SCN-000004", "ROL-000001", "STG-000001", "2027-05", "2027-06", "window_open"),
            ("SCN-000004", "ROL-000004", "STG-000001", "2027-05", "2027-06", "window_open"),
            ("SCN-000004", "ROL-000005", "STG-000002", "2027-02", "2027-02", "window_passed"),
        ])
        self.assertEqual(snap("SCN-000001", "ROL-000004", "2027-05")["trigger_events"], "STG-000001:cleared")
        self.assertEqual(snap("SCN-000004", "ROL-000005", "2027-03")["trigger_events"], "STG-000002:cleared")
        self.assertEqual(snap("SCN-000002", "ROL-000001", "2026-12")["trigger_state"], "watch")
        self.assertEqual(snap("SCN-000002", "ROL-000001", "2027-01")["trigger_state"], "not_triggered")
        self.assertFalse(any(r["scenario_id"] == "SCN-000002" for r in recs))

    def test_training_exclusion_story(self) -> None:
        trc = {t["training_demand_id"]: t for t in rows("training-capacity.csv")}
        self.assertEqual(trc["TRD-000001"]["capacity_inclusion_method"], "excluded_to_prevent_double_count")
        self.assertEqual(trc["TRD-000001"]["covered_by"], "TSK-000024")
        self.assertEqual(trc["TRD-000006"]["class_size_source"], "default_parameter")

    def test_both_methods_for_one_project_never_both_authoritative(self) -> None:
        dem = [d for d in rows("phase-demand.csv") if d["project_id"] == "PRJ-000001"]
        methods = {(d["period"], d["demand_method"], d["capacity_inclusion_method"]) for d in dem}
        self.assertIn(("2026-09", "bottom_up", "authoritative_workload"), methods)
        self.assertIn(("2026-09", "top_down", "excluded_to_prevent_double_count"), methods)
        self.assertIn(("2026-11", "top_down", "authoritative_workload"), methods)
        self.assertNotIn(("2026-09", "top_down", "authoritative_workload"), methods)


class ProseFacts(unittest.TestCase):
    """Every computed value quoted in prose (outside worked-example blocks) is checked here."""

    def test_capacity_formula_prose(self) -> None:
        s = next(x for x in rows("capacity-snapshots.csv") if x["capacity_snapshot_id"] == "CAP-000001")
        self.assertEqual((s["scenario_id"], s["role_id"], s["period"], s["demand_hours"], s["project_demand_hours"]),
                         ("SCN-000001", "ROL-000001", "2026-09", "11", "11"))
        s = next(x for x in rows("capacity-snapshots.csv") if x["capacity_snapshot_id"] == "CAP-000120")
        self.assertEqual((s["scenario_id"], s["role_id"], s["period"], s["demand_hours"], s["effective_capacity_hours"], s["capacity_gap_hours"], s["load_ratio"]),
                         ("SCN-000004", "ROL-000004", "2027-06", "515.6", "432", "83.6", "1.1935"))
        s = next(x for x in rows("capacity-snapshots.csv") if x["capacity_snapshot_id"] == "CAP-000126")
        self.assertEqual((s["scenario_id"], s["role_id"], s["period"], s["demand_hours"], s["effective_capacity_hours"], s["load_ratio_state"]),
                         ("SCN-000004", "ROL-000005", "2027-02", "24", "0", "undefined_no_capacity"))
        sup = {x["supply_record_id"]: x for x in rows("supply-records.csv")}
        self.assertEqual((sup["SUP-000061"]["person_id"], sup["SUP-000061"]["period"], sup["SUP-000061"]["effective_capacity_hours"]), ("PER-000007", "2026-11", "10"))
        self.assertEqual((sup["SUP-000053"]["person_id"], sup["SUP-000053"]["period"], sup["SUP-000053"]["effective_capacity_hours"]), ("PER-000006", "2026-11", "120"))
        rec = next(r for r in rows("staffing-recommendations.csv") if r["scenario_id"] == "SCN-000004" and r["role_id"] == "ROL-000004")
        self.assertEqual(rec["latest_staffing_start_date"], "2026-11-02")

    def test_training_and_golive_prose(self) -> None:
        trc = {t["training_demand_id"]: t for t in rows("training-capacity.csv")}
        self.assertEqual((trc["TRD-000003"]["trainer_hours"], trc["TRD-000003"]["learner_seat_hours"]), ("40", "270"))
        self.assertEqual(trc["TRD-000007"]["cohorts_required"], "3")
        gls = {g["golive_support_demand_id"]: g["support_hours"] for g in rows("golive-support.csv")}
        self.assertEqual((gls["GLS-000005"], gls["GLS-000008"], gls["GLS-000012"]), ("24", "16", "36"))

    def test_worked_examples_reproduce(self) -> None:
        from support import V
        res = V.validate(ROOT)
        row = next(r for r in res.rows if r[0].startswith("V48"))
        self.assertTrue(row[1], row[2])
        self.assertIn("14 worked examples", row[2])


if __name__ == "__main__":
    unittest.main()
