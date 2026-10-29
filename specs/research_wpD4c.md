# SPEC wpD4c: PATCH research/pieces/d4_reconstruct.py + test_d4_reconstruct.py

STAGE 3 OF 3 (this job only): audit and audio rules. semantic_status is ALWAYS exactly "NOT_VERIFIED"; add a separate field audited_status that is set ('AUDITED_' + verdict) ONLY when an `audit` dict with all four of auditor, video_id, verdict, notes is supplied, otherwise absent/None. Sound claims are rejected unless real audio evidence exists; when audio status is UNAVAILABLE or NO_AUDIO_STREAM the sound_image section is exactly {"status": "UNAVAILABLE"}. Unhashable values in unknowns/findings must not raise (report a problem instead). Keep stages 1-2 behaviour and tests.

D1 BEAT SHAPE (authoritative): a beat is a dict with keys beat_id, video_id, start_time {seconds,basis}, end_time {seconds,basis}, information_conveyed, department_findings = {"1".."16": [ {term, status in OBSERVED|NOT_OBSERVED|UNKNOWN|NOT_EXAMINED, observed, evidence:[{frame:int,time:float}], inferred_purpose, alternatives:[str], contraindication, confidence} ]}, reproduction {status, artwork_needed, simplest_method}, unknowns:[str], sequence_pattern. department_findings values are LISTS of finding dicts (NOT one dict per department).

BASE REQUIREMENT (for context):
# WP-D4: full-sequence reconstruction + mechanical truth check (pure; no network/model/Kimi calls). Model text is injected as data.
Goal: turn validated beats (from D1 BeatDict shape, plain dicts) plus audio evidence into the 8-part reconstruction of ONE video, and mechanically check it against the evidence so it teaches more than independent shot descriptions.
1. `reconstruct_sequence(beats, audio_evidence)` -> dict with keys: "narrative_progression" (ordered beat summaries using information_conveyed), "shots_and_transitions" (per shot id: start/end, terms from department_findings 4,5,6,7), "performance" (departments 8,9), "sound_image" (department 13 findings plus audio_evidence; if audio status is UNAVAILABLE or NO_AUDIO_STREAM the section is exactly {"status":"UNAVAILABLE"}), "techniques" (departments 10,11,12,14), "why_it_may_work" (list of {"hypothesis": inferred_purpose, "based_on_beat_ids":[...], "confidence"}), "simplest_reproduction" (reproduction.status/artwork_needed/simplest_method of each beat, NEED_NEW preserved), "unknowns" (union of beats' unknowns + NOT_OBSERVED/UNKNOWN findings) and "relationships" (list of {"from_beat","to_beat","pattern"} for consecutive beats with the sequence_pattern, so order and setup->payoff links are kept).
2. `verify_reconstruction(reconstruction, beats)` -> {"ok": bool, "problems": [str]}. Mechanical checks only: every OBSERVED claim cites an evidence frame/time that exists in a source beat; every hypothesis is in why_it_may_work (never in observed sections); no sound claim exists when audio is UNAVAILABLE; at least one relationship entry exists when there are >=2 beats; no field asserts editing software, lens, hidden rig or screenplay text; no preset id appears that is not in the beats' reproduction data.
Worked example: 3 beats (withhold close-up -> reveal wide cut -> reaction hold) give relationships [{"from_beat":"b1","to_beat":"b2",...},{"from_beat":"b2","to_beat":"b3",...}], why_it_may_work entries are hypotheses with based_on_beat_ids, and a frame-only video gives sound_image == {"status":"UNAVAILABLE"}; deleting one evidence entry makes verify_reconstruction return ok False naming the claim.
STRUCTURAL VS SEMANTIC: verify_reconstruction returns also {"structural_ok": bool, "semantic_status": "NOT_VERIFIED"}. It can only prove structure (evidence cited, hypotheses separated, audio rule, relationships). It must NEVER return semantic_status other than "NOT_VERIFIED"; semantic accuracy (correct technique names, real motion vs replaced illustration, usefulness of the lesson) is verified later by a recorded human/video-grounded audit passed in as `audit` dict {"auditor","video_id","verdict","notes"}; only with such an audit may a separate field semantic_status be set to "AUDITED_" + verdict. NOT_EXAMINED departments are listed under unknowns as "not examined", never as "not observed".


HARD RULES: stdlib only; tests use tempfile/in-memory data, no absolute drive paths, no network; do not drop existing public functions (reconstruct_sequence, verify_reconstruction); keep every currently passing behaviour. The reply must contain BOTH complete files.

OUTPUT FORMAT (mandatory): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/d4_reconstruct.py
```python
<complete module source>
```
FILE: research/pieces/test_d4_reconstruct.py
```python
<complete test source>
```
