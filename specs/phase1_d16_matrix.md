# SPEC D16MAT: NEW `pieces/d16_matrix.py` and `pieces/test_d16_matrix.py` (16-department x 13-video coverage matrix)

GOAL: build the 208-row matrix work/phase1/departments_16/DEPARTMENT_VIDEO_MATRIX.csv (16 departments x 13 reference videos). Each row records what exists, what was extracted, the timestamps and beat ids, the existing software capability, the evidence type, what is missing, and whether further offline analysis is justified. Facts are read from existing files only. Nothing is judged as verified by this module. Human verification is copied from the ledger and never upgrades any evidence type.

REAL FACTS (verified 2026-10-31 against the real files):
- Ledger: work/phase1/coverage_16/DEPARTMENT_VIDEO_LEDGER_16x13.csv, 208 data rows. Columns: dept, dept_name, video_id, set, category, beats, evidence_type, source_reference, verification_status, human_verified_items, missing_data, dependencies, recoverable_from_existing_evidence. Categories: NEVER_EXAMINED, MODEL_ONLY, PARTIAL_MEASUREMENT, HUMAN_VERIFIED_PARTIAL, UNKNOWN, HELDOUT_PROTECTED.
- Beat files: work/phase1/v4/audit_<video_id>/beats_<video_id>.json, key "beats" (a list). Each beat has beat_id, start_time, end_time, and department_findings. department_findings is a DICT keyed by the strings "1" to "16". Each value is a LIST of finding dicts with keys term, status, observed, evidence, confidence. Status values seen: OBSERVED, UNKNOWN, NOT_EXAMINED. A department with no items is treated as MISSING.
- Audio files: work/phase1/v4/audit_<video_id>/audio_<video_id>.json with keys transcript_status (e.g. UNVERIFIED), speech_segments (list of dicts with start, end, text, confidence), sound_classes (e.g. UNKNOWN), silences, gap_classes. Video 5c93ec37 has an empty transcript (0 speech segments).
- Measurements (read-only, existing output of the FROZEN detector; never run it): work/phase1/step4/STEP4_MEASUREMENTS.json, top-level keys "7434a0f7" and "7a1e2b26" only.
- Module list: work/phase1/roadmap_audit/18_MODULE_COVERAGE.csv, columns module_id, module_name, video_id, existing_code, coverage_status. Module ids M01 to M18 (names: M01 SOURCE AND PROVENANCE, M02 STORY EVENTS, M03 HOOKS, M04 STORY STRUCTURE, M05 SCENE PURPOSE, M06 SCENE DIRECTION, M07 CHARACTERS AND CONTINUITY, M08 PERFORMANCE, M09 SHOT SEQUENCING, M10 COMPOSITION, M11 SCREEN MOTION, M12 ANIMATION BEHAVIOR, M13 EDITING AND TRANSITIONS, M14 TIMING AND PACING, M15 VISUAL DESIGN, M16 VFX AND IMPLEMENTATION HYPOTHESES, M17 AUDIO AND SOUND DESIGN, M18 TEXT AND GRAPHICS).

HELD-OUT RULE (hard): the held-out videos are 354a38a0, 37745d70 and baf59433. The module must NEVER open any file under a held-out id (no beats, audio, or measurement read). For those videos, rows come from the ledger only.

DEPARTMENTS (dept number and name):
1 Storytelling / screenwriting; 2 Narrative construction; 3 Direction; 4 Shot planning; 5 Camera language; 6 Composition / visual hierarchy; 7 Editing / transitions; 8 Animation principles; 9 Character performance; 10 Animation production; 11 VFX / compositing; 12 Colour / lighting / art direction; 13 Sound / audiovisual editing; 14 Captions / motion graphics; 15 Pacing / attention; 16 Practical execution.

DEPARTMENT TO MODULE MAP (fixed; use exactly this, it is not a new architecture):
1 -> M02, M03, M04; 2 -> M02, M04, M07; 3 -> M05, M06, M07; 4 -> M05, M09; 5 -> M11; 6 -> M10, M15; 7 -> M09, M13; 8 -> M12; 9 -> M08; 10 -> M12, M16; 11 -> M16; 12 -> M15; 13 -> M17; 14 -> M18; 15 -> M14; 16 -> M16.
For the capability column, take the existing_code text of the matching module row for that video from 18_MODULE_COVERAGE.csv (first row found for that module_id and video_id). Copy the text; do not rewrite it.

CONSTANTS: HELD = {"354a38a0", "37745d70", "baf59433"}; DEV = {"10151cce", "264e48c4", "585b32de", "5c93ec37", "69a00a0f", "7434a0f7", "7a1e2b26", "85c38505", "a44aef0b", "caf6fb64"}; MEASURED_VIDEOS = {"7434a0f7", "7a1e2b26"}; MEASURED_DEPTS = {5, 7}; ROOT = repository root (the directory that contains pieces/).

FUNCTIONS (standard library plus the already installed packages only; no network; no model calls):
- load_ledger(root) -> dict keyed by (int dept, video_id) with the ledger row as a dict. Read the CSV with the csv module.
- load_beats(root, video_id) -> list of beat dicts from the beat file. RAISE ValueError if video_id is in HELD, before any open() call.
- findings_for(beat, dept) -> list of finding dicts for that department ([] if missing).
- status_summary(beats, dept) -> dict with counts observed, unknown, not_examined, missing (missing = beats with no finding items for that department).
- observed_beats(beats, dept) -> list of beat dicts where at least one finding has status OBSERVED.
- audio_facts(root, video_id) -> dict with transcript_status, speech_segment_count, sound_classes (raw value), read from the audio file. Only for dept 13 rows.
- capability_text(root, module_ids, video_id) -> str, existing_code of the first matching module row, or "NONE_RECORDED".
- build_rows(root) -> list of 208 dicts with the COLUMNS below, ordered by dept then video_id.
- write_matrix(root, out_path) -> writes the CSV with header and the rows (creates the parent folder with os.makedirs(exist_ok=True)); returns the row count.
- main(argv): with no arguments, write to ROOT/work/phase1/departments_16/DEPARTMENT_VIDEO_MATRIX.csv and print the row count.

COLUMNS (in this order):
dept, dept_name, video_id, set, ledger_category, research_status, evidence_type, measured, observed_beat_count, observed_beat_ids, observed_time_min, observed_time_max, unknown_beat_count, not_examined_beat_count, missing_beat_count, extraction_performed, sources_read, implemented_capability, human_verified_items_count, further_offline_analysis, teachable_to_writer_director, remaining_validation.

RULES FOR EACH COLUMN:
- ledger_category: copied from the ledger.
- research_status (record level; the vocabulary is RESEARCH_COMPLETE_FROM_AVAILABLE_EVIDENCE, PARTIAL_RESEARCH, NOT_EXAMINED, BLOCKED_BY_SOURCE, UNKNOWN):
  - held-out video: BLOCKED_BY_SOURCE.
  - video 5c93ec37 and dept 13: BLOCKED_BY_SOURCE (empty transcript).
  - ledger category NEVER_EXAMINED: NOT_EXAMINED.
  - ledger category UNKNOWN: UNKNOWN.
  - MODEL_ONLY, PARTIAL_MEASUREMENT, HUMAN_VERIFIED_PARTIAL: PARTIAL_RESEARCH.
  - RESEARCH_COMPLETE_FROM_AVAILABLE_EVIDENCE is NEVER produced at record level by this module. It is assigned later at department level by hand. The test asserts this.
- evidence_type: "NONE_NOT_READ" for held-out rows; "MEASUREMENT" if measured is Y; "AI_OBSERVATION" if observed_beat_count > 0 and not measured; "TRANSCRIPT_UNVERIFIED" for dept 13 when speech_segment_count > 0 and not AI_OBSERVATION; otherwise "NONE".
- measured: Y if video in MEASURED_VIDEOS and dept in MEASURED_DEPTS and the video key exists in STEP4_MEASUREMENTS.json; else N. Held-out rows: N.
- observed_beat_count, observed_beat_ids (semicolon separated, in file order), observed_time_min and observed_time_max (min start_time and max end_time over observed beats; empty if none), unknown_beat_count, not_examined_beat_count, missing_beat_count: from status_summary. Held-out rows: all 0 and empty, with extraction_performed "none (protected; not read)".
- extraction_performed: text, one of: "vision-report text read per beat (department_findings)" when observed_beat_count > 0; "frozen Step 4 detector measurement (existing output, read only)" when measured; "cached speech-to-text transcript read (unverified)" for dept 13 with speech segments; "none (status NOT_EXAMINED on every beat)" for NEVER_EXAMINED; "none" otherwise. A row can carry more than one; join with " + ".
- sources_read: repo-relative paths actually read for that row, joined with ";". Always include the beat file (for non-held-out rows), the ledger path, and the audio file for dept 13, and STEP4_MEASUREMENTS.json for measured rows.
- implemented_capability: "modules " + module ids + ": " + capability_text(...).
- human_verified_items_count: 1 if the ledger human_verified_items cell is non-empty, else 0. This is copied only. It never changes evidence_type or research_status.
- further_offline_analysis: "JUSTIFIED_NON_MODEL: <reason>" for dept 12 (brightness summary from media, if media exists), dept 13 (speech timing from the cached transcript when present), dept 14 (caption text already in observations), dept 15 (durations and rhythm from beat timings). For all other departments and all held-out rows: "NOT_JUSTIFIED_WITHOUT_HUMAN_OR_NEW_MODEL: <reason>". For depts 5 and 7 the reason is "frozen detector; Step 5 deferred; no re-run". Held-out rows: "NOT_ALLOWED: protected".
- teachable_to_writer_director: by evidence_type: MEASUREMENT -> "measured camera or transition fact for this interval only; no meaning attached"; AI_OBSERVATION -> "AI reading of this video only; teach only after human verification"; TRANSCRIPT_UNVERIFIED -> "speech timing only; wording unverified"; NONE -> "nothing teachable from this record"; NONE_NOT_READ -> "none (protected)".
- remaining_validation: "human verification of listed beats" for AI_OBSERVATION; "human check of meaning" for MEASUREMENT; "transcript verification" for TRANSCRIPT_UNVERIFIED; "new evidence or method required" for NONE; "protected; Step 5 only" for held-out rows.

HARD RULES:
- Standard library plus json, csv, os, re, ast only. No network. No model calls. No subprocess. No import of pieces/p6_measure_track.py or any detector module.
- Read only. The only write is the matrix CSV at the output path (and its folder).
- Do not print or read any file under D:\aai work\secrets or any .env file.
- Do not write the seven-letter name of the 3D software tool anywhere in code, tests or comments. The loop rejects the file.
- Use ast.literal_eval only if a value is a string that looks like a list; prefer the dict form already present in the file.

TESTS for `pieces/test_d16_matrix.py` (pytest; the test file imports pieces/d16_matrix.py; ROOT is found from the test file location):
1. build_rows returns exactly 208 rows; the pairs (dept, video_id) are unique; there are 16 departments and 13 videos.
2. Every held-out row has research_status BLOCKED_BY_SOURCE, evidence_type NONE_NOT_READ, observed_beat_count 0, observed_beat_ids "", and extraction_performed "none (protected; not read)".
3. load_beats raises ValueError for each held-out id.
4. Every row whose ledger_category is NEVER_EXAMINED has research_status NOT_EXAMINED and observed_beat_count 0.
5. For every non-held-out row, observed_beat_count equals the number of beats in the real beat file whose department_findings[str(dept)] contains an item with status OBSERVED (recompute in the test from the file; do not reuse build_rows output for this).
6. measured is Y only for depts 5 and 7 and videos 7434a0f7 and 7a1e2b26.
7. No row has research_status RESEARCH_COMPLETE_FROM_AVAILABLE_EVIDENCE.
8. evidence_type values are only in {NONE_NOT_READ, MEASUREMENT, AI_OBSERVATION, TRANSCRIPT_UNVERIFIED, NONE}. No value equals HUMAN_VERIFIED.
9. human_verified_items_count equals 1 exactly where the ledger's human_verified_items cell is non-empty.
10. Every path listed in sources_read exists in the repository (paths split on ";").
11. write_matrix(root, tmp_path / "m.csv") writes a CSV with a header and 208 data rows and does not write anywhere else (check that the rest of tmp_path only contains m.csv).
12. Uncertainty handling: for dept 13 and video 5c93ec37 the row is BLOCKED_BY_SOURCE and its speech segment count is 0 in the real audio file (recompute in the test).

REAL-DATA NOTE: tests must read the real files in the repository (not mocked data) for items 5, 6, 9, 10 and 12.

REPLY RULE: return the complete source of both files. Do not add any other text.
REPLY PARSER TRAP: no line of any file you write may start with the letters F-I-L-E followed by a colon.
FORBIDDEN-WORD TRAP: the loop refuses any file containing the seven-letter name of the 3D software tool. Never type it, not even in a comment or a test string.

OUTPUT FORMAT (mandatory): reply with ONLY these two blocks, no other text. Each block starts with the line `FILE: <path>` directly followed by a fenced code block starting with ```python on its own line and ending with ``` on its own line:
FILE: pieces/d16_matrix.py
```python
<complete source>
```
FILE: pieces/test_d16_matrix.py
```python
<complete source>
```
