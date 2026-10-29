# WP-F4: technique classification + two Kimi views (pure; no network/model/Kimi calls)
Separate assessments per technique: research_confidence (how reliably references show it) and executability (can GranthStudio do it with approved artwork, existing presets, valid JSON, permitted sounds). Never hide a well-supported lesson only because an asset is missing.
1. `classify_technique(evidence)` evidence={"videos":n,"independent_creators":n,"styles":n,"method_verified":bool} -> "GENERAL" if independent_creators>=2 and styles>=2; "STYLE_SPECIFIC" if (videos>=2 or independent_creators>=2) and styles==1; else "EXPERIMENTAL". UNKNOWN creators count toward videos but never toward independent_creators. `research_confidence(evidence)` -> "LOW" (videos<2 or not method_verified), "HIGH" (independent_creators>=3 and method_verified), else "MEDIUM".
2. `usage_bucket(technique)` technique has classification, executability in (EXISTING_PRESET, POSE_OR_LAYER_CHANGE, NEED_NEW, RESEARCH_ONLY), and `assets_available` bool -> "USABLE_NOW" (not EXPERIMENTAL, executability in EXISTING_PRESET/POSE_OR_LAYER_CHANGE, assets_available True); "USEFUL_BUT_BLOCKED" (not EXPERIMENTAL, directing idea is reliable but needs NEED_NEW, or a pose/image/renderer capability that is missing); "RESEARCH_ONLY" (EXPERIMENTAL, unresolved mechanism, or unsuitable). 
3. `kimi_views(techniques)` -> {"stage1":[USABLE_NOW + USEFUL_BUT_BLOCKED items, each with its blocked_reason and the string "report via existing NEED_NEW if no approved asset" for blocked ones], "stage2":[USABLE_NOW items only, with registered preset ids copied from the technique's `preset_id` field if present, else omitted], "research_only":[...]}. Stage 2 must never contain an item without an existing `preset_id`/arrangement reference; no preset names are ever invented or generated.
Worked example: {"videos":5,"independent_creators":3,"styles":2,"method_verified":True} + executability NEED_NEW + assets_available False => GENERAL, HIGH, USEFUL_BUT_BLOCKED, appears in stage1 with blocked_reason and NOT in stage2. {"videos":1,"independent_creators":1,"styles":1,"method_verified":False} => EXPERIMENTAL, LOW, RESEARCH_ONLY.
ADDITIONS (reviewer-agreed):
4. executability is validated against the fixed set (EXISTING_PRESET, POSE_OR_LAYER_CHANGE, NEED_NEW, RESEARCH_ONLY) after strip(); an unknown value raises ValueError (never silently routes to RESEARCH_ONLY). Complete usage_bucket truth table: not EXPERIMENTAL + executability EXISTING_PRESET/POSE_OR_LAYER_CHANGE + assets_available True => USABLE_NOW; same with assets_available False => USEFUL_BUT_BLOCKED with blocked_reason "MISSING_ASSET"; not EXPERIMENTAL + NEED_NEW => USEFUL_BUT_BLOCKED with blocked_reason "NEED_NEW" (regardless of assets_available); RESEARCH_ONLY or EXPERIMENTAL => RESEARCH_ONLY. stage2 = USABLE_NOW items that HAVE a preset_id (items without one are DROPPED from stage2, never emitted without it). Output ordering is stable (sorted by technique id) and each stage1 item carries an evidence_summary {videos,independent_creators,styles}. `styles` for evidence is the count of distinct art_style values across the technique's videos.
FINAL CORRECTION (offline decision tests, in test_f4_classify.py; the stub director is a ~10-line pure function defined inside the test): given kimi_views output it returns per scene need a decision: "USE_PRESET:<preset_id>" for a stage2 item matching the need, "NEED_NEW" for a stage1 blocked item matching the need, else "BASELINE". Positive tests: adding a valid, relevant, supported technique changes the decision (BASELINE -> USE_PRESET or NEED_NEW). Negative tests: adding an irrelevant technique, a contradictory/low-confidence (EXPERIMENTAL) one, or a supported one for a different need must NOT change the decision; an unavailable preset never appears as USE_PRESET; no preset id is ever invented (every USE_PRESET id exists in the input).


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/f4_classify.py; test file: research/pieces/test_f4_classify.py (tests import the module by its plain file name, e.g. `from f4_classify import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
Sonnet G4 review (wpF2, wpF3, wpF4). All 72 tests in the three files pass; findings below are spec/edge/test-quality defects.


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF4
SONNET (latest):
wpF4
- MED - f4_classify.py:32-69 - spec says `usage_bucket(technique)` returns the bucket string ("USABLE_NOW" / "USEFUL_BUT_BLOCKED" / "RESEARCH_ONLY"); it returns a dict {"bucket","evidence_summary","blocked_reason"}, so any caller comparing to the string (worked example) fails. Tests are written to the dict shape. - Fix: return the string (blocked_reason via a separate helper used by kimi_views) or confirm the dict contract with the spec owner.
- LOW - f4_classify.py:50-52 - `technique.get("evidence", {})` raises AttributeError if evidence is None. - Fix: `(technique.get("evidence") or {})`.
- LOW - f4_classify.py:42,60 - assets_available is used by truthiness; the string "false" counts as True. - Fix: require `is True`.
- LOW - f4_classify.py:84 - `executability` local in kimi_views is unused (and .strip() on a missing key would only be reached after usage_bucket validated). Dead code.
Everything else checks out: truth table, stage2 only with preset_id, stable id ordering, stub-director positive/negative tests present.


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF4
SONNET (latest):
wpF4
- MED - f4_classify.py:32-69 - spec says `usage_bucket(technique)` returns the bucket string ("USABLE_NOW" / "USEFUL_BUT_BLOCKED" / "RESEARCH_ONLY"); it returns a dict {"bucket","evidence_summary","blocked_reason"}, so any caller comparing to the string (worked example) fails. Tests are written to the dict shape. - Fix: return the string (blocked_reason via a separate helper used by kimi_views) or confirm the dict contract with the spec owner.
- LOW - f4_classify.py:50-52 - `technique.get("evidence", {})` raises AttributeError if evidence is None. - Fix: `(technique.get("evidence") or {})`.
- LOW - f4_classify.py:42,60 - assets_available is used by truthiness; the string "false" counts as True. - Fix: require `is True`.
- LOW - f4_classify.py:84 - `executability` local in kimi_views is unused (and .strip() on a missing key would only be reached after usage_bucket validated). Dead code.
Everything else checks out: truth table, stage2 only with preset_id, stable id ordering, stub-director positive/negative tests present.

HAIKU (low, stand-in):
Summary
- wpE2: HIGH 1 / MED 0 -> FAIL
- wpF2: HIGH 0 / MED 1 -> FAIL
- wpF4: HIGH 0 / MED 1 -> FAIL


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF4
SONNET (latest):
wpF4
- MED - f4_classify.py:32-69 - spec says `usage_bucket(technique)` returns the bucket string ("USABLE_NOW" / "USEFUL_BUT_BLOCKED" / "RESEARCH_ONLY"); it returns a dict {"bucket","evidence_summary","blocked_reason"}, so any caller comparing to the string (worked example) fails. Tests are written to the dict shape. - Fix: return the string (blocked_reason via a separate helper used by kimi_views) or confirm the dict contract with the spec owner.
- LOW - f4_classify.py:50-52 - `technique.get("evidence", {})` raises AttributeError if evidence is None. - Fix: `(technique.get("evidence") or {})`.
- LOW - f4_classify.py:42,60 - assets_available is used by truthiness; the string "false" counts as True. - Fix: require `is True`.
- LOW - f4_classify.py:84 - `executability` local in kimi_views is unused (and .strip() on a missing key would only be reached after usage_bucket validated). Dead code.
Everything else checks out: truth table, stage2 only with preset_id, stable id ordering, stub-director positive/negative tests present.


REVIEW FINDINGS (round 5, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF4
HAIKU (low, stand-in):
MED - research/pieces/f4_classify.py:10 - `styles` is read from a precomputed `evidence["styles"]` and never derived from the technique's videos, but the spec defines it as the count of distinct `art_style` values across those videos - fix: when the technique carries a videos list, compute `styles = len({v["art_style"] for v in videos if v.get("art_style")})` and use it in `classify_technique` and `evidence_summary`.
MED - research/pieces/f4_classify.py:23 - `method_verified` is used by truthiness, so the string `"false"` makes `research_confidence` return HIGH or MEDIUM instead of LOW, the same defect class already fixed for `assets_available` - fix: `method_verified = evidence.get("method_verified") is True`.
MED - research/pieces/f4_classify.py:12 - no test pins the classify boundaries (`independent_creators == 2 and styles == 2` should be GENERAL, `independent_creators == 1 and styles == 2` should be EXPERIMENTAL), so changing `>=` to `>` still passes the suite - fix: add both cases to test_f4_classify.py `TestClassifyTechnique`.
MED - research/pieces/test_f4_classify.py:22 - `test_unknown_creators_count_toward_videos_not_independent` never models UNKNOWN creators; it passes precomputed numbers to `classify_technique`, so it is indistinguishable from the other classify tests and is vacuous for the rule its name claims - fix: rename it to what it checks, or test the counting rule where it actually lives and say the rule is untested here.
MED - research/pieces/test_f4_classify.py:392 - `test_no_preset_id_ever_invented` checks one BASELINE result and never asserts the spec invariant that every `USE_PRESET:<id>` the director can return exists in the input - fix: loop over a set of needs and assert that any returned `USE_PRESET` id is in the input's `preset_id` set and that stage2 has no item without a `preset_id`.
LOW - research/pieces/test_f4_classify.py:56 - the usage_bucket tests cover `EXISTING_PRESET` for the missing-asset case but not `POSE_OR_LAYER_CHANGE` with `assets_available` False, and no test checks that an invalid classification raises ValueError - fix: add both cases.
LOW - research/pieces/f4_classify.py:61 - the fallback `return "RESEARCH_ONLY"` is unreachable, and if it were ever reached it would silently route a technique to research, which the spec forbids - fix: replace it with `raise ValueError`.
LOW - research/pieces/f4_classify.py:77 - `sorted(..., key=lambda t: t.get("id", ""))` raises TypeError when an id is None or the ids mix types - fix: `key=lambda t: str(t.get("id") or "")`.
LOW - research/pieces/f4_classify.py:110 - any truthy `preset_id` is copied into stage2, including a list or dict, so a non-string value becomes a "preset id" - fix: require `isinstance(preset_id, str) and preset_id.strip()`.
LOW - research/pieces/f4_classify.py:12 - `classify_technique` calls `evidence.get` directly, so `evidence=None` raises AttributeError, while `kimi_views` already tolerates None - fix: `evidence = evidence or {}` at the top of the function.


REVIEW FINDINGS (round 6, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF4
LUNA (gpt-6-luna medium):
MED - research/pieces/f4_classify.py:13 - `classify_technique` reads precomputed `evidence["styles"]` instead of counting distinct `art_style` values across the technique’s videos, so classification can be wrong when the supplied count disagrees with the videos - derive the style count from the videos list and use it in classification and `evidence_summary`.
MED - research/pieces/test_f4_classify.py:23 - `test_unknown_creators_count_toward_videos_not_independent` supplies aggregate counts and never models UNKNOWN creators, so it does not test the rule its name claims - rename it to describe the aggregate boundary it tests, or test creator counting where that rule is implemented.

HAIKU (low, stand-in):
MED - research/pieces/f4_classify.py:kimi_views (evidence_summary) and classify_technique - `styles` is read from a precomputed `evidence["styles"]`, but the spec defines it as the number of distinct `art_style` values across the technique's videos, and no code path derives it - when the technique carries a `videos` list, compute `len({v["art_style"] for v in videos if v.get("art_style")})` and use it for both classification and `evidence_summary`. Add a test.
MED - research/pieces/test_f4_classify.py:TestClassifyTechnique.test_unknown_creators_count_toward_videos_not_independent - the test passes precomputed numbers and never models UNKNOWN creators, so its name claims a rule it does not test - rename it to what it checks (for example `test_one_independent_creator_with_videos_is_style_specific`). The counting rule lives upstream of this module, so say that it is untested here.
LOW - research/pieces/f4_classify.py:kimi_views - `research_confidence` is never included in any output item, but the spec asks for separate research_confidence and executability assessments per technique - add it to stage1 and research_only items, or state in the module docstring that it is outside the views contract.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/f4_classify.py
```python
<complete module source>
```
FILE: research/pieces/test_f4_classify.py
```python
<complete test source>
```
