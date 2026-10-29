import unittest
from d2_recipe_compiler import (
    compile_recipes,
    _make_recipe_key,
    _merge_sound_lessons,
)


class TestMakeRecipeKey(unittest.TestCase):
    def test_make_recipe_key_basic(self):
        beat = {
            "purpose": "ESTABLISH",
            "how_filmed": {"camera_movement": "STATIC"},
            "how_animated": {"method": "CAMERA_ONLY"},
        }
        result = _make_recipe_key(beat)
        self.assertEqual(result, ("ESTABLISH", "STATIC", "CAMERA_ONLY"))

    def test_make_recipe_key_missing_fields(self):
        beat = {}
        result = _make_recipe_key(beat)
        self.assertEqual(result, ("", "", ""))

    def test_make_recipe_key_partial_fields(self):
        beat = {
            "purpose": "REVEAL",
            "how_filmed": {},
            "how_animated": {"method": "LAYER_SWAP"},
        }
        result = _make_recipe_key(beat)
        self.assertEqual(result, ("REVEAL", "", "LAYER_SWAP"))


class TestMergeSoundLessons(unittest.TestCase):
    def test_merge_sound_lessons_with_music(self):
        beats = [{
            "sound": {"music": "Ambient drone", "narration": "UNAVAILABLE", "ambience": "UNAVAILABLE", "sfx": "UNAVAILABLE"}
        }]
        result = _merge_sound_lessons(beats)
        # Exact string per spec worked example
        expected = "Ambient drone works; if no music, do not assume \u2014 mark UNAVAILABLE."
        self.assertEqual(result, expected)

    def test_merge_sound_lessons_all_unavailable(self):
        beats = [{
            "sound": {"music": "UNAVAILABLE", "narration": "UNAVAILABLE", "ambience": "UNAVAILABLE", "sfx": "UNAVAILABLE"}
        }]
        result = _merge_sound_lessons(beats)
        self.assertEqual(result, "UNAVAILABLE \u2013 do not assume")

    def test_merge_sound_lessons_multiple_beats(self):
        beats = [
            {"sound": {"music": "Ambient drone", "narration": "UNAVAILABLE", "ambience": "UNAVAILABLE", "sfx": "UNAVAILABLE"}},
            {"sound": {"music": "UNAVAILABLE", "narration": "Voiceover", "ambience": "UNAVAILABLE", "sfx": "UNAVAILABLE"}},
        ]
        result = _merge_sound_lessons(beats)
        self.assertIn("Ambient drone", result)
        self.assertIn("Voiceover", result)

    def test_merge_sound_lessons_empty_list(self):
        result = _merge_sound_lessons([])
        self.assertEqual(result, "UNAVAILABLE \u2013 do not assume")

    def test_merge_sound_lessons_narration_with_works_no_false_trigger(self):
        """Narration containing 'works' should not trigger music warning."""
        beats = [{
            "sound": {"music": "UNAVAILABLE", "narration": "This works well", "ambience": "UNAVAILABLE", "sfx": "UNAVAILABLE"}
        }]
        result = _merge_sound_lessons(beats)
        self.assertIn("Narration: This works well", result)
        self.assertNotIn("if no music", result)


class TestCompileRecipes(unittest.TestCase):
    def setUp(self):
        self.beat1 = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS", "angle": "EYE", "framing": "CENTER", "cut_type": "HARD", "composition": "RULE_OF_THIRDS"},
            "how_animated": {"method": "CAMERA_ONLY", "notes": "Slow zoom"},
            "sound": {"narration": "UNAVAILABLE", "silence": "UNKNOWN", "ambience": "UNAVAILABLE", "sfx": "UNAVAILABLE", "music": "Ambient drone", "sync_with_cut": "UNKNOWN"},
            "observed": ["Wide landscape"], "inferred": [],
            "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use preset 'landscape_establish'"},
            "counterexample": "Fast zoom loses mood", "evidence": [],
            "department_findings": {}
        }
        self.beat2 = {
            "video_id": "vid2", "beat_id": "b2", "purpose": "ESTABLISH", "start_time": 10.0, "end_time": 15.0,
            "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS", "angle": "EYE", "framing": "CENTER", "cut_type": "HARD", "composition": "RULE_OF_THIRDS"},
            "how_animated": {"method": "CAMERA_ONLY", "notes": "Slow zoom"},
            "sound": {"narration": "UNAVAILABLE", "silence": "UNKNOWN", "ambience": "UNAVAILABLE", "sfx": "UNAVAILABLE", "music": "UNAVAILABLE", "sync_with_cut": "UNKNOWN"},
            "observed": ["Wide room"], "inferred": [],
            "reproduction": {"status": "POSE_OR_LAYER_CHANGE", "artwork_needed": ["background"], "simplest_method": "Swap background layer"},
            "counterexample": "Static camera feels dead", "evidence": [],
            "department_findings": {}
        }

    def test_compile_recipes_multi_source(self):
        result = compile_recipes([self.beat1, self.beat2])
        self.assertEqual(result["status"], "OK")
        self.assertEqual(len(result["recipes"]), 1)

        recipe = result["recipes"][0]
        self.assertEqual(recipe["key"]["purpose"], "ESTABLISH")
        self.assertEqual(recipe["key"]["camera_movement"], "STATIC")
        self.assertEqual(recipe["key"]["method"], "CAMERA_ONLY")
        self.assertEqual(recipe["verification"], "MULTI_SOURCE")
        self.assertEqual(len(recipe["source_beats"]), 2)
        self.assertIn("Fast zoom loses mood", recipe["counterexamples"])
        self.assertIn("Static camera feels dead", recipe["counterexamples"])
        self.assertIn("Ambient drone", recipe["sound_lesson"])
        self.assertEqual(recipe["applicability"], "Adapt 9:16 reel pacing to 16:9 devotional film; no copying reel dramatic cues.")

    def test_compile_recipes_single_source(self):
        result = compile_recipes([self.beat1])
        self.assertEqual(result["status"], "OK")
        self.assertEqual(len(result["recipes"]), 1)

        recipe = result["recipes"][0]
        self.assertEqual(recipe["verification"], "SINGLE_SOURCE")
        self.assertEqual(len(recipe["source_beats"]), 1)
        self.assertEqual(recipe["source_beats"][0]["video_id"], "vid1")
        self.assertEqual(recipe["source_beats"][0]["beat_id"], "b1")
        self.assertEqual(recipe["counterexamples"], ["Fast zoom loses mood"])

    def test_compile_recipes_different_keys_separate_recipes(self):
        beat3 = {
            "video_id": "vid3", "beat_id": "b3", "purpose": "REVEAL", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "PAN", "shot_scale": "MS", "angle": "EYE", "framing": "CENTER", "cut_type": "HARD", "composition": "RULE_OF_THIRDS"},
            "how_animated": {"method": "CAMERA_ONLY", "notes": "Pan right"},
            "sound": {"narration": "UNAVAILABLE", "silence": "UNKNOWN", "ambience": "UNAVAILABLE", "sfx": "UNAVAILABLE", "music": "UNAVAILABLE", "sync_with_cut": "UNKNOWN"},
            "observed": ["Character enters"], "inferred": [],
            "reproduction": {"status": "NEED_NEW", "artwork_needed": ["character"], "simplest_method": "Animate character entry"},
            "counterexample": "Fast pan disorients", "evidence": [],
            "department_findings": {}
        }
        result = compile_recipes([self.beat1, beat3])
        self.assertEqual(len(result["recipes"]), 2)

        keys = {(r["key"]["purpose"], r["key"]["camera_movement"], r["key"]["method"]) for r in result["recipes"]}
        self.assertIn(("ESTABLISH", "STATIC", "CAMERA_ONLY"), keys)
        self.assertIn(("REVEAL", "PAN", "CAMERA_ONLY"), keys)

    def test_compile_recipes_empty_input(self):
        result = compile_recipes([])
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["recipes"], [])

    def test_compile_recipes_stage2_format(self):
        result = compile_recipes([self.beat1, self.beat2])
        recipe = result["recipes"][0]
        stage2 = recipe["stage2"]
        self.assertIn("Status: EXISTING_PRESET or POSE_OR_LAYER_CHANGE", stage2)
        self.assertIn("Artwork needed: background", stage2)
        self.assertIn("Simplest:", stage2)

    def test_compile_recipes_sequence_pattern(self):
        beat_a = {**self.beat1, "beat_id": "b1", "start_time": 0.0, "purpose": "ESTABLISH"}
        beat_b = {**self.beat1, "beat_id": "b2", "start_time": 5.0, "purpose": "REVEAL"}
        beat_c = {**self.beat1, "beat_id": "b3", "start_time": 10.0, "purpose": "EMPHASIZE"}
        result = compile_recipes([beat_a, beat_b, beat_c])
        # Each different purpose+camera+method creates separate recipe
        # But if same key, sequence_pattern should have ordered purposes
        # Here all have same key (STATIC, CAMERA_ONLY) but different purposes -> different keys
        # So test that sequence_pattern exists and is list
        for recipe in result["recipes"]:
            self.assertIsInstance(recipe["sequence_pattern"], list)
            self.assertTrue(all(isinstance(p, str) for p in recipe["sequence_pattern"]))

    def test_compile_recipes_when_not_to_use(self):
        result = compile_recipes([self.beat1, self.beat2])
        recipe = result["recipes"][0]
        when_not = recipe["when_not_to_use"]
        self.assertIn("Fast zoom loses mood", when_not)
        self.assertIn("Static camera feels dead", when_not)
        self.assertTrue(when_not.startswith("Avoid:"))

    def test_compile_recipes_preset_id_from_registry(self):
        registered = {"landscape_establish", "portrait_reveal"}
        result = compile_recipes([self.beat1], registered_presets=registered)
        recipe = result["recipes"][0]
        self.assertEqual(recipe["preset_id"], "landscape_establish")

    def test_compile_recipes_preset_id_not_in_registry_dropped(self):
        registered = {"other_preset"}
        result = compile_recipes([self.beat1], registered_presets=registered)
        recipe = result["recipes"][0]
        self.assertIsNone(recipe["preset_id"])

    def test_compile_recipes_preset_id_none_when_no_preset_mentioned(self):
        beat_no_preset = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS"},
            "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"},
            "reproduction": {"status": "NEED_NEW", "artwork_needed": ["bg"], "simplest_method": "Create new background"},
            "counterexample": "", "evidence": [],
            "department_findings": {}
        }
        result = compile_recipes([beat_no_preset], registered_presets={"some_preset"})
        recipe = result["recipes"][0]
        self.assertIsNone(recipe["preset_id"])

    def test_compile_recipes_stage1_lessons_structure(self):
        result = compile_recipes([self.beat1, self.beat2])
        recipe = result["recipes"][0]
        stage1_lessons = recipe["stage1_lessons"]
        self.assertIsInstance(stage1_lessons, list)
        self.assertTrue(len(stage1_lessons) > 0)
        # Check categories present
        lesson_text = " ".join(stage1_lessons)
        self.assertIn("Narrative", lesson_text)
        self.assertIn("Camera/composition", lesson_text)
        self.assertIn("Artwork requirements", lesson_text)
        self.assertIn("Sound", lesson_text)

    def test_compile_recipes_stage2_lessons_structure(self):
        registered = {"landscape_establish"}
        result = compile_recipes([self.beat1, self.beat2], registered_presets=registered)
        recipe = result["recipes"][0]
        stage2_lessons = recipe["stage2_lessons"]
        self.assertIsInstance(stage2_lessons, list)
        self.assertTrue(len(stage2_lessons) > 0)
        lesson_text = " ".join(stage2_lessons)
        self.assertIn("Approved preset", lesson_text)
        self.assertIn("Compatible assets", lesson_text)
        self.assertIn("Feasible alternatives", lesson_text)
        self.assertIn("Exact NEED_NEW gap", lesson_text)

    def test_compile_recipes_stage2_lessons_need_new_gap(self):
        beat_need_new = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "REVEAL", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "PAN", "shot_scale": "MS"},
            "how_animated": {"method": "LAYER_SWAP"},
            "sound": {"music": "UNAVAILABLE"},
            "reproduction": {"status": "NEED_NEW", "artwork_needed": ["character", "prop"], "simplest_method": "Build new layers"},
            "counterexample": "", "evidence": [],
            "department_findings": {}
        }
        result = compile_recipes([beat_need_new])
        recipe = result["recipes"][0]
        stage2_lessons = recipe["stage2_lessons"]
        gap_lesson = [l for l in stage2_lessons if "NEED_NEW gap" in l][0]
        self.assertIn("REVEAL", gap_lesson)
        self.assertIn("LAYER_SWAP", gap_lesson)
        self.assertIn("character", gap_lesson)
        self.assertIn("prop", gap_lesson)

    def test_compile_recipes_source_beats_all_kept(self):
        beats = [self.beat1, self.beat2]
        # Add a third beat with same key
        beat3 = {**self.beat1, "video_id": "vid3", "beat_id": "b3", "start_time": 20.0}
        result = compile_recipes(beats + [beat3])
        recipe = result["recipes"][0]
        self.assertEqual(len(recipe["source_beats"]), 3)
        video_ids = {sb["video_id"] for sb in recipe["source_beats"]}
        self.assertEqual(video_ids, {"vid1", "vid2", "vid3"})

    def test_compile_recipes_sound_lesson_unavailable_when_all_unavailable(self):
        beat_silent = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS"},
            "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE", "narration": "UNAVAILABLE", "ambience": "UNAVAILABLE", "sfx": "UNAVAILABLE"},
            "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use preset"},
            "counterexample": "", "evidence": [],
            "department_findings": {}
        }
        result = compile_recipes([beat_silent])
        recipe = result["recipes"][0]
        self.assertEqual(recipe["sound_lesson"], "UNAVAILABLE \u2013 do not assume")

    def test_compile_recipes_inferred_as_dicts_no_crash(self):
        """Test that inferred list of dicts (with claim field) doesn't cause TypeError."""
        beat_with_inferred = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS"},
            "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"},
            "observed": ["Wide shot"],
            "inferred": [{"claim": "Subject appears calm", "confidence": 0.8, "based_on": "facial expression"},
                         {"claim": "Slow pacing intended", "confidence": 0.6, "based_on": "duration"}],
            "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use preset"},
            "counterexample": "", "evidence": [],
            "department_findings": {}
        }
        result = compile_recipes([beat_with_inferred])
        self.assertEqual(result["status"], "OK")
        recipe = result["recipes"][0]
        # Check stage1_lessons includes inferred claims
        lesson_text = " ".join(recipe["stage1_lessons"])
        self.assertIn("Subject appears calm", lesson_text)
        self.assertIn("Slow pacing intended", lesson_text)

    def test_compile_recipes_department_contraindications_in_counterexamples(self):
        """Test that contraindications from department_findings are included in counterexamples and when_not_to_use."""
        beat_with_contra = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS"},
            "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"},
            "observed": [], "inferred": [],
            "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use preset"},
            "counterexample": "Fast zoom loses mood",
            "evidence": [],
            "department_findings": {
                "camera": [{"term": "static_wide", "contraindication": "Avoid in tight spaces"}],
                "lighting": {"term": "natural", "contraindication": "Fails in low light"}
            }
        }
        result = compile_recipes([beat_with_contra])
        recipe = result["recipes"][0]
        self.assertIn("Fast zoom loses mood", recipe["counterexamples"])
        self.assertIn("Avoid in tight spaces", recipe["counterexamples"])
        self.assertIn("Fails in low light", recipe["counterexamples"])
        when_not = recipe["when_not_to_use"]
        self.assertIn("Avoid in tight spaces", when_not)
        self.assertIn("Fails in low light", when_not)

    def test_compile_recipes_sequence_pattern_from_department_terms(self):
        """Test sequence_pattern derives from department_findings terms in temporal order, preserving repeats."""
        beat1 = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0,
            "how_filmed": {"camera_movement": "STATIC"}, "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"}, "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": ""},
            "counterexample": "", "evidence": [],
            "department_findings": {"editing": [{"term": "withhold", "contraindication": ""}]}
        }
        beat2 = {
            "video_id": "vid1", "beat_id": "b2", "purpose": "ESTABLISH", "start_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC"}, "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"}, "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": ""},
            "counterexample": "", "evidence": [],
            "department_findings": {"camera": [{"term": "push_in", "contraindication": ""}]}
        }
        beat3 = {
            "video_id": "vid1", "beat_id": "b3", "purpose": "ESTABLISH", "start_time": 10.0,
            "how_filmed": {"camera_movement": "STATIC"}, "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"}, "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": ""},
            "counterexample": "", "evidence": [],
            "department_findings": {"editing": [{"term": "pause", "contraindication": ""}]}
        }
        beat4 = {
            "video_id": "vid1", "beat_id": "b4", "purpose": "ESTABLISH", "start_time": 15.0,
            "how_filmed": {"camera_movement": "STATIC"}, "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"}, "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": ""},
            "counterexample": "", "evidence": [],
            "department_findings": {"editing": [{"term": "hold", "contraindication": ""}]}
        }
        beat5 = {
            "video_id": "vid1", "beat_id": "b5", "purpose": "ESTABLISH", "start_time": 20.0,
            "how_filmed": {"camera_movement": "STATIC"}, "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"}, "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": ""},
            "counterexample": "", "evidence": [],
            "department_findings": {"editing": [{"term": "hold", "contraindication": ""}]}
        }
        
        result = compile_recipes([beat1, beat2, beat3, beat4, beat5])
        self.assertEqual(len(result["recipes"]), 1)
        recipe = result["recipes"][0]
        # sequence_pattern should have terms in temporal order, preserving repeats (hold appears twice consecutively -> deduped to once)
        self.assertEqual(recipe["sequence_pattern"], ["withhold", "push_in", "pause", "hold"])

    def test_compile_recipes_sequence_pattern_preserves_non_consecutive_repeats(self):
        """Test that non-consecutive repeated terms are preserved."""
        beat1 = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0,
            "how_filmed": {"camera_movement": "STATIC"}, "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"}, "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": ""},
            "counterexample": "", "evidence": [],
            "department_findings": {"editing": [{"term": "hold", "contraindication": ""}]}
        }
        beat2 = {
            "video_id": "vid1", "beat_id": "b2", "purpose": "ESTABLISH", "start_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC"}, "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"}, "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": ""},
            "counterexample": "", "evidence": [],
            "department_findings": {"camera": [{"term": "push_in", "contraindication": ""}]}
        }
        beat3 = {
            "video_id": "vid1", "beat_id": "b3", "purpose": "ESTABLISH", "start_time": 10.0,
            "how_filmed": {"camera_movement": "STATIC"}, "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"}, "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": ""},
            "counterexample": "", "evidence": [],
            "department_findings": {"editing": [{"term": "hold", "contraindication": ""}]}
        }
        
        result = compile_recipes([beat1, beat2, beat3])
        recipe = result["recipes"][0]
        # hold appears, then push_in, then hold again - non-consecutive repeat should be preserved
        self.assertEqual(recipe["sequence_pattern"], ["hold", "push_in", "hold"])

    def test_compile_recipes_stage2_filters_unregistered_preset(self):
        """Test that stage2 does not leak unregistered preset names."""
        registered = {"approved_preset"}
        beat_with_unregistered = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS"},
            "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"},
            "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use preset 'unregistered_preset'"},
            "counterexample": "", "evidence": [],
            "department_findings": {}
        }
        result = compile_recipes([beat_with_unregistered], registered_presets=registered)
        recipe = result["recipes"][0]
        stage2 = recipe["stage2"]
        # Unregistered preset should not appear in stage2
        self.assertNotIn("unregistered_preset", stage2)
        # But registered preset would appear if mentioned
        beat_with_registered = {**beat_with_unregistered, "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use preset 'approved_preset'"}}
        result2 = compile_recipes([beat_with_registered], registered_presets=registered)
        stage2_2 = result2["recipes"][0]["stage2"]
        self.assertIn("approved_preset", stage2_2)

    def test_compile_recipes_stage2_lessons_filters_unregistered_preset(self):
        """Test that stage2_lessons filters each preset reference against registry."""
        registered = {"approved_preset"}
        beat_mixed = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS"},
            "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"},
            "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use preset 'approved_preset' or preset 'unregistered_preset'"},
            "counterexample": "", "evidence": [],
            "department_findings": {}
        }
        result = compile_recipes([beat_mixed], registered_presets=registered)
        recipe = result["recipes"][0]
        stage2_lessons = recipe["stage2_lessons"]
        lesson_text = " ".join(stage2_lessons)
        # Approved preset should be present
        self.assertIn("approved_preset", lesson_text)
        # Unregistered preset should NOT be present
        self.assertNotIn("unregistered_preset", lesson_text)

    def test_compile_recipes_preset_id_with_hyphen_and_dot(self):
        """Test that preset IDs with hyphens and dots are recognized."""
        registered = {"landscape-establish", "portrait.reveal"}
        beat = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS"},
            "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"},
            "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use preset 'landscape-establish'"},
            "counterexample": "", "evidence": [],
            "department_findings": {}
        }
        result = compile_recipes([beat], registered_presets=registered)
        recipe = result["recipes"][0]
        self.assertEqual(recipe["preset_id"], "landscape-establish")

    def test_compile_recipes_multiple_registered_presets_in_group(self):
        """Test that all registered presets in a group are captured (preset_id takes first, but stage2_lessons knows)."""
        registered = {"preset_a", "preset_b"}
        beat1 = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0,
            "how_filmed": {"camera_movement": "STATIC"}, "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"}, "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use preset 'preset_a'"},
            "counterexample": "", "evidence": [], "department_findings": {}
        }
        beat2 = {
            "video_id": "vid2", "beat_id": "b2", "purpose": "ESTABLISH", "start_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC"}, "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"}, "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use preset 'preset_b'"},
            "counterexample": "", "evidence": [], "department_findings": {}
        }
        result = compile_recipes([beat1, beat2], registered_presets=registered)
        recipe = result["recipes"][0]
        # preset_id should be one of them (deterministic: sorted first)
        self.assertIn(recipe["preset_id"], {"preset_a", "preset_b"})
        # stage2_lessons approved preset should match preset_id
        stage2_lessons_text = " ".join(recipe["stage2_lessons"])
        self.assertIn(f"Approved preset: {recipe['preset_id']}", stage2_lessons_text)

    def test_compile_recipes_stage1_uses_camera_movement_from_key(self):
        """Test that stage1 lesson uses actual camera_movement, not hardcoded 'static'."""
        beat_pan = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "PAN", "shot_scale": "WS"},
            "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"},
            "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use preset"},
            "counterexample": "", "evidence": [],
            "department_findings": {}
        }
        result = compile_recipes([beat_pan])
        recipe = result["recipes"][0]
        stage1 = recipe["stage1"]
        self.assertIn("pan", stage1.lower())
        self.assertNotIn("static wide shot", stage1.lower())

    def test_compile_recipes_stage2_bare_quoted_preset_stripped_when_no_registry(self):
        """Test that bare quoted preset IDs are stripped from stage2 when no registry provided."""
        beat = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS"},
            "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"},
            "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use 'landscape_establish' preset"},
            "counterexample": "", "evidence": [],
            "department_findings": {}
        }
        result = compile_recipes([beat], registered_presets=set())
        recipe = result["recipes"][0]
        stage2 = recipe["stage2"]
        # Bare quoted preset should be stripped when no registry
        self.assertNotIn("landscape_establish", stage2)

    def test_compile_recipes_stage2_bare_quoted_non_preset_preserved(self):
        """Test that bare quoted words not following 'preset' are preserved."""
        beat = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS"},
            "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"},
            "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use 'hero' asset"},
            "counterexample": "", "evidence": [],
            "department_findings": {}
        }
        result = compile_recipes([beat], registered_presets=set())
        recipe = result["recipes"][0]
        stage2 = recipe["stage2"]
        # 'hero' should be preserved since it doesn't follow "preset"
        self.assertIn("hero", stage2)

    def test_compile_recipes_stage2_lessons_bare_quoted_preset_stripped(self):
        """Test that stage2_lessons also strips bare quoted presets when no registry."""
        beat = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS"},
            "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"},
            "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use 'landscape_establish' preset"},
            "counterexample": "", "evidence": [],
            "department_findings": {}
        }
        result = compile_recipes([beat], registered_presets=set())
        recipe = result["recipes"][0]
        stage2_lessons = recipe["stage2_lessons"]
        lesson_text = " ".join(stage2_lessons)
        self.assertNotIn("landscape_establish", lesson_text)

    def test_compile_recipes_stage2_lessons_mixed_registered_unregistered(self):
        """Test that stage2_lessons filters each preset reference individually when mixed."""
        registered = {"approved_preset"}
        beat_mixed = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS"},
            "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"},
            "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use preset 'approved_preset' and preset 'unregistered_preset'"},
            "counterexample": "", "evidence": [],
            "department_findings": {}
        }
        result = compile_recipes([beat_mixed], registered_presets=registered)
        recipe = result["recipes"][0]
        stage2_lessons = recipe["stage2_lessons"]
        lesson_text = " ".join(stage2_lessons)
        # Approved preset should be present
        self.assertIn("approved_preset", lesson_text)
        # Unregistered preset should NOT be present
        self.assertNotIn("unregistered_preset", lesson_text)
        # The method should still be included (with only approved preset)
        self.assertIn("Feasible alternatives:", lesson_text)

    def test_compile_recipes_stage2_bare_quoted_preset_before_keyword_stripped_with_registry(self):
        """Test that 'name' preset pattern is stripped when preset not in registry."""
        registered = {"approved_preset"}
        beat = {
            "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0,
            "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS"},
            "how_animated": {"method": "CAMERA_ONLY"},
            "sound": {"music": "UNAVAILABLE"},
            "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use 'unregistered_preset' preset"},
            "counterexample": "", "evidence": [],
            "department_findings": {}
        }
        result = compile_recipes([beat], registered_presets=registered)
        recipe = result["recipes"][0]
        stage2 = recipe["stage2"]
        self.assertNotIn("unregistered_preset", stage2)
        # But registered preset in same pattern should work
        beat2 = {**beat, "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use 'approved_preset' preset"}}
        result2 = compile_recipes([beat2], registered_presets=registered)
        stage2_2 = result2["recipes"][0]["stage2"]
        self.assertIn("approved_preset", stage2_2)


if __name__ == "__main__":
    unittest.main()
