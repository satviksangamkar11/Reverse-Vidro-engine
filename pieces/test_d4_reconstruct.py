import unittest
import copy
from d4_reconstruct import reconstruct_sequence, verify_reconstruction

class TestReconstructSequence(unittest.TestCase):
    """Tests for reconstruct_sequence function."""
    
    def setUp(self):
        # Department findings are now lists of finding dicts
        self.sample_beats = [
            {
                "beat_id": "b1",
                "information_conveyed": "Protagonist discovers hidden letter",
                "inferred_purpose": "Establish mystery hook",
                "confidence": 0.9,
                "sequence_pattern": "withhold_reveal",
                "department_findings": {
                    "1": [{"status": "OBSERVED", "start_frame": 100, "end_frame": 250, "frame": 100, "term": "shot timing", "observed": "shot timing", "evidence": [{"frame": 100, "time": 4.0}], "inferred_purpose": None, "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "4": [{"status": "OBSERVED", "term": "Close-up on hands", "observed": "Close-up on hands", "evidence": [{"frame": 100, "time": 4.0}], "inferred_purpose": "Focus on tactile discovery", "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "5": [{"status": "OBSERVED", "term": "Warm key light", "observed": "Warm key light", "evidence": [{"frame": 100, "time": 4.0}], "inferred_purpose": "Create intimate mood", "alternatives": [], "contraindication": None, "confidence": "MEDIUM"}],
                    "6": [{"status": "OBSERVED", "term": "Shallow depth of field", "observed": "Shallow depth of field", "evidence": [{"frame": 100, "time": 4.0}], "inferred_purpose": "Isolate subject", "alternatives": [], "contraindication": None, "confidence": "MEDIUM"}],
                    "7": [{"status": "OBSERVED", "term": "Static camera", "observed": "Static camera", "evidence": [{"frame": 100, "time": 4.0}], "inferred_purpose": "Hold attention on action", "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "8": [{"status": "OBSERVED", "term": "Trembling fingers", "observed": "Trembling fingers", "evidence": [{"frame": 100, "time": 4.0}], "inferred_purpose": "Show nervous anticipation", "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "9": [{"status": "NOT_OBSERVED", "term": "Facial expression", "observed": "", "evidence": [], "inferred_purpose": None, "alternatives": [], "contraindication": None, "confidence": "LOW", "examined_basis": "Face not in frame"}],
                    "10": [{"status": "OBSERVED", "term": "Practical prop letter", "observed": "Practical prop letter", "evidence": [{"frame": 100, "time": 4.0}], "inferred_purpose": "Ground the mystery in tangible object", "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "11": [{"status": "NOT_OBSERVED", "term": "Visual effect", "observed": "", "evidence": [], "inferred_purpose": None, "alternatives": [], "contraindication": None, "confidence": "LOW", "examined_basis": "No VFX apparent"}],
                    "12": [{"status": "OBSERVED", "term": "Diegetic paper rustle", "observed": "Diegetic paper rustle", "evidence": [{"frame": 100, "time": 4.0}], "inferred_purpose": "Enhance tactile realism", "alternatives": [], "contraindication": None, "confidence": "MEDIUM"}],
                    "13": [{"status": "OBSERVED", "term": "Paper rustle sound", "observed": "Paper rustle sound", "evidence": [{"frame": 100, "time": 4.0}], "inferred_purpose": "Auditory cue for discovery", "alternatives": [], "contraindication": None, "confidence": "MEDIUM"}],
                    "14": [{"status": "NOT_OBSERVED", "term": "Color grade", "observed": "", "evidence": [], "inferred_purpose": None, "alternatives": [], "contraindication": None, "confidence": "LOW", "examined_basis": "No grade shift"}]
                },
                "reproduction": {
                    "status": "REPRODUCIBLE",
                    "artwork_needed": ["prop_letter"],
                    "simplest_method": "Practical close-up with prop",
                    "preset_id": "preset_closeup_prop"
                },
                "unknowns": ["letter contents"]
            },
            {
                "beat_id": "b2",
                "information_conveyed": "Wide shot reveals empty room",
                "inferred_purpose": "Establish isolation",
                "confidence": 0.85,
                "sequence_pattern": "reveal_wide",
                "department_findings": {
                    "1": [{"status": "OBSERVED", "start_frame": 251, "end_frame": 400, "frame": 251, "term": "shot timing", "observed": "shot timing", "evidence": [{"frame": 251, "time": 10.0}], "inferred_purpose": None, "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "4": [{"status": "OBSERVED", "term": "Wide establishing shot", "observed": "Wide establishing shot", "evidence": [{"frame": 251, "time": 10.0}], "inferred_purpose": "Reveal environment", "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "5": [{"status": "OBSERVED", "term": "Cold ambient light", "observed": "Cold ambient light", "evidence": [{"frame": 251, "time": 10.0}], "inferred_purpose": "Convey bleakness", "alternatives": [], "contraindication": None, "confidence": "MEDIUM"}],
                    "6": [{"status": "OBSERVED", "term": "Deep focus", "observed": "Deep focus", "evidence": [{"frame": 251, "time": 10.0}], "inferred_purpose": "Show entire space", "alternatives": [], "contraindication": None, "confidence": "MEDIUM"}],
                    "7": [{"status": "OBSERVED", "term": "Slow dolly out", "observed": "Slow dolly out", "evidence": [{"frame": 251, "time": 10.0}], "inferred_purpose": "Gradual reveal", "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "8": [{"status": "NOT_OBSERVED", "term": "Performance", "observed": "", "evidence": [], "inferred_purpose": None, "alternatives": [], "contraindication": None, "confidence": "LOW", "examined_basis": "No actor in frame"}],
                    "9": [{"status": "OBSERVED", "term": "Empty space performance", "observed": "Empty space performance", "evidence": [{"frame": 251, "time": 10.0}], "inferred_purpose": "Emphasize absence", "alternatives": [], "contraindication": None, "confidence": "MEDIUM"}],
                    "10": [{"status": "OBSERVED", "term": "Production design - bare room", "observed": "Production design - bare room", "evidence": [{"frame": 251, "time": 10.0}], "inferred_purpose": "Reinforce isolation", "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "11": [{"status": "OBSERVED", "term": "Hard cut from close-up", "observed": "Hard cut from close-up", "evidence": [{"frame": 251, "time": 10.0}], "inferred_purpose": "Jarring transition", "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "12": [{"status": "OBSERVED", "term": "Silence", "observed": "Silence", "evidence": [{"frame": 251, "time": 10.0}], "inferred_purpose": "Heighten tension", "alternatives": [], "contraindication": None, "confidence": "MEDIUM"}],
                    "13": [{"status": "OBSERVED", "term": "Room tone silence", "observed": "Room tone silence", "evidence": [{"frame": 251, "time": 10.0}], "inferred_purpose": "Auditory vacuum", "alternatives": [], "contraindication": None, "confidence": "MEDIUM"}],
                    "14": [{"status": "OBSERVED", "term": "Color grade shift to cool", "observed": "Color grade shift to cool", "evidence": [{"frame": 251, "time": 10.0}], "inferred_purpose": "Visual temperature drop", "alternatives": [], "contraindication": None, "confidence": "HIGH"}]
                },
                "reproduction": {
                    "status": "REPRODUCIBLE",
                    "artwork_needed": ["set_bare_room"],
                    "simplest_method": "Wide shot on empty set",
                    "preset_id": "preset_wide_establishing"
                },
                "unknowns": []
            },
            {
                "beat_id": "b3",
                "information_conveyed": "Protagonist reacts with shock",
                "inferred_purpose": "Payoff emotional impact",
                "confidence": 0.88,
                "sequence_pattern": "reaction_hold",
                "department_findings": {
                    "1": [{"status": "OBSERVED", "start_frame": 401, "end_frame": 550, "frame": 401, "term": "shot timing", "observed": "shot timing", "evidence": [{"frame": 401, "time": 16.0}], "inferred_purpose": None, "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "4": [{"status": "OBSERVED", "term": "Medium close-up face", "observed": "Medium close-up face", "evidence": [{"frame": 401, "time": 16.0}], "inferred_purpose": "Capture micro-expressions", "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "5": [{"status": "OBSERVED", "term": "Key light with fill", "observed": "Key light with fill", "evidence": [{"frame": 401, "time": 16.0}], "inferred_purpose": "Model face for emotion", "alternatives": [], "contraindication": None, "confidence": "MEDIUM"}],
                    "6": [{"status": "OBSERVED", "term": "Shallow depth of field", "observed": "Shallow depth of field", "evidence": [{"frame": 401, "time": 16.0}], "inferred_purpose": "Isolate face", "alternatives": [], "contraindication": None, "confidence": "MEDIUM"}],
                    "7": [{"status": "OBSERVED", "term": "Locked off", "observed": "Locked off", "evidence": [{"frame": 401, "time": 16.0}], "inferred_purpose": "Stabilize for performance", "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "8": [{"status": "OBSERVED", "term": "Micro-expressions of shock", "observed": "Micro-expressions of shock", "evidence": [{"frame": 401, "time": 16.0}], "inferred_purpose": "Convey internal realization", "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "9": [{"status": "OBSERVED", "term": "Breath hold", "observed": "Breath hold", "evidence": [{"frame": 401, "time": 16.0}], "inferred_purpose": "Physicalize shock", "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "10": [{"status": "NOT_OBSERVED", "term": "Practical effect", "observed": "", "evidence": [], "inferred_purpose": None, "alternatives": [], "contraindication": None, "confidence": "LOW", "examined_basis": "No practical effect"}],
                    "11": [{"status": "OBSERVED", "term": "Hold on reaction", "observed": "Hold on reaction", "evidence": [{"frame": 401, "time": 16.0}], "inferred_purpose": "Let emotion land", "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "12": [{"status": "OBSERVED", "term": "Heartbeat sound design", "observed": "Heartbeat sound design", "evidence": [{"frame": 401, "time": 16.0}], "inferred_purpose": "Internalize tension", "alternatives": [], "contraindication": None, "confidence": "MEDIUM"}],
                    "13": [{"status": "OBSERVED", "term": "Heartbeat SFX", "observed": "Heartbeat SFX", "evidence": [{"frame": 401, "time": 16.0}], "inferred_purpose": "Subjective audio perspective", "alternatives": [], "contraindication": None, "confidence": "MEDIUM"}],
                    "14": [{"status": "NOT_EXAMINED", "term": "Color grade", "observed": "", "evidence": [], "inferred_purpose": None, "alternatives": [], "contraindication": None, "confidence": "LOW"}]
                },
                "reproduction": {
                    "status": "NEED_NEW",
                    "artwork_needed": ["actor_performance"],
                    "simplest_method": "Direct performance capture",
                    "preset_id": "preset_reaction_hold"
                },
                "unknowns": ["internal thought"]
            }
        ]
        self.audio_evidence_available = {
            "status": "AVAILABLE",
            "format": "stereo",
            "sample_rate": 48000,
            "duration": 5.5
        }
        self.audio_evidence_unavailable = {
            "status": "UNAVAILABLE"
        }
    
    def test_reconstruct_sequence_basic_structure(self):
        """Test that reconstruction returns all 9 required keys."""
        result = reconstruct_sequence(self.sample_beats, self.audio_evidence_available)
        expected_keys = {
            "narrative_progression", "shots_and_transitions", "performance",
            "sound_image", "techniques", "why_it_may_work",
            "simplest_reproduction", "unknowns", "relationships"
        }
        self.assertEqual(set(result.keys()), expected_keys)
    
    def test_narrative_progression_ordered_by_beat_order(self):
        """Test narrative_progression uses information_conveyed in supplied beat order."""
        result = reconstruct_sequence(self.sample_beats, self.audio_evidence_available)
        prog = result["narrative_progression"]
        self.assertEqual(len(prog), 3)
        self.assertEqual(prog[0]["beat_id"], "b1")
        self.assertEqual(prog[0]["summary"], "Protagonist discovers hidden letter")
        self.assertEqual(prog[1]["beat_id"], "b2")
        self.assertEqual(prog[1]["summary"], "Wide shot reveals empty room")
        self.assertEqual(prog[2]["beat_id"], "b3")
        self.assertEqual(prog[2]["summary"], "Protagonist reacts with shock")
    
    def test_shots_and_transitions_includes_dept_4_5_6_7(self):
        """Test shots_and_transitions includes terms from departments 4,5,6,7."""
        result = reconstruct_sequence(self.sample_beats, self.audio_evidence_available)
        shots = result["shots_and_transitions"]
        self.assertIn("b1", shots)
        self.assertIn("b2", shots)
        self.assertIn("b3", shots)
        
        b1_terms = shots["b1"]["terms"]
        self.assertIn("dept_4", b1_terms)
        self.assertIn("dept_5", b1_terms)
        self.assertIn("dept_6", b1_terms)
        self.assertIn("dept_7", b1_terms)
        self.assertEqual(b1_terms["dept_4"], "Close-up on hands")
        self.assertEqual(b1_terms["dept_5"], "Warm key light")
        self.assertEqual(b1_terms["dept_6"], "Shallow depth of field")
        self.assertEqual(b1_terms["dept_7"], "Static camera")
    
    def test_performance_includes_dept_8_9(self):
        """Test performance includes departments 8 and 9 when OBSERVED."""
        result = reconstruct_sequence(self.sample_beats, self.audio_evidence_available)
        perf = result["performance"]
        self.assertIn("b1", perf)
        self.assertIn("dept_8", perf["b1"])
        self.assertNotIn("dept_9", perf["b1"])  # NOT_OBSERVED
        
        self.assertIn("b2", perf)
        self.assertNotIn("dept_8", perf["b2"])  # NOT_OBSERVED
        self.assertIn("dept_9", perf["b2"])
        
        self.assertIn("b3", perf)
        self.assertIn("dept_8", perf["b3"])
        self.assertIn("dept_9", perf["b3"])
    
    def test_sound_image_unavailable_when_audio_unavailable(self):
        """Test sound_image is exactly {'status':'UNAVAILABLE'} when audio unavailable."""
        result = reconstruct_sequence(self.sample_beats, self.audio_evidence_unavailable)
        sound = result["sound_image"]
        self.assertEqual(sound, {"status": "UNAVAILABLE"})
    
    def test_sound_image_includes_dept13_and_audio_when_available(self):
        """Test sound_image includes dept 13 findings and audio evidence when available."""
        result = reconstruct_sequence(self.sample_beats, self.audio_evidence_available)
        sound = result["sound_image"]
        self.assertNotEqual(sound.get("status"), "UNAVAILABLE")
        self.assertIn("dept_13_findings", sound)
        self.assertEqual(len(sound["dept_13_findings"]), 3)
        self.assertIn("audio_evidence", sound)
        self.assertEqual(sound["audio_evidence"]["status"], "AVAILABLE")
    
    def test_techniques_includes_dept_10_11_12_14(self):
        """Test techniques includes departments 10,11,12,14 when OBSERVED."""
        result = reconstruct_sequence(self.sample_beats, self.audio_evidence_available)
        tech = result["techniques"]
        self.assertIn("b1", tech)
        self.assertIn("dept_10", tech["b1"])
        self.assertIn("dept_12", tech["b1"])
        self.assertNotIn("dept_11", tech["b1"])  # NOT_OBSERVED
        self.assertNotIn("dept_14", tech["b1"])  # NOT_OBSERVED
        
        self.assertIn("b2", tech)
        self.assertIn("dept_10", tech["b2"])
        self.assertIn("dept_11", tech["b2"])
        self.assertIn("dept_12", tech["b2"])
        self.assertIn("dept_14", tech["b2"])
        
        self.assertIn("b3", tech)
        self.assertIn("dept_11", tech["b3"])
        self.assertIn("dept_12", tech["b3"])
        self.assertNotIn("dept_10", tech["b3"])  # NOT_OBSERVED
        self.assertNotIn("dept_14", tech["b3"])  # NOT_EXAMINED
    
    def test_why_it_may_work_includes_hypotheses_from_findings(self):
        """Test why_it_may_work contains hypotheses from each finding's inferred_purpose."""
        result = reconstruct_sequence(self.sample_beats, self.audio_evidence_available)
        why = result["why_it_may_work"]
        # Should have at least one per finding with inferred_purpose (many) plus cross-beat patterns
        self.assertGreaterEqual(len(why), 10)
        
        # Check that each entry has hypothesis, based_on_beat_ids, confidence
        for entry in why:
            self.assertIn("hypothesis", entry)
            self.assertIn("based_on_beat_ids", entry)
            self.assertIn("confidence", entry)
            self.assertIsInstance(entry["based_on_beat_ids"], list)
            self.assertGreaterEqual(entry["confidence"], 0.0)
            self.assertLessEqual(entry["confidence"], 1.0)
        
        # Check cross-beat pattern hypotheses exist
        pattern_hyps = [w for w in why if len(w["based_on_beat_ids"]) == 2]
        self.assertGreaterEqual(len(pattern_hyps), 2)
    
    def test_simplest_reproduction_preserves_need_new(self):
        """Test simplest_reproduction preserves NEED_NEW status."""
        result = reconstruct_sequence(self.sample_beats, self.audio_evidence_available)
        repro = result["simplest_reproduction"]
        self.assertEqual(repro["b1"]["status"], "REPRODUCIBLE")
        self.assertEqual(repro["b2"]["status"], "REPRODUCIBLE")
        self.assertEqual(repro["b3"]["status"], "NEED_NEW")
        self.assertEqual(repro["b3"]["artwork_needed"], ["actor_performance"])
        self.assertEqual(repro["b3"]["simplest_method"], "Direct performance capture")
    
    def test_unknowns_union_of_beat_unknowns_and_not_observed(self):
        """Test unknowns includes beat unknowns and NOT_OBSERVED/UNKNOWN/NOT_EXAMINED findings."""
        result = reconstruct_sequence(self.sample_beats, self.audio_evidence_available)
        unknowns = result["unknowns"]
        self.assertIn("letter contents", unknowns)
        self.assertIn("internal thought", unknowns)
        self.assertIn("dept_9: not_observed", unknowns)  # b1 dept 9
        self.assertIn("dept_8: not_observed", unknowns)  # b2 dept 8
        self.assertIn("dept_10: not_observed", unknowns)  # b3 dept 10
        self.assertIn("dept_11: not_observed", unknowns)  # b1 dept 11
        self.assertIn("dept_14: not_observed", unknowns)  # b1 dept 14
        self.assertIn("dept_14: not examined", unknowns)  # b3 dept 14 NOT_EXAMINED
    
    def test_relationships_consecutive_beats_with_pattern(self):
        """Test relationships links consecutive beats with sequence_pattern."""
        result = reconstruct_sequence(self.sample_beats, self.audio_evidence_available)
        rels = result["relationships"]
        self.assertEqual(len(rels), 2)
        self.assertEqual(rels[0]["from_beat"], "b1")
        self.assertEqual(rels[0]["to_beat"], "b2")
        self.assertEqual(rels[0]["pattern"], "withhold_reveal")
        self.assertEqual(rels[1]["from_beat"], "b2")
        self.assertEqual(rels[1]["to_beat"], "b3")
        self.assertEqual(rels[1]["pattern"], "reveal_wide")
    
    def test_empty_beats_returns_empty_reconstruction(self):
        """Test empty beats list returns empty reconstruction."""
        result = reconstruct_sequence([], self.audio_evidence_available)
        self.assertEqual(result["narrative_progression"], [])
        self.assertEqual(result["shots_and_transitions"], {})
        self.assertEqual(result["relationships"], [])


class TestVerifyReconstruction(unittest.TestCase):
    """Tests for verify_reconstruction function."""
    
    def setUp(self):
        self.sample_beats = [
            {
                "beat_id": "b1",
                "information_conveyed": "Beat 1",
                "inferred_purpose": "Hypothesis 1",
                "confidence": 0.9,
                "sequence_pattern": "pattern1",
                "department_findings": {
                    "1": [{"status": "OBSERVED", "start_frame": 100, "end_frame": 200, "frame": 100, "term": "shot timing", "observed": "shot timing", "evidence": [{"frame": 100, "time": 4.0}], "inferred_purpose": None, "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "4": [{"status": "OBSERVED", "term": "Shot type A", "observed": "Shot type A", "evidence": [{"frame": 100, "time": 4.0}], "inferred_purpose": "Hypothesis A", "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "13": [{"status": "OBSERVED", "term": "Sound A", "observed": "Sound A", "evidence": [{"frame": 100, "time": 4.0}], "inferred_purpose": "Hypothesis Sound", "alternatives": [], "contraindication": None, "confidence": "MEDIUM"}]
                },
                "reproduction": {
                    "status": "REPRODUCIBLE",
                    "artwork_needed": [],
                    "simplest_method": "Method A",
                    "preset_id": "preset_a"
                },
                "unknowns": []
            },
            {
                "beat_id": "b2",
                "information_conveyed": "Beat 2",
                "inferred_purpose": "Hypothesis 2",
                "confidence": 0.8,
                "sequence_pattern": "pattern2",
                "department_findings": {
                    "1": [{"status": "OBSERVED", "start_frame": 201, "end_frame": 300, "frame": 201, "term": "shot timing", "observed": "shot timing", "evidence": [{"frame": 201, "time": 8.0}], "inferred_purpose": None, "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "4": [{"status": "OBSERVED", "term": "Shot type B", "observed": "Shot type B", "evidence": [{"frame": 201, "time": 8.0}], "inferred_purpose": "Hypothesis B", "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                    "13": [{"status": "NOT_OBSERVED", "term": "Sound", "observed": "", "evidence": [], "inferred_purpose": None, "alternatives": [], "contraindication": None, "confidence": "LOW", "examined_basis": "No sound"}]
                },
                "reproduction": {
                    "status": "REPRODUCIBLE",
                    "artwork_needed": [],
                    "simplest_method": "Method B",
                    "preset_id": "preset_b"
                },
                "unknowns": []
            }
        ]
        self.audio_available = {"status": "AVAILABLE"}
        self.audio_unavailable = {"status": "UNAVAILABLE"}
    
    def test_verify_ok_for_valid_reconstruction(self):
        """Test verify returns ok=True for valid reconstruction."""
        recon = reconstruct_sequence(self.sample_beats, self.audio_available)
        result = verify_reconstruction(recon, self.sample_beats)
        self.assertTrue(result["ok"])
        self.assertTrue(result["structural_ok"])
        self.assertEqual(result["semantic_status"], "NOT_VERIFIED")
        self.assertEqual(result["problems"], [])
    
    def test_verify_fails_missing_evidence_for_observed_claim(self):
        """Test verify fails when OBSERVED claim lacks evidence frame/time."""
        beats_no_evidence = [{
            "beat_id": "b1",
            "information_conveyed": "Beat 1",
            "inferred_purpose": "Hypothesis 1",
            "confidence": 0.9,
            "sequence_pattern": "pattern1",
            "department_findings": {
                "1": [{"status": "OBSERVED", "start_frame": 100, "end_frame": 200, "term": "shot timing", "observed": "shot timing", "evidence": [{"frame": 100, "time": 4.0}], "inferred_purpose": None, "alternatives": [], "contraindication": None, "confidence": "HIGH"}],
                "4": [{"status": "OBSERVED", "term": "Shot type A", "observed": "Shot type A", "evidence": [], "inferred_purpose": "Hypothesis A", "alternatives": [], "contraindication": None, "confidence": "HIGH"}]  # No evidence
            },
            "reproduction": {"status": "REPRODUCIBLE", "artwork_needed": [], "simplest_method": "Method A", "preset_id": "preset_a"},
            "unknowns": []
        }]
        recon = reconstruct_sequence(beats_no_evidence, self.audio_available)
        result = verify_reconstruction(recon, beats_no_evidence)
        self.assertFalse(result["ok"])
        self.assertFalse(result["structural_ok"])
        self.assertTrue(any("lacks evidence" in p for p in result["problems"]))
    
    def test_verify_fails_hypothesis_in_observed_section(self):
        """Test verify fails when hypothesis appears in observed section."""
        beats = copy.deepcopy(self.sample_beats)
        # Inject hypothesis-like text into observed finding
        beats[0]["department_findings"]["4"][0]["term"] = "Shot type A suggests mystery"
        beats[0]["department_findings"]["4"][0]["observed"] = "Shot type A suggests mystery"
        recon = reconstruct_sequence(beats, self.audio_available)
        result = verify_reconstruction(recon, beats)
        self.assertFalse(result["ok"])
        self.assertTrue(any("Hypothesis-like text found in observed section" in p for p in result["problems"]))
    
    def test_verify_fails_sound_claim_when_audio_unavailable(self):
        """Test verify fails when sound claim exists but audio is UNAVAILABLE."""
        beats = copy.deepcopy(self.sample_beats)
        beats[0]["department_findings"]["13"] = [{"status": "OBSERVED", "term": "Sound present", "observed": "Sound present", "evidence": [{"frame": 100, "time": 4.0}], "inferred_purpose": "Hypothesis", "alternatives": [], "contraindication": None, "confidence": "MEDIUM"}]
        recon = reconstruct_sequence(beats, self.audio_unavailable)
        # Manually corrupt sound_image to have extra fields
        recon["sound_image"] = {"status": "UNAVAILABLE", "extra": "field"}
        result = verify_reconstruction(recon, beats)
        self.assertFalse(result["ok"])
        self.assertTrue(any("extra fields when status is UNAVAILABLE" in p for p in result["problems"]))
    
    def test_verify_fails_no_relationships_for_multiple_beats(self):
        """Test verify fails when >=2 beats but no relationships."""
        beats = copy.deepcopy(self.sample_beats)
        # Remove sequence_pattern so no relationships generated
        beats[0]["sequence_pattern"] = None
        beats[1]["sequence_pattern"] = None
        recon = reconstruct_sequence(beats, self.audio_available)
        result = verify_reconstruction(recon, beats)
        self.assertFalse(result["ok"])
        self.assertTrue(any("No relationships found for sequence with 2+ beats" in p for p in result["problems"]))
    
    def test_verify_fails_forbidden_assertions(self):
        """Test verify fails on editing software, lens, hidden rig, screenplay assertions."""
        beats = copy.deepcopy(self.sample_beats)
        beats[0]["department_findings"]["4"][0]["term"] = "Edited in Premiere Pro"
        beats[0]["department_findings"]["4"][0]["observed"] = "Edited in Premiere Pro"
        recon = reconstruct_sequence(beats, self.audio_available)
        result = verify_reconstruction(recon, beats)
        self.assertFalse(result["ok"])
        self.assertTrue(any("Forbidden assertion" in p and "premiere" in p.lower() for p in result["problems"]))
        
        beats[0]["department_findings"]["4"][0]["term"] = "Shot with 50mm lens"
        beats[0]["department_findings"]["4"][0]["observed"] = "Shot with 50mm lens"
        recon = reconstruct_sequence(beats, self.audio_available)
        result = verify_reconstruction(recon, beats)
        self.assertTrue(any("Forbidden assertion" in p and "lens" in p.lower() for p in result["problems"]))
        
        beats[0]["department_findings"]["4"][0]["term"] = "Hidden rig removed in post"
        beats[0]["department_findings"]["4"][0]["observed"] = "Hidden rig removed in post"
        recon = reconstruct_sequence(beats, self.audio_available)
        result = verify_reconstruction(recon, beats)
        self.assertTrue(any("Forbidden assertion" in p and "hidden rig" in p.lower() for p in result["problems"]))
        
        beats[0]["department_findings"]["4"][0]["term"] = "According to screenplay, character enters"
        beats[0]["department_findings"]["4"][0]["observed"] = "According to screenplay, character enters"
        recon = reconstruct_sequence(beats, self.audio_available)
        result = verify_reconstruction(recon, beats)
        self.assertTrue(any("Forbidden assertion" in p and "screenplay" in p.lower() for p in result["problems"]))
    
    def test_verify_fails_unknown_preset_id(self):
        """Test verify fails when preset_id not in beats' reproduction data."""
        beats = copy.deepcopy(self.sample_beats)
        recon = reconstruct_sequence(beats, self.audio_available)
        # Inject unknown preset_id
        recon["simplest_reproduction"]["b1"]["preset_id"] = "preset_unknown"
        result = verify_reconstruction(recon, beats)
        self.assertFalse(result["ok"])
        self.assertTrue(any("Unknown preset_id" in p for p in result["problems"]))
    
    def test_verify_semantic_status_audited_with_audit(self):
        """Test semantic_status becomes AUDITED_* when audit provided."""
        recon = reconstruct_sequence(self.sample_beats, self.audio_available)
        audit = {"auditor": "test", "video_id": "v1", "verdict": "PASS", "notes": "Looks good"}
        result = verify_reconstruction(recon, self.sample_beats, audit=audit)
        self.assertEqual(result["semantic_status"], "AUDITED_PASS")
    
    def test_verify_semantic_status_not_verified_without_audit(self):
        """Test semantic_status stays NOT_VERIFIED without audit."""
        recon = reconstruct_sequence(self.sample_beats, self.audio_available)
        result = verify_reconstruction(recon, self.sample_beats)
        self.assertEqual(result["semantic_status"], "NOT_VERIFIED")
    
    def test_verify_semantic_status_not_verified_even_with_invalid_audit(self):
        """Test semantic_status stays NOT_VERIFIED with invalid audit."""
        recon = reconstruct_sequence(self.sample_beats, self.audio_available)
        audit = {"auditor": "test"}  # Missing verdict
        result = verify_reconstruction(recon, self.sample_beats, audit=audit)
        self.assertEqual(result["semantic_status"], "NOT_VERIFIED")
    
    def test_verify_structural_ok_false_when_problems_exist(self):
        """Test structural_ok is False when problems exist."""
        beats = copy.deepcopy(self.sample_beats)
        beats[0]["department_findings"]["4"][0]["evidence"] = []  # Remove evidence
        recon = reconstruct_sequence(beats, self.audio_available)
        result = verify_reconstruction(recon, beats)
        self.assertFalse(result["structural_ok"])
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
