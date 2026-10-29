import json
import os
import tempfile
import unittest

from d3_deliverables import (
    write_deliverables,
    playbook_guard,
    _generate_playbook_content,
    _generate_beats_section,
    _replace_section,
)


class TestWriteDeliverables(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.beats = [
            {
                "video_id": "vid1",
                "beat_id": "b1",
                "purpose": "ESTABLISH",
                "start_time": 0.0,
                "end_time": 5.0,
            }
        ]
        self.recipes = [
            {
                "key": {
                    "purpose": "ESTABLISH",
                    "camera_movement": "STATIC",
                    "method": "CAMERA_ONLY",
                },
                "preset_id": "landscape_establish",
                "stage1": "Use a static wide shot to establish setting; let the environment speak.",
                "stage2": "Status: EXISTING_PRESET or POSE_OR_LAYER_CHANGE. Artwork needed: background. Simplest: use preset or swap background layer.",
                "sound_lesson": "Ambient drone works; if no music, do not assume — mark UNAVAILABLE.",
                "applicability": "Adapt 9:16 reel pacing to 16:9 devotional film; no copying reel dramatic cues.",
                "counterexamples": ["Ex1"],
                "verification": "SINGLE_SOURCE",
                "source_beats": [{"video_id": "vid1", "beat_id": "b1"}],
            }
        ]

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_io(self, existing_files=None):
        existing_files = existing_files or {}

        def read_file(path):
            filename = os.path.basename(path)
            if filename in existing_files:
                return existing_files[filename]
            raise FileNotFoundError(filename)

        written = {}

        def write_file(path, content):
            filename = os.path.basename(path)
            written[filename] = content

        def list_dir(path):
            return list(existing_files.keys()) + [f for f in written if f not in existing_files]

        return read_file, write_file, list_dir, written

    def test_write_deliverables_creates_all_files(self):
        read_file, write_file, list_dir, written = self._make_io({})

        result = write_deliverables(
            self.temp_dir, self.beats, self.recipes, read_file, write_file, list_dir
        )

        self.assertEqual(result["status"], "OK")
        self.assertCountEqual(
            result["files_written"],
            ["MASTER_REPORT.md", "MASTER_TECHNIQUES.json", "KIMI_ANIMATION_PLAYBOOK.md"],
        )

        # Check MASTER_REPORT.md
        report = written["MASTER_REPORT.md"]
        self.assertIn("<!-- BEATS_START -->", report)
        self.assertIn("<!-- BEATS_END -->", report)
        self.assertIn("vid1/b1: ESTABLISH (0.0-5.0s)", report)

        # Check MASTER_TECHNIQUES.json
        techniques = json.loads(written["MASTER_TECHNIQUES.json"])
        self.assertIn("_beat_recipes", techniques)
        self.assertEqual(techniques["_beat_recipes"], self.recipes)

        # Check KIMI_ANIMATION_PLAYBOOK.md
        playbook = written["KIMI_ANIMATION_PLAYBOOK.md"]
        self.assertIn("# KIMI Animation Playbook", playbook)
        self.assertIn("## Stage 1: Directing Lessons", playbook)
        self.assertIn("Use a static wide shot to establish setting", playbook)
        self.assertIn("## Stage 2: Execution Hints", playbook)
        self.assertIn("EXISTING_PRESET or POSE_OR_LAYER_CHANGE", playbook)
        self.assertIn("## Sound & Silence Rules", playbook)
        self.assertIn("Ambient drone works", playbook)
        self.assertIn("## Applicability", playbook)
        self.assertIn("Adapt 9:16 reel pacing", playbook)
        self.assertIn("read-only hints: canon and schema win", playbook)
        self.assertIn("reference music is research-only and prohibited in production", playbook)
        self.assertIn("reference dialogue never alters EASY wording", playbook)

    def test_write_deliverables_idempotent(self):
        # Pre-populate with new-format content
        existing = {
            "MASTER_REPORT.md": "# Report\n<!-- BEATS_START -->\n## Beats\n- vid1/b1: ESTABLISH (0.0-5.0s)\n<!-- BEATS_END -->\nEnd",
            "MASTER_TECHNIQUES.json": json.dumps({"other_key": "value", "_beat_recipes": self.recipes}),
        }
        read_file, write_file, list_dir, written = self._make_io(existing)

        # First call
        result1 = write_deliverables(
            self.temp_dir, self.beats, self.recipes, read_file, write_file, list_dir
        )
        report1 = written["MASTER_REPORT.md"]

        # Second call - should be idempotent
        read_file2, write_file2, list_dir2, written2 = self._make_io({"MASTER_REPORT.md": report1, "MASTER_TECHNIQUES.json": written["MASTER_TECHNIQUES.json"]})
        result2 = write_deliverables(
            self.temp_dir, self.beats, self.recipes, read_file2, write_file2, list_dir2
        )
        report2 = written2["MASTER_REPORT.md"]

        self.assertEqual(result1["status"], "OK")
        self.assertEqual(result2["status"], "OK")
        # Report should be unchanged after second call
        self.assertEqual(report1, report2)
        self.assertEqual(report1.count("<!-- BEATS_START -->"), 1)
        self.assertEqual(report1.count("<!-- BEATS_END -->"), 1)

    def test_write_deliverables_replaces_old_beats_section(self):
        existing = {
            "MASTER_REPORT.md": "# Report\n<!-- BEATS_START -->\nOld beats\n<!-- BEATS_END -->\nEnd",
            "MASTER_TECHNIQUES.json": json.dumps({"other_key": "value"}),
        }
        read_file, write_file, list_dir, written = self._make_io(existing)

        result = write_deliverables(
            self.temp_dir, self.beats, self.recipes, read_file, write_file, list_dir
        )

        report = written["MASTER_REPORT.md"]
        self.assertNotIn("Old beats", report)
        self.assertIn("vid1/b1: ESTABLISH (0.0-5.0s)", report)
        self.assertEqual(report.count("<!-- BEATS_START -->"), 1)

    def test_write_deliverables_preserves_other_keys_in_techniques(self):
        existing = {
            "MASTER_TECHNIQUES.json": json.dumps({"other_key": "value", "another": 123}),
        }
        read_file, write_file, list_dir, written = self._make_io(existing)

        write_deliverables(self.temp_dir, self.beats, self.recipes, read_file, write_file, list_dir)

        techniques = json.loads(written["MASTER_TECHNIQUES.json"])
        self.assertEqual(techniques["other_key"], "value")
        self.assertEqual(techniques["another"], 123)
        self.assertEqual(techniques["_beat_recipes"], self.recipes)

    def test_write_deliverables_guard_violation_raises(self):
        # Recipe with forbidden playbook instruction
        bad_recipes = [
            {
                "key": {"purpose": "ESTABLISH", "camera_movement": "STATIC", "method": "CAMERA_ONLY"},
                "preset_id": "landscape_establish",
                "stage1": "Rewrite the EASY wording to be more dramatic.",
                "stage2": "Hint",
                "sound_lesson": "Sound",
                "applicability": "Adapt",
                "counterexamples": [],
                "verification": "SINGLE_SOURCE",
                "source_beats": [],
            }
        ]
        read_file, write_file, list_dir, _ = self._make_io({})

        with self.assertRaises(ValueError) as cm:
            write_deliverables(self.temp_dir, self.beats, bad_recipes, read_file, write_file, list_dir)

        self.assertIn("Playbook guard violations", str(cm.exception))
        self.assertIn("rewrite or paraphrase EASY wording", str(cm.exception))

    def test_write_deliverables_uses_start_time_end_time(self):
        """Test that beats with start_time/end_time (D1 spec) work correctly."""
        beats_time = [
            {
                "video_id": "vid1",
                "beat_id": "b1",
                "purpose": "ESTABLISH",
                "start_time": 1.5,
                "end_time": 6.5,
            }
        ]
        read_file, write_file, list_dir, written = self._make_io({})

        result = write_deliverables(
            self.temp_dir, beats_time, self.recipes, read_file, write_file, list_dir
        )

        self.assertEqual(result["status"], "OK")
        report = written["MASTER_REPORT.md"]
        self.assertIn("vid1/b1: ESTABLISH (1.5-6.5s)", report)

    def test_write_deliverables_fallback_to_start_sec(self):
        """Test fallback to start_sec/end_sec for legacy beats."""
        beats_legacy = [
            {
                "video_id": "vid1",
                "beat_id": "b1",
                "purpose": "ESTABLISH",
                "start_sec": 2.0,
                "end_sec": 7.0,
            }
        ]
        read_file, write_file, list_dir, written = self._make_io({})

        result = write_deliverables(
            self.temp_dir, beats_legacy, self.recipes, read_file, write_file, list_dir
        )

        self.assertEqual(result["status"], "OK")
        report = written["MASTER_REPORT.md"]
        self.assertIn("vid1/b1: ESTABLISH (2.0-7.0s)", report)

    def test_write_deliverables_invalid_techniques_json_raises(self):
        """Test that non-dict JSON in MASTER_TECHNIQUES.json raises clear error."""
        existing = {
            "MASTER_TECHNIQUES.json": json.dumps(["not", "a", "dict"]),
        }
        read_file, write_file, list_dir, _ = self._make_io(existing)

        with self.assertRaises(TypeError) as cm:
            write_deliverables(self.temp_dir, self.beats, self.recipes, read_file, write_file, list_dir)

        self.assertIn("must contain a JSON object", str(cm.exception))

    def test_write_deliverables_multiple_recipes_allowed_presets(self):
        """Test that multiple recipes with different preset_ids are all allowed."""
        multi_recipes = [
            {
                "key": {"purpose": "ESTABLISH", "camera_movement": "STATIC", "method": "CAMERA_ONLY"},
                "preset_id": "landscape_establish",
                "stage1": "Lesson 1",
                "stage2": "Use preset 'landscape_establish' for wide shot.",
                "sound_lesson": "Sound 1",
                "applicability": "Apply 1",
                "counterexamples": [],
                "verification": "SINGLE_SOURCE",
                "source_beats": [],
            },
            {
                "key": {"purpose": "REVEAL", "camera_movement": "PAN", "method": "CAMERA_ONLY"},
                "preset_id": "portrait_reveal",
                "stage1": "Lesson 2",
                "stage2": "Use preset 'portrait_reveal' for closeup.",
                "sound_lesson": "Sound 2",
                "applicability": "Apply 2",
                "counterexamples": [],
                "verification": "SINGLE_SOURCE",
                "source_beats": [],
            },
        ]
        beats = [
            {"video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0},
            {"video_id": "vid1", "beat_id": "b2", "purpose": "REVEAL", "start_time": 5.0, "end_time": 10.0},
        ]
        read_file, write_file, list_dir, written = self._make_io({})

        result = write_deliverables(self.temp_dir, beats, multi_recipes, read_file, write_file, list_dir)

        self.assertEqual(result["status"], "OK")
        playbook = written["KIMI_ANIMATION_PLAYBOOK.md"]
        self.assertIn("landscape_establish", playbook)
        self.assertIn("portrait_reveal", playbook)

    def test_write_deliverables_non_string_preset_id_ignored(self):
        """Non-string preset_id values should not be added to allowed_presets."""
        recipes = [
            {
                "key": {"purpose": "ESTABLISH", "camera_movement": "STATIC", "method": "CAMERA_ONLY"},
                "preset_id": ["not", "a", "string"],
                "stage1": "Lesson",
                "stage2": "Hint",
                "sound_lesson": "Sound",
                "applicability": "Apply",
                "counterexamples": [],
                "verification": "SINGLE_SOURCE",
                "source_beats": [],
            }
        ]
        read_file, write_file, list_dir, written = self._make_io({})

        result = write_deliverables(self.temp_dir, self.beats, recipes, read_file, write_file, list_dir)
        self.assertEqual(result["status"], "OK")

    def test_write_deliverables_validation_before_write(self):
        """Test that validation happens before any file writes."""
        # Non-serializable recipes should raise before any write
        bad_recipes = [{"key": {}, "stage1": set()}]  # set is not JSON serializable
        read_file, write_file, list_dir, written = self._make_io({})

        with self.assertRaises(TypeError):
            write_deliverables(self.temp_dir, self.beats, bad_recipes, read_file, write_file, list_dir)

        # No files should have been written
        self.assertEqual(len(written), 0)

    def test_write_deliverables_section_position_preserved(self):
        """Test that the beats section stays in its original position, not moved to end."""
        existing = {
            "MASTER_REPORT.md": "# Report\n<!-- BEATS_START -->\nOld beats\n<!-- BEATS_END -->\nTrailing content after section.",
            "MASTER_TECHNIQUES.json": json.dumps({}),
        }
        read_file, write_file, list_dir, written = self._make_io(existing)

        write_deliverables(self.temp_dir, self.beats, self.recipes, read_file, write_file, list_dir)

        report = written["MASTER_REPORT.md"]
        # The new section should appear before "Trailing content after section."
        beats_pos = report.find("vid1/b1: ESTABLISH")
        trailing_pos = report.find("Trailing content after section.")
        self.assertLess(beats_pos, trailing_pos, "Beats section should remain before trailing content")


class TestPlaybookGuard(unittest.TestCase):
    def test_invented_preset_violation(self):
        text = "Use preset 'my_custom_preset' for this."
        allowed = ["landscape_establish", "portrait_reveal"]
        result = playbook_guard(text, allowed)
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertIn("Invented preset-like ID: 'my_custom_preset' not in allowed list", result["violations"])

    def test_allowed_preset_ok(self):
        text = "Use preset 'landscape_establish' for this."
        allowed = ["landscape_establish", "portrait_reveal"]
        result = playbook_guard(text, allowed)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["violations"], [])

    def test_creator_intent_phrase_violation(self):
        text = "The creator wanted a dramatic zoom."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("creator wanted" in v for v in result["violations"]))

    def test_author_intended_case_insensitive(self):
        text = "THE AUTHOR INTENDED this to be sad."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("author intended" in v.lower() for v in result["violations"]))

    def test_multiple_intent_phrases(self):
        text = "The creator wanted X. The author intended Y. The director wanted Z."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertGreaterEqual(len(result["violations"]), 3)

    def test_clean_text_ok(self):
        text = "Use preset 'landscape_establish'. This beat establishes the setting."
        allowed = ["landscape_establish", "portrait_reveal"]
        result = playbook_guard(text, allowed)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["violations"], [])

    def test_playbook_forbidden_rewrite_easy(self):
        text = "Rewrite the EASY wording for clarity."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("rewrite or paraphrase EASY wording" in v for v in result["violations"]))

    def test_playbook_forbidden_invent_story(self):
        text = "Invent story events to fill gaps."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("invent story events or dialogue" in v for v in result["violations"]))

    def test_playbook_forbidden_assign_timings(self):
        text = "Assign timing to 5 seconds for each beat."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("assign timings in seconds/frames" in v for v in result["violations"]))

    def test_playbook_forbidden_set_duration_seconds(self):
        text = "Set duration to 5 seconds for the shot."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("assign timings in seconds/frames" in v for v in result["violations"]))

    def test_playbook_forbidden_specify_frame_timing(self):
        text = "Specify timing to 30 frames for the transition."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("assign timings in seconds/frames" in v for v in result["violations"]))

    def test_playbook_timing_false_positive_not_flagged(self):
        """Ordinary mention of timing in frame should not trigger violation."""
        text = "The timing in the frame looks correct."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "OK")

    def test_playbook_forbidden_unregistered_preset(self):
        text = "Name an unregistered preset id for this shot."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("unregistered preset id" in v for v in result["violations"]))

    def test_playbook_forbidden_emit_animation_code(self):
        text = "Emit animation code for the transition."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("emit animation code" in v for v in result["violations"]))

    def test_playbook_forbidden_add_music_production(self):
        text = "Add background score to production."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("add music/background score to production" in v for v in result["violations"]))

    def test_reference_music_allowed_as_research(self):
        text = "Reference music: 'Some Track' (reference only)."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "OK")

    def test_reference_music_not_blanket_exception(self):
        """Reference only elsewhere should not suppress production music violation."""
        text = "Reference only: some note. Add background score to production."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("add music/background score to production" in v for v in result["violations"]))

    def test_reference_music_in_same_clause_allows(self):
        """Reference only in same clause as music instruction should allow."""
        text = "Add background score to production (reference only)."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "OK")

    def test_unquoted_preset_word_not_flagged(self):
        # The word "preset" used as ordinary English should not trigger violation
        text = "Simplest: use preset or swap background layer."
        allowed = ["CAMERA_ONLY", "STATIC"]
        result = playbook_guard(text, allowed)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["violations"], [])

    def test_backtick_quoted_preset_flagged(self):
        text = "Use preset `custom_preset` here."
        allowed = ["landscape_establish"]
        result = playbook_guard(text, allowed)
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertIn("Invented preset-like ID: 'custom_preset' not in allowed list", result["violations"])

    def test_double_quoted_preset_flagged(self):
        text = 'Use preset "custom_preset" here.'
        allowed = ["landscape_establish"]
        result = playbook_guard(text, allowed)
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertIn("Invented preset-like ID: 'custom_preset' not in allowed list", result["violations"])

    def test_playbook_forbidden_set_each_shot_duration(self):
        """Test that 'Set each shot duration to 5 seconds' is flagged."""
        text = "Set each shot duration to 5 seconds."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("assign timings in seconds/frames" in v for v in result["violations"]))

    def test_playbook_forbidden_set_the_beat_duration(self):
        """Test that 'Set the beat duration to 3 seconds' is flagged."""
        text = "Set the beat duration to 3 seconds."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("assign timings in seconds/frames" in v for v in result["violations"]))

    def test_playbook_forbidden_set_shot_duration_no_qualifier(self):
        """Test that 'Set shot duration to 5 seconds' is flagged (no each/the/this/every)."""
        text = "Set shot duration to 5 seconds."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("assign timings in seconds/frames" in v for v in result["violations"]))

    def test_playbook_forbidden_set_beat_duration_no_qualifier(self):
        """Test that 'Set beat duration to 3 seconds' is flagged (no each/the/this/every)."""
        text = "Set beat duration to 3 seconds."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("assign timings in seconds/frames" in v for v in result["violations"]))

    def test_playbook_forbidden_set_each_shots_duration(self):
        """Test that 'Set each shot's duration to 5 seconds' is flagged (possessive)."""
        text = "Set each shot's duration to 5 seconds."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("assign timings in seconds/frames" in v for v in result["violations"]))

    def test_playbook_forbidden_set_the_duration_of_each_shot(self):
        """Test that 'Set the duration of each shot to 5 seconds' is flagged."""
        text = "Set the duration of each shot to 5 seconds."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("assign timings in seconds/frames" in v for v in result["violations"]))

    def test_playbook_forbidden_set_duration_decimal_seconds(self):
        """Test that 'Set duration to 5.5 seconds' is flagged (decimal)."""
        text = "Set duration to 5.5 seconds."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        self.assertTrue(any("assign timings in seconds/frames" in v for v in result["violations"]))

    def test_intent_violation_reports_lowercase_pattern(self):
        """Violation message should use lowercase pattern per spec worked example."""
        text = "THE CREATOR WANTED a dramatic zoom."
        result = playbook_guard(text, [])
        self.assertEqual(result["status"], "VIOLATIONS")
        # Should report the lowercase pattern, not the matched uppercase text
        self.assertTrue(any("the creator wanted" == v.split("'")[1] for v in result["violations"]))


class TestGeneratePlaybookContent(unittest.TestCase):
    def test_generate_playbook_content_full(self):
        recipes = [
            {
                "stage1": "Lesson 1",
                "stage2": "Hint 1",
                "sound_lesson": "Sound 1",
                "applicability": "Apply 1",
            },
            {
                "stage1": "Lesson 2",
                "stage2": "Hint 2",
                "sound_lesson": "Sound 2",
                "applicability": "Apply 2",
            },
        ]
        content = _generate_playbook_content(recipes)
        self.assertIn("## Stage 1: Directing Lessons", content)
        self.assertIn("- Lesson 1", content)
        self.assertIn("- Lesson 2", content)
        self.assertIn("## Stage 2: Execution Hints", content)
        self.assertIn("- Hint 1", content)
        self.assertIn("- Hint 2", content)
        self.assertIn("## Sound & Silence Rules", content)
        self.assertIn("- Sound 1", content)
        self.assertIn("- Sound 2", content)
        self.assertIn("## Applicability", content)
        self.assertIn("- Apply 1", content)
        self.assertIn("- Apply 2", content)
        self.assertIn("read-only hints: canon and schema win", content)
        self.assertIn("reference music is research-only and prohibited in production", content)
        self.assertIn("reference dialogue never alters EASY wording", content)

    def test_generate_playbook_content_empty_recipes(self):
        content = _generate_playbook_content([])
        self.assertIn("## Stage 1: Directing Lessons", content)
        self.assertIn("(no lessons)", content)
        self.assertIn("## Stage 2: Execution Hints", content)
        self.assertIn("(no hints)", content)
        self.assertIn("## Sound & Silence Rules", content)
        self.assertIn("(no sound rules)", content)
        self.assertIn("## Applicability", content)
        self.assertIn("(no applicability notes)", content)


class TestGenerateBeatsSection(unittest.TestCase):
    def test_generate_beats_section(self):
        beats = [
            {"video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0},
            {"video_id": "vid2", "beat_id": "b2", "purpose": "REVEAL", "start_time": 5.0, "end_time": 10.0},
        ]
        section = _generate_beats_section(beats)
        self.assertIn("## Beats", section)
        self.assertIn("vid1/b1: ESTABLISH (0.0-5.0s)", section)
        self.assertIn("vid2/b2: REVEAL (5.0-10.0s)", section)

    def test_generate_beats_section_fallback_to_sec(self):
        beats = [
            {"video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_sec": 0.0, "end_sec": 5.0},
        ]
        section = _generate_beats_section(beats)
        self.assertIn("vid1/b1: ESTABLISH (0.0-5.0s)", section)


class TestReplaceSection(unittest.TestCase):
    def test_replace_existing_section(self):
        content = "Header\n<!-- BEATS_START -->\nOld\n<!-- BEATS_END -->\nFooter"
        new = _replace_section(content, "<!-- BEATS_START -->", "<!-- BEATS_END -->", "New Section")
        self.assertIn("Header", new)
        self.assertIn("New Section", new)
        self.assertIn("Footer", new)
        self.assertNotIn("Old", new)
        self.assertEqual(new.count("<!-- BEATS_START -->"), 1)

    def test_append_section_when_markers_missing(self):
        content = "Header\nFooter"
        new = _replace_section(content, "<!-- BEATS_START -->", "<!-- BEATS_END -->", "New Section")
        self.assertIn("Header", new)
        self.assertIn("Footer", new)
        self.assertIn("<!-- BEATS_START -->", new)
        self.assertIn("New Section", new)
        self.assertIn("<!-- BEATS_END -->", new)

    def test_append_section_empty_content(self):
        content = ""
        new = _replace_section(content, "<!-- BEATS_START -->", "<!-- BEATS_END -->", "New Section")
        self.assertIn("<!-- BEATS_START -->", new)
        self.assertIn("New Section", new)
        self.assertIn("<!-- BEATS_END -->", new)

    def test_end_marker_before_start_marker_repairs(self):
        """When end marker appears before start marker, should repair to single section."""
        content = "Header\n<!-- BEATS_END -->\n<!-- BEATS_START -->\nOld\nFooter"
        new = _replace_section(content, "<!-- BEATS_START -->", "<!-- BEATS_END -->", "New Section")
        self.assertIn("Header", new)
        self.assertIn("Footer", new)
        self.assertIn("New Section", new)
        self.assertNotIn("Old", new)
        self.assertEqual(new.count("<!-- BEATS_START -->"), 1)
        self.assertEqual(new.count("<!-- BEATS_END -->"), 1)

    def test_multiple_existing_sections_collapsed_to_one(self):
        """Multiple existing sections should be collapsed to one."""
        content = "Header\n<!-- BEATS_START -->\nOld1\n<!-- BEATS_END -->\nMid\n<!-- BEATS_START -->\nOld2\n<!-- BEATS_END -->\nFooter"
        new = _replace_section(content, "<!-- BEATS_START -->", "<!-- BEATS_END -->", "New Section")
        self.assertIn("Header", new)
        self.assertIn("Mid", new)
        self.assertIn("Footer", new)
        self.assertIn("New Section", new)
        self.assertNotIn("Old1", new)
        self.assertNotIn("Old2", new)
        self.assertEqual(new.count("<!-- BEATS_START -->"), 1)
        self.assertEqual(new.count("<!-- BEATS_END -->"), 1)

    def test_section_inserted_at_first_marker_position(self):
        """New section should be inserted at the first START marker's position."""
        content = "Header\n<!-- BEATS_START -->\nOld\n<!-- BEATS_END -->\nMiddle\nFooter"
        new = _replace_section(content, "<!-- BEATS_START -->", "<!-- BEATS_END -->", "New Section")
        # New section should appear before "Middle"
        new_section_pos = new.find("New Section")
        middle_pos = new.find("Middle")
        self.assertLess(new_section_pos, middle_pos)


if __name__ == "__main__":
    unittest.main()
