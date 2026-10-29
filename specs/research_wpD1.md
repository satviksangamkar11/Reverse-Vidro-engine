
# WP-D1: Beat Schema, Validation, Prompt Building, and Parsing

## Data Shapes

**BeatDict** (validated by `validate_beat`):
```python
{
    "video_id": str,
    "beat_id": str,
    "start_time": float,
    "end_time": float,
    "purpose": "ESTABLISH" | "REVEAL" | "EMPHASIZE" | "REACT" | "RESOLVE" | "TRANSITION" | "UNKNOWN",
    "how_filmed": {
        "shot_scale": str,
        "angle": str,
        "framing": str,
        "camera_movement": str,
        "cut_type": str,
        "composition": str
    },
    "how_animated": {
        "method": "POSE_SWAP" | "LAYER_MOTION" | "RIG_ARTICULATION" | "CAMERA_ONLY" | "EFFECT" | "UNKNOWN",
        "notes": str
    },
    "sound": {
        "narration": str,
        "silence": str,
        "ambience": str,
        "sfx": str,
        "music": str,
        "sync_with_cut": str
    },
    "observed": [str],
    "inferred": [{"claim": str, "confidence": "LOW" | "MEDIUM" | "HIGH", "based_on": [str]}],
    "reproduction": {
        "status": "EXISTING_PRESET" | "POSE_OR_LAYER_CHANGE" | "NEED_NEW" | "RESEARCH_ONLY",
        "artwork_needed": [str],
        "simplest_method": str
    },
    "counterexample": str,
    "evidence": [{"frame": int, "time": float}]
}
```

**ValidationResult**:
```python
{"status": "OK", "beat": BeatDict} | {"status": "ERROR", "reason": str}
```

**ParseResult**:
```python
{"status": "OK", "beat": BeatDict} | {"status": "ERROR", "reason": str}
```

## Public Functions (≤3)

### 1. validate_beat(beat: dict) -> ValidationResult
Validates a beat dict against the schema. Returns OK with the beat if valid, ERROR with reason if invalid.

**WORKED EXAMPLE**
```python
# Input
beat = {
    "video_id": "vid1",
    "beat_id": "b1",
    "start_time": 0.0,
    "end_time": 5.0,
    "purpose": "ESTABLISH",
    "how_filmed": {"shot_scale": "WS", "angle": "EYE", "framing": "CENTER", "camera_movement": "STATIC", "cut_type": "HARD", "composition": "RULE_OF_THIRDS"},
    "how_animated": {"method": "CAMERA_ONLY", "notes": "Slow zoom in"},
    "sound": {"narration": "UNAVAILABLE", "silence": "UNKNOWN", "ambience": "UNAVAILABLE", "sfx": "UNAVAILABLE", "music": "UNAVAILABLE", "sync_with_cut": "UNKNOWN"},
    "observed": ["Wide shot of landscape"],
    "inferred": [{"claim": "Sets the mood", "confidence": "MEDIUM", "based_on": ["Wide shot of landscape"]}],
    "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use preset 'landscape_establish'"},
    "counterexample": "None",
    "evidence": [{"frame": 0, "time": 0.0}, {"frame": 150, "time": 5.0}]
}
# Output
{"status": "OK", "beat": beat}
```

```python
# Input (invalid purpose)
beat_bad = {**beat, "purpose": "INVALID"}
# Output
{"status": "ERROR", "reason": "Invalid purpose: INVALID"}
```

```python
# Input (observed/inferred mixed - inferred item missing claim)
beat_bad2 = {**beat, "inferred": [{"confidence": "HIGH", "based_on": []}]}
# Output
{"status": "ERROR", "reason": "Inferred item missing required keys: claim"}
```

---

### 2. beat_prompt(shot_context: dict, audio_evidence: dict) -> dict
Builds the six-question prompt demanding JSON in the beat schema. Returns dict with `prompt` (str) and `schema_hint` (str).

**WORKED EXAMPLE**
```python
# Input
shot_context = {"video_id": "vid1", "beat_id": "b1", "start_time": 0.0, "end_time": 5.0, "shot_description": "Wide landscape, slow zoom"}
audio_evidence = {"narration": "UNAVAILABLE", "music": "Ambient drone", "sfx": "Wind", "sync_with_cut": "UNKNOWN"}
# Output
{
    "prompt": "Analyze this cinematic beat and return ONLY valid JSON matching the schema below.\n\nContext:\n- Video ID: vid1\n- Beat ID: b1\n- Time: 0.0s - 5.0s\n- Shot: Wide landscape, slow zoom\n- Audio: narration=UNAVAILABLE, music=Ambient drone, sfx=Wind, sync_with_cut=UNKNOWN\n\nAnswer these six questions in the JSON:\n1. What is the storytelling beat (purpose)? Choose from: ESTABLISH, REVEAL, EMPHASIZE, REACT, RESOLVE, TRANSITION, UNKNOWN.\n2. How was it filmed? (shot_scale, angle, framing, camera_movement, cut_type, composition)\n3. How was it animated? (method: POSE_SWAP, LAYER_MOTION, RIG_ARTICULATION, CAMERA_ONLY, EFFECT, UNKNOWN + notes)\n4. What sound is present? (narration, silence, ambience, sfx, music, sync_with_cut — each a string or UNAVAILABLE/UNKNOWN)\n5. Why might this beat work? (hypothesis)\n6. How reproducible in GranthStudio? (reproduction status, artwork_needed, simplest_method)\n\nAlso include: observed (list of strings), inferred (list of {claim, confidence: LOW/MEDIUM/HIGH, based_on: [str]}), counterexample (string), evidence (list of {frame: int, time: float}).\n\nReturn ONLY the JSON object.",
    "schema_hint": "See BeatDict schema in module docstring."
}
```

---

### 3. parse_beat(text: str, validate_fn: callable) -> ParseResult
Extracts JSON from text, validates using `validate_fn` (injected `validate_beat`), rejects if observed/inferred are mixed or purpose invalid. Returns OK with beat or ERROR with reason.

**WORKED EXAMPLE**
```python
# Input (valid JSON)
text = '''{
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
# Output (using validate_beat from above)
{"status": "OK", "beat": {...}}  # same beat dict as validate_beat example
```

```python
# Input (observed/inferred mixed - inferred inside observed)
text_bad = '''{"observed": ["Wide shot", {"claim": "Mood", "confidence": "HIGH", "based_on": []}], "inferred": []}'''
# Output
{"status": "ERROR", "reason": "Observed contains non-string items (inferred mixed in)"}
```

```python
# Input (invalid JSON)
text_bad2 = "not json"
# Output
{"status": "ERROR", "reason": "Failed to parse JSON: ..."}
```
GRAMMAR EXTENSION (owner requirement; keep <=3 public functions; no per-technique enums):
- BeatDict gains these optional-safe fields, validated by the existing validate function: `source_url` (str|None), `level_links` {"video_id","sequence_id","shot_ids":[str]} (a beat may span several shots), `verification_status` in ("UNVERIFIED","FRAME_CHECKED","AUDIO_CHECKED","BOTH_CHECKED"), `unknowns` list[str], `information_conveyed` str, and `department_findings`: dict keyed by department id "1".."16" (storytelling, narrative, direction, shot_planning, camera, composition, editing, animation_principles, performance, production, vfx, color_lighting, sound, captions, pacing, practical) -> list of finding dicts {"term": free-text technique name (no fixed enum; any evidence-supported term allowed), "status": "OBSERVED"|"NOT_OBSERVED"|"UNKNOWN", "observed": str, "evidence": [{"frame":int,"time":float}], "inferred_purpose": str|None, "alternatives": list[str], "contraindication": str|None, "confidence": "LOW"|"MEDIUM"|"HIGH"}. A department may be absent or empty: unobserved techniques stay unobserved and are never required.
- Validation rules in parse_beat/validate: any finding with status OBSERVED needs >=1 evidence entry; inferred_purpose is always a hypothesis (stored apart from observed); reject any text asserting editing software, camera lens/focal length, hidden rig or original screenplay wording as fact; if the supplied audio status is "UNAVAILABLE" (frame-only ZIP) every sound finding must have status UNKNOWN and no observed audio text, else reject.
EVIDENCE-STATUS CORRECTION: finding status is one of "OBSERVED", "NOT_OBSERVED" (examined and absent), "UNKNOWN" (examined, unclear) or "NOT_EXAMINED" (never analyzed). A department with no analysis is NOT_EXAMINED, never NOT_OBSERVED: absence of a finding must not be read as absence of the technique. UNKNOWN and NOT_EXAMINED need no fabricated evidence. validate rejects NOT_OBSERVED without a non-empty `examined_basis` string (what was looked at, e.g. frame range).


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/d1_beat_schema.py; test file: research/pieces/test_d1_beat_schema.py (tests import the module by its plain file name, e.g. `from d1_beat_schema import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD1 (d1_beat_schema.py, test_d1_beat_schema.py)
Verdict: 1 HIGH, 2 MED, 3 LOW
- HIGH - d1_beat_schema.py:31-38,40-46 - FORBIDDEN_FACT_PATTERNS contains bare `editing` (and the other four are bare substrings). Any text containing the word is rejected, including legitimate department 7 (editing) findings such as "fast editing rhythm" or "continuity editing". The spec forbids asserting editing SOFTWARE, lens/focal length, hidden rig, original screenplay wording as fact. The test "Used Adobe Premiere for editing" only passes because of the word "editing"; "Used Adobe Premiere" alone passes. - Fix: match software names (premiere, final cut, davinci, after effects, capcut, etc.) and assertion phrasing, not the bare word "editing"; add a positive test that an ordinary editing-technique finding passes.
- MED - d1_beat_schema.py:270-285 - the forbidden-fact check runs only on top-level observed[], inferred[].claim and finding.observed. It skips how_animated.notes, information_conveyed, finding.term, sound.* strings, unknowns, simplest_method, counterexample. Spec says "reject any text asserting ...". - Fix: run the check over all free-text string fields (walk the beat).
- MED - d1_beat_schema.py:372-381 - the UNAVAILABLE-audio rule fires only when the model's own output has sound.narration == "UNAVAILABLE", and only for dept "13". parse_beat has no audio_evidence input, so the model can defeat it by emitting any other narration value (or "UNKNOWN"), and top-level sound.music/sfx/ambience text is never checked. - Fix: take an optional audio_status argument (keep default None for the existing call shape) and treat any of sound.* with real text as an error when audio is UNAVAILABLE; do not key off the model's narration field alone.
- LOW - d1_beat_schema.py:66-69,173-176,247 - bool passes isinstance int/float (True as start_time/frame). NaN passes. - Fix: reject bool, check math.isfinite.
- LOW - d1_beat_schema.py:49 - validate_beat(non-dict) raises TypeError/returns wrong message instead of ERROR. - Fix: first line `if not isinstance(beat, dict)`.
- LOW - d1_beat_schema.py:324 - schema_hint says "module docstring" but the docstring holds no schema. - Fix: put the schema in the docstring or return it in schema_hint.
- Tests: test_d1_beat_schema.py:1-8 unused imports (tempfile, Path); no test for NOT_OBSERVED/UNKNOWN-forbidden-facts edge, bool/non-dict input, or a legitimate "editing" finding (would expose the HIGH).


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD1

The 48 tests pass, but none of the Sonnet findings are applied. The code on disk is the pre-review Nemotron version. Rounds 0-1 were real attempts; rounds 2-3 were API failures (status=0, empty), so the review-driven round never produced output.

Checked in the current code:
- HIGH, bare `editing` pattern: still there. `_check_forbidden_facts("fast editing rhythm")` is rejected, and "Used Adobe Premiere" passes.
- MED, forbidden-fact check scope: still only top-level observed, inferred claims and finding.observed.
- MED, audio rule: still keyed off the model's own sound.narration and only dept "13". There is no audio_status argument.
- LOW: there is no bool or isfinite check, and no non-dict guard (a string input returns "Missing required field"). schema_hint still points at a docstring that holds no schema.
- Tests: unused tempfile and Path imports are still there. The edge-case tests are missing.

Verdict: CODE incomplete, not wrong. The existing tests are consistent with the spec and should stay.

Fix, all in code plus added tests:
1. Replace the "editing" pattern with software names (premiere, final cut, davinci, after effects, capcut) and assertion phrasing. Keep the lens, focal length, hidden rig and screenplay patterns.
2. Walk every free-text string in the beat: notes, information_conveyed, term, sound.*, unknowns, simplest_method, counterexample.
3. Add an optional audio_status=None argument to parse_beat. When it is "UNAVAILABLE", reject any sound.* field with real text and any non-UNKNOWN sound finding.
4. Reject bool, and check math.isfinite for numbers.
5. Add a non-dict guard on the first line of validate_beat.
6. Put the schema in schema_hint.

New tests: a legitimate editing finding passes, "Used Adobe Premiere" is rejected, forbidden text in notes is rejected, an audio_status=UNAVAILABLE rejection with a non-UNKNOWN narration, bool/NaN/non-dict inputs, and removal of the unused imports.


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD1
LUNA (gpt-6-luna medium):
MED - research/pieces/d1_beat_schema.py:475 - `parse_beat` calls `.get()` on parsed JSON without checking it is an object, so valid JSON such as `[]` raises `AttributeError` instead of returning an ERROR result - Reject non-dict JSON with an ERROR result before accessing fields.

MED - research/pieces/d1_beat_schema.py:338 - the forbidden-fact walk skips every `sound.*` field, allowing forbidden assertions in narration, music, and other sound text - Check free-text sound values for forbidden facts.

MED - research/pieces/d1_beat_schema.py:39-44 - forbidden-fact patterns miss assertion forms such as “DaVinci Resolve was used” and “50mm lens,” allowing prohibited software and lens claims through - Cover those assertion forms while keeping ordinary technique descriptions valid.

SONNET (latest):
wpD1

The 48 tests pass, but none of the Sonnet findings are applied. The code on disk is the pre-review Nemotron version. Rounds 0-1 were real attempts; rounds 2-3 were API failures (status=0, empty), so the review-driven round never produced output.

Checked in the current code:
- HIGH, bare `editing` pattern: still there. `_check_forbidden_facts("fast editing rhythm")` is rejected, and "Used Adobe Premiere" passes.
- MED, forbidden-fact check scope: still only top-level observed, inferred claims and finding.observed.
- MED, audio rule: still keyed off the model's own sound.narration and only dept "13". There is no audio_status argument.
- LOW: there is no bool or isfinite check, and no non-dict guard (a string input returns "Missing required field"). schema_hint still points at a docstring that holds no schema.
- Tests: unused tempfile and Path imports are still there. The edge-case tests are missing.

Verdict: CODE incomplete, not wrong. The existing tests are consistent with the spec and should stay.

Fix, all in code plus added tests:
1. Replace the "editing" pattern with software names (premiere, final cut, davinci, after effects, capcut) and assertion phrasing. Keep the lens, focal length, hidden rig and screenplay patterns.
2. Walk every free-text string in the beat: notes, information_conveyed, term, sound.*, unknowns, simplest_method, counterexample.
3. Add an optional audio_status=None argument to parse_beat. When it is "UNAVAILABLE", reject any sound.* field with real text and any non-UNKNOWN sound finding.
4. Reject bool, and check math.isfinite for numbers.
5. Add a non-dict guard on the first line of validate_beat.
6. Put the schema in schema_hint.

New tests: a legitimate editing finding passes, "Used Adobe Premiere" is rejected, forbidden text in notes is rejected, an audio_status=UNAVAILABLE rejection with a non-UNKNOWN narration, bool/NaN/non-dict inputs, and removal of the unused imports.

HAIKU (low, stand-in for GLM/MiniMax):
wpD1

- MED - research/pieces/d1_beat_schema.py:91-92 - the software alternation includes bare `resolve`, and `vegas` and `avid` are bare words too. Verified: `_check_forbidden_facts("a slow resolve using a dissolve")` returns a forbidden-fact error, so a legitimate editing-technique finding is rejected. This is the same class of defect as the round-1 HIGH. Fix: drop bare `resolve`, `vegas`, `avid`; keep `davinci resolve` as a phrase. Add a positive test for "using a slow resolve" passing.
- MED - research/pieces/d1_beat_schema.py:363-371 - `skip_paths` exempts all `sound.*` fields and all `how_filmed.*` fields from the forbidden-fact walk. Verified: `sound.music="Edited with Premiere"` returns OK, and `how_filmed.angle="shot on a 35mm focal length"` returns OK. The spec requires rejecting asserted forbidden facts in any free text. Fix: remove the `sound.*` and `how_filmed.*` entries from skip_paths; keep only true identifiers and enums (video_id, beat_id, purpose, method, status, verification_status, source_url, level_links ids). Add tests for both paths.
- MED - research/pieces/d1_beat_schema.py:164, 184, 223, 239, 291, 327, 349 - membership tests like `purpose not in VALID_PURPOSES` run on unvalidated JSON values. Verified: `purpose=["ESTABLISH"]` makes validate_beat raise TypeError ("cannot use 'list' as a set element") instead of returning ERROR. Malformed model output would crash the pipeline. Fix: check `isinstance(value, str)` before each set-membership test and return ERROR on non-string. Add a test with a list-valued purpose.
- LOW - research/pieces/d1_beat_schema.py:491 - the audio trigger ORs `beat["sound"]["narration"] == "UNAVAILABLE"`, so the model's own output can switch the audio rule on and reject a real-audio beat. Fix: drop the `or` clause and use `audio_status == "UNAVAILABLE"` only. The default `audio_status=None` keeps the existing call shape.

Verdict: 3 MED, so not PASS. Items from round 1 are fixed: software-name patterns replace bare "editing"; `_walk_strings` covers the non-skipped fields; `audio_status` parameter added; bool, NaN and inf rejected; non-dict guard added; schema included in `schema_hint`; unused imports removed.


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD1
LUNA (gpt-6-luna medium):
MED - research/pieces/d1_beat_schema.py:505 - With no `audio_status` argument, the parser triggers the UNAVAILABLE rule based on the model’s own `sound.narration`; a model can therefore make a real-audio beat fail by returning `"UNAVAILABLE"` - Run the cross-check only when the supplied `audio_status` is `"UNAVAILABLE"`.

MED - research/pieces/d1_beat_schema.py:518 - The UNAVAILABLE-audio check examines findings only in department `"13"`, so audio findings placed under another department can claim observed audio despite the source having no audio - Check sound-related findings across all departments.

SONNET (latest):
wpD1

The 48 tests pass, but none of the Sonnet findings are applied. The code on disk is the pre-review Nemotron version. Rounds 0-1 were real attempts; rounds 2-3 were API failures (status=0, empty), so the review-driven round never produced output.

Checked in the current code:
- HIGH, bare `editing` pattern: still there. `_check_forbidden_facts("fast editing rhythm")` is rejected, and "Used Adobe Premiere" passes.
- MED, forbidden-fact check scope: still only top-level observed, inferred claims and finding.observed.
- MED, audio rule: still keyed off the model's own sound.narration and only dept "13". There is no audio_status argument.
- LOW: there is no bool or isfinite check, and no non-dict guard (a string input returns "Missing required field"). schema_hint still points at a docstring that holds no schema.
- Tests: unused tempfile and Path imports are still there. The edge-case tests are missing.

Verdict: CODE incomplete, not wrong. The existing tests are consistent with the spec and should stay.

Fix, all in code plus added tests:
1. Replace the "editing" pattern with software names (premiere, final cut, davinci, after effects, capcut) and assertion phrasing. Keep the lens, focal length, hidden rig and screenplay patterns.
2. Walk every free-text string in the beat: notes, information_conveyed, term, sound.*, unknowns, simplest_method, counterexample.
3. Add an optional audio_status=None argument to parse_beat. When it is "UNAVAILABLE", reject any sound.* field with real text and any non-UNKNOWN sound finding.
4. Reject bool, and check math.isfinite for numbers.
5. Add a non-dict guard on the first line of validate_beat.
6. Put the schema in schema_hint.

New tests: a legitimate editing finding passes, "Used Adobe Premiere" is rejected, forbidden text in notes is rejected, an audio_status=UNAVAILABLE rejection with a non-UNKNOWN narration, bool/NaN/non-dict inputs, and removal of the unused imports.

HAIKU (low, stand-in):
Summary
- wpD1: 2 MED (PASS fails)
- wpD2: PASS (1 LOW)
- wpD3: 3 MED (PASS fails)


REVIEW FINDINGS (round 5, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD1
LUNA (gpt-6-luna medium):
MED - research/pieces/d1_beat_schema.py:505 - When `audio_status` is omitted, `parse_beat` triggers the UNAVAILABLE-audio check from the model’s own `sound.narration`; a real-audio beat can be rejected if the model returns `"UNAVAILABLE"` - Run the cross-check only when the supplied `audio_status` is `"UNAVAILABLE"`.

SONNET (latest):
wpD1

The 48 tests pass, but none of the Sonnet findings are applied. The code on disk is the pre-review Nemotron version. Rounds 0-1 were real attempts; rounds 2-3 were API failures (status=0, empty), so the review-driven round never produced output.

Checked in the current code:
- HIGH, bare `editing` pattern: still there. `_check_forbidden_facts("fast editing rhythm")` is rejected, and "Used Adobe Premiere" passes.
- MED, forbidden-fact check scope: still only top-level observed, inferred claims and finding.observed.
- MED, audio rule: still keyed off the model's own sound.narration and only dept "13". There is no audio_status argument.
- LOW: there is no bool or isfinite check, and no non-dict guard (a string input returns "Missing required field"). schema_hint still points at a docstring that holds no schema.
- Tests: unused tempfile and Path imports are still there. The edge-case tests are missing.

Verdict: CODE incomplete, not wrong. The existing tests are consistent with the spec and should stay.

Fix, all in code plus added tests:
1. Replace the "editing" pattern with software names (premiere, final cut, davinci, after effects, capcut) and assertion phrasing. Keep the lens, focal length, hidden rig and screenplay patterns.
2. Walk every free-text string in the beat: notes, information_conveyed, term, sound.*, unknowns, simplest_method, counterexample.
3. Add an optional audio_status=None argument to parse_beat. When it is "UNAVAILABLE", reject any sound.* field with real text and any non-UNKNOWN sound finding.
4. Reject bool, and check math.isfinite for numbers.
5. Add a non-dict guard on the first line of validate_beat.
6. Put the schema in schema_hint.

New tests: a legitimate editing finding passes, "Used Adobe Premiere" is rejected, forbidden text in notes is rejected, an audio_status=UNAVAILABLE rejection with a non-UNKNOWN narration, bool/NaN/non-dict inputs, and removal of the unused imports.


REVIEW FINDINGS (round 6, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD1
LUNA (gpt-6-luna medium):
MED - research/pieces/d1_beat_schema.py:505 - When `audio_status` is omitted, `parse_beat` uses the model’s `sound.narration` to trigger the UNAVAILABLE check, so model output can reject a real-audio beat - Run the cross-check only when the supplied `audio_status` is `"UNAVAILABLE"`.

HAIKU (low, stand-in):
MED - research/pieces/d1_beat_schema.py:parse_beat (audio_status sentinel branch) - when `audio_status` is omitted, the UNAVAILABLE check still runs off the model's own `sound.narration`, so a real-audio beat that emits "UNAVAILABLE" is rejected - run the check only when `audio_status == "UNAVAILABLE"` and drop the sentinel branch; the `TestParseBeat` audio tests that rely on the default must pass `audio_status="UNAVAILABLE"` explicitly.
MED - research/pieces/d1_beat_schema.py:FORBIDDEN_FACT_PATTERNS (software alternation) - only the phrase `davinci resolve` is listed, so "Edited with DaVinci." passes although DaVinci is named software - change to `davinci( resolve)?` and add a test for the bare form.
MED - research/pieces/d1_beat_schema.py:FORBIDDEN_FACT_PATTERNS (the `used|using|was used` two-way patterns) - a bare "premiere" or "final cut" plus any `used`/`using` in the same text is rejected, so "using a premiere-style reveal" or "the final cut was used to end the scene" fail - require software forms (`premiere pro`, `adobe premiere`, `final cut pro`) and add a positive test for a non-software use.
MED - research/pieces/d1_beat_schema.py:parse_beat (audio cross-check, `is_sound_finding`) - only the term keyword or department "13" is checked, so a dept-5 finding with term "shot framing" and observed "music swells over the cut" passes - scan `observed` for audio keywords as well, require every dept-13 finding to be UNKNOWN with empty `observed`, and add a test.
LOW - research/pieces/d1_beat_schema.py:parse_beat (audio cross-check) - `if val and val not in (...)` counts whitespace-only text as real - use `val.strip()`.
LOW - research/pieces/d1_beat_schema.py:parse_beat - a non-string `text` (e.g. None) raises AttributeError on `.strip()` instead of returning ERROR - guard with `isinstance(text, str)`.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/d1_beat_schema.py
```python
<complete module source>
```
FILE: research/pieces/test_d1_beat_schema.py
```python
<complete test source>
```
