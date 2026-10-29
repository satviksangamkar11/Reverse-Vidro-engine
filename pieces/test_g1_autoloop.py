"""Tests for g1_autoloop module."""

import unittest
from unittest.mock import MagicMock, call

from g1_autoloop import decide, merge_findings, run_cycles


class TestDecide(unittest.TestCase):
    def base_state(self, **overrides):
        state = {
            "id": "p1",
            "job": "passed",
            "tests_green": True,
            "changed_since_review": False,
            "last_review": {"luna": "PASS", "glm": "PASS", "minimax": "PASS"},
            "findings_text": "",
            "escalations": 0,
        }
        state.update(overrides)
        return state

    def test_wait_running(self):
        state = self.base_state(job="running")
        self.assertEqual(decide(state), "WAIT")

    def test_relaunch_missing(self):
        state = self.base_state(job="missing")
        self.assertEqual(decide(state), "RELAUNCH")

    def test_relaunch_failed(self):
        state = self.base_state(job="failed")
        self.assertEqual(decide(state), "RELAUNCH")

    def test_escalate(self):
        state = self.base_state(job="escalate")
        self.assertEqual(decide(state), "ESCALATE")

    def test_fix_tests_passed_not_green(self):
        state = self.base_state(job="passed", tests_green=False)
        self.assertEqual(decide(state), "FIX_TESTS")

    def test_fix_tests_passed_no_review_not_green(self):
        state = self.base_state(job="passed-no-review", tests_green=False)
        self.assertEqual(decide(state), "FIX_TESTS")

    def test_review_no_last_review(self):
        state = self.base_state(last_review=None)
        self.assertEqual(decide(state), "REVIEW")

    def test_review_changed_since_review(self):
        state = self.base_state(changed_since_review=True)
        self.assertEqual(decide(state), "REVIEW")

    def test_apply_has_findings(self):
        state = self.base_state(last_review={"luna": "FINDINGS", "glm": "PASS", "minimax": "PASS"})
        self.assertEqual(decide(state), "APPLY")

    def test_done_has_pass_no_findings(self):
        state = self.base_state(last_review={"luna": "PASS", "glm": "NO_REVIEW", "minimax": "NO_REVIEW"})
        self.assertEqual(decide(state), "DONE")

    def test_done_one_pass_two_no_review(self):
        state = self.base_state(last_review={"luna": "PASS", "glm": "NO_REVIEW", "minimax": "NO_REVIEW"})
        self.assertEqual(decide(state), "DONE")

    def test_review_all_three_no_review(self):
        state = self.base_state(last_review={"luna": "NO_REVIEW", "glm": "NO_REVIEW", "minimax": "NO_REVIEW"})
        self.assertEqual(decide(state), "REVIEW")

    def test_priority_wait_over_relaunch(self):
        state = self.base_state(job="running", tests_green=False)
        self.assertEqual(decide(state), "WAIT")

    def test_priority_relaunch_over_escalate(self):
        state = self.base_state(job="missing")
        self.assertEqual(decide(state), "RELAUNCH")

    def test_priority_escalate_over_fix_tests(self):
        state = self.base_state(job="escalate", tests_green=False)
        self.assertEqual(decide(state), "ESCALATE")

    def test_priority_fix_tests_over_review(self):
        state = self.base_state(job="passed", tests_green=False, last_review=None)
        self.assertEqual(decide(state), "FIX_TESTS")

    def test_priority_review_over_apply(self):
        state = self.base_state(changed_since_review=True, last_review={"luna": "FINDINGS"})
        self.assertEqual(decide(state), "REVIEW")

    def test_priority_apply_over_done(self):
        state = self.base_state(last_review={"luna": "FINDINGS", "glm": "PASS"})
        self.assertEqual(decide(state), "APPLY")

    def test_job_normalization_strips_and_lowers(self):
        state = self.base_state(job="  PASSED  ", last_review=None)
        self.assertEqual(decide(state), "REVIEW")  # passed, tests_green, no review -> REVIEW

    def test_unknown_job_raises_value_error(self):
        state = self.base_state(job="unknown")
        with self.assertRaises(ValueError):
            decide(state)

    def test_job_none_treated_as_missing(self):
        state = self.base_state(job=None)
        self.assertEqual(decide(state), "RELAUNCH")

    def test_table_driven_all_combinations(self):
        # Table: (job, tests_green, last_review, changed, expected_action)
        cases = [
            ("running", True, None, False, "WAIT"),
            ("running", False, None, False, "WAIT"),
            ("missing", True, None, False, "RELAUNCH"),
            ("missing", False, None, False, "RELAUNCH"),
            ("failed", True, None, False, "RELAUNCH"),
            ("failed", False, None, False, "RELAUNCH"),
            ("escalate", True, None, False, "ESCALATE"),
            ("escalate", False, None, False, "ESCALATE"),
            ("passed", False, None, False, "FIX_TESTS"),
            ("passed-no-review", False, None, False, "FIX_TESTS"),
            ("passed", True, None, False, "REVIEW"),
            ("passed-no-review", True, None, False, "REVIEW"),
            ("passed", True, {"luna": "PASS"}, True, "REVIEW"),
            ("passed", True, {"luna": "PASS"}, False, "DONE"),
            ("passed", True, {"luna": "FINDINGS"}, False, "APPLY"),
            ("passed", True, {"luna": "NO_REVIEW", "glm": "NO_REVIEW", "minimax": "NO_REVIEW"}, False, "REVIEW"),
            ("passed", True, {"luna": "PASS", "glm": "NO_REVIEW", "minimax": "NO_REVIEW"}, False, "DONE"),
            ("passed", True, {"luna": "PASS", "glm": "PASS", "minimax": "PASS"}, False, "DONE"),
        ]
        for job, tests_green, last_review, changed, expected in cases:
            with self.subTest(job=job, tests_green=tests_green, last_review=last_review, changed=changed):
                state = self.base_state(job=job, tests_green=tests_green, last_review=last_review, changed_since_review=changed)
                self.assertEqual(decide(state), expected)


class TestMergeFindings(unittest.TestCase):
    def test_ordering_luna_glm_minimax_then_alpha(self):
        reviews = {
            "zeta": "zeta text long enough",
            "luna": "luna text long enough",
            "alpha": "alpha text long enough",
            "glm": "glm text long enough",
            "minimax": "minimax text long enough",
        }
        result = merge_findings(reviews, minimum_len=10)
        lines = result.split("\n")
        headers = [line.rstrip(":") for line in lines if line.endswith(":")]
        self.assertEqual(headers, ["luna", "glm", "minimax", "alpha", "zeta"])

    def test_filters_no_review(self):
        reviews = {"luna": "NO_REVIEW", "glm": "glm text long enough"}
        result = merge_findings(reviews, minimum_len=10)
        self.assertNotIn("luna:", result)
        self.assertIn("glm:", result)

    def test_filters_pass_prefix(self):
        reviews = {"luna": "PASS all good", "glm": "glm text long enough"}
        result = merge_findings(reviews, minimum_len=10)
        self.assertNotIn("luna:", result)
        self.assertIn("glm:", result)

    def test_filters_short_text(self):
        reviews = {"luna": "short", "glm": "glm text long enough"}
        result = merge_findings(reviews, minimum_len=10)
        self.assertNotIn("luna:", result)
        self.assertIn("glm:", result)

    def test_keeps_high_med_even_if_short(self):
        reviews = {"luna": "HIGH: critical issue", "glm": "glm text long enough"}
        result = merge_findings(reviews, minimum_len=50)
        self.assertIn("luna:", result)
        self.assertIn("HIGH", result)

    def test_keeps_high_med_even_if_pass_prefix(self):
        reviews = {"luna": "PASS but HIGH: something", "glm": "glm text long enough"}
        result = merge_findings(reviews, minimum_len=10)
        self.assertIn("luna:", result)
        self.assertIn("HIGH", result)

    def test_empty_result(self):
        reviews = {"luna": "NO_REVIEW", "glm": "PASS"}
        result = merge_findings(reviews, minimum_len=10)
        self.assertEqual(result, "")

    def test_custom_minimum_len(self):
        reviews = {"luna": "medium length text"}
        result = merge_findings(reviews, minimum_len=5)
        self.assertIn("luna:", result)
        result2 = merge_findings(reviews, minimum_len=30)
        self.assertEqual(result2, "")


class TestRunCycles(unittest.TestCase):
    def setUp(self):
        self.ids = ["p1", "p2"]
        self.deps = {
            "get_state": MagicMock(),
            "relaunch": MagicMock(),
            "run_reviewers": MagicMock(return_value={"luna": "PASS", "glm": "PASS", "minimax": "PASS"}),
            "apply_findings": MagicMock(),
            "escalate": MagicMock(),
            "sleep": MagicMock(),
        }

    def make_state(self, job="passed", tests_green=True, changed=False, last_review=..., escalations=0):
        if last_review is ...:
            last_review = {"luna": "PASS", "glm": "PASS", "minimax": "PASS"}
        return {
            "id": "p1",
            "job": job,
            "tests_green": tests_green,
            "changed_since_review": changed,
            "last_review": last_review,
            "findings_text": "",
            "escalations": escalations,
        }

    def test_finishes_all_done(self):
        self.deps["get_state"].side_effect = [
            self.make_state(),  # p1 cycle 1
            self.make_state(),  # p2 cycle 1
        ]
        result = run_cycles(self.ids, self.deps, max_cycles=10, sleep_s=0)
        self.assertEqual(result["done"], ["p1", "p2"])
        self.assertEqual(result["stuck"], [])
        self.assertEqual(result["cycles"], 1)
        self.deps["sleep"].assert_called_once_with(0)

    def test_stuck_after_three_escalations(self):
        states = [
            self.make_state(job="escalate", escalations=0),  # cycle 1
            self.make_state(job="escalate", escalations=1),  # cycle 2
            self.make_state(job="escalate", escalations=2),  # cycle 3
            self.make_state(job="escalate", escalations=3),  # cycle 4 -> stuck
        ]
        states_p2 = [self.make_state()]
        call_count = {"p1": 0, "p2": 0}

        def get_state(pid):
            if pid == "p1":
                idx = call_count["p1"]
                call_count["p1"] += 1
                return states[idx]
            else:
                return states_p2[0]

        self.deps["get_state"].side_effect = get_state

        result = run_cycles(self.ids, self.deps, max_cycles=10, sleep_s=0)
        self.assertIn("p1", result["stuck"])
        self.assertIn("p2", result["done"])
        self.assertEqual(result["cycles"], 4)

    def test_exception_in_one_piece_does_not_stop_others(self):
        def get_state(pid):
            if pid == "p1":
                raise ValueError("boom")
            return self.make_state()

        self.deps["get_state"].side_effect = get_state
        result = run_cycles(self.ids, self.deps, max_cycles=2, sleep_s=0)
        actions_p1 = [entry[2] for entry in result["log"] if entry[1] == "p1"]
        actions_p2 = [entry[2] for entry in result["log"] if entry[1] == "p2"]
        self.assertTrue(any("ERROR:ValueError" in a for a in actions_p1))
        self.assertIn("DONE", actions_p2)

    def test_max_cycles_bound(self):
        self.deps["get_state"].return_value = self.make_state(job="running")
        result = run_cycles(self.ids, self.deps, max_cycles=5, sleep_s=0)
        self.assertEqual(result["cycles"], 5)
        self.assertEqual(self.deps["sleep"].call_count, 5)

    def test_sleep_called_once_per_cycle_with_given_seconds(self):
        self.deps["get_state"].return_value = self.make_state(job="running")
        run_cycles(self.ids, self.deps, max_cycles=3, sleep_s=42)
        self.assertEqual(self.deps["sleep"].call_count, 3)
        self.deps["sleep"].assert_has_calls([call(42), call(42), call(42)])

    def test_review_action_calls_run_reviewers(self):
        self.deps["get_state"].return_value = self.make_state(last_review=None)
        run_cycles(["p1"], self.deps, max_cycles=2, sleep_s=0)
        self.deps["run_reviewers"].assert_called_with("p1")

    def test_apply_action_calls_apply_findings_with_merged(self):
        state = self.make_state(last_review={"luna": "FINDINGS", "glm": "PASS", "minimax": "PASS"})
        self.deps["get_state"].return_value = state
        run_cycles(["p1"], self.deps, max_cycles=1, sleep_s=0)
        self.deps["apply_findings"].assert_called_once()
        args = self.deps["apply_findings"].call_args[0]
        self.assertEqual(args[0], "p1")
        self.assertIn("luna:", args[1])
        self.assertIn("FINDINGS", args[1])

    def test_fix_tests_calls_relaunch(self):
        state = self.make_state(job="passed", tests_green=False)
        self.deps["get_state"].return_value = state
        run_cycles(["p1"], self.deps, max_cycles=2, sleep_s=0)
        self.deps["relaunch"].assert_called_with("p1")

    def test_relaunch_action_calls_relaunch(self):
        state = self.make_state(job="missing")
        self.deps["get_state"].return_value = state
        run_cycles(["p1"], self.deps, max_cycles=2, sleep_s=0)
        self.deps["relaunch"].assert_called_with("p1")

    def test_escalate_action_calls_escalate(self):
        state = self.make_state(job="escalate")
        self.deps["get_state"].return_value = state
        run_cycles(["p1"], self.deps, max_cycles=2, sleep_s=0)
        self.deps["escalate"].assert_called_with("p1")

    def test_missing_sleep_raises_value_error(self):
        deps_no_sleep = {k: v for k, v in self.deps.items() if k != "sleep"}
        with self.assertRaises(ValueError) as cm:
            run_cycles(["p1"], deps_no_sleep, max_cycles=1, sleep_s=0)
        self.assertIn("missing deps: sleep", str(cm.exception))
        self.deps["get_state"].assert_not_called()
        self.deps["sleep"].assert_not_called()

    def test_run_cycles_records_sleep_calls(self):
        """Integration-style test: fake runner, recording sleep, tmp dirs not needed for g1."""
        sleep_calls = []
        def recording_sleep(seconds):
            sleep_calls.append(seconds)

        deps = {
            "get_state": MagicMock(return_value=self.make_state(job="running")),
            "relaunch": MagicMock(),
            "run_reviewers": MagicMock(return_value={"luna": "PASS", "glm": "PASS", "minimax": "PASS"}),
            "apply_findings": MagicMock(),
            "escalate": MagicMock(),
            "sleep": recording_sleep,
        }
        run_cycles(["p1"], deps, max_cycles=2, sleep_s=5)
        self.assertEqual(sleep_calls, [5, 5])


if __name__ == "__main__":
    unittest.main()
