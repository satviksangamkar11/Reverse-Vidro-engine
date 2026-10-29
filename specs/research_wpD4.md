# WP-D4: full-sequence reconstruction + mechanical truth check (pure; no network/model/Kimi calls). Model text is injected as data.
Goal: turn validated beats (from D1 BeatDict shape, plain dicts) plus audio evidence into the 8-part reconstruction of ONE video, and mechanically check it against the evidence so it teaches more than independent shot descriptions.
1. `reconstruct_sequence(beats, audio_evidence)` -> dict with keys: "narrative_progression" (ordered beat summaries using information_conveyed), "shots_and_transitions" (per shot id: start/end, terms from department_findings 4,5,6,7), "performance" (departments 8,9), "sound_image" (department 13 findings plus audio_evidence; if audio status is UNAVAILABLE or NO_AUDIO_STREAM the section is exactly {"status":"UNAVAILABLE"}), "techniques" (departments 10,11,12,14), "why_it_may_work" (list of {"hypothesis": inferred_purpose, "based_on_beat_ids":[...], "confidence"}), "simplest_reproduction" (reproduction.status/artwork_needed/simplest_method of each beat, NEED_NEW preserved), "unknowns" (union of beats' unknowns + NOT_OBSERVED/UNKNOWN findings) and "relationships" (list of {"from_beat","to_beat","pattern"} for consecutive beats with the sequence_pattern, so order and setup->payoff links are kept).
2. `verify_reconstruction(reconstruction, beats)` -> {"ok": bool, "problems": [str]}. Mechanical checks only: every OBSERVED claim cites an evidence frame/time that exists in a source beat; every hypothesis is in why_it_may_work (never in observed sections); no sound claim exists when audio is UNAVAILABLE; at least one relationship entry exists when there are >=2 beats; no field asserts editing software, lens, hidden rig or screenplay text; no preset id appears that is not in the beats' reproduction data.
Worked example: 3 beats (withhold close-up -> reveal wide cut -> reaction hold) give relationships [{"from_beat":"b1","to_beat":"b2",...},{"from_beat":"b2","to_beat":"b3",...}], why_it_may_work entries are hypotheses with based_on_beat_ids, and a frame-only video gives sound_image == {"status":"UNAVAILABLE"}; deleting one evidence entry makes verify_reconstruction return ok False naming the claim.
STRUCTURAL VS SEMANTIC: verify_reconstruction returns also {"structural_ok": bool, "semantic_status": "NOT_VERIFIED"}. It can only prove structure (evidence cited, hypotheses separated, audio rule, relationships). It must NEVER return semantic_status other than "NOT_VERIFIED"; semantic accuracy (correct technique names, real motion vs replaced illustration, usefulness of the lesson) is verified later by a recorded human/video-grounded audit passed in as `audit` dict {"auditor","video_id","verdict","notes"}; only with such an audit may a separate field semantic_status be set to "AUDITED_" + verdict. NOT_EXAMINED departments are listed under unknowns as "not examined", never as "not observed".


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/d4_reconstruct.py; test file: research/pieces/test_d4_reconstruct.py (tests import the module by its plain file name, e.g. `from d4_reconstruct import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD4
LUNA (gpt-6-luna high):
HIGH - research/pieces/d4_reconstruct.py:267 - OBSERVED claims contain no evidence citations, and the verifier only checks whether some evidence exists in the source department; deleting the evidence for a specific claim can still pass - attach frame/time citations to each claim and verify each citation against its source beat; add a regression that removes one cited entry

MED - research/pieces/d4_reconstruct.py:11 - Sorting by beat ID can reverse the supplied sequence (for example, `b2` before `b10`), changing narrative order and setup/payoff links - preserve the validated beat order

MED - research/pieces/d4_reconstruct.py:231 - Any audit containing a truthy `verdict` sets `AUDITED_*`, even if required `auditor`, `video_id`, or `notes` fields are absent - require the specified audit fields before setting the audited status

MED - research/pieces/d4_reconstruct.py:381 - If an unavailable reconstruction’s `sound_image` loses its `status` field, sound claims can pass verification because the verifier treats the missing status as available - reject sound claims unless availability is established by audio evidence; retain the exact unavailable sentinel requirement

SONNET (latest):
wpD4
- HIGH - d4_reconstruct.py:28-110,152-157,252-259 - department_findings treated as {dept: dict}, but the D1 schema is {dept_id: [finding,...]} with finding.term/status/observed/evidence[{frame|time}]. Any D1-valid beat raises AttributeError ('list' has no 'get'); reproduced. Tests use the wrong dict shape so never catch it - fix: iterate the list per dept, use term/observed, evidence entries for frame/time; update fixtures.
- MED - d4_reconstruct.py:238-241 - spec: semantic_status must NEVER be other than "NOT_VERIFIED" (audit sets a separate field); code sets semantic_status = "AUDITED_<verdict>". Fix: keep semantic_status NOT_VERIFIED and put audit result in e.g. `audited_status`; also require audit video_id/auditor present.
- MED - d4_reconstruct.py:112,128 - why_it_may_work reads nonexistent top-level beat["inferred_purpose"]/["confidence"]; in D1 inferred_purpose lives in each finding (and top-level `inferred` claims), so hypotheses are never produced from real beats - fix: collect finding["inferred_purpose"] and inferred[*].claim/confidence.
- MED - d4_reconstruct.py:11 - beats ordered by beat_id string ("b10" < "b2"), corrupting narrative order and relationships - fix: sort by (start_time, beat_id).
- LOW - d4_reconstruct.py:149 - unknowns set.update on unhashable items raises; sort mixed types.
- LOW - d4_reconstruct.py:348,377 - hypothesis words ("likely","indicates") flag legitimate observed text over 20 chars.
- LOW - d4_reconstruct.py:267-343 - evidence check only tests that an evidence key exists, not that cited frame/time exists in the beat's evidence list (spec: "exists in a source beat").


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD4
Rounds: 0, 2 and 3 were API failures (status=0, empty). Only round 1 was a real attempt (200, files parsed, tests failed), after which the older seed was restored. None of the review findings has been applied, and the 23 tests are green only because they use the wrong fixture shape.

Unapplied findings and the fix for each:
- Sonnet HIGH (schema): `department_findings` is {dept_id: [finding, ...]}, each finding having term, status, observed and evidence[{frame|time}]. Code calls `.get` on a dict, so a D1-valid beat raises AttributeError. Fix: iterate the list per department, use term/observed for text, read frame/time from the evidence entries, and rewrite all test fixtures to the list shape.
- Luna HIGH (citations): claims carry no citations and the verifier only checks that some evidence key exists. Fix: each reconstructed claim keeps its frame/time evidence. The verifier checks every cited frame/time against that source beat's evidence list. Add a regression test that deletes one cited evidence entry and expects ok False naming the claim.
- Luna MED and Sonnet MED (order): sorting by beat_id puts "b10" before "b2". Fix: keep the supplied order (or sort by start_time, then beat_id).
- Luna MED and Sonnet MED (audit): the code sets semantic_status to "AUDITED_<verdict>". Fix: semantic_status is always "NOT_VERIFIED"; set a separate `audited_status` only when auditor, video_id, verdict and notes are all present.
- Luna MED (audio): a sound_image missing `status` passes. Fix: allow sound claims only when audio evidence is actually available, and require the exact {"status":"UNAVAILABLE"} sentinel otherwise.
- Sonnet MED (hypotheses): `why_it_may_work` reads a nonexistent top-level `inferred_purpose` and `confidence`. Fix: use each finding's inferred_purpose and the `inferred[*].claim` and confidence entries.
- Sonnet LOW (unknowns): `set.update` raises on unhashable items. Fix: de-duplicate with a list and sort with a string key.
- Sonnet LOW (hypothesis words): "likely", "indicates" and similar words flag legitimate observed text longer than 20 characters. Fix: apply the check only to hypothesis markers, not to any long string.


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpD4
Why rounds failed: round 0 produced code on the wrong fixture shape. Round 1 (Nemotron, 23 KB reply) was cut or malformed and contained only the module, no test block (files_ok False, "missing test_d4_reconstruct.py"). Rounds 2-3 Codex fixer: API failures (status=0, empty). No finding was ever applied. Restored 23 tests pass only because fixtures use department_findings as {dept: dict}, but the D1 schema is {dept_id: [finding,...]} with term/status/observed/evidence[{frame|time}].
1. HIGH: all department reads (reconstruct_sequence and verify helpers, _build_evidence_index) must iterate the finding list per dept, use term/observed text and evidence frame/time. Rewrite every fixture to the list shape. A D1-valid beat currently raises AttributeError.
2. HIGH: each OBSERVED claim must carry its evidence citations (frame/time); verify_reconstruction must check each citation exists in that source beat's evidence list. Regression: delete one evidence entry, expect ok False naming the claim.
3. MED: semantic_status must stay "NOT_VERIFIED" always. Audit result goes to a separate audited_status, set only when auditor, video_id, verdict and notes are all present.
4. MED: preserve supplied beat order (drop sort by beat_id; "b10" < "b2"). why_it_may_work must read finding inferred_purpose and inferred[*].claim/confidence, not top-level keys.
5. MED: sound claims allowed only when audio evidence is available; missing sound_image status must fail verification. unknowns: dedupe via list, sort by str; limit hypothesis-word check to marker words.
Tip: ask for the module and the test as two smaller requests, since the combined reply got truncated.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/d4_reconstruct.py
```python
<complete module source>
```
FILE: research/pieces/test_d4_reconstruct.py
```python
<complete test source>
```
