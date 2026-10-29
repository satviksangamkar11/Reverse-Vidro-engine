
# WP-B1: Audio Extraction & Energy Analysis
# Pure stdlib + numpy. No ML dependencies.

## Module: a1_audio_io.py

### Function 1: extract_audio
**Signature:**
```python
def extract_audio(
    source: str,
    wav_path: str,
    ffmpeg_runner: callable,
    get_source_size_mtime: callable,
    cache_get: callable,
    cache_set: callable
) -> dict:
```

**Behaviour:**
- `source`: path to video file, image sequence directory, or ZIP archive.
- `wav_path`: output path for 16 kHz mono WAV.
- `ffmpeg_runner(cmd: list[str]) -> dict`: runs ffmpeg command, returns `{"status": "OK"}` or `{"status": "ERROR", "stderr": str}`.
- `get_source_size_mtime(source: str) -> dict`: returns `{"size": int, "mtime": float}` or `{"status": "NOT_FOUND"}`.
- `cache_get(key: str) -> dict | None`: returns cached `{"wav_path": str, "source_size": int, "source_mtime": float}` or None.
- `cache_set(key: str, value: dict) -> None`: stores cache entry.
- **Cache key**: `f"extract_audio:{source}:{wav_path}"`.
- If cache hit (size+mtime match), return `{"status": "OK", "wav_path": wav_path, "from_cache": true}`.
- Detect source kind: if `source` ends with `.zip` or is a directory containing only image files (extensions .png,.jpg,.jpeg,.tiff,.bmp,.dpx,.exr), return `{"status": "UNAVAILABLE"}`.
- Run ffmpeg: `-i {source} -vn -acodec pcm_s16le -ar 16000 -ac 1 {wav_path}`.
- If ffmpeg fails with "no audio stream" or output WAV has zero frames, return `{"status": "NO_AUDIO_STREAM"}`.
- On success, cache and return `{"status": "OK", "wav_path": wav_path, "from_cache": false}`.

**Worked Example:**
```python
# Inputs
source = "/media/clip.mp4"
wav_path = "/tmp/clip.wav"
def ffmpeg_runner(cmd): return {"status": "OK"}
def get_source_size_mtime(s): return {"size": 1024000, "mtime": 1700000000.0}
def cache_get(k): return None
def cache_set(k, v): pass

# Call
extract_audio(source, wav_path, ffmpeg_runner, get_source_size_mtime, cache_get, cache_set)

# Expected Output
{"status": "OK", "wav_path": "/tmp/clip.wav", "from_cache": false}
```

```python
# Inputs (cache hit)
def cache_get(k): return {"wav_path": "/tmp/clip.wav", "source_size": 1024000, "source_mtime": 1700000000.0}

# Call
extract_audio(source, wav_path, ffmpeg_runner, get_source_size_mtime, cache_get, cache_set)

# Expected Output
{"status": "OK", "wav_path": "/tmp/clip.wav", "from_cache": true}
```

```python
# Inputs (image sequence)
source = "/media/frames/"
def get_source_size_mtime(s): return {"size": 5000000, "mtime": 1700000000.0}

# Call
extract_audio(source, wav_path, ffmpeg_runner, get_source_size_mtime, cache_get, cache_set)

# Expected Output
{"status": "UNAVAILABLE"}
```

```python
# Inputs (silent video)
def ffmpeg_runner(cmd): return {"status": "OK"}  # but wav has 0 frames
import wave
def mock_wave_open(path, mode):
    class MockWav:
        def getnframes(self): return 0
        def getframerate(self): return 16000
        def getsampwidth(self): return 2
        def getnchannels(self): return 1
        def readframes(self, n): return b""
        def close(self): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
    return MockWav()
# (Assume wave.open is patched to mock_wave_open)

# Call
extract_audio("/media/silent.mp4", wav_path, ffmpeg_runner, get_source_size_mtime, cache_get, cache_set)

# Expected Output
{"status": "NO_AUDIO_STREAM"}
```

---

### Function 2: energy_profile
**Signature:**
```python
def energy_profile(
    wav_path: str,
    win: float = 0.05,
    wave_open: callable = wave.open,
    np_array: callable = np.array,
    np_sqrt: callable = np.sqrt,
    np_mean: callable = np.mean,
    np_log10: callable = np.log10
) -> dict:
```

**Behaviour:**
- Read WAV via `wave_open(wav_path, 'rb')`. Expect 16-bit mono 16kHz.
- Frame size = `int(win * sample_rate)`.
- For each window, compute RMS: `sqrt(mean(samples^2))`, convert to dB: `20 * log10(rms / 32768.0)`.
- If rms == 0, dB = -120.0.
- Return `{"status": "OK", "profile": [{"time": float, "db": float}, ...], "sample_rate": int, "window_sec": float}`.
- `time` is window centre in seconds.

**Worked Example:**
```python
# Synthetic WAV: 16kHz, 16-bit mono, 0.2s = 3200 samples
# Window 0.05s = 800 samples. 4 windows.
# Samples: [0]*800 + [10000]*800 + [0]*800 + [5000]*800
import wave, numpy as np
def mock_wave_open(path, mode):
    class MockWav:
        def getnframes(self): return 3200
        def getframerate(self): return 16000
        def getsampwidth(self): return 2
        def getnchannels(self): return 1
        def readframes(self, n):
            # Return raw bytes for the synthetic signal
            arr = np.array([0]*800 + [10000]*800 + [0]*800 + [5000]*800, dtype=np.int16)
            return arr.tobytes()
        def close(self): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
    return MockWav()

def np_array(x, dtype=np.int16): return np.array(x, dtype=dtype)
def np_sqrt(x): return np.sqrt(x)
def np_mean(x): return np.mean(x)
def np_log10(x): return np.log10(x)

energy_profile("/tmp/test.wav", 0.05, mock_wave_open, np_array, np_sqrt, np_mean, np_log10)

# Expected Output (db values approximate)
{
  "status": "OK",
  "profile": [
    {"time": 0.025, "db": -120.0},
    {"time": 0.075, "db": 20 * np.log10(10000/32768.0)},
    {"time": 0.125, "db": -120.0},
    {"time": 0.175, "db": 20 * np.log10(5000/32768.0)}
  ],
  "sample_rate": 16000,
  "window_sec": 0.05
}
```

---

### Function 3: find_silences
**Signature:**
```python
def find_silences(
    profile: list[dict],
    thresh_db: float = -35.0,
    min_dur: float = 0.35
) -> dict:
```

**Behaviour:**
- `profile`: list of `{"time": float, "db": float}` from `energy_profile`.
- Contiguous windows with `db <= thresh_db` form a silence region.
- Merge regions separated by < 0.05s (one window).
- Keep only regions with duration >= `min_dur`.
- Return `{"status": "OK", "silences": [{"start": float, "end": float}, ...]}`.
- `start` = first window time - win/2, `end` = last window time + win/2.

**Worked Example:**
```python
profile = [
    {"time": 0.025, "db": -40.0},
    {"time": 0.075, "db": -40.0},
    {"time": 0.125, "db": -20.0},
    {"time": 0.175, "db": -40.0},
    {"time": 0.225, "db": -40.0},
    {"time": 0.275, "db": -40.0},
]
# win=0.05, thresh=-35, min_dur=0.35
# Region 1: 0.025-0.075 (dur 0.1s) -> too short, dropped
# Region 2: 0.175-0.275 (dur 0.15s) -> too short, dropped
# Result: empty

find_silences(profile, -35.0, 0.35)
# Expected Output
{"status": "OK", "silences": []}
```

```python
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
# 8 windows = 0.4s duration. start=0.0, end=0.4
find_silences(profile, -35.0, 0.35)
# Expected Output
{"status": "OK", "silences": [{"start": 0.0, "end": 0.4}]}
```

---

## Test File: test_a1_audio_io.py
- Use `unittest`.
- Test `extract_audio`: mock `ffmpeg_runner`, `get_source_size_mtime`, `cache_get/set`. Verify UNAVAILABLE for .zip and image dir, NO_AUDIO_STREAM for silent, cache hit/miss.
- Test `energy_profile`: synthesize WAV with `wave` + `numpy` (tone + silence + tone burst), assert profile length and dB values at known indices.
- Test `find_silences`: feed synthetic profile, assert silence intervals match expected start/end.
- All mocks injected as parameters; no filesystem/network.


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/a1_audio_io.py; test file: research/pieces/test_a1_audio_io.py (tests import the module by its plain file name, e.g. `from a1_audio_io import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
Sonnet G1 review (wpB1, wpB3, wpE2)


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB1
LUNA (gpt-6-luna high):
MED - research/pieces/a1_audio_io.py:78-81 - ffmpeg reports a silent source as “Output file #0 does not contain any stream”; this is returned as ERROR instead of NO_AUDIO_STREAM - Match that ffmpeg message and add a regression test.
MED - research/pieces/a1_audio_io.py:52-62 - A nonexistent image-sequence path ending in `/` is not recognized as a directory, so the worked example proceeds to ffmpeg instead of returning UNAVAILABLE - Recognize the trailing directory separator and add a test for that case.

SONNET (latest):
wpB1
PASS (no HIGH/MED). Earlier findings: nothing listed beyond header; module matches spec behaviours.
- LOW - a1_audio_io.py:219 - merge threshold hardcoded 0.05 instead of the inferred window size - use `win`.
- LOW - a1_audio_io.py:79 - real ffmpeg reports "does not contain any stream", not "no audio stream"; also match that - add substring.
- LOW - test_a1_audio_io.py:118-132 - mixed-dir test asserts no status (only that ffmpeg ran) - assert result["status"]=="OK".
- LOW - test_a1_audio_io.py:18-19 - uses POSIX literal paths /media, /tmp (not drive paths; spec uses them) - acceptable.


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB1
LUNA (gpt-6-luna medium):
MED - research/pieces/a1_audio_io.py:39-41 - A matching cache entry returns `OK` before source-kind detection, so a cached `.zip` source bypasses the required `UNAVAILABLE` result - Detect ZIP and image-sequence sources before checking the cache.

SONNET (latest):
wpB1
PASS (no HIGH/MED). Earlier findings: nothing listed beyond header; module matches spec behaviours.
- LOW - a1_audio_io.py:219 - merge threshold hardcoded 0.05 instead of the inferred window size - use `win`.
- LOW - a1_audio_io.py:79 - real ffmpeg reports "does not contain any stream", not "no audio stream"; also match that - add substring.
- LOW - test_a1_audio_io.py:118-132 - mixed-dir test asserts no status (only that ffmpeg ran) - assert result["status"]=="OK".
- LOW - test_a1_audio_io.py:18-19 - uses POSIX literal paths /media, /tmp (not drive paths; spec uses them) - acceptable.

HAIKU (low, stand-in for GLM/MiniMax):
wpB1
Result: PASS (HIGH 0, MED 0)
- LOW - research/pieces/a1_audio_io.py:83 - `result.get("stderr", "")` raises AttributeError if ffmpeg_runner returns `"stderr": None` - use `(result.get("stderr") or "")`.
- LOW - research/pieces/a1_audio_io.py:224 - merge test is `<= win + 1e-9`; spec text says separated by `< 0.05s`, so an exact one-window gap is merged where the spec wording may not merge it - confirm intent and record it; no test pins the exact-boundary case.
- Verified fixed: "does not contain any stream" match (line 84) with regression test; trailing-separator image dir (line 53) with test; merge threshold uses inferred `win`; test_extract_audio_mixed_directory asserts OK.


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB1
LUNA (gpt-6-luna medium):
LOW - research/pieces/a1_audio_io.py:48 - A nonexistent `.zip` source returns `ERROR` because the `NOT_FOUND` check runs before ZIP detection - detect ZIP sources before checking source existence

LOW - research/pieces/a1_audio_io.py:57-63 - An empty directory is not classified as an image sequence, though it contains only image files vacuously - return `UNAVAILABLE` when the directory has no non-image entries

LOW - research/pieces/a1_audio_io.py:219 - Silence regions exactly one window apart are merged, while the spec says to merge only when separated by less than one window - use a strict `< win` comparison

LOW - research/pieces/test_a1_audio_io.py:18-19 - Tests use hard-coded absolute paths such as `/media/clip.mp4` and `/tmp/clip.wav`, contrary to the test-path rule - use temporary paths from `tempfile` for test inputs and outputs

LOW - research/pieces/test_a1_audio_io.py:111-119 - The trailing-backslash test uses a hard-coded absolute drive path, contrary to the no-drive-path rule - build the test path from a temporary directory or use a relative path

SONNET (latest):
wpB1
PASS (no HIGH/MED). Earlier findings: nothing listed beyond header; module matches spec behaviours.
- LOW - a1_audio_io.py:219 - merge threshold hardcoded 0.05 instead of the inferred window size - use `win`.
- LOW - a1_audio_io.py:79 - real ffmpeg reports "does not contain any stream", not "no audio stream"; also match that - add substring.
- LOW - test_a1_audio_io.py:118-132 - mixed-dir test asserts no status (only that ffmpeg ran) - assert result["status"]=="OK".
- LOW - test_a1_audio_io.py:18-19 - uses POSIX literal paths /media, /tmp (not drive paths; spec uses them) - acceptable.

HAIKU (low, stand-in):
Summary

- wpB1: MED 1, LOW 2 - FAIL
- wpB2: PASS (LOW 2)
- wpB3: MED 1, LOW 3 - FAIL


REVIEW FINDINGS (round 5, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB1
SONNET (latest):
wpB1
PASS (no HIGH/MED). Earlier findings: nothing listed beyond header; module matches spec behaviours.
- LOW - a1_audio_io.py:219 - merge threshold hardcoded 0.05 instead of the inferred window size - use `win`.
- LOW - a1_audio_io.py:79 - real ffmpeg reports "does not contain any stream", not "no audio stream"; also match that - add substring.
- LOW - test_a1_audio_io.py:118-132 - mixed-dir test asserts no status (only that ffmpeg ran) - assert result["status"]=="OK".
- LOW - test_a1_audio_io.py:18-19 - uses POSIX literal paths /media, /tmp (not drive paths; spec uses them) - acceptable.


REVIEW FINDINGS (round 6, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB1
HAIKU (low, stand-in):
MED - research/pieces/test_a1_audio_io.py (`test_energy_profile_synthetic`) - The spec requires synthesizing a real WAV with `wave` and numpy (tone, silence and tone burst) and asserting dB values at known indices. This test injects a fake `wave_open` with constant levels, so the real `wave` read path and the default parameters never run. - Write a WAV to a `tempfile` path with `wave.open(path, "wb")`, call `energy_profile(path)` with defaults, and assert profile length and dB at the known indices.
LOW - research/pieces/a1_audio_io.py:219 - The merge test `s["start"] - last["end"] < win` compares float-derived gaps. The exact-one-window case can round below `win` and merge, which would fail `test_find_silences_exact_one_window_gap_not_merged`. - Use `< win - 1e-9`.
LOW - research/pieces/a1_audio_io.py (`extract_audio` directory check) - Only `os.sep` is tested, so on POSIX `"nonexistent\\frames\\"` is not treated as a directory. `test_extract_audio_image_sequence_with_trailing_backslash_unavailable` then fails there. - Check both `"/"` and `"\\"` explicitly.
LOW - research/pieces/a1_audio_io.py (`extract_audio` ffmpeg error return) - `result.get("stderr", "ffmpeg failed")` returns `None` when stderr is `None`. - Use `result.get("stderr") or "ffmpeg failed"`.
LOW - research/pieces/a1_audio_io.py:9 - `Any` is imported and never used. - Remove it.
LOW - research/pieces/test_a1_audio_io.py (`test_extract_audio_image_sequence_with_trailing_slash_unavailable`, `test_energy_profile_*`) - Literal POSIX paths `/nonexistent/frames/` and `/tmp/test.wav` break the tempfile-only rule. - Build the paths from a `TemporaryDirectory`.


REVIEW FINDINGS (round 7, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB1
HAIKU (low, stand-in):
MED - research/pieces/a1_audio_io.py:find_silences - `win` is inferred from `profile[1]["time"] - profile[0]["time"]` instead of the spec's fixed 0.05 window, so the half-window and merge threshold follow the timestamps - add a keyword `win: float = 0.05` (same default as `energy_profile`) and use it for both.
MED - research/pieces/test_a1_audio_io.py:test_find_silences_merge_close_regions - it merges only because the non-uniform timestamps make the inferred window 0.1; with the spec's 0.05 window that gap is not merged, so the test encodes the inference rather than the spec - pass `win` explicitly and assert merge behaviour under that window.
MED - research/pieces/test_a1_audio_io.py:test_extract_audio_image_sequence_with_trailing_slash_unavailable - it uses an existing empty temp directory, so the spec worked example (a nonexistent `.../frames/` path, handled by the `OSError` branch) is never tested - add a test with `os.path.join(tmpdir, "missing") + os.sep` asserting `UNAVAILABLE` and that ffmpeg is not called.
LOW - research/pieces/test_a1_audio_io.py:test_energy_profile_invalid_format, test_energy_profile_stereo - literal `/tmp/test.wav` is used against the tempfile-only rule - build the path inside a `TemporaryDirectory`.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/a1_audio_io.py
```python
<complete module source>
```
FILE: research/pieces/test_a1_audio_io.py
```python
<complete test source>
```
