"""Unit tests for every v0.1 formula in tools/capacity_calc.py, positive and negative.
All values are synthetic data and an illustrative example."""

from __future__ import annotations

import datetime as dt
import re
import unittest
from decimal import Decimal as D

import yaml

from support import ROOT, C


def row(**kw):
    base = {"demand_record_id": "DMN-000001", "project_id": "PRJ-000001", "period": "2026-11", "workload_component_id": "TSK-000001",
            "demand_method": "bottom_up", "capacity_inclusion_method": "authoritative_workload", "exclusion_reason": ""}
    base.update(kw)
    return base


class Demand(unittest.TestCase):
    def test_top_down_hours(self) -> None:
        self.assertEqual(C.top_down_hours(480, D("0.35"), 2), D("84.00"))
        self.assertEqual(C.top_down_hours(1200, D("0.35"), 3), D("140.00"))
        self.assertEqual(C.top_down_hours(320, D("0.17"), 2), D("27.20"))

    def test_top_down_rejects_bad_input(self) -> None:
        for args in ((480, D("0.35"), 0), (-1, D("0.2"), 1), (100, D("1.5"), 1)):
            with self.assertRaises(ValueError):
                C.top_down_hours(*args)

    def test_curve_rows_cover_months_and_shares(self) -> None:
        curves = {c["curve_id"]: c for c in yaml.safe_load((ROOT / "config/phase-effort-curves.yaml").read_text(encoding="utf-8"))["curves"]}
        rows = C.curve_rows(curves["curve_standard"])
        self.assertEqual(len(rows), 7)
        self.assertEqual([r["month_offset"] for r in rows], list(range(7)))
        total = sum(r["effort_share"] / r["duration_months"] for r in rows)
        self.assertEqual(total, D(1))

    def test_bottom_up_and_top_down_alone_are_clean(self) -> None:
        self.assertEqual(C.double_count_problems([row()]), [])
        self.assertEqual(C.double_count_problems([row(demand_method="top_down", workload_component_id="DMN-000001")]), [])

    def test_mixed_method_double_count_rejected(self) -> None:
        probs = C.double_count_problems([row(), row(demand_record_id="DMN-000002", demand_method="top_down", workload_component_id="DMN-000002")])
        self.assertTrue(any("more than one method" in p for p in probs))

    def test_same_component_twice_rejected(self) -> None:
        probs = C.double_count_problems([row(), row(demand_record_id="DMN-000002")])
        self.assertTrue(any("authoritative more than once" in p for p in probs))

    def test_excluded_and_informational_rows_ignored(self) -> None:
        rows = [row(), row(demand_record_id="DMN-000002", demand_method="top_down", workload_component_id="DMN-000002",
                           capacity_inclusion_method="excluded_to_prevent_double_count", exclusion_reason="covered"),
                row(demand_record_id="DMN-000003", capacity_inclusion_method="informational_only", exclusion_reason="summary")]
        self.assertEqual(C.double_count_problems(rows), [])

    def test_non_authoritative_row_needs_reason(self) -> None:
        probs = C.double_count_problems([row(capacity_inclusion_method="informational_only")])
        self.assertTrue(any("without exclusion_reason" in p for p in probs))

    def test_unknown_method_and_inclusion_rejected(self) -> None:
        probs = C.double_count_problems([row(demand_method="middle_out"), row(demand_record_id="DMN-000002", capacity_inclusion_method="maybe", exclusion_reason="x")])
        self.assertTrue(any("unknown demand_method" in p for p in probs))
        self.assertTrue(any("unknown capacity_inclusion_method" in p for p in probs))

    def test_demand_aggregation_counts_only_authoritative(self) -> None:
        model = C.compute(C.load_inputs(ROOT))
        for s in model["snapshots"]:
            k = (s["scenario_id"], s["role_id"], s["period"])
            proj = sum((d["hours"] for d in model["demand"] if (d["scenario_id"], d["role_id"], d["period"]) == k
                        and d["capacity_inclusion_method"] == "authoritative_workload"), D(0))
            self.assertEqual(s["project_demand_hours"], proj)
            self.assertEqual(s["demand_hours"], s["project_demand_hours"] + s["training_demand_hours"] + s["golive_support_hours"])


class Supply(unittest.TestCase):
    def test_effective_capacity_fully_ramped(self) -> None:
        b = C.supply_breakdown(112, 16, 16, 0, 0, 1, 0)
        self.assertEqual((b["gross_available_hours"], b["project_available_hours"], b["effective_capacity_hours"]), (D(96), D(80), D(80)))
        self.assertEqual(C.gross_available_hours(160, 80), D(80))

    def test_ramp_adjustment(self) -> None:
        b = C.supply_breakdown(160, 80, 8, 32, 0, D("0.25"), 0)
        self.assertEqual((b["project_available_hours"], b["ramp_adjusted_hours"], b["ramp_loss_hours"], b["effective_capacity_hours"]),
                         (D(40), D(10), D(30), D(10)))

    def test_mentor_capacity_reduction(self) -> None:
        b = C.supply_breakdown(160, 0, 16, 0, 0, 1, 24)
        self.assertEqual((b["ramp_loss_hours"], b["effective_capacity_hours"]), (D(0), D(120)))

    def test_mentor_hours_not_charged_to_mentee(self) -> None:
        model = C.compute(C.load_inputs(ROOT))
        for s in model["supply"]:
            if s["mentor_person_id"]:
                self.assertEqual(s["mentor_hours"], 0)
                mentor = next(m for m in model["supply"] if m["person_id"] == s["mentor_person_id"] and m["period"] == s["period"])
                self.assertEqual(mentor["mentee_person_id"], s["person_id"])
                self.assertEqual(mentor["ramp_loss_hours"], 0)

    def test_negative_effective_capacity_rejected(self) -> None:
        with self.assertRaises(ValueError):
            C.supply_breakdown(160, 0, 16, 0, 0, D("0.1"), 40)

    def test_allowances_above_scheduled_rejected(self) -> None:
        with self.assertRaises(ValueError):
            C.supply_breakdown(160, 160, 16)

    def test_bad_ramp_factor_and_negative_input_rejected(self) -> None:
        for kw in ({"ramp_factor": D("1.2")}, {"ramp_factor": D("-0.1")}, {"non_project": -1}):
            with self.assertRaises(ValueError):
                C.supply_breakdown(160, **kw)


class GapAndRatio(unittest.TestCase):
    def test_negative_gap_means_spare_capacity(self) -> None:
        self.assertEqual(C.capacity_gap_hours(11, 96), D(-85))

    def test_positive_gap_means_demand_exceeds_supply(self) -> None:
        self.assertEqual(C.capacity_gap_hours(D("515.6"), 432), D("83.6"))

    def test_balanced_gap(self) -> None:
        self.assertEqual(C.capacity_gap_hours(120, 120), D(0))
        self.assertEqual(C.load_ratio(120, 120), (D("1.0000"), "defined"))

    def test_load_ratio(self) -> None:
        self.assertEqual(C.load_ratio(D("515.6"), 432), (D("1.1935"), "defined"))
        self.assertEqual(C.load_ratio(0, 96), (D("0.0000"), "defined"))

    def test_zero_capacity_period(self) -> None:
        self.assertEqual(C.load_ratio(24, 0), (None, "undefined_no_capacity"))
        self.assertEqual(C.load_ratio(0, 0), (None, "undefined_no_capacity"))
        self.assertEqual(C.capacity_gap_hours(24, 0), D(24))


class Training(unittest.TestCase):
    def test_cohorts_round_up(self) -> None:
        self.assertEqual(C.training_capacity(25, 10, 6, 3, D("1.5"), 1)["cohorts_required"], 3)
        self.assertEqual(C.training_capacity(24, 12, 4, 2, 1)["cohorts_required"], 2)
        self.assertEqual(C.training_capacity(0, 12, 4, 2, 1)["cohorts_required"], 0)

    def test_sessions_round_up(self) -> None:
        r = C.training_capacity(8, 10, 3, D("1.5"), D("0.5"), D("0.5"))
        self.assertEqual((r["sessions_per_cohort"], r["sessions_required"]), (2, 2))
        r = C.training_capacity(10, 12, 5, 2, 1)
        self.assertEqual((r["sessions_per_cohort"], r["sessions_required"]), (3, 3))

    def test_delivery_hours_use_track_hours(self) -> None:
        r = C.training_capacity(10, 12, 5, 2, 1)
        self.assertEqual(r["trainer_delivery_hours"], D(5))

    def test_preparation_hours(self) -> None:
        r = C.training_capacity(45, 12, 6, 2, 1, 1)
        self.assertEqual((r["trainer_preparation_hours"], r["trainer_assessment_hours"], r["trainer_hours"]), (D(12), D(4), D(40)))

    def test_learner_hours_not_trainer_hours(self) -> None:
        r = C.training_capacity(45, 12, 6, 2, 1, 1)
        self.assertEqual(r["learner_seat_hours"], D(270))
        self.assertNotEqual(r["learner_seat_hours"], r["trainer_hours"])
        model = C.compute(C.load_inputs(ROOT))
        seat = sum((t["learner_seat_hours"] for t in model["training_capacity"]), D(0))
        trainer = sum((t["trainer_hours"] for t in model["training_capacity"] if t["capacity_inclusion_method"] == "authoritative_workload"), D(0))
        self.assertEqual(sum((s["training_demand_hours"] for s in model["snapshots"]), D(0)), trainer)
        self.assertNotEqual(seat, trainer)

    def test_invalid_training_input_rejected(self) -> None:
        for args in ((10, 0, 4, 2, 1), (10, 12, 4, 0, 1), (-1, 12, 4, 2, 1), (10, 12, 4, 2, -1)):
            with self.assertRaises(ValueError):
                C.training_capacity(*args)


class GoLive(unittest.TestCase):
    def test_golive_support_demand(self) -> None:
        self.assertEqual(C.golive_support_hours(2, 8, 1), D(16))
        self.assertEqual(C.golive_support_hours(2, 6, 3), D(36))
        self.assertEqual(C.golive_support_hours(1, 0, 5), D(0))

    def test_golive_negative_rejected(self) -> None:
        with self.assertRaises(ValueError):
            C.golive_support_hours(-1, 8, 1)


class Triggers(unittest.TestCase):
    def states(self, above, below, fire=2, clear=2):
        return [(r["state"], r["event"]) for r in C.evaluate_trigger(above, below, fire, clear)]

    def test_trigger_after_required_persistence(self) -> None:
        out = self.states([True, True, True], [False, False, False])
        self.assertEqual(out, [("watch", None), ("triggered", "fired"), ("triggered", None)])

    def test_trigger_does_not_fire_too_early(self) -> None:
        out = self.states([True, False, True, False], [False, False, False, False])
        self.assertEqual([s for s, _ in out], ["watch", "not_triggered", "watch", "not_triggered"])
        self.assertNotIn("fired", [e for _, e in out])

    def test_hysteresis_clearing(self) -> None:
        above = [True, True, False, False, False, False]
        below = [False, False, True, False, True, True]
        out = self.states(above, below)
        self.assertEqual(out, [("watch", None), ("triggered", "fired"), ("clearing", None), ("triggered", None),
                               ("clearing", None), ("not_triggered", "cleared")])

    def test_between_thresholds_stays_triggered(self) -> None:
        out = self.states([True, True, False, False], [False, False, False, False])
        self.assertEqual([s for s, _ in out], ["watch", "triggered", "triggered", "triggered"])

    def test_single_period_rule(self) -> None:
        out = self.states([True, False], [False, True], fire=1, clear=1)
        self.assertEqual(out, [("triggered", "fired"), ("not_triggered", "cleared")])

    def test_staffing_timing_calculation(self) -> None:
        self.assertEqual(C.latest_staffing_start_date(dt.date(2027, 5, 1), 60, 120), dt.date(2026, 11, 2))
        self.assertEqual(C.latest_staffing_start_date(dt.date(2026, 11, 1), 60, 120), dt.date(2026, 5, 5))

    def test_recommendations_carry_timing_and_stay_proposed(self) -> None:
        model = C.compute(C.load_inputs(ROOT))
        states = {r["timing_state"] for r in model["recommendations"]}
        self.assertEqual(states, {"window_open", "window_passed"})
        for r in model["recommendations"]:
            self.assertEqual(r["status"], "proposed")
            self.assertEqual(r["decision_owner"], "named_human")


class Periods(unittest.TestCase):
    def test_period_helpers(self) -> None:
        self.assertEqual(C.add_months("2026-11", 3), "2027-02")
        self.assertEqual(C.periods_between("2026-11", "2027-01"), ["2026-11", "2026-12", "2027-01"])

    def test_invalid_period_rejected_by_pattern(self) -> None:
        for bad in ("2026-13", "2026-1", "26-10", "2026-W40", "2026-10-01"):
            self.assertIsNone(re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", bad), bad)


if __name__ == "__main__":
    unittest.main()
