
# WP-D2: Recipe Compilation from Beats

## Data Shapes

**BeatDict**: (as defined in WP-D1, passed in as plain dict)

**RecipeDict**:
```python
{
    "key": {"purpose": str, "camera_movement": str, "method": str},
    "stage1": str,  # directing lesson
    "stage2": str,  # execution hint using only status/artwork_needed, never invented preset names
    "sound_lesson": str,  # from beats with real audio; else "UNAVAILABLE – do not assume"
    "applicability": str,  # note: adapt 9:16 reel pacing to 16:9 devotional film; no copying reel dramatic cues
    "counterexamples": [str],  # union of counterexamples from source beats
    "verification": "SINGLE_SOURCE" | "MULTI_SOURCE",
    "source_beats": [{"video_id": str, "beat_id": str}]  # ALL source references kept
}
```

**CompileResult**:
```python
{"status": "OK", "recipes": [RecipeDict]}
```

## Public Functions (≤3)

### 1. compile_recipes(beats: list[dict]) -> CompileResult
Consolidates beats across videos by (purpose, camera_movement, method) key. Keeps ALL source references. Each recipe gets stage1, stage2, sound_lesson, applicability, counterexamples (union), verification, source_beats.

**WORKED EXAMPLE**
```python
# Input
beats = [
    {
        "video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", "start_time": 0.0, "end_time": 5.0,
        "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS", "angle": "EYE", "framing": "CENTER", "cut_type": "HARD", "composition": "RULE_OF_THIRDS"},
        "how_animated": {"method": "CAMERA_ONLY", "notes": "Slow zoom"},
        "sound": {"narration": "UNAVAILABLE", "silence": "UNKNOWN", "ambience": "UNAVAILABLE", "sfx": "UNAVAILABLE", "music": "Ambient drone", "sync_with_cut": "UNKNOWN"},
        "observed": ["Wide landscape"], "inferred": [],
        "reproduction": {"status": "EXISTING_PRESET", "artwork_needed": [], "simplest_method": "Use preset 'landscape_establish'"},
        "counterexample": "Fast zoom loses mood", "evidence": []
    },
    {
        "video_id": "vid2", "beat_id": "b2", "purpose": "ESTABLISH", "start_time": 10.0, "end_time": 15.0,
        "how_filmed": {"camera_movement": "STATIC", "shot_scale": "WS", "angle": "EYE", "framing": "CENTER", "cut_type": "HARD", "composition": "RULE_OF_THIRDS"},
        "how_animated": {"method": "CAMERA_ONLY", "notes": "Slow zoom"},
        "sound": {"narration": "UNAVAILABLE", "silence": "UNKNOWN", "ambience": "UNAVAILABLE", "sfx": "UNAVAILABLE", "music": "UNAVAILABLE", "sync_with_cut": "UNKNOWN"},
        "observed": ["Wide room"], "inferred": [],
        "reproduction": {"status": "POSE_OR_LAYER_CHANGE", "artwork_needed": ["background"], "simplest_method": "Swap background layer"},
        "counterexample": "Static camera feels dead", "evidence": []
    }
]
# Output
{
    "status": "OK",
    "recipes": [
        {
            "key": {"purpose": "ESTABLISH", "camera_movement": "STATIC", "method": "CAMERA_ONLY"},
            "stage1": "Use a static wide shot to establish setting; let the environment speak.",
            "stage2": "Status: EXISTING_PRESET or POSE_OR_LAYER_CHANGE. Artwork needed: background. Simplest: use preset or swap background layer.",
            "sound_lesson": "Ambient drone works; if no music, do not assume — mark UNAVAILABLE.",
            "applicability": "Adapt 9:16 reel pacing to 16:9 devotional film; no copying reel dramatic cues.",
            "counterexamples": ["Fast zoom loses mood", "Static camera feels dead"],
            "verification": "MULTI_SOURCE",
            "source_beats": [{"video_id": "vid1", "beat_id": "b1"}, {"video_id": "vid2", "beat_id": "b2"}]
        }
    ]
}
```

```python
# Input (single beat)
beats_single = [beats[0]]
# Output
{
    "status": "OK",
    "recipes": [{
        "key": {"purpose": "ESTABLISH", "camera_movement": "STATIC", "method": "CAMERA_ONLY"},
        "stage1": "Use a static wide shot to establish setting; let the environment speak.",
        "stage2": "Status: EXISTING_PRESET. Artwork needed: . Simplest: Use preset 'landscape_establish'.",
        "sound_lesson": "Ambient drone works; if no music, do not assume — mark UNAVAILABLE.",
        "applicability": "Adapt 9:16 reel pacing to 16:9 devotional film; no copying reel dramatic cues.",
        "counterexamples": ["Fast zoom loses mood"],
        "verification": "SINGLE_SOURCE",
        "source_beats": [{"video_id": "vid1", "beat_id": "b1"}]
    }]
}
```

---

### 2. _make_recipe_key(beat: dict) -> tuple
Internal helper (not public, but specified for testability): returns (purpose, camera_movement, method) tuple.

**WORKED EXAMPLE**
```python
# Input: beats[0] from above
# Output: ("ESTABLISH", "STATIC", "CAMERA_ONLY")
```

---

### 3. _merge_sound_lessons(beats: list[dict]) -> str
Internal helper: merges sound lessons from beats with real audio; returns "UNAVAILABLE – do not assume" if none.

**WORKED EXAMPLE**
```python
# Input: beats from above (first has music, second UNAVAILABLE)
# Output: "Ambient drone works; if no music, do not assume — mark UNAVAILABLE."
```

```python
# Input: beats where all sound.music == "UNAVAILABLE"
# Output: "UNAVAILABLE – do not assume"
```
GRAMMAR EXTENSION: recipes keep the cross-level link: each recipe carries `sequence_pattern` (ordered list of the purposes/terms of the beats that formed it, e.g. ["withhold","push_in","pause","hard_cut","reaction","hold"]) so the arrangement is kept, not six tags; `when_not_to_use` (str, from union of counterexamples/contraindications); `preset_id` (str|None) copied ONLY from a caller-supplied registry argument `registered_presets` (a set); a preset id not in that set is dropped and never generated. Recipes also expose `stage1_lessons` list for: narrative presentation, shot sequencing, performance, camera/composition, editing/continuity, artwork requirements, sound; and `stage2_lessons` for: approved preset, compatible assets, feasible alternatives, exact NEED_NEW gap (text only; no invented ids).


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/d2_recipe_compiler.py; test file: research/pieces/test_d2_recipe_compiler.py (tests import the module by its plain file name, e.g. `from d2_recipe_compiler import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD2 (d2_recipe_compiler.py, test_d2_recipe_compiler.py)
Verdict: 1 HIGH, 4 MED, 3 LOW
- HIGH - d2_recipe_compiler.py:260 - `sorted(set(all_inferred))`: all_inferred is a list of dicts ({"claim","confidence","based_on"} per the D1 schema), so set() raises TypeError (unhashable) for every group where any beat has a non-empty `inferred`. compile_recipes crashes on real beats. Tests never catch it because every fixture uses `"inferred": []`. - Fix: use the claim strings (`i["claim"]` if dict) and add a test with a non-empty inferred list.
- MED - d2_recipe_compiler.py:151,146-155 - contraindications are read from a nonexistent beat key `contraindications`. The real source is department_findings[*][*].contraindication (D1 schema). So counterexamples and when_not_to_use (spec: union of counterexamples/contraindications) ignore all finding contraindications. - Fix: also gather non-null finding["contraindication"] from beat["department_findings"]; test it.
- MED - d2_recipe_compiler.py:373-377,391-396 - sequence_pattern is built from beats already grouped by identical (purpose, camera_movement, method), so it is always ["ESTABLISH","ESTABLISH",...]: not the ordered arrangement of purposes/terms the spec wants (e.g. withhold,push_in,pause,...), and department_findings terms are never used. The test (146-157) only asserts isinstance list, so it is vacuous. - Fix: derive the pattern from the ordered terms of each beat's findings / the beat order by start_time within a video; strengthen test to check content and order.
- MED - d2_recipe_compiler.py:98-129 - stage2 appends every beat's simplest_method verbatim ("Use preset 'landscape_establish'"), so a preset name not in registered_presets (or with no registry) still appears in stage2, violating "never invented preset names" / "dropped and never generated". Only stage2_lessons filters. - Fix: apply the same registered-preset filter in _build_stage2; test that an unregistered preset name is absent from stage2.
- MED - d2_recipe_compiler.py:167 - registered preset ids not matching ^[a-zA-Z0-9_]+$ (hyphens, dots) are silently ignored, so a legitimately registered id like "landscape-establish" is never copied. - Fix: allow `-` and `.` (re.escape already handles injection).
- LOW - d2_recipe_compiler.py:76,90 - stage1 text for ESTABLISH hard-codes "static wide shot" even when the key camera_movement is PAN etc. - Fix: build from key values.
- LOW - d2_recipe_compiler.py:54 - `"works" in l` heuristic for adding the warning triggers on narration text containing "works" and is brittle. - Fix: track a has_music flag.
- LOW - d2_recipe_compiler.py:412-419 - preset_id takes the first matching beat only; other registered presets in the group are lost silently.
- Tests: test_d2_recipe_compiler.py:2-4 unused imports; nothing exercises dropped-preset leakage in stage2, non-empty inferred, department contraindications, or sequence_pattern content.


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD2
LUNA (gpt-6-luna high):
MED - research/pieces/d2_recipe_compiler.py:49 - With no usable audio, `_merge_sound_lessons` returns `"UNAVAILABLE - do not assume"` instead of the required `"UNAVAILABLE – do not assume"`; tests assert the same incorrect string. - Return the exact specified sentinel and update both tests.

MED - research/pieces/d2_recipe_compiler.py:379 - If a method mentions both a registered and an unregistered preset, the entire method is included in `stage2_lessons`, leaking the unregistered ID; unquoted unregistered preset names can also pass through at lines 384–386. - Filter each preset reference against the registry before including the method.

MED - research/pieces/d2_recipe_compiler.py:436 - `sequence_pattern` drops repeated terms, so a pattern such as `["hold", "push_in", "hold"]` becomes `["hold", "push_in"]` and loses the beat arrangement. - Preserve each beat’s terms in temporal order, including repeats.

SONNET (latest):
wpD2
Round-1 findings: inferred-dict crash fixed; department contraindications now read; stage2 filtered; hyphen/dot ids allowed; has_music flag fixed; stage1 built from key values. sequence_pattern now content-based.
- LOW - d2_recipe_compiler.py:436,441,447 - `term not in pattern` dedups repeated terms and sorts by video_id first, so the ordered arrangement (e.g. hold..hold) loses repeats and cross-video interleave - fix: keep per-beat order, dedup only identical consecutive terms.
- LOW - d2_recipe_compiler.py:141 - with no registry only `preset 'x'` is stripped; a bare quoted id ('landscape_establish') stays in stage2 - fix: apply the bare-quote strip in the empty-registry branch too.
- LOW - d2_recipe_compiler.py:155 - bare-quote strip deletes any quoted word-like token (e.g. 'hero') not just preset ids - fix: only strip when it follows "preset".
- LOW - d2_recipe_compiler.py:495 - only first sorted preset kept as preset_id; others dropped silently (acknowledged limitation of single-id field).
PASS


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD2
Why rounds failed: rounds 0-1 (Nemotron) parsed fine but tests stayed red; rounds 2-3 (Codex fixer) were pure API failures (status=0, empty reply), so no more attempts were made. Restored code is mostly the round-2 review state; most findings are already applied. Currently 3 failures, 32 pass.
1. HIGH, TEST wrong: test_merge_sound_lessons_with_music asserts the en-dash sentinel "UNAVAILABLE – do not assume" inside the result for a beat WITH music. Per the spec worked example, that case must return "Ambient drone works; if no music, do not assume — mark UNAVAILABLE."; the sentinel is only for the no-audio case. Fix the assertion (keep the separate no-audio sentinel test).
2. HIGH, CODE wrong: _filter_unregistered_presets only strips the form `preset 'x'` / `preset "x"`. A method written `Use 'landscape_establish' preset` (quoted id BEFORE the word preset) leaks into stage2 and stage2_lessons. Fails test_..._stage2_bare_quoted_preset_stripped_when_no_registry and test_..._stage2_lessons_bare_quoted_preset_stripped. Required: also strip/neutralise a quoted id directly followed by "preset" when not in the registry (both empty-registry and registry branches), while 'hero' asset stays untouched (that test passes).
3. MED, CODE: when a method mixes registered and unregistered ids, filter each reference individually, not the whole method (Luna round-2 MED); add a test.
4. LOW: sequence_pattern should keep repeats (hold, push_in, hold) and only collapse identical consecutive terms; verify with a content test.
5. LOW: only first preset kept as preset_id; acceptable, document.


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD2
LUNA (gpt-6-luna medium):
HIGH - research/pieces/d2_recipe_compiler.py:48 - The unavailable-audio return string is corrupted and does not match the required `UNAVAILABLE – do not assume` sentinel; the music warning at line 53 is corrupted too - restore the exact specified Unicode punctuation in both strings.

MED - research/pieces/d2_recipe_compiler.py:143 - With a nonempty registry, unquoted preset IDs in `simplest_method` pass through the filter unchanged and can leak into `stage2` and `stage2_lessons` - filter unquoted preset references against `registered_presets` as well.

SONNET (latest):
wpD2
Why rounds failed: rounds 0-1 (Nemotron) parsed fine but tests stayed red; rounds 2-3 (Codex fixer) were pure API failures (status=0, empty reply), so no more attempts were made. Restored code is mostly the round-2 review state; most findings are already applied. Currently 3 failures, 32 pass.
1. HIGH, TEST wrong: test_merge_sound_lessons_with_music asserts the en-dash sentinel "UNAVAILABLE – do not assume" inside the result for a beat WITH music. Per the spec worked example, that case must return "Ambient drone works; if no music, do not assume — mark UNAVAILABLE."; the sentinel is only for the no-audio case. Fix the assertion (keep the separate no-audio sentinel test).
2. HIGH, CODE wrong: _filter_unregistered_presets only strips the form `preset 'x'` / `preset "x"`. A method written `Use 'landscape_establish' preset` (quoted id BEFORE the word preset) leaks into stage2 and stage2_lessons. Fails test_..._stage2_bare_quoted_preset_stripped_when_no_registry and test_..._stage2_lessons_bare_quoted_preset_stripped. Required: also strip/neutralise a quoted id directly followed by "preset" when not in the registry (both empty-registry and registry branches), while 'hero' asset stays untouched (that test passes).
3. MED, CODE: when a method mixes registered and unregistered ids, filter each reference individually, not the whole method (Luna round-2 MED); add a test.
4. LOW: sequence_pattern should keep repeats (hold, push_in, hold) and only collapse identical consecutive terms; verify with a content test.
5. LOW: only first preset kept as preset_id; acceptable, document.

HAIKU (low, stand-in):
Summary
- wpD1: 2 MED (PASS fails)
- wpD2: PASS (1 LOW)
- wpD3: 3 MED (PASS fails)


REVIEW FINDINGS (round 5, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD2
LUNA (gpt-6-luna medium):
MED - research/pieces/d2_recipe_compiler.py:188 - A standalone unquoted preset ID in `simplest_method` passes through unchanged because filtering only recognizes IDs adjacent to the word `preset`; it can leak into `stage2` and `stage2_lessons` - Filter unquoted registered and unregistered preset IDs individually, and add coverage for a bare unregistered ID.

HAIKU (low, stand-in):
MED - d2_recipe_compiler.py:_filter_unregistered_presets (empty-registry branch, `preset\s+[a-zA-Z0-9_.-]+` and `[a-zA-Z0-9_.-]+\s+preset`) - The unquoted patterns delete the words next to "preset", not just the id. "Use a preset or swap layer" becomes "Use a  swap layer" because "or" is removed. - Only strip unquoted tokens that look like preset ids (contain `_`, `-`, `.` or a digit), or drop the unquoted forms and keep the quoted ones. Add a test that "Use a preset or swap layer" keeps "swap layer".

MED - d2_recipe_compiler.py:_filter_unregistered_presets (registry branch, `preset\s+([a-zA-Z0-9_.-]+)` and `([a-zA-Z0-9_.-]+)\s+preset`) - Same over-deletion when a registry is given. "Use the preset approach" with registry {"x"} becomes "Use the". - Same fix as above, and add a registry-branch test.

MED - d2_recipe_compiler.py:_build_stage1 - Output does not match the spec worked example. `shot_scale` is raw ("WS", lowercased to "ws", not "wide"), and the beat's `notes` ("Slow zoom.") is appended. The spec expects "Use a static wide shot to establish setting; let the environment speak." - Map WS to "wide" and stop appending notes to stage1. Add an exact-string test for the worked example. No current test checks it; the only assertion is `"pan" in stage1.lower()`.

LOW - d2_recipe_compiler.py:_build_sequence_pattern - Beats sort by `(video_id, start_time)`, so cross-video order is alphabetical by video_id, not temporal. - Keep input video order and sort by `start_time` within each video.

LOW - test_d2_recipe_compiler.py:test_compile_recipes_sequence_pattern - Vacuous. It only checks that each element is a string. - Delete it, since the content tests below cover this, or assert the exact pattern.

LOW - test_d2_recipe_compiler.py:test_compile_recipes_multiple_registered_presets_in_group - Name and docstring say all presets in the group are captured, but the test only checks that `preset_id` is one of them. - Rename it, or assert the documented limitation (only the first sorted preset kept).

LOW - d2_recipe_compiler.py:_build_stage2 and _build_stage2_lessons - Identical simplest methods repeat ("Simplest: X | X | X"). Stripping can also leave fragments such as "Simplest: Use." - Dedupe with `dict.fromkeys` and drop empty fragments after filtering.

LOW - d2_recipe_compiler.py:_build_stage1_lessons, _build_stage2_lessons, compile_recipes - Dead code: `purposes` and `statuses` are never read, and `group_beats_sorted = group_beats` is an alias. - Delete them.

LOW - d2_recipe_compiler.py:_build_counterexamples, _build_stage1, _build_stage1_lessons, _build_stage2, _build_sequence_pattern - A null value (`"how_filmed": null`, `"reproduction": null`, `"department_findings": null`, `"artwork_needed": null`) raises AttributeError or TypeError because `.get(key, {})` only defaults when the key is missing. - Use `beat.get(key) or {}` and `or []` throughout.

LOW - d2_recipe_compiler.py:_build_stage1_lessons (Camera/composition line) - Missing fields produce empty comma fragments such as "Camera/composition:  camera, WS scale, , framing". - Drop empty values before joining.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/d2_recipe_compiler.py
```python
<complete module source>
```
FILE: research/pieces/test_d2_recipe_compiler.py
```python
<complete test source>
```
