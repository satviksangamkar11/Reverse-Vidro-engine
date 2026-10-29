import unittest
from a3_blind_scoring import (
    blind_pairs,
    score_plan,
    summarize,
    promotion_verdict,
    render_review_note
)


class TestBlindPairs(unittest.TestCase):
    def test_blind_pairs_basic(self):
        results_a = [{"scene_id": "s1", "plan": "plan_a1"}, {"scene_id": "s2", "plan": "plan_a2"}]
        results_b = [{"scene_id": "s1", "plan": "plan_b1"}, {"scene_id": "s2", "plan": "plan_b2"}]
        result = blind_pairs(results_a, results_b, seed=42)
        self.assertEqual(result["status"], "ok")
        self.assertIsNotNone(result["pairs"])
        self.assertIsNotNone(result["key"])
        self.assertEqual(len(result["pairs"]), 2)
        self.assertEqual(len(result["key"]), 2)
        for pair in result["pairs"]:
            self.assertIn("scene_id", pair)
            self.assertIn("X", pair)
            self.assertIn("Y", pair)
        for scene_id, mapping in result["key"].items():
            self.assertIn("X", mapping)
            self.assertIn("Y", mapping)
            self.assertIn(mapping["X"], ["A", "B"])
            self.assertIn(mapping["Y"], ["A", "B"])
            self.assertNotEqual(mapping["X"], mapping["Y"])

    def test_blind_pairs_deterministic(self):
        results_a = [{"scene_id": "s1", "plan": "a1"}, {"scene_id": "s2", "plan": "a2"}]
        results_b = [{"scene_id": "s1", "plan": "b1"}, {"scene_id": "s2", "plan": "b2"}]
        r1 = blind_pairs(results_a, results_b, seed=123)
        r2 = blind_pairs(results_a, results_b, seed=123)
        self.assertEqual(r1["pairs"], r2["pairs"])
        self.assertEqual(r1["key"], r2["key"])

    def test_blind_pairs_different_seeds(self):
        results_a = [{"scene_id": "s1", "plan": "a1"}, {"scene_id": "s2", "plan": "a2"}]
        results_b = [{"scene_id": "s1", "plan": "b1"}, {"scene_id": "s2", "plan": "b2"}]
        r1 = blind_pairs(results_a, results_b, seed=1)
        r2 = blind_pairs(results_a, results_b, seed=2)
        self.assertNotEqual(r1["key"], r2["key"])

    def test_blind_pairs_length_mismatch(self):
        results_a = [{"scene_id": "s1", "plan": "a1"}]
        results_b = [{"scene_id": "s1", "plan": "b1"}, {"scene_id": "s2", "plan": "b2"}]
        result = blind_pairs(results_a, results_b, seed=42)
        self.assertEqual(result["status"], "error")
        self.assertIn("same length", result["error"])

    def test_blind_pairs_scene_id_mismatch(self):
        results_a = [{"scene_id": "s1", "plan": "a1"}, {"scene_id": "s2", "plan": "a2"}]
        results_b = [{"scene_id": "s1", "plan": "b1"}, {"scene_id": "s3", "plan": "b2"}]
        result = blind_pairs(results_a, results_b, seed=42)
        self.assertEqual(result["status"], "error")
        self.assertIn("mismatch", result["error"])

    def test_blind_pairs_duplicate_scene_ids(self):
        results_a = [{"scene_id": "s1", "plan": "a1"}, {"scene_id": "s1", "plan": "a2"}]
        results_b = [{"scene_id": "s1", "plan": "b1"}, {"scene_id": "s1", "plan": "b2"}]
        result = blind_pairs(results_a, results_b, seed=42)
        self.assertEqual(result["status"], "error")
        self.assertIn("duplicate", result["error"])

    def test_blind_pairs_non_dict_items(self):
        results_a = [{"scene_id": "s1", "plan": "a1"}, "not a dict"]
        results_b = [{"scene_id": "s1", "plan": "b1"}, {"scene_id": "s2", "plan": "b2"}]
        result = blind_pairs(results_a, results_b, seed=42)
        self.assertEqual(result["status"], "error")
        self.assertIn("must be dicts", result["error"])

    def test_blind_pairs_non_list_inputs(self):
        result = blind_pairs("not a list", [{"scene_id": "s1"}], seed=42)
        self.assertEqual(result["status"], "error")
        self.assertIn("must be lists", result["error"])

    def test_blind_pairs_non_string_scene_id(self):
        results_a = [{"scene_id": 123, "plan": "a1"}, {"scene_id": "s2", "plan": "a2"}]
        results_b = [{"scene_id": 123, "plan": "b1"}, {"scene_id": "s2", "plan": "b2"}]
        result = blind_pairs(results_a, results_b, seed=42)
        self.assertEqual(result["status"], "error")
        self.assertIn("scene_id must be a string", result["error"])

    def test_blind_pairs_none_scene_id(self):
        results_a = [{"scene_id": None, "plan": "a1"}, {"scene_id": "s2", "plan": "a2"}]
        results_b = [{"scene_id": None, "plan": "b1"}, {"scene_id": "s2", "plan": "b2"}]
        result = blind_pairs(results_a, results_b, seed=42)
        self.assertEqual(result["status"], "error")
        self.assertIn("scene_id must be a string", result["error"])

    def test_blind_pairs_unhashable_scene_id(self):
        results_a = [{"scene_id": ["unhashable"], "plan": "a1"}, {"scene_id": "s2", "plan": "a2"}]
        results_b = [{"scene_id": ["unhashable"], "plan": "b1"}, {"scene_id": "s2", "plan": "b2"}]
        result = blind_pairs(results_a, results_b, seed=42)
        self.assertEqual(result["status"], "error")
        self.assertIn("scene_id must be a string", result["error"])

    def test_blind_pairs_seed42_matches_spec_example(self):
        """Test that seed=42 produces the exact assignment from the spec worked example."""
        results_a = [{"scene_id": "s1", "plan": "plan_a1"}, {"scene_id": "s2", "plan": "plan_a2"}]
        results_b = [{"scene_id": "s1", "plan": "plan_b1"}, {"scene_id": "s2", "plan": "plan_b2"}]
        result = blind_pairs(results_a, results_b, seed=42)
        self.assertEqual(result["status"], "ok")
        # Spec example: s1->A=X,B=Y; s2->A=Y,B=X
        self.assertEqual(result["key"]["s1"]["X"], "A")
        self.assertEqual(result["key"]["s1"]["Y"], "B")
        self.assertEqual(result["key"]["s2"]["X"], "B")
        self.assertEqual(result["key"]["s2"]["Y"], "A")
        # Verify pairs content matches key
        for pair in result["pairs"]:
            scene_id = pair["scene_id"]
            key_map = result["key"][scene_id]
            if key_map["X"] == "A":
                self.assertEqual(pair["X"], results_a[0] if scene_id == "s1" else results_a[1])
                self.assertEqual(pair["Y"], results_b[0] if scene_id == "s1" else results_b[1])
            else:
                self.assertEqual(pair["X"], results_b[0] if scene_id == "s1" else results_b[1])
                self.assertEqual(pair["Y"], results_a[0] if scene_id == "s1" else results_a[1])
            # Ensure no A/B labels exposed in pairs
            self.assertNotIn("A", pair)
            self.assertNotIn("B", pair)

    def test_blind_pairs_pairs_content_matches_key(self):
        """Test that each pair's X/Y content agrees with key mapping."""
        results_a = [{"scene_id": "s1", "plan": "a1", "extra": "data1"}, {"scene_id": "s2", "plan": "a2", "extra": "data2"}]
        results_b = [{"scene_id": "s1", "plan": "b1", "extra": "data3"}, {"scene_id": "s2", "plan": "b2", "extra": "data4"}]
        result = blind_pairs(results_a, results_b, seed=999)
        self.assertEqual(result["status"], "ok")
        for pair in result["pairs"]:
            scene_id = pair["scene_id"]
            key_map = result["key"][scene_id]
            # Find original a and b for this scene
            a_orig = next(a for a in results_a if a["scene_id"] == scene_id)
            b_orig = next(b for b in results_b if b["scene_id"] == scene_id)
            if key_map["X"] == "A":
                self.assertEqual(pair["X"], a_orig)
                self.assertEqual(pair["Y"], b_orig)
            else:
                self.assertEqual(pair["X"], b_orig)
                self.assertEqual(pair["Y"], a_orig)
            # Ensure pairs expose no A/B labels
            self.assertNotIn("A", pair)
            self.assertNotIn("B", pair)


class TestScorePlan(unittest.TestCase):
    def setUp(self):
        self.mock_validator = lambda plan: {
            "unsupported_facts": ["fact1", "fact2"],
            "continuity_errors": ["error1"]
        }
        self.assets = {
            "presets": {"preset1", "preset2"},
            "assets": {"asset1", "asset2", "asset3", "asset4"}
        }

    def test_score_plan_basic(self):
        plan = {
            "shots": [
                {"shot_id": "sh1", "composition": "close_up", "movement": "static", "purpose": "emotion", "preset": "preset1", "asset": "asset1", "sfx": "heartbeat", "justification": "tension"},
                {"shot_id": "sh2", "composition": "wide", "movement": "pan_left", "purpose": "establishing", "preset": "preset2", "asset": "asset2", "sfx": "", "justification": "silence for focus"},
                {"shot_id": "sh3", "composition": "close_up", "movement": "static", "purpose": "emotion", "preset": "preset3", "asset": "asset3", "sfx": "whoosh", "justification": ""},
                {"shot_id": "sh4", "composition": "medium", "movement": "zoom_in", "purpose": "reaction", "preset": "NEED_NEW", "asset": "asset4", "sfx": None, "justification": None}
            ]
        }
        result = score_plan(plan, self.mock_validator, self.assets)
        self.assertEqual(result["status"], "ok")
        metrics = result["metrics"]
        self.assertEqual(metrics["canon_fidelity"], 2)
        self.assertEqual(metrics["coverage"], 3)
        self.assertEqual(metrics["continuity_errors"], 1)
        self.assertEqual(metrics["repetition"], 1)
        self.assertEqual(metrics["executability"], 0.5)
        self.assertEqual(metrics["need_new_count"], 2)
        self.assertEqual(metrics["sound_judgment"], 1)
        self.assertEqual(metrics["justified_silence_count"], 1)

    def test_score_plan_empty_shots(self):
        plan = {"shots": []}
        result = score_plan(plan, self.mock_validator, self.assets)
        self.assertEqual(result["status"], "ok")
        metrics = result["metrics"]
        self.assertEqual(metrics["canon_fidelity"], 2)
        self.assertEqual(metrics["coverage"], 0)
        self.assertEqual(metrics["continuity_errors"], 1)
        self.assertEqual(metrics["repetition"], 0)
        self.assertEqual(metrics["executability"], 0.0)
        self.assertEqual(metrics["need_new_count"], 0)
        self.assertEqual(metrics["sound_judgment"], 0)
        self.assertEqual(metrics["justified_silence_count"], 0)

    def test_score_plan_no_shots_key(self):
        plan = {}
        result = score_plan(plan, self.mock_validator, self.assets)
        self.assertEqual(result["status"], "error")
        self.assertIn("shots", result["error"])

    def test_score_plan_repetition_count(self):
        plan = {
            "shots": [
                {"shot_id": "sh1", "composition": "close_up", "movement": "static", "purpose": "emotion", "preset": "preset1", "asset": "asset1", "sfx": None, "justification": None},
                {"shot_id": "sh2", "composition": "close_up", "movement": "static", "purpose": "emotion", "preset": "preset1", "asset": "asset1", "sfx": None, "justification": None},
                {"shot_id": "sh3", "composition": "close_up", "movement": "static", "purpose": "emotion", "preset": "preset1", "asset": "asset1", "sfx": None, "justification": None},
            ]
        }
        result = score_plan(plan, self.mock_validator, self.assets)
        self.assertEqual(result["metrics"]["repetition"], 2)

    def test_score_plan_sound_judgment_and_justified_silence(self):
        plan = {
            "shots": [
                {"shot_id": "sh1", "composition": "c1", "movement": "m1", "purpose": "p1", "preset": "preset1", "asset": "asset1", "sfx": "sfx1", "justification": ""},
                {"shot_id": "sh2", "composition": "c2", "movement": "m2", "purpose": "p2", "preset": "preset1", "asset": "asset1", "sfx": "", "justification": "reason"},
                {"shot_id": "sh3", "composition": "c3", "movement": "m3", "purpose": "p3", "preset": "preset1", "asset": "asset1", "sfx": None, "justification": "reason"},
                {"shot_id": "sh4", "composition": "c4", "movement": "m4", "purpose": "p4", "preset": "preset1", "asset": "asset1", "sfx": "sfx2", "justification": "reason"},
            ]
        }
        result = score_plan(plan, self.mock_validator, self.assets)
        self.assertEqual(result["metrics"]["sound_judgment"], 1)
        self.assertEqual(result["metrics"]["justified_silence_count"], 2)

    def test_score_plan_validator_exception(self):
        def bad_validator(plan):
            raise ValueError("validator failed")
        plan = {"shots": [{"shot_id": "sh1", "composition": "c1", "movement": "m1", "purpose": "p1", "preset": "preset1", "asset": "asset1", "sfx": None, "justification": None}]}
        result = score_plan(plan, bad_validator, self.assets)
        self.assertEqual(result["status"], "error")
        self.assertIn("validator raised exception", result["error"])

    def test_score_plan_validator_returns_non_dict(self):
        def bad_validator(plan):
            return "not a dict"
        plan = {"shots": [{"shot_id": "sh1", "composition": "c1", "movement": "m1", "purpose": "p1", "preset": "preset1", "asset": "asset1", "sfx": None, "justification": None}]}
        result = score_plan(plan, bad_validator, self.assets)
        self.assertEqual(result["status"], "error")
        self.assertIn("validator must return a dict", result["error"])

    def test_score_plan_validator_returns_non_list_fields(self):
        def bad_validator(plan):
            return {"unsupported_facts": "not a list", "continuity_errors": ["error1"]}
        plan = {"shots": [{"shot_id": "sh1", "composition": "c1", "movement": "m1", "purpose": "p1", "preset": "preset1", "asset": "asset1", "sfx": None, "justification": None}]}
        result = score_plan(plan, bad_validator, self.assets)
        self.assertEqual(result["status"], "error")
        self.assertIn("must return 'unsupported_facts' and 'continuity_errors' as lists", result["error"])

    def test_score_plan_validator_missing_fields(self):
        def bad_validator(plan):
            return {"unsupported_facts": ["fact1"]}  # missing continuity_errors
        plan = {"shots": [{"shot_id": "sh1", "composition": "c1", "movement": "m1", "purpose": "p1", "preset": "preset1", "asset": "asset1", "sfx": None, "justification": None}]}
        result = score_plan(plan, bad_validator, self.assets)
        self.assertEqual(result["status"], "error")
        self.assertIn("must return 'unsupported_facts' and 'continuity_errors' as lists", result["error"])

    def test_score_plan_non_dict_shot(self):
        plan = {"shots": [{"shot_id": "sh1", "composition": "c1", "movement": "m1", "purpose": "p1", "preset": "preset1", "asset": "asset1", "sfx": None, "justification": None}, "not a dict"]}
        result = score_plan(plan, self.mock_validator, self.assets)
        self.assertEqual(result["status"], "ok")
        # Should skip the non-dict shot and process the valid one
        self.assertEqual(result["metrics"]["coverage"], 1)

    def test_score_plan_unhashable_preset_asset(self):
        plan = {"shots": [{"shot_id": "sh1", "composition": "c1", "movement": "m1", "purpose": "p1", "preset": ["unhashable"], "asset": {"also": "unhashable"}, "sfx": None, "justification": None}]}
        result = score_plan(plan, self.mock_validator, self.assets)
        self.assertEqual(result["status"], "ok")
        # Unhashable preset/asset should be treated as not available
        self.assertEqual(result["metrics"]["need_new_count"], 1)
        self.assertEqual(result["metrics"]["executability"], 0.0)

    def test_score_plan_unhashable_composition_movement(self):
        plan = {"shots": [{"shot_id": "sh1", "composition": ["unhashable"], "movement": {"also": "unhashable"}, "purpose": "p1", "preset": "preset1", "asset": "asset1", "sfx": None, "justification": None}]}
        result = score_plan(plan, self.mock_validator, self.assets)
        self.assertEqual(result["status"], "ok")
        # Should not crash on unhashable composition/movement
        self.assertEqual(result["metrics"]["repetition"], 0)

    def test_score_plan_unhashable_purpose(self):
        plan = {"shots": [{"shot_id": "sh1", "composition": "c1", "movement": "m1", "purpose": ["unhashable"], "preset": "preset1", "asset": "asset1", "sfx": None, "justification": None}]}
        result = score_plan(plan, self.mock_validator, self.assets)
        self.assertEqual(result["status"], "ok")
        # Should not crash on unhashable purpose
        self.assertEqual(result["metrics"]["coverage"], 0)

    def test_score_plan_non_dict_plan(self):
        result = score_plan("not a dict", self.mock_validator, self.assets)
        self.assertEqual(result["status"], "error")
        self.assertIn("plan must be a dict", result["error"])

    def test_score_plan_non_dict_assets(self):
        plan = {"shots": [{"shot_id": "sh1", "composition": "c1", "movement": "m1", "purpose": "p1", "preset": "preset1", "asset": "asset1", "sfx": None, "justification": None}]}
        result = score_plan(plan, self.mock_validator, "not a dict")
        self.assertEqual(result["status"], "error")
        self.assertIn("assets must be a dict", result["error"])

    def test_score_plan_executability_divides_by_dict_shots(self):
        """Test that executability divides by count of dict shots, not len(shots)."""
        plan = {
            "shots": [
                {"shot_id": "sh1", "composition": "c1", "movement": "m1", "purpose": "p1", "preset": "preset1", "asset": "asset1", "sfx": None, "justification": None},
                "not a dict",
                {"shot_id": "sh3", "composition": "c3", "movement": "m3", "purpose": "p3", "preset": "preset1", "asset": "asset1", "sfx": None, "justification": None},
            ]
        }
        result = score_plan(plan, self.mock_validator, self.assets)
        self.assertEqual(result["status"], "ok")
        # 2 dict shots, both executable -> 2/2 = 1.0
        self.assertEqual(result["metrics"]["executability"], 1.0)

    def test_score_plan_all_skipped_shots(self):
        """Test executability is 0.0 when all shots are non-dict."""
        plan = {"shots": ["not a dict", 123, None]}
        result = score_plan(plan, self.mock_validator, self.assets)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["metrics"]["executability"], 0.0)


class TestSummarize(unittest.TestCase):
    def test_summarize_basic(self):
        scores_a = [
            {"canon_fidelity": 2, "coverage": 3, "continuity_errors": 1, "repetition": 1, "executability": 0.5, "need_new_count": 2, "sound_judgment": 1, "justified_silence_count": 1},
            {"canon_fidelity": 1, "coverage": 4, "continuity_errors": 0, "repetition": 0, "executability": 0.75, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 2}
        ]
        scores_b = [
            {"canon_fidelity": 1, "coverage": 4, "continuity_errors": 0, "repetition": 0, "executability": 0.75, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 2},
            {"canon_fidelity": 1, "coverage": 5, "continuity_errors": 0, "repetition": 0, "executability": 1.0, "need_new_count": 0, "sound_judgment": 0, "justified_silence_count": 2}
        ]
        cost = {
            "kimi_calls_a": 10, "kimi_calls_b": 12,
            "tokens_a": 5000, "tokens_b": 6200,
            "timeouts_a": 0, "timeouts_b": 1,
            "retries_a": 1, "retries_b": 2,
            "owner_corrections_a": 2, "owner_corrections_b": 1
        }
        result = summarize(scores_a, scores_b, cost)
        self.assertEqual(result["status"], "ok")
        summary = result["summary"]
        self.assertAlmostEqual(summary["metrics_a"]["canon_fidelity"], 1.5)
        self.assertAlmostEqual(summary["metrics_a"]["coverage"], 3.5)
        self.assertAlmostEqual(summary["metrics_a"]["continuity_errors"], 0.5)
        self.assertAlmostEqual(summary["metrics_a"]["repetition"], 0.5)
        self.assertAlmostEqual(summary["metrics_a"]["executability"], 0.625)
        self.assertAlmostEqual(summary["metrics_a"]["need_new_count"], 1.5)
        self.assertAlmostEqual(summary["metrics_a"]["sound_judgment"], 0.5)
        self.assertAlmostEqual(summary["metrics_a"]["justified_silence_count"], 1.5)

        self.assertAlmostEqual(summary["metrics_b"]["canon_fidelity"], 1.0)
        self.assertAlmostEqual(summary["metrics_b"]["coverage"], 4.5)
        self.assertAlmostEqual(summary["metrics_b"]["continuity_errors"], 0.0)
        self.assertAlmostEqual(summary["metrics_b"]["repetition"], 0.0)
        self.assertAlmostEqual(summary["metrics_b"]["executability"], 0.875)
        self.assertAlmostEqual(summary["metrics_b"]["need_new_count"], 0.5)
        self.assertAlmostEqual(summary["metrics_b"]["sound_judgment"], 0.0)
        self.assertAlmostEqual(summary["metrics_b"]["justified_silence_count"], 2.0)

        self.assertAlmostEqual(summary["deltas"]["canon_fidelity"], -0.5)
        self.assertAlmostEqual(summary["deltas"]["coverage"], 1.0)
        self.assertAlmostEqual(summary["deltas"]["continuity_errors"], -0.5)
        self.assertAlmostEqual(summary["deltas"]["repetition"], -0.5)
        self.assertAlmostEqual(summary["deltas"]["executability"], 0.25)
        self.assertAlmostEqual(summary["deltas"]["need_new_count"], -1.0)
        self.assertAlmostEqual(summary["deltas"]["sound_judgment"], -0.5)
        self.assertAlmostEqual(summary["deltas"]["justified_silence_count"], 0.5)
        self.assertEqual(summary["cost"], cost)

    def test_summarize_length_mismatch(self):
        scores_a = [{"canon_fidelity": 1}]
        scores_b = [{"canon_fidelity": 1}, {"canon_fidelity": 2}]
        cost = {}
        result = summarize(scores_a, scores_b, cost)
        self.assertEqual(result["status"], "error")
        self.assertIn("same length", result["error"])

    def test_summarize_empty_lists(self):
        scores_a = []
        scores_b = []
        cost = {
            "kimi_calls_a": 0, "kimi_calls_b": 0,
            "tokens_a": 0, "tokens_b": 0,
            "timeouts_a": 0, "timeouts_b": 0,
            "retries_a": 0, "retries_b": 0,
            "owner_corrections_a": 0, "owner_corrections_b": 0
        }
        result = summarize(scores_a, scores_b, cost)
        self.assertEqual(result["status"], "ok")
        summary = result["summary"]
        for m in summary["metrics_a"]:
            self.assertEqual(summary["metrics_a"][m], 0.0)
            self.assertEqual(summary["metrics_b"][m], 0.0)
            self.assertEqual(summary["deltas"][m], 0.0)

    def test_summarize_non_list_inputs(self):
        result = summarize("not a list", [], {})
        self.assertEqual(result["status"], "error")
        self.assertIn("must be lists", result["error"])

    def test_summarize_non_dict_cost(self):
        scores_a = [{"canon_fidelity": 1}]
        scores_b = [{"canon_fidelity": 1}]
        result = summarize(scores_a, scores_b, "not a dict")
        self.assertEqual(result["status"], "error")
        self.assertIn("cost must be a dict", result["error"])

    def test_summarize_missing_cost_keys(self):
        scores_a = [{"canon_fidelity": 1}]
        scores_b = [{"canon_fidelity": 1}]
        cost = {"kimi_calls_a": 10}  # missing most keys
        result = summarize(scores_a, scores_b, cost)
        self.assertEqual(result["status"], "error")
        self.assertIn("cost missing required key", result["error"])

    def test_summarize_non_int_cost_values(self):
        scores_a = [{"canon_fidelity": 1}]
        scores_b = [{"canon_fidelity": 1}]
        cost = {
            "kimi_calls_a": 10, "kimi_calls_b": 12,
            "tokens_a": 5000, "tokens_b": 6200,
            "timeouts_a": 0, "timeouts_b": 1,
            "retries_a": 1, "retries_b": 2,
            "owner_corrections_a": 2, "owner_corrections_b": "not an int"
        }
        result = summarize(scores_a, scores_b, cost)
        self.assertEqual(result["status"], "error")
        self.assertIn("must be an integer", result["error"])

    def test_summarize_bool_cost_values(self):
        scores_a = [{"canon_fidelity": 1}]
        scores_b = [{"canon_fidelity": 1}]
        cost = {
            "kimi_calls_a": 10, "kimi_calls_b": 12,
            "tokens_a": 5000, "tokens_b": 6200,
            "timeouts_a": 0, "timeouts_b": 1,
            "retries_a": 1, "retries_b": 2,
            "owner_corrections_a": 2, "owner_corrections_b": True
        }
        result = summarize(scores_a, scores_b, cost)
        self.assertEqual(result["status"], "error")
        self.assertIn("must be an integer", result["error"])

    def test_summarize_non_dict_score_entry(self):
        scores_a = [
            {"canon_fidelity": 1, "coverage": 3, "continuity_errors": 0, "repetition": 0, "executability": 0.5, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 1},
            "not a dict"
        ]
        scores_b = [
            {"canon_fidelity": 1, "coverage": 4, "continuity_errors": 0, "repetition": 0, "executability": 0.5, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 1},
            {"canon_fidelity": 2, "coverage": 4, "continuity_errors": 0, "repetition": 0, "executability": 0.5, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 1}
        ]
        cost = {
            "kimi_calls_a": 10, "kimi_calls_b": 12,
            "tokens_a": 5000, "tokens_b": 6200,
            "timeouts_a": 0, "timeouts_b": 1,
            "retries_a": 1, "retries_b": 2,
            "owner_corrections_a": 2, "owner_corrections_b": 1
        }
        result = summarize(scores_a, scores_b, cost)
        self.assertEqual(result["status"], "error")
        self.assertIn("each score entry must be a dict", result["error"])

    def test_summarize_non_numeric_metric(self):
        scores_a = [{"canon_fidelity": "not a number", "coverage": 3, "continuity_errors": 0, "repetition": 0, "executability": 0.5, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 1}]
        scores_b = [{"canon_fidelity": 1, "coverage": 4, "continuity_errors": 0, "repetition": 0, "executability": 0.5, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 1}]
        cost = {
            "kimi_calls_a": 10, "kimi_calls_b": 12,
            "tokens_a": 5000, "tokens_b": 6200,
            "timeouts_a": 0, "timeouts_b": 1,
            "retries_a": 1, "retries_b": 2,
            "owner_corrections_a": 2, "owner_corrections_b": 1
        }
        result = summarize(scores_a, scores_b, cost)
        self.assertEqual(result["status"], "error")
        self.assertIn("must be numeric", result["error"])

    def test_summarize_bool_metric(self):
        scores_a = [{"canon_fidelity": True, "coverage": 3, "continuity_errors": 0, "repetition": 0, "executability": 0.5, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 1}]
        scores_b = [{"canon_fidelity": 1, "coverage": 4, "continuity_errors": 0, "repetition": 0, "executability": 0.5, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 1}]
        cost = {
            "kimi_calls_a": 10, "kimi_calls_b": 12,
            "tokens_a": 5000, "tokens_b": 6200,
            "timeouts_a": 0, "timeouts_b": 1,
            "retries_a": 1, "retries_b": 2,
            "owner_corrections_a": 2, "owner_corrections_b": 1
        }
        result = summarize(scores_a, scores_b, cost)
        self.assertEqual(result["status"], "error")
        self.assertIn("must be numeric", result["error"])

    def test_summarize_nan_metric(self):
        scores_a = [{"canon_fidelity": float('nan'), "coverage": 3, "continuity_errors": 0, "repetition": 0, "executability": 0.5, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 1}]
        scores_b = [{"canon_fidelity": 1, "coverage": 4, "continuity_errors": 0, "repetition": 0, "executability": 0.5, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 1}]
        cost = {
            "kimi_calls_a": 10, "kimi_calls_b": 12,
            "tokens_a": 5000, "tokens_b": 6200,
            "timeouts_a": 0, "timeouts_b": 1,
            "retries_a": 1, "retries_b": 2,
            "owner_corrections_a": 2, "owner_corrections_b": 1
        }
        result = summarize(scores_a, scores_b, cost)
        self.assertEqual(result["status"], "error")
        self.assertIn("must be finite", result["error"])

    def test_summarize_inf_metric(self):
        scores_a = [{"canon_fidelity": float('inf'), "coverage": 3, "continuity_errors": 0, "repetition": 0, "executability": 0.5, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 1}]
        scores_b = [{"canon_fidelity": 1, "coverage": 4, "continuity_errors": 0, "repetition": 0, "executability": 0.5, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 1}]
        cost = {
            "kimi_calls_a": 10, "kimi_calls_b": 12,
            "tokens_a": 5000, "tokens_b": 6200,
            "timeouts_a": 0, "timeouts_b": 1,
            "retries_a": 1, "retries_b": 2,
            "owner_corrections_a": 2, "owner_corrections_b": 1
        }
        result = summarize(scores_a, scores_b, cost)
        self.assertEqual(result["status"], "error")
        self.assertIn("must be finite", result["error"])

    def test_summarize_missing_metric_key(self):
        scores_a = [{"canon_fidelity": 1, "coverage": 3}]  # missing other metrics
        scores_b = [{"canon_fidelity": 1, "coverage": 4, "continuity_errors": 0, "repetition": 0, "executability": 0.5, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 1}]
        cost = {
            "kimi_calls_a": 10, "kimi_calls_b": 12,
            "tokens_a": 5000, "tokens_b": 6200,
            "timeouts_a": 0, "timeouts_b": 1,
            "retries_a": 1, "retries_b": 2,
            "owner_corrections_a": 2, "owner_corrections_b": 1
        }
        result = summarize(scores_a, scores_b, cost)
        self.assertEqual(result["status"], "error")
        self.assertIn("missing required metric", result["error"])


class TestPromotionVerdict(unittest.TestCase):
    def make_summary(self, deltas, cost_tokens_a=5000, cost_tokens_b=6000):
        return {
            "status": "ok",
            "summary": {
                "metrics_a": {},
                "metrics_b": {},
                "deltas": deltas,
                "cost": {
                    "tokens_a": cost_tokens_a,
                    "tokens_b": cost_tokens_b,
                    "kimi_calls_a": 10, "kimi_calls_b": 12,
                    "timeouts_a": 0, "timeouts_b": 0,
                    "retries_a": 0, "retries_b": 0,
                    "owner_corrections_a": 0, "owner_corrections_b": 0
                }
            }
        }

    def test_promotion_verdict_promote(self):
        deltas = {
            "canon_fidelity": -1.0,
            "coverage": 2.0,
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = self.make_summary(deltas)
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["verdict"], "PROMOTE")
        self.assertEqual(result["reasons"], [])

    def test_promotion_verdict_hold_owner_not_approved(self):
        deltas = {
            "canon_fidelity": -1.0,
            "coverage": 2.0,
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = self.make_summary(deltas)
        result = promotion_verdict(summary, owner_approved=False, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("owner_approved flag is False", result["reasons"])

    def test_promotion_verdict_hold_animatic_not_compared(self):
        deltas = {
            "canon_fidelity": -1.0,
            "coverage": 2.0,
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = self.make_summary(deltas)
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=False)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("animatic_compared flag is False", result["reasons"])

    def test_promotion_verdict_hold_canon_fidelity_worse(self):
        deltas = {
            "canon_fidelity": 1.0,
            "coverage": 2.0,
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = self.make_summary(deltas)
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("canon_fidelity worsened", result["reasons"])

    def test_promotion_verdict_hold_continuity_worse(self):
        deltas = {
            "canon_fidelity": -1.0,
            "coverage": 2.0,
            "continuity_errors": 1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = self.make_summary(deltas)
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("continuity_errors worsened", result["reasons"])

    def test_promotion_verdict_hold_insufficient_improved_metrics(self):
        deltas = {
            "canon_fidelity": -1.0,
            "coverage": 0.0,
            "continuity_errors": -1.0,
            "repetition": 0.0,
            "executability": 0.0,
            "need_new_count": 0.0,
            "sound_judgment": 0.0,
            "justified_silence_count": 0.0
        }
        summary = self.make_summary(deltas)
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertTrue(any("improved" in r for r in result["reasons"]))

    def test_promotion_verdict_hold_cost_increase_too_high(self):
        deltas = {
            "canon_fidelity": -1.0,
            "coverage": 2.0,
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = self.make_summary(deltas, cost_tokens_a=5000, cost_tokens_b=7000)
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertTrue(any("Cost increase" in r and "exceeds 25%" in r for r in result["reasons"]))

    def test_promotion_verdict_cost_increase_exactly_25_percent(self):
        deltas = {
            "canon_fidelity": -1.0,
            "coverage": 2.0,
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = self.make_summary(deltas, cost_tokens_a=5000, cost_tokens_b=6250)
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertTrue(any("Cost increase" in r for r in result["reasons"]))

    def test_promotion_verdict_cost_increase_under_25_percent(self):
        deltas = {
            "canon_fidelity": -1.0,
            "coverage": 2.0,
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = self.make_summary(deltas, cost_tokens_a=5000, cost_tokens_b=6249)
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "PROMOTE")

    def test_promotion_verdict_invalid_summary(self):
        summary = {"status": "error"}
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("Invalid summary", result["reasons"])

    def test_promotion_verdict_non_dict_summary(self):
        result = promotion_verdict("not a dict", owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("summary must be a dict", result["reasons"])

    def test_promotion_verdict_missing_canon_fidelity_delta(self):
        deltas = {
            "coverage": 2.0,
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = self.make_summary(deltas)
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("incomplete summary: missing delta field 'canon_fidelity'", result["reasons"])

    def test_promotion_verdict_missing_continuity_errors_delta(self):
        deltas = {
            "canon_fidelity": -1.0,
            "coverage": 2.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = self.make_summary(deltas)
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("incomplete summary: missing delta field 'continuity_errors'", result["reasons"])

    def test_promotion_verdict_missing_coverage_delta(self):
        deltas = {
            "canon_fidelity": -1.0,
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = self.make_summary(deltas)
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("incomplete summary: missing delta field 'coverage'", result["reasons"])

    def test_promotion_verdict_non_numeric_canon_fidelity_delta(self):
        deltas = {
            "canon_fidelity": "not a number",
            "coverage": 2.0,
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = self.make_summary(deltas)
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("incomplete summary: delta field 'canon_fidelity' must be numeric", result["reasons"])

    def test_promotion_verdict_bool_delta(self):
        deltas = {
            "canon_fidelity": -1.0,
            "coverage": True,
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = self.make_summary(deltas)
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("incomplete summary: delta field 'coverage' must be numeric", result["reasons"])

    def test_promotion_verdict_nan_delta(self):
        deltas = {
            "canon_fidelity": -1.0,
            "coverage": float('nan'),
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = self.make_summary(deltas)
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("incomplete summary: delta field 'coverage' must be finite", result["reasons"])

    def test_promotion_verdict_missing_cost_tokens(self):
        deltas = {
            "canon_fidelity": -1.0,
            "coverage": 2.0,
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = {
            "status": "ok",
            "summary": {
                "metrics_a": {},
                "metrics_b": {},
                "deltas": deltas,
                "cost": {"kimi_calls_a": 10}  # missing tokens_a, tokens_b
            }
        }
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("incomplete summary: cost missing tokens_a or tokens_b", result["reasons"])

    def test_promotion_verdict_non_numeric_cost_tokens(self):
        deltas = {
            "canon_fidelity": -1.0,
            "coverage": 2.0,
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = {
            "status": "ok",
            "summary": {
                "metrics_a": {},
                "metrics_b": {},
                "deltas": deltas,
                "cost": {"tokens_a": "5000", "tokens_b": 6000}
            }
        }
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("incomplete summary: cost tokens must be numeric", result["reasons"])

    def test_promotion_verdict_bool_cost_tokens(self):
        deltas = {
            "canon_fidelity": -1.0,
            "coverage": 2.0,
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = {
            "status": "ok",
            "summary": {
                "metrics_a": {},
                "metrics_b": {},
                "deltas": deltas,
                "cost": {"tokens_a": True, "tokens_b": 6000}
            }
        }
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("incomplete summary: cost tokens must be numeric", result["reasons"])

    def test_promotion_verdict_deltas_not_dict(self):
        summary = {
            "status": "ok",
            "summary": {
                "metrics_a": {},
                "metrics_b": {},
                "deltas": "not a dict",
                "cost": {"tokens_a": 5000, "tokens_b": 6000}
            }
        }
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("incomplete summary: deltas must be a dict", result["reasons"])

    def test_promotion_verdict_cost_not_dict(self):
        deltas = {
            "canon_fidelity": -1.0,
            "coverage": 2.0,
            "continuity_errors": -1.0,
            "repetition": -1.0,
            "executability": 0.5,
            "need_new_count": -2.0,
            "sound_judgment": -1.0,
            "justified_silence_count": 1.0
        }
        summary = {
            "status": "ok",
            "summary": {
                "metrics_a": {},
                "metrics_b": {},
                "deltas": deltas,
                "cost": "not a dict"
            }
        }
        result = promotion_verdict(summary, owner_approved=True, animatic_compared=True)
        self.assertEqual(result["verdict"], "HOLD")
        self.assertIn("incomplete summary: cost must be a dict", result["reasons"])


class TestRenderReviewNote(unittest.TestCase):
    def test_render_review_note(self):
        result = render_review_note()
        self.assertEqual(result["status"], "ok")
        self.assertIn("REMINDER", result["note"])
        self.assertIn("animatic_compared", result["note"])
        self.assertIn("PROMOTE", result["note"])


if __name__ == "__main__":
    unittest.main()
