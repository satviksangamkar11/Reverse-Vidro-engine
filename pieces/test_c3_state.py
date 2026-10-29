"""Unit tests for c3_state module."""
from __future__ import annotations

import unittest

import c3_state


class TestRecordResult(unittest.TestCase):
    def test_valid_report_updates_state(self):
        state = {"e1": {"disposition": "PENDING_REVIEW"}}
        report = {
            "verdict": "POSE_SWAP",
            "evidence_frames": [5, 10],
            "counterexample": "none",
            "artwork_needed": "mask",
        }
        result = c3_state.record_result(state, "e1", report)
        self.assertEqual(result, {"status": "ok", "event_id": "e1"})
        self.assertEqual(state["e1"], {
            "disposition": "REVIEWED",
            "verdict": "POSE_SWAP",
            "evidence_frames": [5, 10],
            "counterexample": "none",
            "artwork_needed": "mask",
            "basis_event_ids": None,
        })

    def test_invalid_verdict_returns_error_and_pending(self):
        state = {"e1": {"disposition": "PENDING_REVIEW"}}
        report = {
            "verdict": "INVALID",
            "evidence_frames": [5],
            "counterexample": "",
            "artwork_needed": "",
        }
        result = c3_state.record_result(state, "e1", report)
        self.assertEqual(result, {"status": "error", "event_id": "e1", "reason": "invalid verdict"})
        self.assertEqual(state["e1"]["disposition"], "PENDING_REVIEW")
        self.assertEqual(state["e1"]["error"], "invalid verdict")

    def test_missing_keys_returns_error(self):
        state = {}
        report = {"verdict": "POSE_SWAP", "evidence_frames": [1]}  # missing counterexample, artwork_needed
        result = c3_state.record_result(state, "e1", report)
        self.assertEqual(result["status"], "error")
        self.assertIn("missing keys", result["reason"])
        self.assertEqual(state["e1"]["disposition"], "PENDING_REVIEW")
        self.assertIn("missing keys", state["e1"]["error"])

    def test_evidence_frames_not_list_of_ints_returns_error(self):
        state = {}
        report = {
            "verdict": "POSE_SWAP",
            "evidence_frames": [5, "ten"],
            "counterexample": "none",
            "artwork_needed": "mask",
        }
        result = c3_state.record_result(state, "e1", report)
        self.assertEqual(result["status"], "error")
        self.assertIn("evidence_frames must be a list of ints", result["reason"])
        self.assertEqual(state["e1"]["disposition"], "PENDING_REVIEW")

    def test_counterexample_not_string_returns_error(self):
        state = {}
        report = {
            "verdict": "POSE_SWAP",
            "evidence_frames": [5],
            "counterexample": 123,
            "artwork_needed": "mask",
        }
        result = c3_state.record_result(state, "e1", report)
        self.assertEqual(result["status"], "error")
        self.assertIn("counterexample and artwork_needed must be strings", result["reason"])
        self.assertEqual(state["e1"]["disposition"], "PENDING_REVIEW")

    def test_artwork_needed_not_string_returns_error(self):
        state = {}
        report = {
            "verdict": "POSE_SWAP",
            "evidence_frames": [5],
            "counterexample": "none",
            "artwork_needed": 123,
        }
        result = c3_state.record_result(state, "e1", report)
        self.assertEqual(result["status"], "error")
        self.assertIn("counterexample and artwork_needed must be strings", result["reason"])
        self.assertEqual(state["e1"]["disposition"], "PENDING_REVIEW")

    def test_bool_frames_rejected(self):
        state = {}
        report = {
            "verdict": "POSE_SWAP",
            "evidence_frames": [True, 5],
            "counterexample": "none",
            "artwork_needed": "mask",
        }
        result = c3_state.record_result(state, "e1", report)
        self.assertEqual(result["status"], "error")
        self.assertIn("evidence_frames must be a list of ints", result["reason"])
        self.assertEqual(state["e1"]["disposition"], "PENDING_REVIEW")

    def test_non_dict_report_returns_error(self):
        state = {}
        report = "not a dict"
        result = c3_state.record_result(state, "e1", report)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason"], "report must be a dict")
        self.assertEqual(state["e1"]["disposition"], "PENDING_REVIEW")
        self.assertEqual(state["e1"]["error"], "report must be a dict")

    def test_invalid_report_on_previously_reviewed_clears_fields(self):
        state = {
            "e1": {
                "disposition": "REVIEWED",
                "verdict": "POSE_SWAP",
                "evidence_frames": [1, 2],
                "counterexample": "old",
                "artwork_needed": "old_mask",
                "basis_event_ids": None,
            }
        }
        report = {
            "verdict": "INVALID",
            "evidence_frames": [5],
            "counterexample": "",
            "artwork_needed": "",
        }
        result = c3_state.record_result(state, "e1", report)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason"], "invalid verdict")
        self.assertEqual(state["e1"]["disposition"], "PENDING_REVIEW")
        self.assertEqual(state["e1"]["error"], "invalid verdict")
        # Ensure stale fields are cleared
        self.assertNotIn("verdict", state["e1"])
        self.assertNotIn("evidence_frames", state["e1"])
        self.assertNotIn("counterexample", state["e1"])
        self.assertNotIn("artwork_needed", state["e1"])
        self.assertNotIn("basis_event_ids", state["e1"])


class TestCoverage(unittest.TestCase):
    def test_counts_dispositions_and_unaccounted(self):
        state = {
            "e1": {"disposition": "REVIEWED"},
            "e2": {"disposition": "INFERRED_FROM_CLUSTER"},
            "e3": {"disposition": "PENDING_REVIEW"},
            "e5": {"disposition": "OTHER"},  # not in events list, should not be counted
        }
        events = [
            {"event_id": "e1"},
            {"event_id": "e2"},
            {"event_id": "e3"},
            {"event_id": "e4"},  # missing from state
        ]
        result = c3_state.coverage(state, events)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["counts"]["REVIEWED"], 1)
        self.assertEqual(result["counts"]["INFERRED_FROM_CLUSTER"], 1)
        self.assertEqual(result["counts"]["PENDING_REVIEW"], 1)
        # e5 is not in events, so OTHER should not appear in counts
        self.assertEqual(result["counts"].get("OTHER", 0), 0)
        self.assertEqual(result["unaccounted"], 1)  # e4 missing

    def test_unknown_disposition_counts_as_unaccounted(self):
        state = {"e1": {"disposition": "WEIRD"}}
        events = [{"event_id": "e1"}]
        result = c3_state.coverage(state, events)
        self.assertEqual(result["unaccounted"], 1)
        # WEIRD is not a known disposition, but it's counted in counts since e1 is in events
        self.assertEqual(result["counts"]["WEIRD"], 1)

    def test_missing_event_id_in_events_list_counts_unaccounted(self):
        state = {"e1": {"disposition": "REVIEWED"}}
        events = [{"event_id": "e1"}, {}]  # second event missing event_id
        result = c3_state.coverage(state, events)
        self.assertEqual(result["unaccounted"], 1)

    def test_non_dict_record_in_state_handled_gracefully(self):
        state = {"e1": "not a dict"}
        events = [{"event_id": "e1"}]
        result = c3_state.coverage(state, events)
        self.assertEqual(result["status"], "ok")
        # The non-dict record is ignored, so no disposition counted, and event is unaccounted
        self.assertEqual(result["unaccounted"], 1)
        self.assertEqual(result["counts"].get("REVIEWED", 0), 0)

    def test_extra_state_entries_not_in_events_not_counted(self):
        """Events in state but not in events list should not contribute to counts."""
        state = {
            "e1": {"disposition": "REVIEWED"},
            "e2": {"disposition": "REVIEWED"},  # not in events
        }
        events = [{"event_id": "e1"}]
        result = c3_state.coverage(state, events)
        self.assertEqual(result["counts"]["REVIEWED"], 1)
        self.assertEqual(result["unaccounted"], 0)


class TestAssertComplete(unittest.TestCase):
    def test_complete_returns_ok(self):
        state = {
            "e1": {"disposition": "REVIEWED"},
            "e2": {"disposition": "INFERRED_FROM_CLUSTER"},
        }
        events = [{"event_id": "e1"}, {"event_id": "e2"}]
        result = c3_state.assert_complete(state, events)
        self.assertEqual(result, {"status": "ok"})

    def test_pending_review_raises_assertion_error(self):
        state = {"e1": {"disposition": "PENDING_REVIEW"}}
        events = [{"event_id": "e1"}]
        with self.assertRaises(AssertionError) as cm:
            c3_state.assert_complete(state, events)
        self.assertIn("Incomplete: 1 PENDING_REVIEW, 0 unaccounted", str(cm.exception))

    def test_unaccounted_raises_assertion_error(self):
        state = {"e1": {"disposition": "REVIEWED"}}
        events = [{"event_id": "e1"}, {"event_id": "e2"}]
        with self.assertRaises(AssertionError) as cm:
            c3_state.assert_complete(state, events)
        self.assertIn("Incomplete: 0 PENDING_REVIEW, 1 unaccounted", str(cm.exception))

    def test_both_pending_and_unaccounted_raises(self):
        state = {"e1": {"disposition": "PENDING_REVIEW"}}
        events = [{"event_id": "e1"}, {"event_id": "e2"}]
        with self.assertRaises(AssertionError) as cm:
            c3_state.assert_complete(state, events)
        self.assertIn("Incomplete: 1 PENDING_REVIEW, 1 unaccounted", str(cm.exception))


class TestPatternsAndExceptions(unittest.TestCase):
    def test_collects_verdict_distribution_and_counterexamples(self):
        state = {
            "e1": {"disposition": "REVIEWED", "verdict": "POSE_SWAP", "counterexample": "occlusion"},
            "e2": {"disposition": "REVIEWED", "verdict": "POSE_SWAP", "counterexample": "fast_motion"},
            "e3": {"disposition": "INFERRED_FROM_CLUSTER"},
        }
        clusters = [{"cluster_id": "C_A", "members": ["e1", "e2", "e3"]}]
        result = c3_state.patterns_and_exceptions(state, clusters)
        self.assertEqual(result["status"], "ok")
        patterns = result["patterns"]
        self.assertEqual(len(patterns), 1)
        p = patterns[0]
        self.assertEqual(p["cluster_id"], "C_A")
        self.assertEqual(p["verdict_distribution"], {"POSE_SWAP": 2})
        self.assertEqual(p["when_it_fails"], ["occlusion", "fast_motion"])

    def test_ignores_non_reviewed_members(self):
        state = {
            "e1": {"disposition": "REVIEWED", "verdict": "CAMERA_MOVE", "counterexample": "shake"},
            "e2": {"disposition": "PENDING_REVIEW", "verdict": "POSE_SWAP", "counterexample": "blur"},
        }
        clusters = [{"cluster_id": "C_B", "members": ["e1", "e2"]}]
        result = c3_state.patterns_and_exceptions(state, clusters)
        p = result["patterns"][0]
        self.assertEqual(p["verdict_distribution"], {"CAMERA_MOVE": 1})
        self.assertEqual(p["when_it_fails"], ["shake"])

    def test_empty_cluster_returns_empty_distribution(self):
        state = {}
        clusters = [{"cluster_id": "C_EMPTY", "members": []}]
        result = c3_state.patterns_and_exceptions(state, clusters)
        p = result["patterns"][0]
        self.assertEqual(p["cluster_id"], "C_EMPTY")
        self.assertEqual(p["verdict_distribution"], {})
        self.assertEqual(p["when_it_fails"], [])

    def test_missing_event_in_state_ignored(self):
        state = {"e1": {"disposition": "REVIEWED", "verdict": "EFFECT", "counterexample": "glitch"}}
        clusters = [{"cluster_id": "C_MISS", "members": ["e1", "e2"]}]
        result = c3_state.patterns_and_exceptions(state, clusters)
        p = result["patterns"][0]
        self.assertEqual(p["verdict_distribution"], {"EFFECT": 1})
        self.assertEqual(p["when_it_fails"], ["glitch"])

    def test_non_dict_cluster_ignored(self):
        state = {"e1": {"disposition": "REVIEWED", "verdict": "EFFECT", "counterexample": "glitch"}}
        clusters = ["not a dict", {"cluster_id": "C_OK", "members": ["e1"]}]
        result = c3_state.patterns_and_exceptions(state, clusters)
        self.assertEqual(len(result["patterns"]), 1)
        self.assertEqual(result["patterns"][0]["cluster_id"], "C_OK")


if __name__ == "__main__":
    unittest.main()
