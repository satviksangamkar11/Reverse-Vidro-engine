"""Unit tests for d1_beat_schema.py"""

import json
import unittest

from d1_beat_schema import validate_beat, beat_prompt, parse_beat


class TestValidateBeat(unittest.TestCase):
    """Tests for validate_beat function."""

    def setUp(self):
        self.valid_beat = {
            "video_id": "vid1",
            "beat_id": "b1",
            "start_time": 0.0,
            "end_time": 5.0,
            "purpose": "ESTABLISH",
            "how_filmed": {
                "shot_scale": "WS",
                "angle": "EYE",
                "framing": "CENTER",
                "camera_movement": "STATIC",
                "cut_type": "HARD",
                "composition": "RULE_OF_THIRDS"
            },
            "how_animated": {
                "method": "CAMERA_ONLY",
                "notes": "Slow zoom in"
            },
            "sound": {
                "narration": "UNAVAILABLE",
                "silence": "UNKNOWN",
                "ambience": "UNAVAILABLE",
                "sfx": "UNAVAILABLE",
                "music": "UNAVAILABLE",
                "sync_with_cut": "UNKNOWN"
            },
            "observed": ["Wide shot of landscape"],
            "inferred": [{"claim": "Sets the mood", "confidence": "MEDIUM", "based_on": ["Wide shot of landscape"]}],
            "reproduction": {
                "status": "EXISTING_PRESET",
                "artwork_needed": [],
                "simplest_method": "Use preset 'landscape_establish'"
            },
            "counterexample": "None",
            "evidence": [{"frame": 0, "time": 0.0}, {"frame": 150, "time": 5.0}]
        }

    def test_valid_beat_returns_ok(self):
        result = validate_beat(self.valid_beat)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["beat"], self.valid_beat)

    def test_invalid_purpose_returns_error(self):
        beat = {**self.valid_beat, "purpose": "INVALID"}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Invalid purpose: INVALID", result["reason"])

    def test_missing_required_field_returns_error(self):
        beat = {**self.valid_beat}
        del beat["video_id"]
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Missing required field: video_id", result["reason"])

    def test_inferred_missing_claim_returns_error(self):
        beat = {**self.valid_beat, "inferred": [{"confidence": "HIGH", "based_on": []}]}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Inferred item missing required keys: claim", result["reason"])

    def test_inferred_missing_confidence_returns_error(self):
        beat = {**self.valid_beat, "inferred": [{"claim": "Test", "based_on": []}]}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Inferred item missing required keys: confidence", result["reason"])

    def test_inferred_missing_based_on_returns_error(self):
        beat = {**self.valid_beat, "inferred": [{"claim": "Test", "confidence": "HIGH"}]}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Inferred item missing required keys: based_on", result["reason"])

    def test_invalid_confidence_returns_error(self):
        beat = {**self.valid_beat, "inferred": [{"claim": "Test", "confidence": "INVALID", "based_on": []}]}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("confidence must be LOW/MEDIUM/HIGH", result["reason"])

    def test_observed_non_string_returns_error(self):
        beat = {**self.valid_beat, "observed": ["Valid", 123]}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("observed[1] must be string", result["reason"])

    def test_invalid_animation_method_returns_error(self):
        beat = {**self.valid_beat, "how_animated": {"method": "INVALID", "notes": "test"}}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Invalid animation method: INVALID", result["reason"])

    def test_invalid_reproduction_status_returns_error(self):
        beat = {**self.valid_beat, "reproduction": {"status": "INVALID", "artwork_needed": [], "simplest_method": "test"}}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Invalid reproduction status: INVALID", result["reason"])

    def test_end_time_before_start_time_returns_error(self):
        beat = {**self.valid_beat, "start_time": 5.0, "end_time": 0.0}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("end_time must be >= start_time", result["reason"])

    def test_evidence_missing_frame_or_time_returns_error(self):
        beat = {**self.valid_beat, "evidence": [{"frame": 0}]}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("evidence[0] missing frame or time", result["reason"])

    def test_optional_source_url_valid(self):
        beat = {**self.valid_beat, "source_url": "https://example.com/video.mp4"}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "OK")

    def test_optional_source_url_none_valid(self):
        beat = {**self.valid_beat, "source_url": None}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "OK")

    def test_optional_source_url_invalid_type_returns_error(self):
        beat = {**self.valid_beat, "source_url": 123}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("source_url must be string or null", result["reason"])

    def test_optional_level_links_valid(self):
        beat = {**self.valid_beat, "level_links": {"video_id": "vid1", "sequence_id": "seq1", "shot_ids": ["shot1", "shot2"]}}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "OK")

    def test_optional_level_links_missing_key_returns_error(self):
        beat = {**self.valid_beat, "level_links": {"video_id": "vid1", "sequence_id": "seq1"}}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("level_links missing required keys", result["reason"])

    def test_optional_verification_status_valid(self):
        beat = {**self.valid_beat, "verification_status": "FRAME_CHECKED"}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "OK")

    def test_optional_verification_status_invalid_returns_error(self):
        beat = {**self.valid_beat, "verification_status": "INVALID"}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Invalid verification_status: INVALID", result["reason"])

    def test_optional_unknowns_valid(self):
        beat = {**self.valid_beat, "unknowns": ["unknown1", "unknown2"]}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "OK")

    def test_optional_information_conveyed_valid(self):
        beat = {**self.valid_beat, "information_conveyed": "Establishes setting"}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "OK")

    def test_department_findings_valid(self):
        beat = {
            **self.valid_beat,
            "department_findings": {
                "1": [{
                    "term": "establishing shot",
                    "status": "OBSERVED",
                    "observed": "Wide landscape shot",
                    "evidence": [{"frame": 0, "time": 0.0}],
                    "inferred_purpose": "Sets the scene",
                    "alternatives": ["close-up"],
                    "contraindication": None,
                    "confidence": "HIGH"
                }]
            }
        }
        result = validate_beat(beat)
        self.assertEqual(result["status"], "OK")

    def test_department_findings_observed_requires_evidence(self):
        beat = {
            **self.valid_beat,
            "department_findings": {
                "1": [{
                    "term": "establishing shot",
                    "status": "OBSERVED",
                    "observed": "Wide landscape shot",
                    "evidence": [],
                    "inferred_purpose": "Sets the scene",
                    "alternatives": [],
                    "contraindication": None,
                    "confidence": "HIGH"
                }]
            }
        }
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("OBSERVED finding requires >=1 evidence entry", result["reason"])

    def test_department_findings_not_observed_requires_examined_basis(self):
        beat = {
            **self.valid_beat,
            "department_findings": {
                "1": [{
                    "term": "establishing shot",
                    "status": "NOT_OBSERVED",
                    "observed": "",
                    "evidence": [],
                    "inferred_purpose": None,
                    "alternatives": [],
                    "contraindication": None,
                    "confidence": "LOW"
                }]
            }
        }
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("NOT_OBSERVED requires non-empty examined_basis", result["reason"])

    def test_department_findings_not_observed_with_examined_basis_valid(self):
        beat = {
            **self.valid_beat,
            "department_findings": {
                "1": [{
                    "term": "establishing shot",
                    "status": "NOT_OBSERVED",
                    "observed": "",
                    "evidence": [],
                    "inferred_purpose": None,
                    "alternatives": [],
                    "contraindication": None,
                    "confidence": "LOW",
                    "examined_basis": "Examined frames 0-150, no establishing shot found"
                }]
            }
        }
        result = validate_beat(beat)
        self.assertEqual(result["status"], "OK")

    def test_department_findings_unknown_no_evidence_required(self):
        beat = {
            **self.valid_beat,
            "department_findings": {
                "1": [{
                    "term": "establishing shot",
                    "status": "UNKNOWN",
                    "observed": "Unclear",
                    "evidence": [],
                    "inferred_purpose": None,
                    "alternatives": [],
                    "contraindication": None,
                    "confidence": "LOW"
                }]
            }
        }
        result = validate_beat(beat)
        self.assertEqual(result["status"], "OK")

    def test_department_findings_not_examined_no_evidence_required(self):
        beat = {
            **self.valid_beat,
            "department_findings": {
                "1": [{
                    "term": "establishing shot",
                    "status": "NOT_EXAMINED",
                    "observed": "",
                    "evidence": [],
                    "inferred_purpose": None,
                    "alternatives": [],
                    "contraindication": None,
                    "confidence": "LOW"
                }]
            }
        }
        result = validate_beat(beat)
        self.assertEqual(result["status"], "OK")

    def test_department_findings_invalid_department_id_returns_error(self):
        beat = {
            **self.valid_beat,
            "department_findings": {
                "99": [{
                    "term": "test",
                    "status": "OBSERVED",
                    "observed": "test",
                    "evidence": [{"frame": 0, "time": 0.0}],
                    "inferred_purpose": None,
                    "alternatives": [],
                    "contraindication": None,
                    "confidence": "HIGH"
                }]
            }
        }
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Invalid department id: 99", result["reason"])

    def test_forbidden_fact_editing_software_in_observed_returns_error(self):
        beat = {**self.valid_beat, "observed": ["Used Adobe Premiere for editing"]}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_forbidden_fact_editing_software_in_notes_returns_error(self):
        beat = {**self.valid_beat, "how_animated": {"method": "CAMERA_ONLY", "notes": "Edited in DaVinci Resolve"}}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_forbidden_fact_camera_lens_in_inferred_claim_returns_error(self):
        beat = {**self.valid_beat, "inferred": [{"claim": "The camera lens was 50mm", "confidence": "HIGH", "based_on": []}]}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_forbidden_fact_focal_length_in_department_finding_returns_error(self):
        beat = {
            **self.valid_beat,
            "department_findings": {
                "5": [{
                    "term": "camera setup",
                    "status": "OBSERVED",
                    "observed": "Used a 35mm focal length lens",
                    "evidence": [{"frame": 0, "time": 0.0}],
                    "inferred_purpose": None,
                    "alternatives": [],
                    "contraindication": None,
                    "confidence": "HIGH"
                }]
            }
        }
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_forbidden_fact_hidden_rig_in_information_conveyed_returns_error(self):
        beat = {**self.valid_beat, "information_conveyed": "Hidden rig was used for the effect"}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_forbidden_fact_original_screenplay_in_counterexample_returns_error(self):
        beat = {**self.valid_beat, "counterexample": "Original screenplay had different dialogue"}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_forbidden_fact_in_sound_narration_returns_error(self):
        beat = {**self.valid_beat, "sound": {**self.valid_beat["sound"], "narration": "Edited with Premiere Pro"}}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_forbidden_fact_in_how_filmed_angle_returns_error(self):
        beat = {**self.valid_beat, "how_filmed": {**self.valid_beat["how_filmed"], "angle": "Shot on a 50mm focal length lens"}}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_forbidden_fact_in_simplest_method_returns_error(self):
        beat = {**self.valid_beat, "reproduction": {**self.valid_beat["reproduction"], "simplest_method": "Edit in Premiere Pro"}}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_forbidden_fact_in_unknowns_returns_error(self):
        beat = {**self.valid_beat, "unknowns": ["What focal length was used"]}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_legitimate_editing_finding_passes(self):
        """Legitimate editing technique finding (not software) should pass."""
        beat = {
            **self.valid_beat,
            "department_findings": {
                "7": [{
                    "term": "fast editing rhythm",
                    "status": "OBSERVED",
                    "observed": "Quick cuts create tension",
                    "evidence": [{"frame": 0, "time": 0.0}],
                    "inferred_purpose": "Builds energy",
                    "alternatives": ["slow pacing"],
                    "contraindication": None,
                    "confidence": "HIGH"
                }]
            }
        }
        result = validate_beat(beat)
        self.assertEqual(result["status"], "OK", f"Legitimate editing finding rejected: {result.get('reason')}")

    def test_legitimate_resolve_technique_passes(self):
        """Legitimate 'resolve' as technique (not software) should pass."""
        beat = {
            **self.valid_beat,
            "department_findings": {
                "7": [{
                    "term": "slow resolve using a dissolve",
                    "status": "OBSERVED",
                    "observed": "Scene resolves with slow dissolve",
                    "evidence": [{"frame": 0, "time": 0.0}],
                    "inferred_purpose": "Calm transition",
                    "alternatives": ["hard cut"],
                    "contraindication": None,
                    "confidence": "HIGH"
                }]
            }
        }
        result = validate_beat(beat)
        self.assertEqual(result["status"], "OK", f"Legitimate resolve technique rejected: {result.get('reason')}")

    def test_bool_start_time_rejected(self):
        beat = {**self.valid_beat, "start_time": True}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("start_time must be finite number", result["reason"])

    def test_bool_frame_rejected(self):
        beat = {**self.valid_beat, "evidence": [{"frame": True, "time": 0.0}]}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("frame must be int", result["reason"])

    def test_nan_start_time_rejected(self):
        beat = {**self.valid_beat, "start_time": float("nan")}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("start_time must be finite number", result["reason"])

    def test_inf_end_time_rejected(self):
        beat = {**self.valid_beat, "end_time": float("inf")}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("end_time must be finite number", result["reason"])

    def test_non_dict_input_returns_error(self):
        result = validate_beat("not a dict")
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Input must be a dict", result["reason"])

    def test_non_dict_list_input_returns_error(self):
        result = validate_beat([1, 2, 3])
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Input must be a dict", result["reason"])

    def test_list_purpose_returns_error_not_crash(self):
        beat = {**self.valid_beat, "purpose": ["ESTABLISH"]}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Invalid purpose", result["reason"])

    def test_list_method_returns_error_not_crash(self):
        beat = {**self.valid_beat, "how_animated": {"method": ["CAMERA_ONLY"], "notes": "test"}}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Invalid animation method", result["reason"])

    def test_list_status_returns_error_not_crash(self):
        beat = {**self.valid_beat, "reproduction": {"status": ["EXISTING_PRESET"], "artwork_needed": [], "simplest_method": "test"}}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Invalid reproduction status", result["reason"])

    def test_list_verification_status_returns_error_not_crash(self):
        beat = {**self.valid_beat, "verification_status": ["FRAME_CHECKED"]}
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Invalid verification_status", result["reason"])

    def test_list_finding_status_returns_error_not_crash(self):
        beat = {
            **self.valid_beat,
            "department_findings": {
                "1": [{
                    "term": "test",
                    "status": ["OBSERVED"],
                    "observed": "test",
                    "evidence": [{"frame": 0, "time": 0.0}],
                    "inferred_purpose": None,
                    "alternatives": [],
                    "contraindication": None,
                    "confidence": "HIGH"
                }]
            }
        }
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("status invalid", result["reason"])

    def test_list_finding_confidence_returns_error_not_crash(self):
        beat = {
            **self.valid_beat,
            "department_findings": {
                "1": [{
                    "term": "test",
                    "status": "OBSERVED",
                    "observed": "test",
                    "evidence": [{"frame": 0, "time": 0.0}],
                    "inferred_purpose": None,
                    "alternatives": [],
                    "contraindication": None,
                    "confidence": ["HIGH"]
                }]
            }
        }
        result = validate_beat(beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("confidence invalid", result["reason"])


class TestBeatPrompt(unittest.TestCase):
    """Tests for beat_prompt function."""

    def test_beat_prompt_returns_dict_with_prompt_and_schema_hint(self):
        shot_context = {
            "video_id": "vid1",
            "beat_id": "b1",
            "start_time": 0.0,
            "end_time": 5.0,
            "shot_description": "Wide landscape, slow zoom"
        }
        audio_evidence = {
            "narration": "UNAVAILABLE",
            "music": "Ambient drone",
            "sfx": "Wind",
            "sync_with_cut": "UNKNOWN"
        }
        result = beat_prompt(shot_context, audio_evidence)
        self.assertIn("prompt", result)
        self.assertIn("schema_hint", result)
        self.assertIsInstance(result["prompt"], str)
        self.assertIsInstance(result["schema_hint"], str)

    def test_beat_prompt_contains_context_info(self):
        shot_context = {
            "video_id": "vid1",
            "beat_id": "b1",
            "start_time": 0.0,
            "end_time": 5.0,
            "shot_description": "Wide landscape, slow zoom"
        }
        audio_evidence = {
            "narration": "UNAVAILABLE",
            "music": "Ambient drone",
            "sfx": "Wind",
            "sync_with_cut": "UNKNOWN"
        }
        result = beat_prompt(shot_context, audio_evidence)
        prompt = result["prompt"]
        self.assertIn("vid1", prompt)
        self.assertIn("b1", prompt)
        self.assertIn("0.0s - 5.0s", prompt)
        self.assertIn("Wide landscape, slow zoom", prompt)
        self.assertIn("narration=UNAVAILABLE", prompt)
        self.assertIn("music=Ambient drone", prompt)
        self.assertIn("sfx=Wind", prompt)
        self.assertIn("sync_with_cut=UNKNOWN", prompt)

    def test_beat_prompt_contains_six_questions(self):
        shot_context = {"video_id": "vid1", "beat_id": "b1", "start_time": 0.0, "end_time": 5.0, "shot_description": "Test"}
        audio_evidence = {"narration": "UNAVAILABLE", "music": "UNAVAILABLE", "sfx": "UNAVAILABLE", "sync_with_cut": "UNKNOWN"}
        result = beat_prompt(shot_context, audio_evidence)
        prompt = result["prompt"]
        self.assertIn("1. What is the storytelling beat", prompt)
        self.assertIn("2. How was it filmed", prompt)
        self.assertIn("3. How was it animated", prompt)
        self.assertIn("4. What sound is present", prompt)
        self.assertIn("5. Why might this beat work", prompt)
        self.assertIn("6. How reproducible", prompt)

    def test_beat_prompt_mentions_required_fields(self):
        shot_context = {"video_id": "vid1", "beat_id": "b1", "start_time": 0.0, "end_time": 5.0, "shot_description": "Test"}
        audio_evidence = {"narration": "UNAVAILABLE", "music": "UNAVAILABLE", "sfx": "UNAVAILABLE", "sync_with_cut": "UNKNOWN"}
        result = beat_prompt(shot_context, audio_evidence)
        prompt = result["prompt"]
        self.assertIn("observed", prompt)
        self.assertIn("inferred", prompt)
        self.assertIn("counterexample", prompt)
        self.assertIn("evidence", prompt)
        self.assertIn("ESTABLISH", prompt)
        self.assertIn("REVEAL", prompt)
        self.assertIn("POSE_SWAP", prompt)
        self.assertIn("CAMERA_ONLY", prompt)

    def test_schema_hint_contains_schema(self):
        shot_context = {"video_id": "vid1", "beat_id": "b1", "start_time": 0.0, "end_time": 5.0, "shot_description": "Test"}
        audio_evidence = {"narration": "UNAVAILABLE", "music": "UNAVAILABLE", "sfx": "UNAVAILABLE", "sync_with_cut": "UNKNOWN"}
        result = beat_prompt(shot_context, audio_evidence)
        schema_hint = result["schema_hint"]
        self.assertIn("BeatDict schema", schema_hint)
        self.assertIn("video_id", schema_hint)
        self.assertIn("department_findings", schema_hint)


class TestParseBeat(unittest.TestCase):
    """Tests for parse_beat function."""

    def setUp(self):
        self.valid_json = '''{
            "video_id": "vid1", "beat_id": "b1", "start_time": 0.0, "end_time": 5.0,
            "purpose": "ESTABLISH",
            "how_filmed": {"shot_scale": "WS", "angle": "EYE", "framing": "CENTER", "camera_movement": "STATIC", "cut_type": "HARD", "composition": "RULE_OF_THIRDS"},
            "how_animated": {"method": "CAMERA_ONLY", "notes": "Slow zoom in"},
            "sound": {"narration": "UNAVAILABLE", "silence": "UNKNOWN", "ambience": "UNAVAILABLE", "sfx": "UNAVAILABLE", "music": "UNAVAILABLE", "sync_with_cut": "UNKNOWN"},
            "observed": ["Wide shot of landscape"],
            "inferred": [{"claim": "Sets the mood", "confidence": "MEDIUM", "based_on": ["Wide shot of landscape"]}],
            "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use preset 'landscape_establish'"},
            "counterexample": "None",
            "evidence": [{"frame": 0, "time": 0.0}, {"frame": 150, "time": 5.0}]
        }'''

    def test_parse_valid_json_returns_ok(self):
        result = parse_beat(self.valid_json, validate_beat)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["beat"]["video_id"], "vid1")
        self.assertEqual(result["beat"]["purpose"], "ESTABLISH")

    def test_parse_invalid_json_returns_error(self):
        result = parse_beat("not json", validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Failed to parse JSON", result["reason"])

    def test_parse_observed_contains_inferred_mixed_returns_error(self):
        text = '''{"observed": ["Wide shot", {"claim": "Mood", "confidence": "HIGH", "based_on": []}], "inferred": []}'''
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Observed contains non-string items", result["reason"])

    def test_parse_inferred_missing_claim_returns_error(self):
        text = '''{"observed": [], "inferred": [{"confidence": "HIGH", "based_on": []}]}'''
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Inferred item missing required keys: claim", result["reason"])

    def test_parse_invalid_purpose_returns_error(self):
        text = self.valid_json.replace('"purpose": "ESTABLISH"', '"purpose": "INVALID"')
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Invalid purpose: INVALID", result["reason"])

    def test_parse_json_in_markdown_code_block(self):
        text = f"```json\n{self.valid_json}\n```"
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "OK")

    def test_parse_json_with_surrounding_text(self):
        text = f"Here is the beat:\n{self.valid_json}\nEnd of beat."
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "OK")

    def test_parse_non_dict_json_returns_error(self):
        result = parse_beat("[]", validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Parsed JSON is not an object", result["reason"])

    def test_parse_audio_unavailable_sound_finding_not_unknown_returns_error(self):
        beat = json.loads(self.valid_json)
        beat["sound"]["narration"] = "UNAVAILABLE"
        beat["department_findings"] = {
            "13": [{
                "term": "ambience",
                "status": "OBSERVED",
                "observed": "Wind sound",
                "evidence": [{"frame": 0, "time": 0.0}],
                "inferred_purpose": None,
                "alternatives": [],
                "contraindication": None,
                "confidence": "HIGH"
            }]
        }
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Audio UNAVAILABLE but sound finding status is not UNKNOWN", result["reason"])

    def test_parse_audio_unavailable_sound_finding_has_observed_text_returns_error(self):
        beat = json.loads(self.valid_json)
        beat["sound"]["narration"] = "UNAVAILABLE"
        beat["department_findings"] = {
            "13": [{
                "term": "ambience",
                "status": "UNKNOWN",
                "observed": "Wind sound",
                "evidence": [],
                "inferred_purpose": None,
                "alternatives": [],
                "contraindication": None,
                "confidence": "LOW"
            }]
        }
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Audio UNAVAILABLE but sound finding has observed text", result["reason"])

    def test_parse_audio_unavailable_sound_finding_unknown_no_observed_valid(self):
        beat = json.loads(self.valid_json)
        beat["sound"]["narration"] = "UNAVAILABLE"
        beat["department_findings"] = {
            "13": [{
                "term": "ambience",
                "status": "UNKNOWN",
                "observed": "",
                "evidence": [],
                "inferred_purpose": None,
                "alternatives": [],
                "contraindication": None,
                "confidence": "LOW"
            }]
        }
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "OK")

    def test_parse_audio_status_unavailable_rejects_real_sound_text(self):
        """audio_status=UNAVAILABLE rejects any sound.* field with real text."""
        beat = json.loads(self.valid_json)
        beat["sound"]["narration"] = "Some narration"  # Not UNAVAILABLE/UNKNOWN
        beat["sound"]["music"] = "Ambient track"
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat, audio_status="UNAVAILABLE")
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Audio UNAVAILABLE but sound.narration has real text", result["reason"])

    def test_parse_audio_status_unavailable_allows_unknown_unavailable(self):
        """audio_status=UNAVAILABLE allows UNKNOWN/UNAVAILABLE in sound fields."""
        beat = json.loads(self.valid_json)
        beat["sound"]["narration"] = "UNKNOWN"
        beat["sound"]["music"] = "UNAVAILABLE"
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat, audio_status="UNAVAILABLE")
        self.assertEqual(result["status"], "OK")

    def test_parse_audio_status_none_ignores_model_narration(self):
        """audio_status=None does not trigger audio check even if model says UNAVAILABLE."""
        beat = json.loads(self.valid_json)
        beat["sound"]["narration"] = "UNAVAILABLE"
        beat["sound"]["music"] = "Real music track"
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat, audio_status=None)
        self.assertEqual(result["status"], "OK")

    def test_parse_forbidden_fact_in_observed_returns_error(self):
        beat = json.loads(self.valid_json)
        beat["observed"] = ["Used Adobe Premiere for editing"]
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_parse_forbidden_fact_in_inferred_claim_returns_error(self):
        beat = json.loads(self.valid_json)
        beat["inferred"] = [{"claim": "The camera lens was 50mm", "confidence": "HIGH", "based_on": []}]
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_parse_forbidden_fact_in_department_finding_returns_error(self):
        beat = json.loads(self.valid_json)
        beat["department_findings"] = {
            "5": [{
                "term": "camera setup",
                "status": "OBSERVED",
                "observed": "Used a 35mm focal length lens",
                "evidence": [{"frame": 0, "time": 0.0}],
                "inferred_purpose": None,
                "alternatives": [],
                "contraindication": None,
                "confidence": "HIGH"
            }]
        }
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_parse_forbidden_fact_in_how_animated_notes_returns_error(self):
        beat = json.loads(self.valid_json)
        beat["how_animated"]["notes"] = "Created with After Effects"
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_parse_forbidden_fact_in_simplest_method_returns_error(self):
        beat = json.loads(self.valid_json)
        beat["reproduction"]["simplest_method"] = "Edit in Premiere Pro"
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_parse_forbidden_fact_in_unknowns_returns_error(self):
        beat = json.loads(self.valid_json)
        beat["unknowns"] = ["What focal length was used"]
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_parse_forbidden_fact_in_sound_field_returns_error(self):
        beat = json.loads(self.valid_json)
        beat["sound"]["music"] = "Edited with DaVinci Resolve"
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_parse_forbidden_fact_in_how_filmed_field_returns_error(self):
        beat = json.loads(self.valid_json)
        beat["how_filmed"]["camera_movement"] = "Shot on a 50mm focal length lens"
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_parse_assertion_form_davinci_resolve_was_used(self):
        beat = json.loads(self.valid_json)
        beat["how_animated"]["notes"] = "DaVinci Resolve was used for color grading"
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_parse_assertion_form_50mm_lens(self):
        beat = json.loads(self.valid_json)
        beat["how_filmed"]["angle"] = "50mm lens used for this shot"
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("forbidden fact assertion", result["reason"])

    def test_parse_audio_status_unavailable_checks_all_departments(self):
        """audio_status=UNAVAILABLE checks sound findings in all departments, not just 13."""
        beat = json.loads(self.valid_json)
        beat["sound"]["narration"] = "UNAVAILABLE"
        # Put sound finding in department 5 (camera) instead of 13
        beat["department_findings"] = {
            "5": [{
                "term": "audio sync",
                "status": "OBSERVED",
                "observed": "Audio synced to cut",
                "evidence": [{"frame": 0, "time": 0.0}],
                "inferred_purpose": None,
                "alternatives": [],
                "contraindication": None,
                "confidence": "HIGH"
            }]
        }
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat, audio_status="UNAVAILABLE")
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Audio UNAVAILABLE but sound finding status is not UNKNOWN", result["reason"])

    def test_parse_non_string_input_returns_error(self):
        result = parse_beat(None, validate_beat)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Input text must be a string", result["reason"])

    def test_parse_whitespace_only_sound_text_treated_as_empty(self):
        """Whitespace-only sound text should not trigger audio error."""
        beat = json.loads(self.valid_json)
        beat["sound"]["narration"] = "   "  # whitespace only
        text = json.dumps(beat)
        result = parse_beat(text, validate_beat, audio_status="UNAVAILABLE")
        self.assertEqual(result["status"], "OK")


if __name__ == "__main__":
    unittest.main()
