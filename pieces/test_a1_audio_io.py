"""Unit tests for a1_audio_io module."""
from __future__ import annotations

import unittest
import tempfile
import os
import numpy as np
import wave
from unittest.mock import Mock, patch, MagicMock

import a1_audio_io


class TestExtractAudio(unittest.TestCase):
    """Tests for extract_audio function."""

    def setUp(self):
        # Use temporary paths instead of hardcoded absolute paths
        self.temp_dir = tempfile.mkdtemp()
        self.source = os.path.join(self.temp_dir, "clip.mp4")
        self.wav_path = os.path.join(self.temp_dir, "clip.wav")
        self.ffmpeg_runner = Mock(return_value={"status": "OK"})
        self.get_source_size_mtime = Mock(return_value={"size": 1024000, "mtime": 1700000000.0})
        self.cache_get = Mock(return_value=None)
        self.cache_set = Mock()

    def tearDown(self):
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _mock_wave_open_success(self):
        """Context manager for mocking wave.open with a valid WAV."""
        mock_wf = MagicMock()
        mock_wf.getnframes.return_value = 16000  # 1 second of audio
        mock_wf.getframerate.return_value = 16000
        mock_wf.getsampwidth.return_value = 2
        mock_wf.getnchannels.return_value = 1
        mock_wf.__enter__.return_value = mock_wf
        mock_wf.__exit__.return_value = None
        return patch("a1_audio_io.wave.open", return_value=mock_wf)

    def test_extract_audio_success(self):
        """Test successful audio extraction."""
        with self._mock_wave_open_success():
            result = a1_audio_io.extract_audio(
                self.source, self.wav_path,
                self.ffmpeg_runner, self.get_source_size_mtime,
                self.cache_get, self.cache_set
            )
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["wav_path"], self.wav_path)
        self.assertFalse(result["from_cache"])
        self.ffmpeg_runner.assert_called_once()
        self.cache_set.assert_called_once()

    def test_extract_audio_cache_hit(self):
        """Test cache hit returns from_cache=True."""
        self.cache_get.return_value = {
            "wav_path": self.wav_path,
            "source_size": 1024000,
            "source_mtime": 1700000000.0
        }
        result = a1_audio_io.extract_audio(
            self.source, self.wav_path,
            self.ffmpeg_runner, self.get_source_size_mtime,
            self.cache_get, self.cache_set
        )
        self.assertEqual(result["status"], "OK")
        self.assertTrue(result["from_cache"])
        self.ffmpeg_runner.assert_not_called()
        self.cache_set.assert_not_called()

    def test_extract_audio_cache_miss_mtime_mismatch(self):
        """Test cache miss when mtime differs."""
        self.cache_get.return_value = {
            "wav_path": self.wav_path,
            "source_size": 1024000,
            "source_mtime": 1600000000.0  # different mtime
        }
        with self._mock_wave_open_success():
            result = a1_audio_io.extract_audio(
                self.source, self.wav_path,
                self.ffmpeg_runner, self.get_source_size_mtime,
                self.cache_get, self.cache_set
            )
        self.assertEqual(result["status"], "OK")
        self.assertFalse(result["from_cache"])
        self.ffmpeg_runner.assert_called_once()

    def test_extract_audio_source_not_found(self):
        """Test source not found returns ERROR."""
        self.get_source_size_mtime.return_value = {"status": "NOT_FOUND"}
        result = a1_audio_io.extract_audio(
            self.source, self.wav_path,
            self.ffmpeg_runner, self.get_source_size_mtime,
            self.cache_get, self.cache_set
        )
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("not found", result["reason"].lower())

    def test_extract_audio_zip_source_unavailable(self):
        """Test .zip source returns UNAVAILABLE."""
        zip_source = os.path.join(self.temp_dir, "clip.zip")
        result = a1_audio_io.extract_audio(
            zip_source, self.wav_path,
            self.ffmpeg_runner, self.get_source_size_mtime,
            self.cache_get, self.cache_set
        )
        self.assertEqual(result["status"], "UNAVAILABLE")

    def test_extract_audio_zip_source_unavailable_even_with_cache(self):
        """Test .zip source returns UNAVAILABLE even if cache has entry (cache bypassed)."""
        zip_source = os.path.join(self.temp_dir, "clip.zip")
        self.cache_get.return_value = {
            "wav_path": self.wav_path,
            "source_size": 1024000,
            "source_mtime": 1700000000.0
        }
        result = a1_audio_io.extract_audio(
            zip_source, self.wav_path,
            self.ffmpeg_runner, self.get_source_size_mtime,
            self.cache_get, self.cache_set
        )
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.ffmpeg_runner.assert_not_called()

    def test_extract_audio_image_sequence_unavailable(self):
        """Test image sequence directory returns UNAVAILABLE."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create image files
            for name in ["frame001.png", "frame002.jpg", "frame003.jpeg"]:
                with open(os.path.join(tmpdir, name), "w") as f:
                    f.write("fake")
            result = a1_audio_io.extract_audio(
                tmpdir, self.wav_path,
                self.ffmpeg_runner, self.get_source_size_mtime,
                self.cache_get, self.cache_set
            )
            self.assertEqual(result["status"], "UNAVAILABLE")

    def test_extract_audio_image_sequence_unavailable_even_with_cache(self):
        """Test image sequence directory returns UNAVAILABLE even if cache has entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["frame001.png", "frame002.jpg"]:
                with open(os.path.join(tmpdir, name), "w") as f:
                    f.write("fake")
            self.cache_get.return_value = {
                "wav_path": self.wav_path,
                "source_size": 1024000,
                "source_mtime": 1700000000.0
            }
            result = a1_audio_io.extract_audio(
                tmpdir, self.wav_path,
                self.ffmpeg_runner, self.get_source_size_mtime,
                self.cache_get, self.cache_set
            )
            self.assertEqual(result["status"], "UNAVAILABLE")
            self.ffmpeg_runner.assert_not_called()

    def test_extract_audio_image_sequence_with_trailing_slash_unavailable(self):
        """Test existing image sequence directory with trailing slash returns UNAVAILABLE."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create image files in the directory
            for name in ["frame001.png", "frame002.jpg"]:
                with open(os.path.join(tmpdir, name), "w") as f:
                    f.write("fake")
            trailing_slash_path = tmpdir + "/"
            result = a1_audio_io.extract_audio(
                trailing_slash_path, self.wav_path,
                self.ffmpeg_runner, self.get_source_size_mtime,
                self.cache_get, self.cache_set
            )
            self.assertEqual(result["status"], "UNAVAILABLE")

    def test_extract_audio_nonexistent_image_sequence_with_trailing_slash_unavailable(self):
        """Test nonexistent image sequence directory with trailing slash returns UNAVAILABLE (spec worked example)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Path that doesn't exist but ends with separator
            nonexistent_path = os.path.join(tmpdir, "missing_frames") + os.sep
            result = a1_audio_io.extract_audio(
                nonexistent_path, self.wav_path,
                self.ffmpeg_runner, self.get_source_size_mtime,
                self.cache_get, self.cache_set
            )
            self.assertEqual(result["status"], "UNAVAILABLE")
            self.ffmpeg_runner.assert_not_called()

    def test_extract_audio_image_sequence_with_trailing_backslash_unavailable(self):
        """Test image sequence directory with trailing backslash returns UNAVAILABLE."""
        # Use a temporary directory path with trailing backslash
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create image files
            for name in ["frame001.png", "frame002.jpg"]:
                with open(os.path.join(tmpdir, name), "w") as f:
                    f.write("fake")
            trailing_backslash_path = tmpdir + "\\"
            result = a1_audio_io.extract_audio(
                trailing_backslash_path, self.wav_path,
                self.ffmpeg_runner, self.get_source_size_mtime,
                self.cache_get, self.cache_set
            )
            self.assertEqual(result["status"], "UNAVAILABLE")

    def test_extract_audio_empty_directory_unavailable(self):
        """Test empty directory returns UNAVAILABLE (vacuously all image files)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = a1_audio_io.extract_audio(
                tmpdir, self.wav_path,
                self.ffmpeg_runner, self.get_source_size_mtime,
                self.cache_get, self.cache_set
            )
            self.assertEqual(result["status"], "UNAVAILABLE")

    def test_extract_audio_mixed_directory_not_unavailable(self):
        """Test directory with non-image files proceeds to ffmpeg."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "frame001.png"), "w") as f:
                f.write("fake")
            with open(os.path.join(tmpdir, "not_image.txt"), "w") as f:
                f.write("fake")
            with self._mock_wave_open_success():
                result = a1_audio_io.extract_audio(
                    tmpdir, self.wav_path,
                    self.ffmpeg_runner, self.get_source_size_mtime,
                    self.cache_get, self.cache_set
                )
            # Should not be UNAVAILABLE; ffmpeg will be called
            self.assertEqual(result["status"], "OK")
            self.ffmpeg_runner.assert_called_once()

    def test_extract_audio_ffmpeg_error(self):
        """Test ffmpeg failure returns ERROR."""
        self.ffmpeg_runner.return_value = {"status": "ERROR", "stderr": "ffmpeg failed"}
        result = a1_audio_io.extract_audio(
            self.source, self.wav_path,
            self.ffmpeg_runner, self.get_source_size_mtime,
            self.cache_get, self.cache_set
        )
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("ffmpeg failed", result["reason"])

    def test_extract_audio_ffmpeg_no_audio_stream(self):
        """Test ffmpeg 'no audio stream' error returns NO_AUDIO_STREAM."""
        self.ffmpeg_runner.return_value = {"status": "ERROR", "stderr": "no audio stream found"}
        result = a1_audio_io.extract_audio(
            self.source, self.wav_path,
            self.ffmpeg_runner, self.get_source_size_mtime,
            self.cache_get, self.cache_set
        )
        self.assertEqual(result["status"], "NO_AUDIO_STREAM")

    def test_extract_audio_ffmpeg_no_audio_stream_case_insensitive(self):
        """Test ffmpeg 'No Audio Stream' error (case insensitive) returns NO_AUDIO_STREAM."""
        self.ffmpeg_runner.return_value = {"status": "ERROR", "stderr": "No Audio Stream in file"}
        result = a1_audio_io.extract_audio(
            self.source, self.wav_path,
            self.ffmpeg_runner, self.get_source_size_mtime,
            self.cache_get, self.cache_set
        )
        self.assertEqual(result["status"], "NO_AUDIO_STREAM")

    def test_extract_audio_ffmpeg_does_not_contain_any_stream(self):
        """Test ffmpeg 'does not contain any stream' error returns NO_AUDIO_STREAM (regression test)."""
        self.ffmpeg_runner.return_value = {"status": "ERROR", "stderr": "Output file #0 does not contain any stream"}
        result = a1_audio_io.extract_audio(
            self.source, self.wav_path,
            self.ffmpeg_runner, self.get_source_size_mtime,
            self.cache_get, self.cache_set
        )
        self.assertEqual(result["status"], "NO_AUDIO_STREAM")

    def test_extract_audio_ffmpeg_stderr_none(self):
        """Test ffmpeg error with None stderr doesn't crash."""
        self.ffmpeg_runner.return_value = {"status": "ERROR", "stderr": None}
        result = a1_audio_io.extract_audio(
            self.source, self.wav_path,
            self.ffmpeg_runner, self.get_source_size_mtime,
            self.cache_get, self.cache_set
        )
        self.assertEqual(result["status"], "ERROR")

    def test_extract_audio_no_audio_stream_zero_frames(self):
        """Test silent video (zero frames) returns NO_AUDIO_STREAM."""
        # Mock wave.open to return a WAV with 0 frames
        with patch("a1_audio_io.wave.open") as mock_wave_open:
            mock_wf = MagicMock()
            mock_wf.getnframes.return_value = 0
            mock_wf.getframerate.return_value = 16000
            mock_wf.getsampwidth.return_value = 2
            mock_wf.getnchannels.return_value = 1
            mock_wf.__enter__.return_value = mock_wf
            mock_wave_open.return_value = mock_wf

            result = a1_audio_io.extract_audio(
                self.source, self.wav_path,
                self.ffmpeg_runner, self.get_source_size_mtime,
                self.cache_get, self.cache_set
            )
            self.assertEqual(result["status"], "NO_AUDIO_STREAM")

    def test_extract_audio_invalid_wav(self):
        """Test invalid WAV output returns ERROR."""
        with patch("a1_audio_io.wave.open", side_effect=wave.Error("invalid")):
            result = a1_audio_io.extract_audio(
                self.source, self.wav_path,
                self.ffmpeg_runner, self.get_source_size_mtime,
                self.cache_get, self.cache_set
            )
            self.assertEqual(result["status"], "ERROR")
            self.assertIn("invalid", result["reason"].lower())


class TestEnergyProfile(unittest.TestCase):
    """Tests for energy_profile function."""

    def test_energy_profile_synthetic(self):
        """Test energy_profile with synthetic signal written to a real WAV file."""
        # Synthetic WAV: 16kHz, 16-bit mono, 0.2s = 3200 samples
        # Window 0.05s = 800 samples. 4 windows.
        # Samples: [0]*800 + [10000]*800 + [0]*800 + [5000]*800
        sample_rate = 16000
        win = 0.05
        frame_size = int(win * sample_rate)  # 800
        samples = np.array(
            [0] * frame_size + [10000] * frame_size + [0] * frame_size + [5000] * frame_size,
            dtype=np.int16
        )

        # Write to a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
        try:
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(samples.tobytes())

            # Call energy_profile with default parameters (no injected mocks)
            result = a1_audio_io.energy_profile(wav_path, win)

            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["sample_rate"], sample_rate)
            self.assertEqual(result["window_sec"], win)
            profile = result["profile"]
            self.assertEqual(len(profile), 4)

            # Window 0: silence -> -120 dB
            self.assertAlmostEqual(profile[0]["db"], -120.0, places=1)
            self.assertAlmostEqual(profile[0]["time"], 0.025, places=3)

            # Window 1: 10000 amplitude
            expected_db1 = 20 * np.log10(10000 / 32768.0)
            self.assertAlmostEqual(profile[1]["db"], expected_db1, places=2)
            self.assertAlmostEqual(profile[1]["time"], 0.075, places=3)

            # Window 2: silence -> -120 dB
            self.assertAlmostEqual(profile[2]["db"], -120.0, places=1)
            self.assertAlmostEqual(profile[2]["time"], 0.125, places=3)

            # Window 3: 5000 amplitude
            expected_db3 = 20 * np.log10(5000 / 32768.0)
            self.assertAlmostEqual(profile[3]["db"], expected_db3, places=2)
            self.assertAlmostEqual(profile[3]["time"], 0.175, places=3)
        finally:
            os.unlink(wav_path)

    def test_energy_profile_invalid_format(self):
        """Test non-16-bit or non-mono returns ERROR."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = os.path.join(tmpdir, "test.wav")
            def mock_wave_open(path, mode):
                class MockWav:
                    def getnframes(self): return 100
                    def getframerate(self): return 16000
                    def getsampwidth(self): return 3  # 24-bit
                    def getnchannels(self): return 1
                    def readframes(self, n): return b"\x00" * 300
                    def close(self): pass
                    def __enter__(self): return self
                    def __exit__(self, *a): pass
                return MockWav()

            result = a1_audio_io.energy_profile(
                wav_path, 0.05, wave_open=mock_wave_open
            )
            self.assertEqual(result["status"], "ERROR")
            self.assertIn("16-bit mono", result["reason"])

    def test_energy_profile_stereo(self):
        """Test stereo WAV returns ERROR."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = os.path.join(tmpdir, "test.wav")
            def mock_wave_open(path, mode):
                class MockWav:
                    def getnframes(self): return 100
                    def getframerate(self): return 16000
                    def getsampwidth(self): return 2
                    def getnchannels(self): return 2  # stereo
                    def readframes(self, n): return b"\x00" * 400
                    def close(self): pass
                    def __enter__(self): return self
                    def __exit__(self, *a): pass
                return MockWav()

            result = a1_audio_io.energy_profile(
                wav_path, 0.05, wave_open=mock_wave_open
            )
            self.assertEqual(result["status"], "ERROR")


class TestFindSilences(unittest.TestCase):
    """Tests for find_silences function."""

    def test_find_silences_empty_profile(self):
        """Test empty profile returns empty silences."""
        result = a1_audio_io.find_silences([])
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["silences"], [])

    def test_find_silences_all_above_threshold(self):
        """Test no silences when all windows above threshold."""
        profile = [
            {"time": 0.025, "db": -20.0},
            {"time": 0.075, "db": -15.0},
            {"time": 0.125, "db": -10.0},
        ]
        result = a1_audio_io.find_silences(profile, thresh_db=-35.0, min_dur=0.35)
        self.assertEqual(result["silences"], [])

    def test_find_silences_short_region_dropped(self):
        """Test short silence region (< min_dur) is dropped."""
        # 2 windows = 0.1s duration, min_dur=0.35
        profile = [
            {"time": 0.025, "db": -40.0},
            {"time": 0.075, "db": -40.0},
            {"time": 0.125, "db": -20.0},
        ]
        result = a1_audio_io.find_silences(profile, thresh_db=-35.0, min_dur=0.35)
        self.assertEqual(result["silences"], [])

    def test_find_silences_exact_min_dur(self):
        """Test region exactly at min_dur is kept."""
        # 7 windows * 0.05 = 0.35s
        profile = [
            {"time": 0.025, "db": -40.0},
            {"time": 0.075, "db": -40.0},
            {"time": 0.125, "db": -40.0},
            {"time": 0.175, "db": -40.0},
            {"time": 0.225, "db": -40.0},
            {"time": 0.275, "db": -40.0},
            {"time": 0.325, "db": -40.0},
        ]
        result = a1_audio_io.find_silences(profile, thresh_db=-35.0, min_dur=0.35)
        self.assertEqual(len(result["silences"]), 1)
        self.assertAlmostEqual(result["silences"][0]["start"], 0.0, places=2)
        self.assertAlmostEqual(result["silences"][0]["end"], 0.35, places=2)

    def test_find_silences_long_region_kept(self):
        """Test long silence region is kept with correct start/end."""
        # 8 windows = 0.4s duration
        profile = [
            {"time": 0.025, "db": -40.0},
            {"time": 0.075, "db": -40.0},
            {"time": 0.125, "db": -40.0},
            {"time": 0.175, "db": -40.0},
            {"time": 0.225, "db": -40.0},
            {"time": 0.275, "db": -40.0},
            {"time": 0.325, "db": -40.0},
            {"time": 0.375, "db": -40.0},
        ]
        result = a1_audio_io.find_silences(profile, thresh_db=-35.0, min_dur=0.35)
        self.assertEqual(len(result["silences"]), 1)
        self.assertAlmostEqual(result["silences"][0]["start"], 0.0, places=2)
        self.assertAlmostEqual(result["silences"][0]["end"], 0.4, places=2)

    def test_find_silences_merge_close_regions(self):
        """Test regions separated by < win (one window) are merged."""
        # Uniform window spacing of 0.05s (win=0.05)
        # Region 1: windows at 0.025, 0.075 (end at 0.1)
        # Gap window at 0.115 (non-silent)
        # Region 2: windows at 0.17, 0.22, 0.27, 0.32, 0.375 (start at 0.145, end at 0.4)
        # Gap between region1 end (0.1) and region2 start (0.145) = 0.045 < 0.05
        # With strict < win, this should merge
        profile = [
            {"time": 0.025, "db": -40.0},
            {"time": 0.075, "db": -40.0},
            {"time": 0.115, "db": -20.0},  # gap window at 0.115
            {"time": 0.17, "db": -40.0},   # region2 starts here (0.17 - 0.025 = 0.145)
            {"time": 0.22, "db": -40.0},
            {"time": 0.27, "db": -40.0},
            {"time": 0.32, "db": -40.0},
            {"time": 0.375, "db": -40.0},  # last window at 0.375 -> end = 0.4
        ]
        # Region 1: 0.0-0.1 (0.1s, dropped)
        # Region 2: 0.145-0.4 (0.255s, dropped)
        # But merged: 0.0-0.4 (0.4s >= 0.35) -> kept
        result = a1_audio_io.find_silences(profile, thresh_db=-35.0, min_dur=0.35, win=0.05)
        self.assertEqual(len(result["silences"]), 1)
        self.assertAlmostEqual(result["silences"][0]["start"], 0.0, places=2)
        self.assertAlmostEqual(result["silences"][0]["end"], 0.4, places=2)

    def test_find_silences_exact_one_window_gap_not_merged(self):
        """Test regions separated by exactly one window (gap == win) are NOT merged."""
        # Two regions separated by exactly one window gap (gap == win = 0.05s)
        # Region 1: windows at 0.025, 0.075 (end at 0.1)
        # Gap window at 0.125 (non-silent)
        # Region 2: windows at 0.175, 0.225, 0.275, 0.325, 0.375 (start at 0.15, end at 0.4)
        # Gap between region1 end (0.1) and region2 start (0.15) = 0.05 = win
        # Should NOT merge because gap is not < win
        profile = [
            {"time": 0.025, "db": -40.0},
            {"time": 0.075, "db": -40.0},
            {"time": 0.125, "db": -20.0},  # gap window (non-silent)
            {"time": 0.175, "db": -40.0},
            {"time": 0.225, "db": -40.0},
            {"time": 0.275, "db": -40.0},
            {"time": 0.325, "db": -40.0},
            {"time": 0.375, "db": -40.0},
        ]
        # Region 1: 0.0-0.1 (0.1s, dropped)
        # Region 2: 0.15-0.4 (0.25s, dropped)
        # Not merged because gap == win (not < win)
        result = a1_audio_io.find_silences(profile, thresh_db=-35.0, min_dur=0.35, win=0.05)
        self.assertEqual(result["silences"], [])

    def test_find_silences_separate_regions_not_merged(self):
        """Test regions separated by >= win are not merged."""
        # Two regions separated by two windows (0.1s gap)
        profile = [
            {"time": 0.025, "db": -40.0},
            {"time": 0.075, "db": -40.0},
            {"time": 0.125, "db": -40.0},
            {"time": 0.175, "db": -40.0},  # region 1: 0.0-0.2 (0.2s, dropped)
            {"time": 0.225, "db": -20.0},  # gap window 1
            {"time": 0.275, "db": -20.0},  # gap window 2
            {"time": 0.325, "db": -40.0},
            {"time": 0.375, "db": -40.0},
            {"time": 0.425, "db": -40.0},
            {"time": 0.475, "db": -40.0},  # region 2: 0.3-0.5 (0.2s, dropped)
        ]
        # Both regions < min_dur, and gap >= win so not merged
        result = a1_audio_io.find_silences(profile, thresh_db=-35.0, min_dur=0.35, win=0.05)
        self.assertEqual(result["silences"], [])

    def test_find_silences_multiple_regions(self):
        """Test multiple distinct silence regions."""
        profile = [
            # Region 1: 8 windows = 0.4s
            {"time": 0.025, "db": -40.0},
            {"time": 0.075, "db": -40.0},
            {"time": 0.125, "db": -40.0},
            {"time": 0.175, "db": -40.0},
            {"time": 0.225, "db": -40.0},
            {"time": 0.275, "db": -40.0},
            {"time": 0.325, "db": -40.0},
            {"time": 0.375, "db": -40.0},
            # Gap
            {"time": 0.425, "db": -20.0},
            {"time": 0.475, "db": -20.0},
            # Region 2: 8 windows = 0.4s
            {"time": 0.525, "db": -40.0},
            {"time": 0.575, "db": -40.0},
            {"time": 0.625, "db": -40.0},
            {"time": 0.675, "db": -40.0},
            {"time": 0.725, "db": -40.0},
            {"time": 0.775, "db": -40.0},
            {"time": 0.825, "db": -40.0},
            {"time": 0.875, "db": -40.0},
        ]
        result = a1_audio_io.find_silences(profile, thresh_db=-35.0, min_dur=0.35, win=0.05)
        self.assertEqual(len(result["silences"]), 2)
        self.assertAlmostEqual(result["silences"][0]["start"], 0.0, places=2)
        self.assertAlmostEqual(result["silences"][0]["end"], 0.4, places=2)
        self.assertAlmostEqual(result["silences"][1]["start"], 0.5, places=2)
        self.assertAlmostEqual(result["silences"][1]["end"], 0.9, places=2)


if __name__ == "__main__":
    unittest.main()
