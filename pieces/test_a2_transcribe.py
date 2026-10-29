import unittest
import tempfile
import os
from a2_transcribe import transcribe, classify_gaps, find_onsets


class TestTranscribe(unittest.TestCase):
    def test_transcribe_with_fake_runner(self):
        def fake_runner(wav_path, language, model_size):
            return {
                "status": "OK",
                "segments": [
                    {"start": 0.5, "end": 1.2, "text": "hello", "avg_logprob": -0.5},
                    {"start": 2.0, "end": 3.0, "text": "world", "avg_logprob": -1.5}
                ],
                "language": "en"
            }

        # Use a temp file path instead of absolute /tmp/test.wav
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(b"RIFF\x00\x00\x00\x00WAVEfmt ")
            tmp_path = tmp.name
        try:
            result = transcribe(tmp_path, runner=fake_runner)
            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["language"], "en")
            self.assertEqual(len(result["segments"]), 2)
            self.assertEqual(result["segments"][0]["confidence"], "OK")
            self.assertEqual(result["segments"][1]["confidence"], "LOW_CONFIDENCE")
            self.assertEqual(result["segments"][0]["text"], "hello")
            self.assertEqual(result["segments"][1]["text"], "world")
        finally:
            os.unlink(tmp_path)

    def test_transcribe_transcriber_unavailable(self):
        def bad_import():
            raise ImportError("no module")

        # Create a temporary non-empty file to bypass file-existence check
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(b"RIFF\x00\x00\x00\x00WAVEfmt ")
            tmp_path = tmp.name
        try:
            result = transcribe(tmp_path, import_faster_whisper=bad_import)
            self.assertEqual(result["status"], "TRANSCRIBER_UNAVAILABLE")
        finally:
            os.unlink(tmp_path)

    def test_transcribe_with_fake_faster_whisper(self):
        """Test real transcriber path with injected fake faster_whisper module."""
        # Track constructor and transcribe calls
        captured = {"model_args": None, "transcribe_kwargs": None}

        class FakeSegment:
            def __init__(self, start, end, text, avg_logprob):
                self.start = start
                self.end = end
                self.text = text
                self.avg_logprob = avg_logprob

        class FakeInfo:
            def __init__(self, language):
                self.language = language

        class FakeWhisperModel:
            def __init__(self, model_size, device, compute_type):
                captured["model_args"] = (model_size, device, compute_type)

            def transcribe(self, wav_path, language, beam_size, vad_filter):
                captured["transcribe_kwargs"] = {
                    "wav_path": wav_path,
                    "language": language,
                    "beam_size": beam_size,
                    "vad_filter": vad_filter
                }
                segments = [
                    FakeSegment(0.5, 1.2, "hello", -0.5),
                    FakeSegment(2.0, 3.0, "world", -1.5),
                ]
                info = FakeInfo("mr")
                return iter(segments), info

        def fake_import():
            class FakeModule:
                WhisperModel = FakeWhisperModel
            return FakeModule()

        # Create a temporary non-empty file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(b"RIFF\x00\x00\x00\x00WAVEfmt ")
            tmp_path = tmp.name
        try:
            result = transcribe(tmp_path, language="mr", model_size="tiny", import_faster_whisper=fake_import)
            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["language"], "mr")
            self.assertEqual(len(result["segments"]), 2)
            self.assertEqual(result["segments"][0]["confidence"], "OK")
            self.assertEqual(result["segments"][1]["confidence"], "LOW_CONFIDENCE")
            self.assertEqual(result["segments"][0]["text"], "hello")
            self.assertEqual(result["segments"][1]["text"], "world")
            self.assertAlmostEqual(result["segments"][0]["avg_logprob"], -0.5)
            self.assertAlmostEqual(result["segments"][1]["avg_logprob"], -1.5)

            # Verify model constructor arguments
            self.assertIsNotNone(captured["model_args"])
            model_size, device, compute_type = captured["model_args"]
            self.assertEqual(model_size, "tiny")
            self.assertEqual(device, "cpu")
            self.assertEqual(compute_type, "int8")

            # Verify transcribe kwargs
            self.assertIsNotNone(captured["transcribe_kwargs"])
            self.assertEqual(captured["transcribe_kwargs"]["beam_size"], 5)
            self.assertEqual(captured["transcribe_kwargs"]["vad_filter"], True)
            self.assertEqual(captured["transcribe_kwargs"]["language"], "mr")
            self.assertEqual(captured["transcribe_kwargs"]["wav_path"], tmp_path)
        finally:
            os.unlink(tmp_path)


class TestClassifyGaps(unittest.TestCase):
    def test_classify_gaps_worked_example(self):
        silences = [
            {"start": 1.0, "end": 1.5},
            {"start": 3.0, "end": 4.5},
            {"start": 5.0, "end": 5.2},
        ]
        speech_segments = [
            {"start": 0.0, "end": 0.5},
            {"start": 2.0, "end": 2.5},
            {"start": 6.0, "end": 7.0},
        ]

        result = classify_gaps(silences, speech_segments)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(len(result["gaps"]), 3)
        self.assertEqual(result["gaps"][0]["label"], "SPEECH_PAUSE")
        self.assertEqual(result["gaps"][1]["label"], "INTENTIONAL_SILENCE_CANDIDATE")
        self.assertEqual(result["gaps"][2]["label"], "LOW_VOLUME_ONLY")
        self.assertAlmostEqual(result["gaps"][0]["start"], 1.0)
        self.assertAlmostEqual(result["gaps"][0]["end"], 1.5)
        self.assertAlmostEqual(result["gaps"][1]["start"], 3.0)
        self.assertAlmostEqual(result["gaps"][1]["end"], 4.5)
        self.assertAlmostEqual(result["gaps"][2]["start"], 5.0)
        self.assertAlmostEqual(result["gaps"][2]["end"], 5.2)

    def test_classify_gaps_edge_cases(self):
        # Silence overlapping speech -> LOW_VOLUME_ONLY
        silences = [{"start": 1.0, "end": 2.0}]
        speech_segments = [{"start": 1.5, "end": 2.5}]
        result = classify_gaps(silences, speech_segments)
        self.assertEqual(result["gaps"][0]["label"], "LOW_VOLUME_ONLY")

        # Long silence with no speech around -> INTENTIONAL_SILENCE_CANDIDATE
        silences = [{"start": 10.0, "end": 12.0}]
        speech_segments = []
        result = classify_gaps(silences, speech_segments)
        self.assertEqual(result["gaps"][0]["label"], "INTENTIONAL_SILENCE_CANDIDATE")

        # Short silence with no speech around -> LOW_VOLUME_ONLY
        silences = [{"start": 10.0, "end": 10.5}]
        speech_segments = []
        result = classify_gaps(silences, speech_segments)
        self.assertEqual(result["gaps"][0]["label"], "LOW_VOLUME_ONLY")

        # Speech pause but gap > 2.0 on one side -> LOW_VOLUME_ONLY
        silences = [{"start": 5.0, "end": 5.5}]
        speech_segments = [{"start": 0.0, "end": 1.0}, {"start": 10.0, "end": 11.0}]
        result = classify_gaps(silences, speech_segments)
        self.assertEqual(result["gaps"][0]["label"], "LOW_VOLUME_ONLY")


class TestFindOnsets(unittest.TestCase):
    def test_find_onsets_worked_example(self):
        profile = [
            {"time": 0.025, "db": -40.0},
            {"time": 0.075, "db": -30.0},
            {"time": 0.125, "db": -35.0},
            {"time": 0.175, "db": -25.0},
            {"time": 0.225, "db": -20.0},
            {"time": 0.275, "db": -10.0},
        ]

        result = find_onsets(profile, 9.0, 0.15)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(len(result["onsets"]), 2)
        self.assertAlmostEqual(result["onsets"][0]["time"], 0.075)
        self.assertAlmostEqual(result["onsets"][0]["rise_db"], 10.0)
        self.assertEqual(result["onsets"][0]["label"], "SOUND_ONSET")
        self.assertAlmostEqual(result["onsets"][1]["time"], 0.275)
        self.assertAlmostEqual(result["onsets"][1]["rise_db"], 10.0)
        self.assertEqual(result["onsets"][1]["label"], "SOUND_ONSET")

    def test_find_onsets_min_gap_enforcement(self):
        profile = [
            {"time": 0.0, "db": -40.0},
            {"time": 0.05, "db": -30.0},  # delta 10 -> onset at 0.05
            {"time": 0.10, "db": -20.0},  # delta 10, but gap 0.05 < 0.15 -> skip
            {"time": 0.20, "db": -10.0},  # delta 10, gap 0.15 from 0.05 -> onset at 0.20
        ]
        result = find_onsets(profile, 9.0, 0.15)
        self.assertEqual(len(result["onsets"]), 2)
        self.assertAlmostEqual(result["onsets"][0]["time"], 0.05)
        self.assertAlmostEqual(result["onsets"][1]["time"], 0.20)

    def test_find_onsets_rise_db_threshold(self):
        profile = [
            {"time": 0.0, "db": -40.0},
            {"time": 0.1, "db": -35.0},  # delta 5 < 9 -> no onset
            {"time": 0.2, "db": -30.0},  # delta 5 < 9 -> no onset
        ]
        result = find_onsets(profile, 9.0, 0.15)
        self.assertEqual(len(result["onsets"]), 0)

    def test_find_onsets_float_precision_boundary(self):
        """Test that epsilon handles exact min_gap boundary (0.15)."""
        profile = [
            {"time": 0.0, "db": -40.0},
            {"time": 0.05, "db": -30.0},  # onset at 0.05
            {"time": 0.20, "db": -20.0},  # gap = 0.15 exactly, should be allowed
        ]
        result = find_onsets(profile, 9.0, 0.15)
        self.assertEqual(len(result["onsets"]), 2)
        self.assertAlmostEqual(result["onsets"][0]["time"], 0.05)
        self.assertAlmostEqual(result["onsets"][1]["time"], 0.20)


if __name__ == "__main__":
    unittest.main()
