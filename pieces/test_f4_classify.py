import unittest
from typing import Dict, List
from f4_classify import classify_technique, research_confidence, usage_bucket, kimi_views

class TestClassifyTechnique(unittest.TestCase):
    def test_general_classification(self):
        evidence = {"videos": 5, "independent_creators": 3, "styles": 2, "method_verified": True}
        self.assertEqual(classify_technique(evidence), "GENERAL")
    
    def test_style_specific_classification_videos(self):
        evidence = {"videos": 3, "independent_creators": 1, "styles": 1, "method_verified": True}
        self.assertEqual(classify_technique(evidence), "STYLE_SPECIFIC")
    
    def test_style_specific_classification_creators(self):
        evidence = {"videos": 1, "independent_creators": 2, "styles": 1, "method_verified": True}
        self.assertEqual(classify_technique(evidence), "STYLE_SPECIFIC")
    
    def test_experimental_classification(self):
        evidence = {"videos": 1, "independent_creators": 1, "styles": 1, "method_verified": False}
        self.assertEqual(classify_technique(evidence), "EXPERIMENTAL")
    
    def test_videos_ge_2_independent_creators_lt_2_styles_1_is_style_specific(self):
        """videos>=2, independent_creators<2, styles==1 => STYLE_SPECIFIC."""
        evidence = {"videos": 3, "independent_creators": 1, "styles": 1, "method_verified": True}
        self.assertEqual(classify_technique(evidence), "STYLE_SPECIFIC")
    
    def test_boundary_independent_creators_2_styles_2_is_general(self):
        """Boundary: independent_creators == 2 and styles == 2 => GENERAL."""
        evidence = {"videos": 2, "independent_creators": 2, "styles": 2, "method_verified": True}
        self.assertEqual(classify_technique(evidence), "GENERAL")
    
    def test_boundary_independent_creators_1_styles_2_is_experimental(self):
        """Boundary: independent_creators == 1 and styles == 2 => EXPERIMENTAL (not GENERAL, not STYLE_SPECIFIC)."""
        evidence = {"videos": 5, "independent_creators": 1, "styles": 2, "method_verified": True}
        self.assertEqual(classify_technique(evidence), "EXPERIMENTAL")
    
    def test_classify_derives_styles_from_videos_list(self):
        """When evidence has videos list with art_style, styles is derived from distinct art_style values."""
        evidence = {
            "videos": [
                {"art_style": "anime"},
                {"art_style": "realistic"},
                {"art_style": "anime"},  # duplicate
                {"art_style": "comic"}
            ],
            "independent_creators": 2,
            "method_verified": True
        }
        # 3 distinct styles (anime, realistic, comic), independent_creators=2 => GENERAL
        self.assertEqual(classify_technique(evidence), "GENERAL")
    
    def test_classify_videos_list_overrides_precomputed_styles(self):
        """When evidence has both videos list and precomputed styles, videos list takes precedence."""
        evidence = {
            "videos": [
                {"art_style": "anime"},
                {"art_style": "realistic"},
                {"art_style": "comic"}
            ],
            "styles": 1,  # precomputed, should be IGNORED
            "independent_creators": 2,
            "method_verified": True
        }
        # 3 distinct styles from videos list, independent_creators=2 => GENERAL
        self.assertEqual(classify_technique(evidence), "GENERAL")
    
    def test_evidence_none_handled_gracefully(self):
        """evidence=None should not raise AttributeError."""
        self.assertEqual(classify_technique(None), "EXPERIMENTAL")
        self.assertEqual(research_confidence(None), "LOW")

class TestResearchConfidence(unittest.TestCase):
    def test_low_confidence_few_videos(self):
        evidence = {"videos": 1, "independent_creators": 3, "styles": 2, "method_verified": True}
        self.assertEqual(research_confidence(evidence), "LOW")
    
    def test_low_confidence_method_not_verified(self):
        evidence = {"videos": 5, "independent_creators": 3, "styles": 2, "method_verified": False}
        self.assertEqual(research_confidence(evidence), "LOW")
    
    def test_low_confidence_method_verified_string_false(self):
        """String 'false' should not count as True."""
        evidence = {"videos": 5, "independent_creators": 3, "styles": 2, "method_verified": "false"}
        self.assertEqual(research_confidence(evidence), "LOW")
    
    def test_high_confidence(self):
        evidence = {"videos": 5, "independent_creators": 3, "styles": 2, "method_verified": True}
        self.assertEqual(research_confidence(evidence), "HIGH")
    
    def test_medium_confidence(self):
        evidence = {"videos": 3, "independent_creators": 2, "styles": 2, "method_verified": True}
        self.assertEqual(research_confidence(evidence), "MEDIUM")
    
    def test_research_confidence_with_videos_list(self):
        """research_confidence should handle videos as a list (use its length)."""
        evidence = {
            "videos": [
                {"art_style": "anime"},
                {"art_style": "realistic"}
            ],
            "independent_creators": 3,
            "method_verified": True
        }
        # 2 videos, independent_creators=3, method_verified=True => HIGH
        self.assertEqual(research_confidence(evidence), "HIGH")
    
    def test_research_confidence_with_videos_list_low(self):
        """research_confidence with videos list of length 1 => LOW."""
        evidence = {
            "videos": [
                {"art_style": "anime"}
            ],
            "independent_creators": 3,
            "method_verified": True
        }
        # 1 video => LOW
        self.assertEqual(research_confidence(evidence), "LOW")

class TestUsageBucket(unittest.TestCase):
    def test_usable_now_existing_preset_assets_available(self):
        technique = {
            "classification": "GENERAL",
            "executability": "EXISTING_PRESET",
            "assets_available": True,
            "evidence": {"videos": 5, "independent_creators": 3, "styles": 2}
        }
        result = usage_bucket(technique)
        self.assertEqual(result, "USABLE_NOW")
    
    def test_usable_now_pose_or_layer_change_assets_available(self):
        technique = {
            "classification": "STYLE_SPECIFIC",
            "executability": "POSE_OR_LAYER_CHANGE",
            "assets_available": True,
            "evidence": {"videos": 3, "independent_creators": 2, "styles": 1}
        }
        result = usage_bucket(technique)
        self.assertEqual(result, "USABLE_NOW")
    
    def test_useful_but_blocked_missing_asset_existing_preset(self):
        technique = {
            "classification": "GENERAL",
            "executability": "EXISTING_PRESET",
            "assets_available": False,
            "evidence": {"videos": 5, "independent_creators": 3, "styles": 2}
        }
        result = usage_bucket(technique)
        self.assertEqual(result, "USEFUL_BUT_BLOCKED")
    
    def test_useful_but_blocked_missing_asset_pose_or_layer_change(self):
        """POSE_OR_LAYER_CHANGE with assets_available False => USEFUL_BUT_BLOCKED (MISSING_ASSET)."""
        technique = {
            "classification": "STYLE_SPECIFIC",
            "executability": "POSE_OR_LAYER_CHANGE",
            "assets_available": False,
            "evidence": {"videos": 3, "independent_creators": 2, "styles": 1}
        }
        result = usage_bucket(technique)
        self.assertEqual(result, "USEFUL_BUT_BLOCKED")
    
    def test_useful_but_blocked_need_new(self):
        technique = {
            "classification": "GENERAL",
            "executability": "NEED_NEW",
            "assets_available": True,
            "evidence": {"videos": 5, "independent_creators": 3, "styles": 2}
        }
        result = usage_bucket(technique)
        self.assertEqual(result, "USEFUL_BUT_BLOCKED")
    
    def test_useful_but_blocked_need_new_assets_false(self):
        technique = {
            "classification": "STYLE_SPECIFIC",
            "executability": "NEED_NEW",
            "assets_available": False,
            "evidence": {"videos": 3, "independent_creators": 2, "styles": 1}
        }
        result = usage_bucket(technique)
        self.assertEqual(result, "USEFUL_BUT_BLOCKED")
    
    def test_research_only_experimental(self):
        technique = {
            "classification": "EXPERIMENTAL",
            "executability": "EXISTING_PRESET",
            "assets_available": True,
            "evidence": {"videos": 1, "independent_creators": 1, "styles": 1}
        }
        result = usage_bucket(technique)
        self.assertEqual(result, "RESEARCH_ONLY")
    
    def test_research_only_executability_research_only(self):
        technique = {
            "classification": "GENERAL",
            "executability": "RESEARCH_ONLY",
            "assets_available": True,
            "evidence": {"videos": 5, "independent_creators": 3, "styles": 2}
        }
        result = usage_bucket(technique)
        self.assertEqual(result, "RESEARCH_ONLY")
    
    def test_invalid_executability_raises_value_error(self):
        technique = {
            "classification": "GENERAL",
            "executability": "INVALID_VALUE",
            "assets_available": True,
            "evidence": {"videos": 5, "independent_creators": 3, "styles": 2}
        }
        with self.assertRaises(ValueError):
            usage_bucket(technique)
    
    def test_invalid_classification_raises_value_error(self):
        technique = {
            "classification": "INVALID_CLASS",
            "executability": "EXISTING_PRESET",
            "assets_available": True,
            "evidence": {"videos": 5, "independent_creators": 3, "styles": 2}
        }
        with self.assertRaises(ValueError):
            usage_bucket(technique)
    
    def test_executability_stripped(self):
        technique = {
            "classification": "GENERAL",
            "executability": "  EXISTING_PRESET  ",
            "assets_available": True,
            "evidence": {"videos": 5, "independent_creators": 3, "styles": 2}
        }
        result = usage_bucket(technique)
        self.assertEqual(result, "USABLE_NOW")
    
    def test_assets_available_string_false_is_not_true(self):
        """String 'false' should not count as True."""
        technique = {
            "classification": "GENERAL",
            "executability": "EXISTING_PRESET",
            "assets_available": "false",
            "evidence": {"videos": 5, "independent_creators": 3, "styles": 2}
        }
        result = usage_bucket(technique)
        self.assertEqual(result, "USEFUL_BUT_BLOCKED")  # MISSING_ASSET
    
    def test_assets_available_none_is_not_true(self):
        technique = {
            "classification": "GENERAL",
            "executability": "EXISTING_PRESET",
            "assets_available": None,
            "evidence": {"videos": 5, "independent_creators": 3, "styles": 2}
        }
        result = usage_bucket(technique)
        self.assertEqual(result, "USEFUL_BUT_BLOCKED")

class TestKimiViews(unittest.TestCase):
    def test_stage1_contains_usable_now_and_useful_but_blocked(self):
        techniques = [
            {
                "id": "tech_a",
                "classification": "GENERAL",
                "executability": "EXISTING_PRESET",
                "assets_available": True,
                "evidence": {"videos": 5, "independent_creators": 3, "styles": 2},
                "preset_id": "preset_1"
            },
            {
                "id": "tech_b",
                "classification": "GENERAL",
                "executability": "NEED_NEW",
                "assets_available": False,
                "evidence": {"videos": 4, "independent_creators": 2, "styles": 2}
            }
        ]
        views = kimi_views(techniques)
        self.assertEqual(len(views["stage1"]), 2)
        self.assertEqual(views["stage1"][0]["id"], "tech_a")
        self.assertEqual(views["stage1"][1]["id"], "tech_b")
        self.assertEqual(views["stage1"][1]["blocked_reason"], "NEED_NEW")
        self.assertEqual(views["stage1"][1]["blocked_note"], "report via existing NEED_NEW if no approved asset")
        # Check research_confidence is present
        self.assertIn("research_confidence", views["stage1"][0])
        self.assertIn("research_confidence", views["stage1"][1])
    
    def test_stage1_blocked_missing_asset_has_blocked_note(self):
        """MISSING_ASSET blocked items in stage1 should have the blocked_note."""
        techniques = [{
            "id": "tech_missing",
            "classification": "GENERAL",
            "executability": "EXISTING_PRESET",
            "assets_available": False,
            "evidence": {"videos": 5, "independent_creators": 3, "styles": 2},
            "preset_id": "preset_1"
        }]
        views = kimi_views(techniques)
        self.assertEqual(len(views["stage1"]), 1)
        self.assertEqual(views["stage1"][0]["id"], "tech_missing")
        self.assertEqual(views["stage1"][0]["blocked_reason"], "MISSING_ASSET")
        self.assertEqual(views["stage1"][0]["blocked_note"], "report via existing NEED_NEW if no approved asset")
        self.assertIn("research_confidence", views["stage1"][0])
        # Should not be in stage2
        self.assertEqual(len(views["stage2"]), 0)
    
    def test_stage2_only_usable_now_with_preset_id(self):
        techniques = [
            {
                "id": "tech_a",
                "classification": "GENERAL",
                "executability": "EXISTING_PRESET",
                "assets_available": True,
                "evidence": {"videos": 5, "independent_creators": 3, "styles": 2},
                "preset_id": "preset_1"
            },
            {
                "id": "tech_b",
                "classification": "GENERAL",
                "executability": "EXISTING_PRESET",
                "assets_available": True,
                "evidence": {"videos": 3, "independent_creators": 2, "styles": 1}
                # no preset_id
            }
        ]
        views = kimi_views(techniques)
        self.assertEqual(len(views["stage2"]), 1)
        self.assertEqual(views["stage2"][0]["id"], "tech_a")
        self.assertEqual(views["stage2"][0]["preset_id"], "preset_1")
    
    def test_research_only_contains_experimental_and_research_only_executability(self):
        techniques = [
            {
                "id": "tech_a",
                "classification": "EXPERIMENTAL",
                "executability": "EXISTING_PRESET",
                "assets_available": True,
                "evidence": {"videos": 1, "independent_creators": 1, "styles": 1}
            },
            {
                "id": "tech_b",
                "classification": "GENERAL",
                "executability": "RESEARCH_ONLY",
                "assets_available": True,
                "evidence": {"videos": 5, "independent_creators": 3, "styles": 2}
            }
        ]
        views = kimi_views(techniques)
        self.assertEqual(len(views["research_only"]), 2)
        self.assertEqual(views["research_only"][0]["id"], "tech_a")
        self.assertEqual(views["research_only"][1]["id"], "tech_b")
        # Check research_confidence is present in research_only items
        self.assertIn("research_confidence", views["research_only"][0])
        self.assertIn("research_confidence", views["research_only"][1])
    
    def test_stable_ordering_by_id(self):
        techniques = [
            {"id": "tech_z", "classification": "GENERAL", "executability": "EXISTING_PRESET", "assets_available": True, "evidence": {"videos": 1, "independent_creators": 1, "styles": 1}},
            {"id": "tech_a", "classification": "GENERAL", "executability": "EXISTING_PRESET", "assets_available": True, "evidence": {"videos": 1, "independent_creators": 1, "styles": 1}},
        ]
        views = kimi_views(techniques)
        self.assertEqual(views["stage1"][0]["id"], "tech_a")
        self.assertEqual(views["stage1"][1]["id"], "tech_z")
    
    def test_stable_ordering_with_none_id(self):
        """None id should not raise TypeError and should sort before strings."""
        techniques = [
            {"id": "tech_b", "classification": "GENERAL", "executability": "EXISTING_PRESET", "assets_available": True, "evidence": {"videos": 1, "independent_creators": 1, "styles": 1}},
            {"id": None, "classification": "GENERAL", "executability": "EXISTING_PRESET", "assets_available": True, "evidence": {"videos": 1, "independent_creators": 1, "styles": 1}},
            {"id": "tech_a", "classification": "GENERAL", "executability": "EXISTING_PRESET", "assets_available": True, "evidence": {"videos": 1, "independent_creators": 1, "styles": 1}},
        ]
        views = kimi_views(techniques)
        # None becomes "" and sorts first
        self.assertEqual(views["stage1"][0]["id"], None)
        self.assertEqual(views["stage1"][1]["id"], "tech_a")
        self.assertEqual(views["stage1"][2]["id"], "tech_b")
    
    def test_evidence_summary_in_stage1_items(self):
        techniques = [{
            "id": "tech_1",
            "classification": "GENERAL",
            "executability": "EXISTING_PRESET",
            "assets_available": True,
            "evidence": {"videos": 7, "independent_creators": 4, "styles": 3}
        }]
        views = kimi_views(techniques)
        self.assertEqual(views["stage1"][0]["evidence_summary"], {"videos": 7, "independent_creators": 4, "styles": 3})
    
    def test_evidence_none_handled_gracefully(self):
        """evidence=None should not raise AttributeError."""
        techniques = [{
            "id": "tech_1",
            "classification": "GENERAL",
            "executability": "EXISTING_PRESET",
            "assets_available": True,
            "evidence": None
        }]
        views = kimi_views(techniques)
        self.assertEqual(views["stage1"][0]["evidence_summary"], {"videos": 0, "independent_creators": 0, "styles": 0})
        self.assertEqual(views["stage1"][0]["research_confidence"], "LOW")
    
    def test_preset_id_non_string_not_copied_to_stage2(self):
        """Non-string preset_id (list, dict, int) should not appear in stage2."""
        techniques = [
            {
                "id": "tech_list",
                "classification": "GENERAL",
                "executability": "EXISTING_PRESET",
                "assets_available": True,
                "evidence": {"videos": 5, "independent_creators": 3, "styles": 2},
                "preset_id": ["preset_1", "preset_2"]
            },
            {
                "id": "tech_dict",
                "classification": "GENERAL",
                "executability": "EXISTING_PRESET",
                "assets_available": True,
                "evidence": {"videos": 5, "independent_creators": 3, "styles": 2},
                "preset_id": {"id": "preset_1"}
            },
            {
                "id": "tech_int",
                "classification": "GENERAL",
                "executability": "EXISTING_PRESET",
                "assets_available": True,
                "evidence": {"videos": 5, "independent_creators": 3, "styles": 2},
                "preset_id": 123
            },
            {
                "id": "tech_empty_str",
                "classification": "GENERAL",
                "executability": "EXISTING_PRESET",
                "assets_available": True,
                "evidence": {"videos": 5, "independent_creators": 3, "styles": 2},
                "preset_id": ""
            },
            {
                "id": "tech_valid",
                "classification": "GENERAL",
                "executability": "EXISTING_PRESET",
                "assets_available": True,
                "evidence": {"videos": 5, "independent_creators": 3, "styles": 2},
                "preset_id": "preset_valid"
            }
        ]
        views = kimi_views(techniques)
        # Only tech_valid should be in stage2
        self.assertEqual(len(views["stage2"]), 1)
        self.assertEqual(views["stage2"][0]["id"], "tech_valid")
        self.assertEqual(views["stage2"][0]["preset_id"], "preset_valid")
    
    def test_evidence_summary_derives_styles_from_videos_list(self):
        """evidence_summary should compute styles from videos list when present."""
        techniques = [{
            "id": "tech_videos",
            "classification": "GENERAL",
            "executability": "EXISTING_PRESET",
            "assets_available": True,
            "evidence": {
                "videos": [
                    {"art_style": "anime"},
                    {"art_style": "realistic"},
                    {"art_style": "anime"}
                ],
                "independent_creators": 2
            }
        }]
        views = kimi_views(techniques)
        # 2 distinct styles (anime, realistic)
        self.assertEqual(views["stage1"][0]["evidence_summary"]["styles"], 2)
        self.assertEqual(views["stage1"][0]["evidence_summary"]["videos"], 3)
        self.assertEqual(views["stage1"][0]["evidence_summary"]["independent_creators"], 2)
    
    def test_evidence_summary_videos_list_overrides_precomputed_styles(self):
        """evidence_summary should derive styles from videos list, ignoring precomputed styles."""
        techniques = [{
            "id": "tech_override",
            "classification": "GENERAL",
            "executability": "EXISTING_PRESET",
            "assets_available": True,
            "evidence": {
                "videos": [
                    {"art_style": "anime"},
                    {"art_style": "realistic"},
                    {"art_style": "comic"}
                ],
                "styles": 1,  # precomputed, should be IGNORED
                "independent_creators": 2
            }
        }]
        views = kimi_views(techniques)
        # 3 distinct styles from videos list, not 1 from precomputed
        self.assertEqual(views["stage1"][0]["evidence_summary"]["styles"], 3)

class TestDirectorDecision(unittest.TestCase):
    """Offline decision tests with stub director function."""
    
    def make_director(self):
        """Stub director: given kimi_views output and a scene need, return decision."""
        def director(views: Dict[str, List[Dict]], need: str) -> str:
            # Check stage2 for matching preset
            for item in views.get("stage2", []):
                if item.get("id") == need:
                    preset_id = item.get("preset_id")
                    if preset_id:
                        return f"USE_PRESET:{preset_id}"
            # Check stage1 for blocked but relevant
            for item in views.get("stage1", []):
                if item.get("id") == need and item.get("blocked_reason"):
                    return "NEED_NEW"
            return "BASELINE"
        return director
    
    def test_positive_usable_now_changes_baseline_to_use_preset(self):
        director = self.make_director()
        techniques = [{
            "id": "lighting_dramatic",
            "classification": "GENERAL",
            "executability": "EXISTING_PRESET",
            "assets_available": True,
            "evidence": {"videos": 5, "independent_creators": 3, "styles": 2},
            "preset_id": "preset_lighting_01"
        }]
        views = kimi_views(techniques)
        
        # Baseline decision without technique
        empty_views = {"stage1": [], "stage2": [], "research_only": []}
        self.assertEqual(director(empty_views, "lighting_dramatic"), "BASELINE")
        
        # With technique, decision changes
        self.assertEqual(director(views, "lighting_dramatic"), "USE_PRESET:preset_lighting_01")
    
    def test_positive_need_new_changes_baseline_to_need_new(self):
        director = self.make_director()
        techniques = [{
            "id": "camera_orbit",
            "classification": "GENERAL",
            "executability": "NEED_NEW",
            "assets_available": False,
            "evidence": {"videos": 4, "independent_creators": 2, "styles": 2}
        }]
        views = kimi_views(techniques)
        
        empty_views = {"stage1": [], "stage2": [], "research_only": []}
        self.assertEqual(director(empty_views, "camera_orbit"), "BASELINE")
        self.assertEqual(director(views, "camera_orbit"), "NEED_NEW")
    
    def test_negative_irrelevant_technique_does_not_change_decision(self):
        director = self.make_director()
        techniques = [{
            "id": "unrelated_effect",
            "classification": "GENERAL",
            "executability": "EXISTING_PRESET",
            "assets_available": True,
            "evidence": {"videos": 5, "independent_creators": 3, "styles": 2},
            "preset_id": "preset_unrelated"
        }]
        views = kimi_views(techniques)
        
        # Need is different from technique id
        self.assertEqual(director(views, "lighting_dramatic"), "BASELINE")
    
    def test_negative_experimental_does_not_change_decision(self):
        director = self.make_director()
        techniques = [{
            "id": "lighting_dramatic",
            "classification": "EXPERIMENTAL",
            "executability": "EXISTING_PRESET",
            "assets_available": True,
            "evidence": {"videos": 1, "independent_creators": 1, "styles": 1}
        }]
        views = kimi_views(techniques)
        
        # EXPERIMENTAL goes to research_only, not stage1/stage2
        self.assertEqual(director(views, "lighting_dramatic"), "BASELINE")
    
    def test_negative_supported_but_different_need_does_not_change(self):
        director = self.make_director()
        techniques = [{
            "id": "camera_orbit",
            "classification": "GENERAL",
            "executability": "EXISTING_PRESET",
            "assets_available": True,
            "evidence": {"videos": 5, "independent_creators": 3, "styles": 2},
            "preset_id": "preset_camera_01"
        }]
        views = kimi_views(techniques)
        
        # Need is lighting, technique is camera
        self.assertEqual(director(views, "lighting_dramatic"), "BASELINE")
    
    def test_negative_unavailable_preset_never_appears_as_use_preset(self):
        director = self.make_director()
        techniques = [{
            "id": "lighting_dramatic",
            "classification": "GENERAL",
            "executability": "EXISTING_PRESET",
            "assets_available": False,  # Missing asset -> USEFUL_BUT_BLOCKED
            "evidence": {"videos": 5, "independent_creators": 3, "styles": 2},
            "preset_id": "preset_lighting_01"
        }]
        views = kimi_views(techniques)
        
        # Should be in stage1 as blocked, not in stage2
        self.assertEqual(len(views["stage2"]), 0)
        self.assertEqual(director(views, "lighting_dramatic"), "NEED_NEW")  # blocked_reason = MISSING_ASSET -> NEED_NEW
    
    def test_no_preset_id_ever_invented(self):
        director = self.make_director()
        techniques = [{
            "id": "lighting_dramatic",
            "classification": "GENERAL",
            "executability": "EXISTING_PRESET",
            "assets_available": True,
            "evidence": {"videos": 5, "independent_creators": 3, "styles": 2}
            # No preset_id provided
        }]
        views = kimi_views(techniques)
        
        # Item in stage1 but NOT in stage2 (no preset_id)
        self.assertEqual(len(views["stage1"]), 1)
        self.assertEqual(len(views["stage2"]), 0)
        self.assertEqual(director(views, "lighting_dramatic"), "BASELINE")
    
    def test_no_preset_id_ever_invented_invariant(self):
        """Spec invariant: every USE_PRESET:<id> returned by director exists in input's preset_id set.
        Stage2 has no item without a preset_id."""
        director = self.make_director()
        techniques = [
            {
                "id": "tech_a",
                "classification": "GENERAL",
                "executability": "EXISTING_PRESET",
                "assets_available": True,
                "evidence": {"videos": 5, "independent_creators": 3, "styles": 2},
                "preset_id": "preset_a"
            },
            {
                "id": "tech_b",
                "classification": "GENERAL",
                "executability": "EXISTING_PRESET",
                "assets_available": True,
                "evidence": {"videos": 3, "independent_creators": 2, "styles": 1}
                # no preset_id
            },
            {
                "id": "tech_c",
                "classification": "GENERAL",
                "executability": "EXISTING_PRESET",
                "assets_available": False,
                "evidence": {"videos": 4, "independent_creators": 2, "styles": 2},
                "preset_id": "preset_c"
            }
        ]
        views = kimi_views(techniques)
        
        # Collect all preset_ids from input
        input_preset_ids = {t.get("preset_id") for t in techniques if isinstance(t.get("preset_id"), str) and t.get("preset_id").strip()}
        
        # Stage2 must only contain items with preset_id, and those preset_ids must be from input
        for item in views["stage2"]:
            self.assertIn("preset_id", item)
            self.assertIsInstance(item["preset_id"], str)
            self.assertTrue(item["preset_id"].strip())
            self.assertIn(item["preset_id"], input_preset_ids)
        
        # Verify no stage2 item lacks preset_id
        for item in views["stage2"]:
            self.assertTrue(item.get("preset_id"))
        
        # Test director decisions for multiple needs
        for need in ["tech_a", "tech_b", "tech_c", "tech_d"]:
            decision = director(views, need)
            if decision.startswith("USE_PRESET:"):
                preset_id = decision.split(":", 1)[1]
                self.assertIn(preset_id, input_preset_ids, f"Invented preset_id: {preset_id}")

if __name__ == "__main__":
    unittest.main()
