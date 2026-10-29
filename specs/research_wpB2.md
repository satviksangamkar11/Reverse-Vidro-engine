
# WP-B2: Transcription & Gap Classification
# Optional faster_whisper (lazy import). Pure Python logic otherwise.

## Module: a2_transcribe.py

### Function 1: transcribe
**Signature:**
```python
def transcribe(
    wav_path: str,
    language: str | None = None,
    model_size: str = "small",
    runner: callable | None = None,
    import_faster_whisper: callable = lambda: __import__("faster_whisper")
) -> dict:
```

**Behaviour:**
- If `runner` provided: call `runner(wav_path, language, model_size)` and return its result directly (must be `{"status": "OK", "segments": [...]} or {"status": "TRANSCRIBER_UNAVAILABLE"}`).
- Else: try `import_faster_whisper()`. On `ImportError`, return `{"status": "TRANSCRIBER_UNAVAILABLE"}`.
- Instantiate `WhisperModel(model_size, device="cpu", compute_type="int8")`.
- Call `model.transcribe(wav_path, language=language, beam_size=5, vad_filter=True)`.
- Collect segments: each `{"start": float, "end": float, "text": str, "avg_logprob": float}`.
- Detect language from first segment or model info; expect mr/hi/en but accept any.
- Flag segments with `avg_logprob < -1.0` by adding `"confidence": "LOW_CONFIDENCE"`, else `"confidence": "OK"`.
- Return `{"status": "OK", "segments": [...], "language": str}`.
- Transcript text is data, never verified fact.

**Worked Example:**
```python
# Fake runner for test
def fake_runner(wav_path, language, model_size):
    return {
        "status": "OK",
        "segments": [
            {"start": 0.5, "end": 1.2, "text": "hello", "avg_logprob": -0.5},
            {"start": 2.0, "end": 3.0, "text": "world", "avg_logprob": -1.5}
        ],
        "language": "en"
    }

transcribe("/tmp/test.wav", runner=fake_runner)
# Expected Output
{
  "status": "OK",
  "segments": [
    {"start": 0.5, "end": 1.2, "text": "hello", "avg_logprob": -0.5, "confidence": "OK"},
    {"start": 2.0, "end": 3.0, "text": "world", "avg_logprob": -1.5, "confidence": "LOW_CONFIDENCE"}
  ],
  "language": "en"
}
```

```python
# No runner, faster_whisper missing
def bad_import(): raise ImportError("no module")
transcribe("/tmp/test.wav", import_faster_whisper=bad_import)
# Expected Output
{"status": "TRANSCRIBER_UNAVAILABLE"}
```

---

### Function 2: classify_gaps
**Signature:**
```python
def classify_gaps(
    silences: list[dict],
    speech_segments: list[dict]
) -> dict:
```

**Behaviour:**
- `silences`: `[{"start": float, "end": float}, ...]` from `find_silences`.
- `speech_segments`: `[{"start": float, "end": float, ...}, ...]` from `transcribe` (only start/end used).
- For each silence:
  - Find speech segment immediately before (max end <= silence start) and after (min start >= silence end).
  - If both exist and `silence.start - prev.end <= 2.0` and `next.start - silence.end <= 2.0`: label `"SPEECH_PAUSE"`.
  - Elif `silence.end - silence.start >= 1.0` and no overlapping speech (i.e., no speech segment with `seg.start < silence.end and seg.end > silence.start`): label `"INTENTIONAL_SILENCE_CANDIDATE"`.
  - Else: label `"LOW_VOLUME_ONLY"`.
- Return `{"status": "OK", "gaps": [{"start": float, "end": float, "label": str}, ...]}`.
- Candidates only; never assert intent.

**Worked Example:**
```python
silences = [
    {"start": 1.0, "end": 1.5},   # between speech, gap 0.5s each side -> SPEECH_PAUSE
    {"start": 3.0, "end": 4.5},   # 1.5s, no speech around -> INTENTIONAL_SILENCE_CANDIDATE
    {"start": 5.0, "end": 5.2},   # 0.2s, no speech -> LOW_VOLUME_ONLY
]
speech_segments = [
    {"start": 0.0, "end": 0.5},
    {"start": 2.0, "end": 2.5},
    {"start": 6.0, "end": 7.0},
]

classify_gaps(silences, speech_segments)
# Expected Output
{
  "status": "OK",
  "gaps": [
    {"start": 1.0, "end": 1.5, "label": "SPEECH_PAUSE"},
    {"start": 3.0, "end": 4.5, "label": "INTENTIONAL_SILENCE_CANDIDATE"},
    {"start": 5.0, "end": 5.2, "label": "LOW_VOLUME_ONLY"}
  ]
}
```

---

### Function 3: find_onsets
**Signature:**
```python
def find_onsets(
    profile: list[dict],
    rise_db: float = 9.0,
    min_gap: float = 0.15
) -> dict:
```

**Behaviour:**
- `profile`: `[{"time": float, "db": float}, ...]` from `energy_profile`.
- For each window i > 0, compute `delta = profile[i]["db"] - profile[i-1]["db"]`.
- If `delta >= rise_db` and time since last onset >= `min_gap`: record onset at `profile[i]["time"]` with `rise_db = delta`.
- Label always `"SOUND_ONSET"` (never "whoosh"/"music").
- Return `{"status": "OK", "onsets": [{"time": float, "rise_db": float, "label": "SOUND_ONSET"}, ...]}`.

**Worked Example:**
```python
profile = [
    {"time": 0.025, "db": -40.0},
    {"time": 0.075, "db": -30.0},  # delta +10 >= 9 -> onset at 0.075
    {"time": 0.125, "db": -35.0},
    {"time": 0.175, "db": -25.0},  # delta +10, but gap 0.1 < 0.15 -> skip
    {"time": 0.225, "db": -20.0},  # delta +5 < 9 -> skip
    {"time": 0.275, "db": -10.0},  # delta +10, gap 0.15 from last onset (0.075) -> onset at 0.275
]

find_onsets(profile, 9.0, 0.15)
# Expected Output
{
  "status": "OK",
  "onsets": [
    {"time": 0.075, "rise_db": 10.0, "label": "SOUND_ONSET"},
    {"time": 0.275, "rise_db": 10.0, "label": "SOUND_ONSET"}
  ]
}
```

---

## Test File: test_a2_transcribe.py
- Use `unittest`.
- Test `transcribe`: inject fake runner returning segments with high/low logprob; assert confidence flags and language passthrough. Test `TRANSCRIBER_UNAVAILABLE` via bad import.
- Test `classify_gaps`: use worked example data; assert labels exactly.
- Test `find_onsets`: use worked example profile; assert onset times and rise_db values.
- No real faster_whisper; all dependencies injected.


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/a2_transcribe.py; test file: research/pieces/test_a2_transcribe.py (tests import the module by its plain file name, e.g. `from a2_transcribe import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB2
Verdict: CODE wrong vs the spec worked example (spec prose and example conflict); rounds 2 and 3 were API failures; round 1 was a format failure.
- Rounds: 0 nemotron ok, 1 test failed; round 1 nemotron status=200 but only the module block returned (test file missing, "files bad"); rounds 2 and 3 codex status=0 (API failures). Disk still holds the round 0 files.
- Only failing test: test_classify_gaps_worked_example. Silence 3.0-4.5 has speech ending 2.5 (gap 0.5) and starting 6.0 (gap 1.5), so the written rule "both gaps <= 2.0 -> SPEECH_PAUSE" returns SPEECH_PAUSE, but the worked example requires INTENTIONAL_SILENCE_CANDIDATE. The test follows the example, so the test is right; the code follows the prose. Fix in classify_gaps: SPEECH_PAUSE additionally requires silence duration < 1.0 (equivalently check the INTENTIONAL test, dur >= 1.0 and no overlap, first). Verified this keeps the other two worked-example rows and all edge-case tests correct. Round 1's module already had this fix (`and sil_dur < 1.0`), so reuse it. Log the spec contradiction in DECISION_LOG.
- Test weakness to fix (not failing): test_transcribe_transcriber_unavailable passes "/tmp/test.wav", a nonexistent absolute path, so it returns UNAVAILABLE from the file-existence check and never exercises the bad_import path (and breaks the no-absolute-paths rule). Create a non-empty file in tempfile and then inject bad_import. Add one fake-faster_whisper test for the real path (confidence flags, language from info).


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB2
LUNA (gpt-6-luna high):
MED - research/pieces/test_a2_transcribe.py:1 - Missing the required fake `faster_whisper` test for the real transcriber path, including confidence flags and language detection from model info - Add an injected fake module/model and assert the transcribed output.

LOW - docs/pilot/DECISION_LOG.md:93 - The worked-example versus prose contradiction for `classify_gaps` is not recorded - Add the decision explaining why silences of at least 1.0 seconds without overlapping speech are classified as candidates.

SONNET (latest):
wpB2
HIGH 0, MED 1
- Earlier findings: classify_gaps worked example fixed (sil_dur < 1.0 added); UNAVAILABLE test now uses a real tempfile and reaches bad_import. Not fixed: fake-faster_whisper test.
- MED - test_a2_transcribe.py (absent) - real faster_whisper path (WhisperModel(model_size, device="cpu", compute_type="int8"), transcribe kwargs beam_size=5/vad_filter=True, per-segment LOW_CONFIDENCE at avg_logprob < -1.0, language from info) is untested; add a test with an injected fake module/WhisperModel returning generator segments and info.language.
- LOW - a2_transcribe.py:49-57 - segments_gen is lazy; errors raised while iterating (line 60) are uncaught - wrap the loop in the try.
- LOW - a2_transcribe.py:30-37 - missing/empty wav returns TRANSCRIBER_UNAVAILABLE (not in spec, misleading) - leave documented or use a distinct status.
- LOW - test_a2_transcribe.py:19 - absolute "/tmp/test.wav" in runner test - use a tempdir path.
- LOW - docs/pilot/DECISION_LOG.md - spec contradiction (prose vs worked example, sil_dur < 1.0) not logged.
- LOW - a2_transcribe.py:155 - onset min_gap compare on float subtraction can flip at exact boundary (0.20-0.05 = 0.15000000000000002) - compare with small epsilon.


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB2
LUNA (gpt-6-luna medium):
MED - research/pieces/test_a2_transcribe.py:76 - The fake faster_whisper test does not verify the required model constructor arguments or transcribe kwargs - Assert `model_size`, `device="cpu"`, `compute_type="int8"`, `beam_size=5`, and `vad_filter=True`.

SONNET (latest):
wpB2
HIGH 0, MED 1
- Earlier findings: classify_gaps worked example fixed (sil_dur < 1.0 added); UNAVAILABLE test now uses a real tempfile and reaches bad_import. Not fixed: fake-faster_whisper test.
- MED - test_a2_transcribe.py (absent) - real faster_whisper path (WhisperModel(model_size, device="cpu", compute_type="int8"), transcribe kwargs beam_size=5/vad_filter=True, per-segment LOW_CONFIDENCE at avg_logprob < -1.0, language from info) is untested; add a test with an injected fake module/WhisperModel returning generator segments and info.language.
- LOW - a2_transcribe.py:49-57 - segments_gen is lazy; errors raised while iterating (line 60) are uncaught - wrap the loop in the try.
- LOW - a2_transcribe.py:30-37 - missing/empty wav returns TRANSCRIBER_UNAVAILABLE (not in spec, misleading) - leave documented or use a distinct status.
- LOW - test_a2_transcribe.py:19 - absolute "/tmp/test.wav" in runner test - use a tempdir path.
- LOW - docs/pilot/DECISION_LOG.md - spec contradiction (prose vs worked example, sil_dur < 1.0) not logged.
- LOW - a2_transcribe.py:155 - onset min_gap compare on float subtraction can flip at exact boundary (0.20-0.05 = 0.15000000000000002) - compare with small epsilon.

HAIKU (low, stand-in for GLM/MiniMax):
wpB2
Result: PASS (HIGH 0, MED 0)
- LOW - research/pieces/a2_transcribe.py:64 - missing `avg_logprob` defaults to -inf, which is stored in the segment and is not valid strict JSON - use 0.0 or None for the stored value while keeping the LOW_CONFIDENCE branch.
- Verified fixed: classify_gaps SPEECH_PAUSE requires `sil_dur < 1.0` (line 128), matching the worked example; fake faster_whisper test present (test_a2_transcribe.py:49); runner-path and bad-import tests use tempfile paths; segment iteration errors caught (line 76); onset epsilon (line 165).
- LOW - docs/pilot/DECISION_LOG.md (no entry) - the classify_gaps spec-vs-worked-example contradiction (sil_dur < 1.0) is not logged; grep finds no entry - add the decision entry.


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB2
LUNA (gpt-6-luna medium):
LOW - research/pieces/a2_transcribe.py:64 - Missing `avg_logprob` is stored as `-inf`, which is not valid strict JSON - use a finite value or `None` while preserving the low-confidence flag

LOW - docs/pilot/DECISION_LOG.md - The `classify_gaps` prose and worked example conflict, but the required decision is not recorded - log why the worked example’s 1.5-second silence is classified as an intentional-silence candidate

SONNET (latest):
wpB2
HIGH 0, MED 1
- Earlier findings: classify_gaps worked example fixed (sil_dur < 1.0 added); UNAVAILABLE test now uses a real tempfile and reaches bad_import. Not fixed: fake-faster_whisper test.
- MED - test_a2_transcribe.py (absent) - real faster_whisper path (WhisperModel(model_size, device="cpu", compute_type="int8"), transcribe kwargs beam_size=5/vad_filter=True, per-segment LOW_CONFIDENCE at avg_logprob < -1.0, language from info) is untested; add a test with an injected fake module/WhisperModel returning generator segments and info.language.
- LOW - a2_transcribe.py:49-57 - segments_gen is lazy; errors raised while iterating (line 60) are uncaught - wrap the loop in the try.
- LOW - a2_transcribe.py:30-37 - missing/empty wav returns TRANSCRIBER_UNAVAILABLE (not in spec, misleading) - leave documented or use a distinct status.
- LOW - test_a2_transcribe.py:19 - absolute "/tmp/test.wav" in runner test - use a tempdir path.
- LOW - docs/pilot/DECISION_LOG.md - spec contradiction (prose vs worked example, sil_dur < 1.0) not logged.
- LOW - a2_transcribe.py:155 - onset min_gap compare on float subtraction can flip at exact boundary (0.20-0.05 = 0.15000000000000002) - compare with small epsilon.

HAIKU (low, stand-in):
Summary

- wpB1: MED 1, LOW 2 - FAIL
- wpB2: PASS (LOW 2)
- wpB3: MED 1, LOW 3 - FAIL


REVIEW FINDINGS (round 5, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpB2
SONNET (latest):
wpB2
HIGH 0, MED 1
- Earlier findings: classify_gaps worked example fixed (sil_dur < 1.0 added); UNAVAILABLE test now uses a real tempfile and reaches bad_import. Not fixed: fake-faster_whisper test.
- MED - test_a2_transcribe.py (absent) - real faster_whisper path (WhisperModel(model_size, device="cpu", compute_type="int8"), transcribe kwargs beam_size=5/vad_filter=True, per-segment LOW_CONFIDENCE at avg_logprob < -1.0, language from info) is untested; add a test with an injected fake module/WhisperModel returning generator segments and info.language.
- LOW - a2_transcribe.py:49-57 - segments_gen is lazy; errors raised while iterating (line 60) are uncaught - wrap the loop in the try.
- LOW - a2_transcribe.py:30-37 - missing/empty wav returns TRANSCRIBER_UNAVAILABLE (not in spec, misleading) - leave documented or use a distinct status.
- LOW - test_a2_transcribe.py:19 - absolute "/tmp/test.wav" in runner test - use a tempdir path.
- LOW - docs/pilot/DECISION_LOG.md - spec contradiction (prose vs worked example, sil_dur < 1.0) not logged.
- LOW - a2_transcribe.py:155 - onset min_gap compare on float subtraction can flip at exact boundary (0.20-0.05 = 0.15000000000000002) - compare with small epsilon.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/a2_transcribe.py
```python
<complete module source>
```
FILE: research/pieces/test_a2_transcribe.py
```python
<complete test source>
```
