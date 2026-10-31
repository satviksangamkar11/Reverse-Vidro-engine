# SPEC D16TCH: NEW `pieces/d16_teacher.py` and `pieces/test_d16_teacher.py` (evidence-linked teacher candidate inventory)

GOAL: build work/phase1/departments_16/CROSS_VIDEO_TEACHER_CANDIDATES.json. Every supported AI observation in the 10 development videos becomes one candidate record, linked to its video, beat id and times. The 7 lessons of the 7434a0f7 candidate file are included with their status unchanged. Nothing is promoted. F4 is not changed. No candidate is eligible for teaching in this build.

REAL FACTS (verified 2026-10-31):
- Beat files: work/phase1/v4/audit_<video_id>/beats_<video_id>.json, key "beats". Each beat: beat_id, start_time, end_time, department_findings (a DICT with keys "1" to "16"; each value is a LIST of dicts with keys term, status, observed, evidence, confidence). Status values: OBSERVED, UNKNOWN, NOT_EXAMINED.
- Lesson file: work/phase1/overlays/lesson_candidates_7434a0f7.json. Top-level keys: schema, source_video, created, note, lessons. lessons is a list of 7 dicts with keys lesson_id (e.g. "L1_preview_then_retell"), title, status, technique_tags (currently an empty list), observed_events (list of dicts with video_id, beat_id, start_time, end_time, event, observation_level, evidence_refs).
- F4 diagnosis: work/phase1/f4_diagnosis_v2.json. Top-level keys: summary, techniques (an integer count of 13), diagnoses (a list of 13 dicts with keys id, classification, research_confidence, executability, bucket, reasons, evidence_summary, technique), input, video_meta. summary.by_classification is {"EXPERIMENTAL": 13}.
- Dev videos (10, the held-out videos are excluded by rule): 10151cce, 264e48c4, 585b32de, 5c93ec37, 69a00a0f, 7434a0f7, 7a1e2b26, 85c38505, a44aef0b, caf6fb64.

HELD-OUT RULE (hard): video ids 354a38a0, 37745d70 and baf59433 must not be opened, and must not appear anywhere in the output. The module raises ValueError if any of them is requested.

CONSTANTS: DEV (the 10 ids above); HELD (the 3 ids); DEPT_NAMES (1 Storytelling / screenwriting, 2 Narrative construction, 3 Direction, 4 Shot planning, 5 Camera language, 6 Composition / visual hierarchy, 7 Editing / transitions, 8 Animation principles, 9 Character performance, 10 Animation production, 11 VFX / compositing, 12 Colour / lighting / art direction, 13 Sound / audiovisual editing, 14 Captions / motion graphics, 15 Pacing / attention, 16 Practical execution); STORY_DEPTS = {1, 2, 3, 4}.

FUNCTIONS (standard library and json only; no network; no model calls):
- load_beats(root, video_id) -> list of beats (RAISE ValueError for held-out ids before opening anything).
- observation_items(beat) -> yields (dept_number, index, item) for each item with status OBSERVED and a non-empty observed text. Use the dict keys "1" to "16".
- build_candidates(root) -> list of candidate dicts (see FIELDS).
- build_lessons(root) -> list of lesson dicts (see LESSON FIELDS).
- build_output(root) -> dict with keys schema, created_note, summary, candidates, lessons.
- write_output(root, out_path) -> writes JSON with indent=2, sorted keys, and returns the candidate count. Creates the parent folder with os.makedirs(exist_ok=True).
- main(argv): with no arguments, writes work/phase1/departments_16/CROSS_VIDEO_TEACHER_CANDIDATES.json under the repository root and prints the count.

FIELDS of each candidate (all required):
- candidate_id: "D<dept>-<video_id>-<beat_id>-<index>" (index is the position of the item in the list, starting at 0).
- department_id (int), department_name.
- video_id, beat_id, start_time, end_time (copied from the beat).
- direct_observation: the item's observed text, copied verbatim.
- observation_source: "AI vision report (department_findings), unverified".
- interpretation: "not assessed" (no interpretation is written by this module).
- directing_application: "not assessed".
- verification_status: "AI_OBSERVATION_UNVERIFIED".
- narrative_scene_relevance: "STORY_OR_DIRECTION" for depts 1 to 4, otherwise "PRODUCTION_OR_PRESENTATION".
- distinct_video_count: 1.
- independent_creator_count: 0 (creator not recorded for any video).
- other_videos_with_same_department_observation: sorted list of other DEV video ids that have an OBSERVED item for the same department. Label: not independent creator evidence.
- unknowns: fixed list ["creator not recorded", "art style not recorded", "vision report is model output with LOW confidence unless the item says otherwise"]. Add "item confidence is LOW" when the item's confidence field is "LOW".
- f4_status: "NOT_MAPPED (no technique id on this observation)".
- eligibility: "NOT_ELIGIBLE (F4 unchanged; no verified creators; no recorded art style)".
- practical_compatibility: "NOT_CHECKED_IN_THIS_RECORD (see PRODUCTION_EXECUTION_COMPATIBILITY.json)".

LESSON FIELDS: for each lesson in the file: lesson_id, title, status (copied), technique_tags (copied), f4_status: "UNMAPPED (technique_tags is empty)", eligibility: "NOT_ELIGIBLE (candidate; not promoted)", and observed_events. Each observed event keeps video_id, beat_id, start_time, end_time, event, observation_level and evidence_refs copied verbatim, plus "distinct_video_count": 1 and "independent_creator_count": 0.
WITHDRAWN RULE (hard): the lesson whose lesson_id starts with "L4" has two observed events with beat_id "event_001" and "event_002" that the owner withdrew (no arm movement at 0.6-1.1 s and 6.7-6.9 s; the 2.27 s and 3.2 s snaps are not confirmed). For those two events set eligibility "WITHDRAWN_INACTIVE" and status_override "UNKNOWN_INACTIVE". They are kept, not deleted. Their text stays in the record.
Do not change any other lesson field.

F4 SUMMARY: copy summary.by_classification and the count of diagnoses from the F4 file into the output key "f4_reference". Do not compute or change F4.

SUMMARY KEY (in the output): counts of candidates per department_id (keys "1" to "16", value int) and per video_id; total candidate count; lesson count; withdrawn event count (2).

HARD RULES:
- Standard library plus json, os only. No network, no model calls, no subprocess.
- Read only, except the single output file.
- Do not modify any lesson, overlay, F4 or beat file.
- Do not print or read any file under D:\aai work\secrets or any .env file.
- Do not write the seven-letter name of the 3D software tool anywhere in code or tests.

TESTS for `pieces/test_d16_teacher.py` (pytest; read the real files):
1. load_beats raises ValueError for each held-out id.
2. The output text contains none of the three held-out ids.
3. Every candidate's video_id is in DEV, and its beat_id exists in that video's real beat file with the same start_time and end_time.
4. The number of candidates equals the number of OBSERVED items with non-empty observed text across the 10 real dev beat files (recompute in the test).
5. Every candidate has independent_creator_count 0, distinct_video_count 1, verification_status AI_OBSERVATION_UNVERIFIED, and eligibility starting with NOT_ELIGIBLE.
6. No eligibility value starts with "ELIGIBLE " or equals "ELIGIBLE".
7. Lesson L4 events event_001 and event_002 have eligibility WITHDRAWN_INACTIVE and status_override UNKNOWN_INACTIVE; the text of their event field equals the lesson file's text.
8. The lesson count is 7 and each lesson's observed_events list length equals the length in the source file.
9. f4_reference counts match the F4 file (13 diagnoses, all EXPERIMENTAL).
10. build_output run twice gives identical JSON (determinism).
11. write_output(root, tmp_path / "c.json") writes only that file under tmp_path.

REPLY RULE: return the complete source of both files. Do not add any other text.
REPLY PARSER TRAP: no line of any file you write may start with the letters F-I-L-E followed by a colon.
FORBIDDEN-WORD TRAP: the loop refuses any file containing the seven-letter name of the 3D software tool. Never type it.

OUTPUT FORMAT (mandatory): reply with ONLY these two blocks, no other text. Each block starts with the line `FILE: <path>` directly followed by a fenced code block starting with ```python on its own line and ending with ``` on its own line:
FILE: pieces/d16_teacher.py
```python
<complete source>
```
FILE: pieces/test_d16_teacher.py
```python
<complete source>
```
