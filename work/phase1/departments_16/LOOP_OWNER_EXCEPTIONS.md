# Loop owner exceptions and final job states (2026-10-31)

Owner decision (verbatim intent): keep test-quality blockers. Judge READY does not override valid Codex test findings. The Loop System review policy is unchanged.

## d16_granth: NOT ACCEPTED. Previous exception record was inaccurate and is withdrawn until the owner decides.
- Final loop state: test-review-open (history preserved in _loop/d16_granth/status.json and review_*.md).
- Correction: this record previously said the one open item was a LOW note. That was wrong. _loop/d16_granth/TEST_FINDINGS.md lists three Codex MED findings on pieces/test_d16_granth.py, at lines 60, 90 and 95:
  - Line 60-63: the asset-availability check compares the module's own asset_status with the module's own assets_available, so a broken found/not-found check would pass.
  - Line 90: lesson story_directing_guidance and need are not asserted against their specified values.
  - Line 95: the consumer-search test passes when the result list is empty. The 124-entry result is not asserted anywhere in the test.
- The judge's rejection of these as "test-coverage notes" conflicts with the owner rule (a MED that lets incorrect output pass must block). They are not closed by a later review that does not repeat them.
- Test status: 11 passed, 1 skipped (the symlink test, named test_symlink_target_refused).
- SKIPPED / UNVERIFIED: test_symlink_target_refused. os.symlink raises OSError on this Windows system, so the symlink refusal is not verified. Cross-platform verification is NOT claimed.
- Boundary: GranthStudio read-only; no write by d16 code.
- Output: work/phase1/departments_16/PRODUCTION_EXECUTION_COMPATIBILITY.json was written by running the module's main(). 124 consumer entries, 11 presets, 13 techniques, 7 lessons. Its content is only as trustworthy as the open test findings above.
</content>

## Loop concurrency exception (owner, 2026-10-31)
- Owner approved a fifth concurrent loop (d16_media) for this D16 repair. Cap of four remains the default. Exception applies to this launch only.

## d16_granth adjudication (2026-10-31, round 2)
- Groq MED, load_techniques propagates assets_available from the F4 file: DISMISSED. Evidence: the F4 file (work/phase1/f4_diagnosis_v2.json) gives assets_available false for all 13 techniques, and the spec says to take the value from that file. Forcing False would hide the real source value.
- Ultra MED, hard-coded lesson filename with hash: NOT a false PASS. The lesson file is a fixed authorised input. Recorded as a rule note, no output change.
- Ultra MED, data-specific technique assertions in test_d16_granth.py: NOT a false PASS. A change in the data makes the test fail, not pass. Recorded as a rule note.
- Ultra MED, silent except in consumer_search: NOT an output error. Logging only.
- Codex round 2: READY (one LOW on excerpt and mentions assertions; not a false PASS).
- Judge round 2: READY.
- Tests: 12 passed, 1 skipped (test_symlink_target_refused, unsupported on this Windows system; UNVERIFIED).

## d16_granth final adjudication (2026-10-31, Opus final decision accepted)
- Codex review pass on the current code: one MED, tests do not assert that the real index and F4 files contain the specified keys. DISMISSED with evidence: a missing key makes the test raise an error (loud failure), so no incorrect output can pass silently. Recorded as a spec-compliance note.
- Ultra HIGHs in TEST_FINDINGS (test_d16_granth.py lines 67 and 85): DISMISSED with evidence: both tests fail loudly on a data change, so they cannot pass wrong output.
- Groq MED on load_techniques: DISMISSED (see earlier adjudication).
- Correction: an earlier line in this file said "Codex/judge round 2: READY". That verdict belongs to review_1 (round-1 code). The current code was reviewed by the Codex pass above.
- Output: PRODUCTION_EXECUTION_COMPATIBILITY.json regenerated from the current code at this time.
- Tests: 12 passed, 1 skipped (symlink test; UNVERIFIED on this Windows system).

## d16_teacher acceptance (2026-10-31, Opus final decision accepted)
- Loop state: passed (1 coder round). Reviews: Ultra READY, Codex READY, Groq NONE (input truncated; recorded as "no review", not READY).
- Tests: 18 passed (re-run 20:36).
- LOW exception (a): summary.lesson_count is not asserted in test_d16_teacher.py. Not a false PASS for candidate content; logged.
- LOW exception (b): a stray eligibility or status_override key added to a non-withdrawn event would pass. Logged; not a false PASS for the required fields.
- Output: CROSS_VIDEO_TEACHER_CANDIDATES.json regenerated at 20:41 from the current code. 2,147 generated candidates are candidate records only, not verified filmmaking knowledge.

## d16_matrix acceptance (2026-10-31)
- Loop state: passed (round 0 after the repair round). Reviews: Ultra READY, Codex READY, Groq NONE (input truncated; recorded as "no review").
- Size limits (characters): module 8,999 of 9,000; test_d16_matrix.py 4,878 of 5,000; test_d16_matrix_extra.py 3,658 of 5,000.
- Tests: 23 passed (re-run 20:48).
- Codex LOW (teacher-style note): module-to-department mapping and implemented_capability copying are not asserted. Logged as LOW; does not permit a wrong evidence status to pass.
- Output: DEPARTMENT_VIDEO_MATRIX.csv not yet regenerated by main() in this pass (next step).

## d16_teacher repair adjudication (2026-10-31, checked by the supervisor)
- Groq HIGH (DEV tuple hard-coded; missing beat file would raise): DISMISSED with evidence. All 10 DEV ids have a beats file on disk (checked 21:04); build_output runs and returns 2,147 candidates and 7 lessons. A missing file would fail loudly, not pass wrongly.
- Ultra, Codex: READY.
- Judge READY: noted as the old judge path (run started before the judge fix). Acceptance rests on the supervisor check above, not on the judge.
- Tests: 24 passed (re-run 21:03). Missing-key label test, lesson-count and event-key assertions present.
- Output: CROSS_VIDEO_TEACHER_CANDIDATES.json regenerated at 21:04 from the repaired code.

## d16_media supervisor closure of the three blockers (2026-10-31, no loop run)
- Opus review (medium, read-only) checked the code and the reviews. Verdict: B2 and B3 valid; B1 not a blocker.
- B1 (audio key validation): NOT A BLOCKER. _audio_stats already checks all 11 keys in AUDIO_KEYS via _need. Codex's finding described an older version.
- B2 (audio key gap reaching colour): FIXED by supervisor. colour_rows now calls _audio_stats first and blocks the row with the key-gap note.
- B3 (hard_cut_count kept on a beats key gap): FIXED by supervisor. _pacing_row sets hard_cut_count only after the beats load succeeds; a gap gives "".
- Regression tests: pieces/test_d16_media_gaps.py (2 tests, pass). Existing media tests: 23 pass.
- Full repository suite: 1922 passed, 1 skipped (symlink, UNVERIFIED), 0 failed.
- Ultra round-1 items: wording only; dismissed (the code already uses the specified messages).
- Codex test MED (hard-coded 9.46.07 PM in test_colour_not_all_blocked): NOT A FALSE PASS; the spec requires that assertion. Logged as a note.
- Outputs regenerated: six media CSVs in work/phase1/departments_16/media. No held-out id appears; the held-out reference timestamps are PROTECTED (not UNMAPPED); 9.47.17 remains the only UNMAPPED row.
- Still OPEN (scope decision): the key-gap exclusion is one-way. A beats key gap still leaves colour MEASURED and audio analysed Y; an audio key gap still leaves pacing statistics and caption rows. Opus recommends one shared key-gap check. Needs owner confirmation of scope.
- Media loop state: review-open (the loop's own state; it was not re-run). Supervisor acceptance applies only to the three blockers above.
