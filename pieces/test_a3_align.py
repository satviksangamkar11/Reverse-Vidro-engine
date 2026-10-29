import unittest
from unittest.mock import MagicMock
import tempfile
import a3_align


class TestAlignToCuts(unittest.TestCase):
    def test_worked_example(self):
        cut_times = [1.0, 2.5, 4.0]
        silences = [{"start": 0.8, "end": 1.2}, {"start": 3.5, "end": 4.5}]
        onsets = [
            {"time": 1.05, "rise_db": 12.0, "label": "SOUND_ONSET"},
            {"time": 3.8, "rise_db": 10.0, "label": "SOUND_ONSET"}
        ]
        speech = [
            {"start": 0.0, "end": 0.7},
            {"start": 1.3, "end": 2.0},
            {"start": 5.0, "end": 6.0}
        ]

        result = a3_align.align_to_cuts(cut_times, silences, onsets, speech, 0.25)

        self.assertEqual(result["status"], "OK")
        self.assertEqual(len(result["alignment"]), 3)

        # Cut 1.0
        a0 = result["alignment"][0]
        self.assertEqual(a0["cut"], 1.0)
        self.assertEqual(a0["near_onset"], {"time": 1.05, "rise_db": 12.0, "label": "SOUND_ONSET"})
        self.assertTrue(a0["in_silence"])
        self.assertFalse(a0["speech_active"])
        self.assertTrue(a0["speech_pause_within_tol"])
        self.assertEqual(a0["relationship"], "CO_OCCURS")

        # Cut 2.5
        a1 = result["alignment"][1]
        self.assertEqual(a1["cut"], 2.5)
        self.assertIsNone(a1["near_onset"])
        self.assertFalse(a1["in_silence"])
        self.assertFalse(a1["speech_active"])
        self.assertFalse(a1["speech_pause_within_tol"])
        self.assertEqual(a1["relationship"], "CO_OCCURS")

        # Cut 4.0
        a2 = result["alignment"][2]
        self.assertEqual(a2["cut"], 4.0)
        self.assertEqual(a2["near_onset"], {"time": 3.8, "rise_db": 10.0, "label": "SOUND_ONSET"})
        self.assertTrue(a2["in_silence"])
        self.assertFalse(a2["speech_active"])
        self.assertTrue(a2["speech_pause_within_tol"])
        self.assertEqual(a2["relationship"], "CO_OCCURS")

    def test_no_onsets_no_silences_no_speech(self):
        result = a3_align.align_to_cuts([1.0, 2.0], [], [], [], 0.25)
        self.assertEqual(result["status"], "OK")
        for a in result["alignment"]:
            self.assertIsNone(a["near_onset"])
            self.assertFalse(a["in_silence"])
            self.assertFalse(a["speech_active"])
            self.assertFalse(a["speech_pause_within_tol"])
            self.assertEqual(a["relationship"], "CO_OCCURS")

    def test_onset_outside_tol(self):
        cut_times = [1.0]
        onsets = [{"time": 2.0, "rise_db": 5.0, "label": "SOUND_ONSET"}]
        result = a3_align.align_to_cuts(cut_times, [], onsets, [], 0.25)
        self.assertIsNone(result["alignment"][0]["near_onset"])

    def test_speech_active_true(self):
        cut_times = [1.0]
        speech = [{"start": 0.5, "end": 1.5}]
        result = a3_align.align_to_cuts(cut_times, [], [], speech, 0.25)
        self.assertTrue(result["alignment"][0]["speech_active"])

    def test_speech_pause_within_tol_false_when_gap_too_large(self):
        cut_times = [2.0]
        silences = [{"start": 1.5, "end": 2.5}]
        speech = [{"start": 0.0, "end": 0.5}, {"start": 5.0, "end": 6.0}]  # gaps 1.0 and 2.5 -> after gap >2
        result = a3_align.align_to_cuts(cut_times, silences, [], speech, 0.25)
        self.assertFalse(result["alignment"][0]["speech_pause_within_tol"])

    def test_speech_pause_within_tol_true_when_cut_anywhere_in_qualifying_silence(self):
        # Cut at 3.6 in silence 3.5-4.5, speech before ends 2.0 (gap 1.5), after starts 5.0 (gap 0.5)
        # Both gaps <= 2s, so should be True regardless of distance from centre
        cut_times = [3.6]
        silences = [{"start": 3.5, "end": 4.5}]
        speech = [{"start": 0.0, "end": 2.0}, {"start": 5.0, "end": 6.0}]
        result = a3_align.align_to_cuts(cut_times, silences, [], speech, 0.25)
        self.assertTrue(result["alignment"][0]["speech_pause_within_tol"])

    def test_speech_pause_within_tol_false_when_no_speech_before(self):
        cut_times = [1.0]
        silences = [{"start": 0.5, "end": 1.5}]
        speech = [{"start": 2.0, "end": 3.0}]  # only after
        result = a3_align.align_to_cuts(cut_times, silences, [], speech, 0.25)
        self.assertFalse(result["alignment"][0]["speech_pause_within_tol"])

    def test_speech_pause_within_tol_false_when_no_speech_after(self):
        cut_times = [1.0]
        silences = [{"start": 0.5, "end": 1.5}]
        speech = [{"start": 0.0, "end": 0.4}]  # only before
        result = a3_align.align_to_cuts(cut_times, silences, [], speech, 0.25)
        self.assertFalse(result["alignment"][0]["speech_pause_within_tol"])

    def test_speech_pause_within_tol_true_at_exact_2s_gap_boundary(self):
        # Gap exactly 2.0s should count as within tolerance
        cut_times = [3.0]
        silences = [{"start": 2.0, "end": 4.0}]
        speech = [{"start": 0.0, "end": 0.0}, {"start": 6.0, "end": 7.0}]  # gaps 2.0 and 2.0
        result = a3_align.align_to_cuts(cut_times, silences, [], speech, 0.25)
        self.assertTrue(result["alignment"][0]["speech_pause_within_tol"])

    def test_speech_pause_within_tol_false_just_over_2s_gap(self):
        # Gap 2.001s should be false
        cut_times = [3.0]
        silences = [{"start": 2.0, "end": 4.0}]
        speech = [{"start": 0.0, "end": 0.0}, {"start": 6.001, "end": 7.0}]  # gaps 2.0 and 2.001
        result = a3_align.align_to_cuts(cut_times, silences, [], speech, 0.25)
        self.assertFalse(result["alignment"][0]["speech_pause_within_tol"])

    def test_near_onset_picks_nearest_of_multiple_within_tol(self):
        cut_times = [5.0]
        onsets = [
            {"time": 4.8, "rise_db": 5.0, "label": "SOUND_ONSET"},   # diff 0.2
            {"time": 5.1, "rise_db": 10.0, "label": "SOUND_ONSET"},  # diff 0.1 - nearest
            {"time": 5.2, "rise_db": 15.0, "label": "SOUND_ONSET"}   # diff 0.2
        ]
        result = a3_align.align_to_cuts(cut_times, [], onsets, [], 0.25)
        self.assertEqual(result["alignment"][0]["near_onset"]["time"], 5.1)


class TestAnalyzeAudio(unittest.TestCase):
    def setUp(self):
        self.source = "/media/clip.mp4"
        self.kind = "video"
        self.cut_times = [1.0, 2.5]
        self.now_val = 1700000000.0

        # Default mocks
        self.transcribe_fn = MagicMock(return_value={
            "status": "OK",
            "segments": [{"start": 0.0, "end": 1.0, "text": "hi", "avg_logprob": -0.5, "confidence": "OK"}],
            "language": "en"
        })
        self.extract_audio_fn = MagicMock(return_value={"status": "OK", "wav_path": "/tmp/test_out/audio.wav", "from_cache": False})
        self.energy_profile_fn = MagicMock(return_value={"status": "OK", "profile": [{"time": 0.5, "db": -20.0}], "sample_rate": 16000, "window_sec": 0.05})
        self.find_silences_fn = MagicMock(return_value={"status": "OK", "silences": []})
        self.find_onsets_fn = MagicMock(return_value={"status": "OK", "onsets": []})
        self.classify_gaps_fn = MagicMock(return_value={"status": "OK", "gaps": []})
        self.align_to_cuts_fn = MagicMock(return_value={"status": "OK", "alignment": [
            {"cut": 1.0, "near_onset": None, "in_silence": False, "speech_active": False, "speech_pause_within_tol": False, "relationship": "CO_OCCURS"},
            {"cut": 2.5, "near_onset": None, "in_silence": False, "speech_active": False, "speech_pause_within_tol": False, "relationship": "CO_OCCURS"}
        ]})
        self.write_json_atomic = MagicMock(return_value={"status": "OK"})
        self.read_json = MagicMock(return_value=None)
        self.path_exists = MagicMock(return_value=False)
        self.get_size_mtime = MagicMock(return_value={"status": "OK", "size": 1000, "mtime": 1234567890.0})
        self.cache_get = MagicMock(return_value=None)
        self.cache_set = MagicMock()
        self.now = MagicMock(return_value=self.now_val)

    def call_analyze(self, folder=None, **overrides):
        if folder is None:
            folder = tempfile.mkdtemp()
        mocks = {
            "transcribe_fn": self.transcribe_fn,
            "extract_audio_fn": self.extract_audio_fn,
            "energy_profile_fn": self.energy_profile_fn,
            "find_silences_fn": self.find_silences_fn,
            "find_onsets_fn": self.find_onsets_fn,
            "classify_gaps_fn": self.classify_gaps_fn,
            "align_to_cuts_fn": self.align_to_cuts_fn,
            "write_json_atomic": self.write_json_atomic,
            "read_json": self.read_json,
            "path_exists": self.path_exists,
            "get_size_mtime": self.get_size_mtime,
            "cache_get": self.cache_get,
            "cache_set": self.cache_set,
            "now": self.now,
        }
        mocks.update(overrides)
        return a3_align.analyze_audio(
            self.source, self.kind, self.cut_times, folder,
            **mocks
        )

    def test_happy_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.call_analyze(folder=tmpdir)

            # Verify all sub-functions called
            self.extract_audio_fn.assert_called_once()
            self.energy_profile_fn.assert_called_once()
            self.find_silences_fn.assert_called_once()
            self.find_onsets_fn.assert_called_once()
            self.transcribe_fn.assert_called_once()
            self.classify_gaps_fn.assert_called_once()
            self.align_to_cuts_fn.assert_called_once()
            self.write_json_atomic.assert_called_once()

            # Verify structure
            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["audio_status"], "OK")
            self.assertEqual(result["transcript"]["status"], "OK")
            self.assertEqual(result["transcript"]["language"], "en")
            self.assertEqual(len(result["transcript"]["segments"]), 1)
            self.assertEqual(result["silences"], [])
            self.assertEqual(result["gaps"], [])
            self.assertEqual(result["onsets"], [])
            self.assertEqual(len(result["cut_alignment"]), 2)
            self.assertEqual(result["uncertainty_notes"], [])
            self.assertFalse(result["from_cache"])
            self.assertEqual(result["cut_times"], self.cut_times)
            self.assertEqual(result["generated_at"], self.now_val)

            # Verify written evidence matches expected structure
            written_path, written_data = self.write_json_atomic.call_args[0]
            self.assertEqual(written_path, f"{tmpdir}/audio_evidence.json")
            self.assertEqual(written_data["status"], "OK")
            self.assertEqual(written_data["audio_status"], "OK")

    def test_extract_audio_unavailable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.extract_audio_fn.return_value = {"status": "UNAVAILABLE"}
            result = self.call_analyze(folder=tmpdir)

            self.assertEqual(result["status"], "UNAVAILABLE")
            self.assertEqual(result["audio_status"], "UNAVAILABLE")
            self.assertEqual(result["transcript"], {"status": "UNAVAILABLE", "segments": [], "language": None})
            self.assertEqual(result["silences"], [])
            self.assertEqual(result["gaps"], [])
            self.assertEqual(result["onsets"], [])
            self.assertEqual(result["cut_alignment"], [])
            self.assertIn("no audio source", result["uncertainty_notes"])
            self.assertFalse(result["from_cache"])
            self.write_json_atomic.assert_called_once()

            # Downstream functions not called
            self.energy_profile_fn.assert_not_called()
            self.transcribe_fn.assert_not_called()

    def test_extract_audio_no_audio_stream(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.extract_audio_fn.return_value = {"status": "NO_AUDIO_STREAM"}
            result = self.call_analyze(folder=tmpdir)

            self.assertEqual(result["status"], "NO_AUDIO_STREAM")
            self.assertEqual(result["audio_status"], "NO_AUDIO_STREAM")
            self.assertEqual(result["transcript"], {"status": "NO_AUDIO_STREAM", "segments": [], "language": None})
            self.assertEqual(result["silences"], [])
            self.assertEqual(result["gaps"], [])
            self.assertEqual(result["onsets"], [])
            self.assertEqual(result["cut_alignment"], [])
            self.assertIn("silent source", result["uncertainty_notes"])

    def test_extract_audio_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.extract_audio_fn.return_value = {"status": "ERROR", "error": "ffmpeg failed"}
            result = self.call_analyze(folder=tmpdir)

            self.assertEqual(result["status"], "ERROR")
            self.assertEqual(result["audio_status"], "ERROR")
            self.assertIn("audio extraction failed: ERROR", result["uncertainty_notes"])
            self.energy_profile_fn.assert_not_called()
            self.transcribe_fn.assert_not_called()

    def test_extract_audio_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.extract_audio_fn.return_value = {"status": "NOT_FOUND"}
            result = self.call_analyze(folder=tmpdir)

            self.assertEqual(result["status"], "NOT_FOUND")
            self.assertEqual(result["audio_status"], "NOT_FOUND")
            self.assertIn("audio extraction failed: NOT_FOUND", result["uncertainty_notes"])

    def test_transcriber_unavailable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.transcribe_fn.return_value = {"status": "TRANSCRIBER_UNAVAILABLE"}
            result = self.call_analyze(folder=tmpdir)

            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["audio_status"], "OK")
            self.assertEqual(result["transcript"], {"status": "TRANSCRIBER_UNAVAILABLE"})
            self.assertIn("transcript unavailable", result["uncertainty_notes"])
            # classify_gaps and align_to_cuts still called with empty speech
            self.classify_gaps_fn.assert_called_once()
            self.align_to_cuts_fn.assert_called_once()

    def test_cache_hit_final_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cached_evidence = {
                "status": "OK",
                "audio_status": "OK",
                "transcript": {"status": "OK", "segments": [], "language": "en"},
                "silences": [], "gaps": [], "onsets": [],
                "cut_alignment": [], "uncertainty_notes": [],
                "cut_times": self.cut_times
            }
            self.path_exists.return_value = True
            self.read_json.return_value = cached_evidence

            result = self.call_analyze(folder=tmpdir)

            self.assertTrue(result["from_cache"])
            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["audio_status"], "OK")
            # No downstream calls
            self.extract_audio_fn.assert_not_called()
            self.transcribe_fn.assert_not_called()
            self.write_json_atomic.assert_not_called()

    def test_cache_hit_final_evidence_invalid_missing_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Cached evidence missing required keys should not be used
            cached_evidence = {"status": "OK", "audio_status": "OK"}  # missing other keys
            self.path_exists.return_value = True
            self.read_json.return_value = cached_evidence

            result = self.call_analyze(folder=tmpdir)

            self.assertFalse(result.get("from_cache", False))
            self.extract_audio_fn.assert_called_once()

    def test_cache_hit_final_evidence_mismatched_cut_times(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cached_evidence = {
                "status": "OK",
                "audio_status": "OK",
                "transcript": {"status": "OK", "segments": [], "language": "en"},
                "silences": [], "gaps": [], "onsets": [],
                "cut_alignment": [], "uncertainty_notes": [],
                "cut_times": [99.0]  # different cut times
            }
            self.path_exists.return_value = True
            self.read_json.return_value = cached_evidence

            result = self.call_analyze(folder=tmpdir)

            self.assertFalse(result.get("from_cache", False))
            self.extract_audio_fn.assert_called_once()

    def test_cache_hit_final_evidence_failed_extraction_not_reused(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Cached evidence with failed extraction should NOT be returned early
            cached_evidence = {
                "status": "ERROR",
                "audio_status": "ERROR",
                "transcript": {"status": "ERROR", "segments": [], "language": None},
                "silences": [], "gaps": [], "onsets": [],
                "cut_alignment": [], "uncertainty_notes": ["audio extraction failed: ERROR"],
                "cut_times": self.cut_times
            }
            self.path_exists.return_value = True
            self.read_json.return_value = cached_evidence

            result = self.call_analyze(folder=tmpdir)

            self.assertFalse(result.get("from_cache", False))
            self.extract_audio_fn.assert_called_once()

    def test_resumable_wav_cache_hit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Cache hit for wav with valid source metadata
            cached_wav = {"status": "OK", "wav_path": f"{tmpdir}/audio.wav", "source_size": 1000, "source_mtime": 1234567890.0}
            self.cache_get.side_effect = lambda k: cached_wav if k == f"wav:{self.source}" else None
            self.path_exists.side_effect = lambda p: p == cached_wav["wav_path"]

            result = self.call_analyze(folder=tmpdir)

            # extract_audio_fn should NOT be called due to cache hit
            self.extract_audio_fn.assert_not_called()
            # But energy_profile etc should be called
            self.energy_profile_fn.assert_called_once()
            self.transcribe_fn.assert_called_once()

    def test_resumable_wav_cache_miss_stale_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Cache hit for wav but source metadata changed
            cached_wav = {"status": "OK", "wav_path": f"{tmpdir}/audio.wav", "source_size": 999, "source_mtime": 1234567890.0}
            self.cache_get.side_effect = lambda k: cached_wav if k == f"wav:{self.source}" else None
            self.path_exists.side_effect = lambda p: p == cached_wav["wav_path"]
            # get_size_mtime returns different size
            self.get_size_mtime.return_value = {"status": "OK", "size": 1000, "mtime": 1234567890.0}

            result = self.call_analyze(folder=tmpdir)

            # extract_audio_fn SHOULD be called because cache is stale
            self.extract_audio_fn.assert_called_once()

    def test_resumable_wav_cache_miss_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Cache hit for wav but file doesn't exist
            cached_wav = {"status": "OK", "wav_path": f"{tmpdir}/audio.wav", "source_size": 1000, "source_mtime": 1234567890.0}
            self.cache_get.side_effect = lambda k: cached_wav if k == f"wav:{self.source}" else None
            self.path_exists.return_value = False

            result = self.call_analyze(folder=tmpdir)

            # extract_audio_fn SHOULD be called because file missing
            self.extract_audio_fn.assert_called_once()

    def test_resumable_transcript_cache_hit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # No wav cache, but transcript cache hit with valid metadata
            cached_transcript = {
                "status": "OK",
                "segments": [{"start": 0, "end": 1, "text": "cached"}],
                "language": "en",
                "source_size": 1000,
                "source_mtime": 1234567890.0
            }
            self.cache_get.side_effect = lambda k: cached_transcript if k == f"transcript:{self.source}:small" else None

            result = self.call_analyze(folder=tmpdir)

            self.transcribe_fn.assert_not_called()
            # But extract_audio should be called
            self.extract_audio_fn.assert_called_once()
            # And transcript in result should be cached one
            self.assertEqual(result["transcript"]["segments"][0]["text"], "cached")

    def test_resumable_transcript_cache_miss_stale_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Transcript cache hit but source metadata changed
            cached_transcript = {
                "status": "OK",
                "segments": [{"start": 0, "end": 1, "text": "cached"}],
                "language": "en",
                "source_size": 999,
                "source_mtime": 1234567890.0
            }
            self.cache_get.side_effect = lambda k: cached_transcript if k == f"transcript:{self.source}:small" else None
            self.get_size_mtime.return_value = {"status": "OK", "size": 1000, "mtime": 1234567890.0}

            result = self.call_analyze(folder=tmpdir)

            # transcribe_fn SHOULD be called because cache is stale
            self.transcribe_fn.assert_called_once()

    def test_transcript_not_cached_on_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Transcriber unavailable should not be cached
            self.transcribe_fn.return_value = {"status": "TRANSCRIBER_UNAVAILABLE"}
            result = self.call_analyze(folder=tmpdir)

            # cache_set should not be called for transcript
            transcript_calls = [c for c in self.cache_set.call_args_list if c[0][0].startswith("transcript:")]
            self.assertEqual(len(transcript_calls), 0)

    def test_transcript_cached_on_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.call_analyze(folder=tmpdir)

            # cache_set should be called for transcript with status OK
            transcript_calls = [c for c in self.cache_set.call_args_list if c[0][0].startswith("transcript:")]
            self.assertEqual(len(transcript_calls), 1)
            cached_value = transcript_calls[0][0][1]
            self.assertEqual(cached_value["status"], "OK")
            self.assertEqual(cached_value["segments"][0]["text"], "hi")
            self.assertEqual(cached_value["language"], "en")
            self.assertEqual(cached_value["source_size"], 1000)
            self.assertEqual(cached_value["source_mtime"], 1234567890.0)

    def test_write_json_atomic_failure_adds_uncertainty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.write_json_atomic.return_value = {"status": "ERROR"}
            result = self.call_analyze(folder=tmpdir)

            self.assertIn("failed to write evidence", result["uncertainty_notes"])

    def test_align_to_cuts_receives_tol(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.call_analyze(folder=tmpdir)
            # Check align_to_cuts_fn was called with tol=0.25
            args, kwargs = self.align_to_cuts_fn.call_args
            self.assertEqual(kwargs.get("tol", args[4] if len(args) > 4 else None), 0.25)

    def test_transcribe_fn_receives_runner_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.call_analyze(folder=tmpdir)
            args, kwargs = self.transcribe_fn.call_args
            # runner must be explicitly passed as kwarg
            self.assertIn("runner", kwargs)
            self.assertIsNone(kwargs["runner"])


if __name__ == "__main__":
    unittest.main()
