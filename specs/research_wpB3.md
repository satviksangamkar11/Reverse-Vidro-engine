
# WP-B3: Cut Alignment & Orchestration
# Depends on dict shapes from wpB1/wpB2 (no imports).

## Module: a3_align.py

### Function 1: align_to_cuts
**Signature:**
```python
def align_to_cuts(
    cut_times: list[float],
    silences: list[dict],
    onsets: list[dict],
    speech: list[dict],
    tol: float = 0.25
) -> dict:
```

**Behaviour:**
- `cut_times`: list of cut timestamps in seconds.
- `silences`: `[{"start": float, "end": float}, ...]`.
- `onsets`: `[{"time": float, "rise_db": float, "label": "SOUND_ONSET"}, ...]`.
- `speech`: `[{"start": float, "end": float, ...}, ...]` (from transcribe).
- For each cut time `ct`:
  - `near_onset`: nearest onset with `abs(onset["time"] - ct) <= tol`, else `null`.
  - `in_silence`: true if any silence has `start <= ct <= end`, else false.
  - `speech_active`: true if any speech segment has `start <= ct <= end`, else false.
  - `speech_pause_within_tol`: true if any silence labelled `SPEECH_PAUSE` (from gaps) has `start <= ct <= end` and `abs(ct - (silence.start + silence.end)/2) <= tol`? No: spec says "speech_pause_within_tol" – interpret as: there exists a speech pause (gap between speech segments <=2s) that contains the cut time within tol of its centre. But we don't have gap labels here. Simpler: check if cut falls in a silence that is between two speech segments with gaps <=2s. Since we only have silences and speech, compute on the fly: find silence containing ct, then check if there is speech before and after within 2s. If yes, true.
  - `relationship`: always `"CO_OCCURS"` (never causal).
- Return `{"status": "OK", "alignment": [{"cut": float, "near_onset": dict|null, "in_silence": bool, "speech_active": bool, "speech_pause_within_tol": bool, "relationship": "CO_OCCURS"}, ...]}`.

**Worked Example:**
```python
cut_times = [1.0, 2.5, 4.0]
silences = [{"start": 0.8, "end": 1.2}, {"start": 3.5, "end": 4.5}]
onsets = [{"time": 1.05, "rise_db": 12.0, "label": "SOUND_ONSET"}, {"time": 3.8, "rise_db": 10.0, "label": "SOUND_ONSET"}]
speech = [{"start": 0.0, "end": 0.7}, {"start": 1.3, "end": 2.0}, {"start": 5.0, "end": 6.0}]

# Cut 1.0: in silence 0.8-1.2 (true), near onset 1.05 (diff 0.05 <= 0.25), speech_active false (no speech at 1.0), speech_pause_within_tol: silence 0.8-1.2 has speech before (ends 0.7, gap 0.1<=2) and after (starts 1.3, gap 0.1<=2) -> true.
# Cut 2.5: not in silence, nearest onset 1.05 (diff 1.45>0.25) -> null, speech_active false (speech ends 2.0), speech_pause_within_tol false.
# Cut 4.0: in silence 3.5-4.5, near onset 3.8 (diff 0.2), speech_active false, speech_pause_within_tol: silence 3.5-4.5 has speech before? last speech ends 2.0, gap 1.5<=2; speech after starts 5.0, gap 0.5<=2 -> true.

align_to_cuts(cut_times, silences, onsets, speech, 0.25)
# Expected Output
{
  "status": "OK",
  "alignment": [
    {"cut": 1.0, "near_onset": {"time": 1.05, "rise_db": 12.0, "label": "SOUND_ONSET"}, "in_silence": true, "speech_active": false, "speech_pause_within_tol": true, "relationship": "CO_OCCURS"},
    {"cut": 2.5, "near_onset": None, "in_silence": false, "speech_active": false, "speech_pause_within_tol": false, "relationship": "CO_OCCURS"},
    {"cut": 4.0, "near_onset": {"time": 3.8, "rise_db": 10.0, "label": "SOUND_ONSET"}, "in_silence": true, "speech_active": false, "speech_pause_within_tol": true, "relationship": "CO_OCCURS"}
  ]
}
```

---

### Function 2: analyze_audio
**Signature:**
```python
def analyze_audio(
    source: str,
    kind: str,
    cut_times: list[float],
    folder: str,
    transcribe_fn: callable,
    extract_audio_fn: callable,
    energy_profile_fn: callable,
    find_silences_fn: callable,
    find_onsets_fn: callable,
    classify_gaps_fn: callable,
    align_to_cuts_fn: callable,
    write_json_atomic: callable,
    read_json: callable,
    path_exists: callable,
    get_size_mtime: callable,
    cache_get: callable,
    cache_set: callable,
    now: callable
) -> dict:
```

**Behaviour:**
- `kind`: "video" | "image_sequence" | "zip" (passed through to extract_audio logic).
- `folder`: output directory for `audio_evidence.json`.
- `write_json_atomic(path: str, data: dict) -> dict`: writes to tmp then rename, returns `{"status": "OK"}` or `{"status": "ERROR"}`.
- `read_json(path: str) -> dict | None`: returns parsed JSON or None.
- `path_exists(path: str) -> bool`.
- `get_size_mtime(path: str) -> dict`: `{"size": int, "mtime": float}` or `{"status": "NOT_FOUND"}`.
- `cache_get(key: str) -> dict | None`, `cache_set(key: str, value: dict) -> None`: for wav/transcript cache.
- `now() -> float`: current timestamp for uncertainty notes.
- **Cache keys**: `f"wav:{source}"`, `f"transcript:{source}:{model_size}"` (model_size="small" fixed).
- **Resumable logic**:
  1. Check `folder/audio_evidence.json` exists and is valid -> return it (with `from_cache: true`).
  2. Call `extract_audio_fn(source, wav_path, ...)` with `wav_path = f"{folder}/audio.wav"`. Pass cache functions.
  3. If extract returns `UNAVAILABLE` or `NO_AUDIO_STREAM`: write evidence with `audio_status` = that status, empty other sections, uncertainty note "no audio source" or "silent source".
  4. Else: call `energy_profile_fn(wav_path)`, `find_silences_fn(profile)`, `find_onsets_fn(profile)`.
  5. Call `transcribe_fn(wav_path, runner=None)` (uses default model_size="small").
  6. Call `classify_gaps_fn(silences, transcript_segments)`.
  7. Call `align_to_cuts_fn(cut_times, silences, onsets, transcript_segments)`.
  8. Build evidence dict:
     ```json
     {
       "audio_status": "OK" | "NO_AUDIO_STREAM" | "UNAVAILABLE",
       "transcript": {"status": "...", "segments": [...], "language": "..."} | {"status": "TRANSCRIBER_UNAVAILABLE"},
       "silences": [{"start", "end"}, ...],
       "gaps": [{"start", "end", "label"}, ...],
       "onsets": [{"time", "rise_db", "label"}, ...],
       "cut_alignment": [{"cut", "near_onset", "in_silence", "speech_active", "speech_pause_within_tol", "relationship"}, ...],
       "uncertainty_notes": [...]
     }
     ```
  9. Write atomically via `write_json_atomic`.
  10. Return evidence dict with added `"from_cache": false`.

**Worked Example:**
```python
# Minimal mocks for a successful run
source = "/media/clip.mp4"
kind = "video"
cut_times = [1.0, 2.5]
folder = "/tmp/out"

def transcribe_fn(wav_path, **kw):
    return {"status": "OK", "segments": [{"start": 0.0, "end": 1.0, "text": "hi", "avg_logprob": -0.5, "confidence": "OK"}], "language": "en"}

def extract_audio_fn(source, wav_path, **kw):
    return {"status": "OK", "wav_path": wav_path, "from_cache": False}

def energy_profile_fn(wav_path, **kw):
    return {"status": "OK", "profile": [{"time": 0.5, "db": -20.0}], "sample_rate": 16000, "window_sec": 0.05}

def find_silences_fn(profile, **kw):
    return {"status": "OK", "silences": []}

def find_onsets_fn(profile, **kw):
    return {"status": "OK", "onsets": []}

def classify_gaps_fn(silences, speech):
    return {"status": "OK", "gaps": []}

def align_to_cuts_fn(cut_times, silences, onsets, speech, **kw):
    return {"status": "OK", "alignment": [{"cut": ct, "near_onset": None, "in_silence": False, "speech_active": False, "speech_pause_within_tol": False, "relationship": "CO_OCCURS"} for ct in cut_times]}

def write_json_atomic(path, data): return {"status": "OK"}
def read_json(path): return None
def path_exists(path): return False
def get_size_mtime(path): return {"status": "NOT_FOUND"}
def cache_get(k): return None
def cache_set(k, v): pass
def now(): return 1700000000.0

analyze_audio(source, kind, cut_times, folder, transcribe_fn, extract_audio_fn, energy_profile_fn, find_silences_fn, find_onsets_fn, classify_gaps_fn, align_to_cuts_fn, write_json_atomic, read_json, path_exists, get_size_mtime, cache_get, cache_set, now)

# Expected Output (abridged)
{
  "status": "OK",  # implicit top-level? spec says returns dict with sections... assume top-level status OK
  "audio_status": "OK",
  "transcript": {"status": "OK", "segments": [{"start": 0.0, "end": 1.0, "text": "hi", "avg_logprob": -0.5, "confidence": "OK"}], "language": "en"},
  "silences": [],
  "gaps": [],
  "onsets": [],
  "cut_alignment": [
    {"cut": 1.0, "near_onset": None, "in_silence": False, "speech_active": False, "speech_pause_within_tol": False, "relationship": "CO_OCCURS"},
    {"cut": 2.5, "near_onset": None, "in_silence": False, "speech_active": False, "speech_pause_within_tol": False, "relationship": "CO_OCCURS"}
  ],
  "uncertainty_notes": [],
  "from_cache": False
}
```

```python
# Cache hit on final evidence
def read_json(path):
    return {
        "audio_status": "OK",
        "transcript": {"status": "OK", "segments": [], "language": "en"},
        "silences": [], "gaps": [], "onsets": [],
        "cut_alignment": [], "uncertainty_notes": []
    }
def path_exists(path): return True

analyze_audio(source, kind, cut_times, folder, transcribe_fn, extract_audio_fn, energy_profile_fn, find_silences_fn, find_onsets_fn, classify_gaps_fn, align_to_cuts_fn, write_json_atomic, read_json, path_exists, get_size_mtime, cache_get, cache_set, now)

# Expected Output
{
  "audio_status": "OK",
  "transcript": {"status": "OK", "segments": [], "language": "en"},
  "silences": [], "gaps": [], "onsets": [],
  "cut_alignment": [], "uncertainty_notes": [],
  "from_cache": True
}
```

---

## Test File: test_a3_align.py
- Use `unittest`.
- Test `align_to_cuts`: use worked example; assert each field exactly.
- Test `analyze_audio`:
  - Mock all injected functions.
  - Test happy path: verify all sub-functions called, evidence written, structure matches.
  - Test `UNAVAILABLE` from extract_audio: assert `audio_status="UNAVAILABLE"`, empty sections, uncertainty note present.
  - Test `NO_AUDIO_STREAM`: similar.
  - Test `TRANSCRIBER_UNAVAILABLE` from transcribe: transcript section has that status.
  - Test cache hit on final JSON: returns early with `from_cache: true`.
  - Test resumable: mock cache_get for wav/transcript to return cached entries; verify extract_audio/transcribe not called (or called with cache hit).
- All I/O and time mocked via injected callables.


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/a3_align.py; test file: research/pieces/test_a3_align.py (tests import the module by its plain file name, e.g. `from a3_align import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
Sonnet G1 review (wpB1, wpB3, wpE2)


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB3
LUNA (gpt-6-luna high):
HIGH - research/pieces/a3_align.py:114 - `analyze_audio` rejects output folders outside `/tmp` or the current working directory, including normal system temp folders - remove the sandbox restriction and build output paths from `folder`.
MED - research/pieces/a3_align.py:71 - `speech_pause_within_tol` incorrectly requires the cut to be near the silence centre; a cut elsewhere in a qualifying silence returns false - remove the centre-distance check and update the contradictory test at `test_a3_align.py:81`.
MED - research/pieces/a3_align.py:138 - The call to the real `extract_audio` function omits required `ffmpeg_runner` and `get_source_size_mtime` arguments and passes unsupported `kind`, so it raises `TypeError` - provide compatible runner and size/mtime plumbing, and pass only supported arguments.
MED - research/pieces/a3_align.py:144 - An extraction result such as `{"status": "ERROR"}` falls through and is reported as `audio_status="OK"` - handle every non-`OK` extraction status and skip downstream analysis.
MED - research/pieces/a3_align.py:132 - A cached WAV is accepted without checking its source metadata or whether the WAV still exists; failed transcripts are also cached at line 196 and can remain unavailable indefinitely - validate WAV cache entries with `get_size_mtime` and cache transcripts only on success.

SONNET (latest):
wpB3
- HIGH - a3_align.py:143-166 - extract result with status ERROR (ffmpeg failure / source NOT_FOUND from real a1) is not handled; code falls through to energy_profile_fn on a nonexistent wav and raises - treat any status other than OK as failure: write evidence with audio_status=that status + uncertainty note, or return it, and add a test.
- HIGH - a3_align.py:111-118 - hardcoded sandbox check (abspath("/tmp") or cwd, plain startswith) raises ValueError for any output folder elsewhere (e.g. another drive, "/tmpfoo" also passes wrongly); not in spec and breaks real use - delete the check; use folder as given (`f"{folder}/audio.wav"`).
- MED - a3_align.py:70-73 - requires `abs(ct-centre) <= tol` for speech_pause_within_tol; spec's final interpretation is only "cut in a silence with speech before and after within 2s" (the centre test is the rejected "No:" variant). Cut 3.6 in silence 3.5-4.5 wrongly False - remove the centre condition and fix test_a3_align.py:81-86 which encodes the wrong rule.
- MED - a3_align.py:194-196 - caches transcript regardless of status, so a TRANSCRIBER_UNAVAILABLE/error result is cached permanently and never retried - only cache_set when status == "OK".
- MED - a3_align.py:130-141,189-192 - wav/transcript caches ignore source size/mtime (get_size_mtime param never used, wav existence never checked), so a changed source returns stale wav/transcript - compare stored size/mtime (or include them in cache value) before using a hit.
- LOW - a3_align.py:124-128 - cached evidence accepted if merely non-None (spec: "valid"); no key check and no status:"OK" top-level key as in the spec worked example; also not checked against current cut_times - validate required keys.
- LOW - a3_align.py:162,235 - write_json_atomic result ignored.
- LOW - a3_align.py:138 - extract_audio_fn called with kind/cache_get/cache_set kwargs only; real a1.extract_audio needs ffmpeg_runner and get_source_size_mtime (get_size_mtime never forwarded) - wiring will TypeError unless wrapped.
- LOW - test_a3_align.py:94 - "/tmp/out" depends on the sandbox check; no test for extract ERROR, or that transcribe_fn gets runner=None / align gets tol.


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB3
Why rounds failed: round 0 produced code that failed tests; round 1 (Nemotron) reply lacked a3_align.py (parser, files_ok False); rounds 2-3 (Codex) returned status=0 empty = API failures, never real fix attempts. Disk code is the old round-0 version; no finding is applied.
Fixes still needed (HIGH first):
1. HIGH analyze_audio: delete the /tmp-or-cwd sandbox check (ValueError for other folders); build paths as f"{folder}/audio_evidence.json" and f"{folder}/audio.wav". Change test folder to a tempfile dir.
2. HIGH analyze_audio: any extract status other than OK (ERROR, NOT_FOUND, UNAVAILABLE, NO_AUDIO_STREAM) must write evidence with audio_status=that status, empty sections, an uncertainty note, and skip energy/transcribe. Add an ERROR test.
3. MED align_to_cuts: speech_pause_within_tol = cut inside a silence with speech before and after, both gaps <=2s; remove the centre-distance test and fix test_speech_pause_within_tol_false_when_cut_not_near_centre (cut 3.6 in 3.5-4.5 must be True).
4. MED analyze_audio: cache_set transcript only when status == "OK"; validate cached wav/transcript with get_size_mtime (store size/mtime in the value, compare on hit) and that the wav exists.
5. LOW: check write_json_atomic result; require key set on cached evidence.
Drop: the extract_audio_fn real-signature (ffmpeg_runner/kind) finding (wiring concern, injected callables per spec) and the Luna/Sonnet duplicates of items 1-4.


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB3
LUNA (gpt-6-luna medium):
LOW - research/pieces/test_a3_align.py:139 - Tests use a fixed `/tmp/test_out` instead of a temporary directory - create the folder with `tempfile.TemporaryDirectory` or `tmp_path` and clean it up.

SONNET (latest):
wpB3
Why rounds failed: round 0 produced code that failed tests; round 1 (Nemotron) reply lacked a3_align.py (parser, files_ok False); rounds 2-3 (Codex) returned status=0 empty = API failures, never real fix attempts. Disk code is the old round-0 version; no finding is applied.
Fixes still needed (HIGH first):
1. HIGH analyze_audio: delete the /tmp-or-cwd sandbox check (ValueError for other folders); build paths as f"{folder}/audio_evidence.json" and f"{folder}/audio.wav". Change test folder to a tempfile dir.
2. HIGH analyze_audio: any extract status other than OK (ERROR, NOT_FOUND, UNAVAILABLE, NO_AUDIO_STREAM) must write evidence with audio_status=that status, empty sections, an uncertainty note, and skip energy/transcribe. Add an ERROR test.
3. MED align_to_cuts: speech_pause_within_tol = cut inside a silence with speech before and after, both gaps <=2s; remove the centre-distance test and fix test_speech_pause_within_tol_false_when_cut_not_near_centre (cut 3.6 in 3.5-4.5 must be True).
4. MED analyze_audio: cache_set transcript only when status == "OK"; validate cached wav/transcript with get_size_mtime (store size/mtime in the value, compare on hit) and that the wav exists.
5. LOW: check write_json_atomic result; require key set on cached evidence.
Drop: the extract_audio_fn real-signature (ffmpeg_runner/kind) finding (wiring concern, injected callables per spec) and the Luna/Sonnet duplicates of items 1-4.

HAIKU (low, stand-in):
Summary

- wpB1: MED 1, LOW 2 - FAIL
- wpB2: PASS (LOW 2)
- wpB3: MED 1, LOW 3 - FAIL


REVIEW FINDINGS (round 5, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB3
LUNA (gpt-6-luna medium):
LOW - research/pieces/a3_align.py:213 - Successful evidence omits the top-level `"status": "OK"` shown in the worked example - add `"status": "OK"` to the evidence dict.

SONNET (latest):
wpB3
Why rounds failed: round 0 produced code that failed tests; round 1 (Nemotron) reply lacked a3_align.py (parser, files_ok False); rounds 2-3 (Codex) returned status=0 empty = API failures, never real fix attempts. Disk code is the old round-0 version; no finding is applied.
Fixes still needed (HIGH first):
1. HIGH analyze_audio: delete the /tmp-or-cwd sandbox check (ValueError for other folders); build paths as f"{folder}/audio_evidence.json" and f"{folder}/audio.wav". Change test folder to a tempfile dir.
2. HIGH analyze_audio: any extract status other than OK (ERROR, NOT_FOUND, UNAVAILABLE, NO_AUDIO_STREAM) must write evidence with audio_status=that status, empty sections, an uncertainty note, and skip energy/transcribe. Add an ERROR test.
3. MED align_to_cuts: speech_pause_within_tol = cut inside a silence with speech before and after, both gaps <=2s; remove the centre-distance test and fix test_speech_pause_within_tol_false_when_cut_not_near_centre (cut 3.6 in 3.5-4.5 must be True).
4. MED analyze_audio: cache_set transcript only when status == "OK"; validate cached wav/transcript with get_size_mtime (store size/mtime in the value, compare on hit) and that the wav exists.
5. LOW: check write_json_atomic result; require key set on cached evidence.
Drop: the extract_audio_fn real-signature (ffmpeg_runner/kind) finding (wiring concern, injected callables per spec) and the Luna/Sonnet duplicates of items 1-4.


REVIEW FINDINGS (round 6, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB3
HAIKU (low, stand-in):
MED - a3_align.py:analyze_audio (step 5-7, uncertainty_notes) - When the transcript is `TRANSCRIBER_UNAVAILABLE` or any non-OK status, no uncertainty note is added, so evidence can show `uncertainty_notes: []` with no transcript, gaps or alignment. Energy and silence failures do add notes. - Append a "transcript unavailable" note when `transcript_result["status"] != "OK"`. The happy-path test only asserts `[]` for the OK case, so it still holds.

MED - a3_align.py:analyze_audio (signature) - The `now` callable is accepted but never called. The spec says `now()` supplies the timestamp for uncertainty notes. - Record `now()` in the evidence (e.g. a `generated_at` field) or in the notes. Do not change the note strings the tests match with `assertIn`.

MED - test_a3_align.py:test_transcribe_fn_receives_runner_none - Vacuous. If `runner` is never passed, `kwargs.get("runner", None)` returns `None`, which equals the expected value, so the test passes without the required `runner=None` argument. - Use `self.assertIn("runner", kwargs)` and then `self.assertIsNone(kwargs["runner"])`.

LOW - a3_align.py:analyze_audio (extract-failure branch) - `transcript: {"status": "TRANSCRIBER_UNAVAILABLE"}` is reported when the transcriber never ran because there was no audio, so the status names the wrong cause. - Use an empty transcript section or a status that names the real cause, and update `test_extract_audio_unavailable` and `test_extract_audio_error`.

LOW - a3_align.py:analyze_audio (step 1, cache hit) - Cached final evidence is returned without checking `cut_times`, so changed cuts get stale `cut_alignment`. - Store `cut_times` in the evidence and recompute when they differ.

LOW - a3_align.py:analyze_audio (write step, both branches) - `"failed to write evidence"` is appended after `write_json_atomic` runs, so the file on disk never contains the note that the returned dict has. - Set the note before writing, or document that the note is returned only.

LOW - a3_align.py:1 - `Any` and `Optional` are imported but unused. - Remove them.

LOW - test_a3_align.py:imports - `call` is imported but unused. - Remove it.

LOW - test_a3_align.py:setUp and call_analyze - The mock wav path is the fixed `/tmp/test_out/audio.wav`, and the default `folder` uses `tempfile.mkdtemp()` with no cleanup. The brief says tests use temp directories. - Derive the mock wav path from the per-test temp folder and use `TemporaryDirectory` for the default.

LOW - test_a3_align.py (missing tests) - Nothing checks that `near_onset` picks the nearest of several onsets within tol, or the gap boundary of exactly 2.0s in `speech_pause_within_tol`. - Add one test for each.


REVIEW FINDINGS (round 7, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB3
LUNA (gpt-6-luna medium):
HIGH - research/pieces/a3_align.py:136 - `extract_audio_fn` is called with unsupported `kind`, `cache_get`, and `cache_set` keywords, so a real extractor with the specified injected-callable contract can raise `TypeError` - call it with only supported arguments.

MED - research/pieces/a3_align.py:103 - The output paths use `os.path.join` instead of the required `f"{folder}/..."`, which changes behavior for folders ending in a path separator - build both paths using the specified format.

MED - research/pieces/test_a3_align.py:143 - `call_analyze` creates a fixed-lifetime temporary directory with `mkdtemp()` and never cleans it up - use `TemporaryDirectory` for the default folder.

LOW - research/pieces/a3_align.py:163 - Extraction failure evidence uses `{"status": "TRANSCRIBER_UNAVAILABLE"}` even though transcription never ran - use an empty transcript section or identify the extraction cause.

LOW - research/pieces/a3_align.py:173 - If atomic writing fails, the uncertainty note is appended after the write, so persisted evidence omits it - add the note before writing.

LOW - research/pieces/a3_align.py:261 - If atomic writing fails, the uncertainty note is appended after the write, so persisted evidence omits it - add the note before writing.

LOW - research/pieces/test_a3_align.py:151 - Default extractor mock returns a fixed `/tmp/test_out/audio.wav`, so tests do not exercise the folder-derived WAV path - derive the mock WAV path from the per-test temporary folder.

LOW - research/pieces/test_a3_align.py:177 - The happy-path test verifies returned evidence but does not assert the evidence passed to `write_json_atomic` matches the expected structure - assert the written path and payload.

LOW - research/pieces/test_a3_align.py:308 - The `runner=None` test only checks keyword arguments; a positional `runner=None` would fail despite being explicitly allowed by its comment/spec - accept and verify either keyword or positional form.

HAIKU (low, stand-in):
MED - a3_align.py:110-118 - Cached final evidence is returned whenever its keys and `cut_times` match, even when it records a failed extraction (`status` ERROR or NOT_FOUND). A transient ffmpeg failure therefore never retries. The transcript cache was already fixed to store only successes, so this is inconsistent - return early only when the cached `status == "OK"` or `audio_status` is `UNAVAILABLE` / `NO_AUDIO_STREAM`, and re-run otherwise.

MED - a3_align.py:161 - The extract-failure evidence sets `transcript` to `{"status": "TRANSCRIBER_UNAVAILABLE"}`. The spec says UNAVAILABLE and NO_AUDIO_STREAM produce "empty other sections", and the transcriber never ran, so the status is false. Use `{"status": audio_status, "segments": [], "language": None}` and update `test_extract_audio_unavailable` to match.

MED - test_a3_align.py: `TestAnalyzeAudio.setUp` - `extract_audio_fn` returns the hard-coded `/tmp/test_out/audio.wav`, which breaks the HARD RULE that tests use tempfile directories. Derive the wav path from the per-test temp folder with `os.path.join`.

LOW - a3_align.py:173 and a3_align.py:269 - "failed to write evidence" is appended after `write_json_atomic` runs, so the file on disk lacks the note that the returned dict carries. Document in the docstring that the note is returned only, since a failed write cannot record itself.

LOW - test_a3_align.py: `TestAnalyzeAudio.call_analyze` - The default `folder=tempfile.mkdtemp()` is never cleaned up, against the tempfile rule. Drop the default, since every caller passes `folder`, or use a `TemporaryDirectory` context.

LOW - test_a3_align.py: `test_extract_audio_no_audio_stream` - The spec says this case is "similar" to UNAVAILABLE (empty sections), but the test asserts only status and note. Add `silences`, `gaps`, `onsets` and `cut_alignment` == `[]` assertions.

LOW - test_a3_align.py: `test_speech_pause_within_tol_false_just_over_2s_gap` - The speech segment `{"start": 0.0, "end": -0.001}` has end before start, so the fixture is malformed. Use `{"start": 0.0, "end": 0.0}` and `{"start": 2.001, "end": 4.0}` for the silence, which keeps the 2.001s gaps.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/a3_align.py
```python
<complete module source>
```
FILE: research/pieces/test_a3_align.py
```python
<complete test source>
```
