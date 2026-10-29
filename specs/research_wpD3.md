
# WP-D3: Deliverables Writing and Playbook Guard

## Data Shapes

**BeatDict**: (as defined in WP-D1)
**RecipeDict**: (as defined in WP-D2)

**WriteResult**:
```python
{"status": "OK", "files_written": [str]}
```

**GuardResult**:
```python
{"status": "OK", "violations": []} | {"status": "VIOLATIONS", "violations": [str]}
```

## Public Functions (≤3)

### 1. write_deliverables(output_dir: str, beats: list[dict], recipes: list[dict], read_file: callable, write_file: callable, list_dir: callable) -> WriteResult
Updates MASTER_REPORT.md between `<!-- BEATS_START -->`/`<!-- BEATS_END -->` (replace section if present), MASTER_TECHNIQUES.json key `_beat_recipes` (preserve other keys), writes KIMI_ANIMATION_PLAYBOOK.md. Uses injected `read_file(path)`, `write_file(path, content)`, `list_dir(path)` for atomic tmp+replace writes. Returns OK with list of written files.

**WORKED EXAMPLE**
```python
# Input
output_dir = "/tmp/out"
beats = [{"video_id": "vid1", "beat_id": "b1", "purpose": "ESTABLISH", ...}]  # from WP-D1 example
recipes = [{"key": {"purpose": "ESTABLISH", "camera_movement": "STATIC", "method": "CAMERA_ONLY"}, "stage1": "Lesson...", "stage2": "Hint...", "sound_lesson": "Sound...", "applicability": "Adapt...", "counterexamples": ["Ex1"], "verification": "SINGLE_SOURCE", "source_beats": [{"video_id": "vid1", "beat_id": "b1"}]}]

# Mock read_file returns:
# MASTER_REPORT.md: "# Report\n<!-- BEATS_START -->\nOld beats\n<!-- BEATS_END -->\nEnd"
# MASTER_TECHNIQUES.json: '{"other_key": "value"}'

# Mock write_file captures writes, list_dir returns ["MASTER_REPORT.md", "MASTER_TECHNIQUES.json"]

# Output
{"status": "OK", "files_written": ["MASTER_REPORT.md", "MASTER_TECHNIQUES.json", "KIMI_ANIMATION_PLAYBOOK.md"]}

# MASTER_REPORT.md after: "# Report\n<!-- BEATS_START -->\n## Beats\n- vid1/b1: ESTABLISH (0.0-5.0s)\n<!-- BEATS_END -->\nEnd"
# MASTER_TECHNIQUES.json after: '{"other_key": "value", "_beat_recipes": [...]}'
# KIMI_ANIMATION_PLAYBOOK.md contains: Stage 1 lessons, Stage 2 hints, sound/silence rules, "read-only hints: canon and schema win"
```

```python
# Input (run twice - idempotent)
# Same as above, but MASTER_REPORT.md already has new beats section
# Output: same files_written, MASTER_REPORT.md unchanged (single section)
```

---

### 2. playbook_guard(text: str, allowed_presets: list[str]) -> GuardResult
Returns violations if text contains invented preset-like IDs not in `allowed_presets`, or phrases implying creator intent as fact ("the creator wanted", "the author intended", etc.). Returns OK with empty violations or VIOLATIONS with list.

**WORKED EXAMPLE**
```python
# Input
text = "Use preset 'my_custom_preset' for this. The creator wanted a dramatic zoom."
allowed_presets = ["landscape_establish", "portrait_reveal"]
# Output
{"status": "VIOLATIONS", "violations": ["Invented preset-like ID: 'my_custom_preset' not in allowed list", "Phrase implies creator intent as fact: 'the creator wanted'"]}
```

```python
# Input (clean)
text = "Use preset 'landscape_establish'. This beat establishes the setting."
allowed_presets = ["landscape_establish", "portrait_reveal"]
# Output
{"status": "OK", "violations": []}
```

```python
# Input (case-insensitive intent phrase)
text = "THE AUTHOR INTENDED this to be sad."
allowed_presets = []
# Output
{"status": "VIOLATIONS", "violations": ["Phrase implies creator intent as fact: 'the author intended'"]}
```

---

### 3. _generate_playbook_content(recipes: list[dict]) -> str
Internal helper: generates KIMI_ANIMATION_PLAYBOOK.md content from recipes (Stage 1 lessons, Stage 2 hints, sound/silence rules, footer).

**WORKED EXAMPLE**
```python
# Input: recipes from WP-D2 example
# Output: "# KIMI Animation Playbook\n\n## Stage 1: Directing Lessons\n- Use a static wide shot to establish setting; let the environment speak.\n\n## Stage 2: Execution Hints\n- Status: EXISTING_PRESET or POSE_OR_LAYER_CHANGE. Artwork needed: background. Simplest: use preset or swap background layer.\n\n## Sound & Silence Rules\n- Ambient drone works; if no music, do not assume — mark UNAVAILABLE.\n\n## Applicability\n- Adapt 9:16 reel pacing to 16:9 devotional film; no copying reel dramatic cues.\n\n---\n*read-only hints: canon and schema win*"
```
GRAMMAR EXTENSION: playbook_guard must also flag (as violations) playbook text that instructs Kimi to: rewrite or paraphrase EASY wording, invent story events or dialogue, assign timings in seconds/frames, name an unregistered preset id, emit animation code, or add music/background score to production (reference music may be described only as research with the words "reference only"). Violations raise ValueError from write_deliverables before any file is written. The playbook must state: reference music is research-only and prohibited in production; reference dialogue never alters EASY wording.


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/d3_deliverables.py; test file: research/pieces/test_d3_deliverables.py (tests import the module by its plain file name, e.g. `from d3_deliverables import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD3

Rounds 0-1 were Nemotron; round 1 failed the parser because the test file was missing. Rounds 2 and 3 were empty Codex calls (status=0), so they were API failures. The code on disk is round 0's.

Four tests fail, all in `TestWriteDeliverables`. They all raise `ValueError: Playbook guard violations: Invented preset-like ID: 'or'`. CODE is wrong, in two places. The tests are consistent with the spec.

1. `playbook_guard`: the second `re.findall` (`preset\s+(\w+)`) catches ordinary English such as "use preset or swap background layer". The spec's own D2 example contains exactly that sentence, so it has to pass. The spec examples only treat quoted IDs as preset-like. Remove the unquoted pattern (or require an underscore or uppercase ID). Keep the quoted check against `allowed_presets`.

2. `_atomic_write` ignores the injected `write_file`. It writes to the real disk through `tempfile` and `os.replace`. The spec requires writes through the injected `write_file(path, content)`, so the test's `written` dict stays empty and the test hits a KeyError once fix 1 is in. Replace the three `_atomic_write(...)` calls with `write_file(path, content)`. Atomicity belongs to the injected writer, and the test's `write_file` stores by basename. `_atomic_write` can then be deleted.

I applied both fixes to a copy in the scratchpad (`d3chk`). All 24 tests passed, and either fix alone still left 4 failing.


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD3
LUNA (gpt-6-luna high):
MED - research/pieces/d3_deliverables.py:128 - “reference only” anywhere in the text suppresses the production music violation, so unrelated reference text can let “Add background score to production” pass - Apply the exception only when that music instruction itself is explicitly research-only.

MED - research/pieces/d3_deliverables.py:27 - The timing guard misses assignments such as “Set each shot duration to 5 seconds” when they omit the word “timing” - Match directives that assign seconds or frames as durations.

MED - research/pieces/d3_deliverables.py:214 - With two existing beats sections, only the first is replaced and the duplicate remains - Ensure replacement leaves exactly one beats section.

LOW - research/pieces/test_d3_deliverables.py:108 - The idempotence test runs once and does not assert that the report is unchanged or remains stable after a second call - Run the writer twice and compare the resulting report content.

SONNET (latest):
wpD3
Round-1 findings (unquoted preset regex, write_file ignored) are fixed: write goes through injected write_file, guard checks quoted ids only.
- HIGH - d3_deliverables.py:51-60,66 - allowed_presets is built from recipe key method/camera_movement names, not from recipes' `preset_id`/registered presets. A registered preset kept by D2 in stage2 ("Use preset 'landscape_establish'", preset_id set) makes write_deliverables raise ValueError "Invented preset-like ID". Reproduced end to end with D2 output - fix: add every recipe["preset_id"] (non-None) to allowed_presets (and drop method/camera names).
- HIGH - d3_deliverables.py:204-209 - uses beat["start_sec"]/["end_sec"], but the D1 BeatDict (and spec worked examples) use start_time/end_time; real beats raise KeyError. Tests only use start_sec so they miss it - fix: read start_time/end_time (fall back to *_sec), and update tests.
- LOW - d3_deliverables.py:92 - non-dict JSON in MASTER_TECHNIQUES.json gives TypeError not a clear error - fix: validate isinstance dict.
- LOW - d3_deliverables.py:27 - `timing.*in.*(second|frame)` false-positives on ordinary lines such as "timing ... in the frame" - fix: tighten to an instruction verb.
- LOW - d3_deliverables.py:217 - end marker before start marker appends a second section instead of repairing.


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD3
LUNA (gpt-6-luna medium):
MED - research/pieces/d3_deliverables.py:27 - The timing guard misses duration assignments such as “Set each shot duration to 5 seconds” because its pattern requires “duration” immediately after the instruction verb - Match instruction verbs followed by a shot or beat qualifier and a seconds/frames duration value.

SONNET (latest):
wpD3
Round-1 findings (unquoted preset regex, write_file ignored) are fixed: write goes through injected write_file, guard checks quoted ids only.
- HIGH - d3_deliverables.py:51-60,66 - allowed_presets is built from recipe key method/camera_movement names, not from recipes' `preset_id`/registered presets. A registered preset kept by D2 in stage2 ("Use preset 'landscape_establish'", preset_id set) makes write_deliverables raise ValueError "Invented preset-like ID". Reproduced end to end with D2 output - fix: add every recipe["preset_id"] (non-None) to allowed_presets (and drop method/camera names).
- HIGH - d3_deliverables.py:204-209 - uses beat["start_sec"]/["end_sec"], but the D1 BeatDict (and spec worked examples) use start_time/end_time; real beats raise KeyError. Tests only use start_sec so they miss it - fix: read start_time/end_time (fall back to *_sec), and update tests.
- LOW - d3_deliverables.py:92 - non-dict JSON in MASTER_TECHNIQUES.json gives TypeError not a clear error - fix: validate isinstance dict.
- LOW - d3_deliverables.py:27 - `timing.*in.*(second|frame)` false-positives on ordinary lines such as "timing ... in the frame" - fix: tighten to an instruction verb.
- LOW - d3_deliverables.py:217 - end marker before start marker appends a second section instead of repairing.

HAIKU (low, stand-in):
Summary
- wpD1: 2 MED (PASS fails)
- wpD2: PASS (1 LOW)
- wpD3: 3 MED (PASS fails)


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD3
LUNA (gpt-6-luna medium):
MED - research/pieces/d3_deliverables.py:26 - “Set shot duration to 5 seconds” and “Set beat duration to 5 seconds” evade the timing guard because it accepts only `each`, `the`, `this`, or `every` before `shot`/`beat` - Allow an optional shot or beat qualifier before `duration`.
MED - research/pieces/d3_deliverables.py:133 - A music instruction can evade the production ban when unrelated “reference only” text appears in the same sentence - Require the music instruction itself to say it is research-only.

SONNET (latest):
wpD3
Round-1 findings (unquoted preset regex, write_file ignored) are fixed: write goes through injected write_file, guard checks quoted ids only.
- HIGH - d3_deliverables.py:51-60,66 - allowed_presets is built from recipe key method/camera_movement names, not from recipes' `preset_id`/registered presets. A registered preset kept by D2 in stage2 ("Use preset 'landscape_establish'", preset_id set) makes write_deliverables raise ValueError "Invented preset-like ID". Reproduced end to end with D2 output - fix: add every recipe["preset_id"] (non-None) to allowed_presets (and drop method/camera names).
- HIGH - d3_deliverables.py:204-209 - uses beat["start_sec"]/["end_sec"], but the D1 BeatDict (and spec worked examples) use start_time/end_time; real beats raise KeyError. Tests only use start_sec so they miss it - fix: read start_time/end_time (fall back to *_sec), and update tests.
- LOW - d3_deliverables.py:92 - non-dict JSON in MASTER_TECHNIQUES.json gives TypeError not a clear error - fix: validate isinstance dict.
- LOW - d3_deliverables.py:27 - `timing.*in.*(second|frame)` false-positives on ordinary lines such as "timing ... in the frame" - fix: tighten to an instruction verb.
- LOW - d3_deliverables.py:217 - end marker before start marker appends a second section instead of repairing.


REVIEW FINDINGS (round 5, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD3
LUNA (gpt-6-luna medium):
MED - research/pieces/d3_deliverables.py:133 - `Add background score to production (reference only).` passes the guard even though the instruction itself directs production use - require the music instruction to state that it is research-only, and update the contradictory test at `test_d3_deliverables.py:302`

HAIKU (low, stand-in):
MED - research/pieces/d3_deliverables.py:_replace_section - the old beats section is removed and the new one is appended at end of file, so trailing text such as "End" moves above it; the spec example keeps the section in place - remove the old section(s) and insert the new one at the first START marker's position, appending only when no marker exists. Add a test that asserts position.
MED - research/pieces/d3_deliverables.py:playbook_guard (music rule) - the "reference only" exception searches the whole sentence from the match start, so "Add background score to production, reference only: note." passes - require the phrase directly after the match: `re.match(r"\s*\(\s*reference\s+only\s*\)", text[match.end():])`.
MED - research/pieces/d3_deliverables.py:PLAYBOOK_FORBIDDEN_PATTERNS (timing) - evades: "Set each shot's duration to 5 seconds", "Set the duration of each shot to 5 seconds", "Set duration to 5.5 seconds" - allow any words between the verb and `timing|duration`, and a decimal before `seconds|frames`, e.g. `(assign|set|specify)\b[^.\n]*?\b(timing|duration)\b[^.\n]*?\b\d+(?:\.\d+)?\s*(?:seconds?|frames?)\b`. Add tests for each evading phrasing.
MED - research/pieces/d3_deliverables.py:write_deliverables - MASTER_REPORT.md is written before MASTER_TECHNIQUES.json is parsed and validated and before `json.dumps(recipes)` runs, so a non-dict techniques file or non-serialisable recipes leaves the report updated and the techniques file not written; `test_write_deliverables_invalid_techniques_json_raises` does not check for this - read, validate and serialise every input before the first `write_file`.
MED - research/pieces/d3_deliverables.py:playbook_guard (intent phrases) - the message uses the matched text ("The creator wanted"), but the spec's worked example expects the lowercase pattern ('the creator wanted') - report `pattern` instead of `match.group()`.
LOW - research/pieces/d3_deliverables.py:write_deliverables (`list_dir` parameter) - accepted but never used - drop it or document why it is kept.
LOW - research/pieces/d3_deliverables.py:write_deliverables (preset loop) - `if preset_id:` puts non-string values (lists, dicts) into `allowed_presets` - require `isinstance(preset_id, str) and preset_id.strip()`.
LOW - research/pieces/test_d3_deliverables.py:imports - `MagicMock` and `patch` are unused - remove them.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/d3_deliverables.py
```python
<complete module source>
```
FILE: research/pieces/test_d3_deliverables.py
```python
<complete test source>
```
