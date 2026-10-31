# AUTOMATED READINESS REPORT (2026-10-31, before the one human round)

Time of writing: about 15:25 IST. Deadline 16:15 IST. Items are reported as DONE, PENDING (still running), or INCOMPLETE. Nothing is reported as passed unless a file or a test shows it.

## 1. Tests and jobs
| Item | Result | Evidence | Status |
|---|---|---|---|
| Engine repository full suite (pieces/) | 1745 passed, 26 subtests, 0 failed | work/phase1/roadmap_audit_tests_2026-10-31.txt | DONE (run earlier today; no later code change to pieces/ except the annotation test files below) |
| Coverage invariants test (12 tests) | 12 passed, no skips | pieces/test_coverage_invariants.py; loop job p6_coverage_invariants passed | DONE |
| Annotation protocol structural test (frozen round-0 file pieces/test_annotation_protocol.py) | 16 tests pass locally; loop job ended test-review-open (FIX FIRST on test quality from codex, groq and ultra) | _loop/p6_annotation_protocol/TEST_FINDINGS.md | INCOMPLETE as a gate. The reviewers' findings are real: (a) scene_boundary check accepts extra values; (b) test reads start_s and end_s but REQUIRED_COLUMNS does not list them (KeyError risk); (c) value search misses continuation lines; (d) time test does not catch KeyError |
| Additive annotation source-reference test (pieces/test_annotation_source_refs.py) | 8 test functions, 24 tests together with the frozen file; passed; loop job p6_annotation_source_refs passed round 0; codex, groq, ultra all READY. Checks source ID, interval, zero-length flags, exact scene_boundary values, detector-word cells, value lists, held-out exclusion | DONE (the frozen file is unchanged) |

## 2. Source references
- Bundle references checked: 8 distinct file names. Two were short names; they are now full paths (work/phase1/step4/STEP4_MEASUREMENTS.json and work/phase1/overlays/lesson_candidates_7434a0f7.json).
- Pilot sheets and label form exist (work/phase1/story_annotation/pilot/).
- Held-out ids: none in the pilot label form or sheet names (checked by the frozen structural test).

## 3. Timestamp issues (known, kept, flagged)
- 7434a0f7 shot_001: 0.0 to 0.0 (zero length). FLAG. Original evidence kept.
- 7434a0f7 shot_004: 9.0 to 9.0 (zero length). FLAG.
- Overlapping spans (same interval, two records): 7434a0f7 shot_003 and event_003 (5.0-8.5 and 5.0-6.5); event_005 and shot_005 (9.5-11.0 and 9.5-12.5). 7a1e2b26 shot_001/event_001, shot_002/event_002, shot_004/event_003, shot_005/event_004. Not errors; read as one span with two records.
- Detector hard-cut times (7a1e2b26): 1.88, 3.04, 4.29, 5.88, 7.62 s are tool output. The 9.96 s cut is owner-confirmed.

## 4. D4 impact analysis (automated)
- Complete: work/phase1/roadmap_audit/D4_PROPOSED_CHANGE_TABLE.md (file and record level) and D4_DECISION_SUMMARY.md.
- Counts (exact): overlay 25 DIRECT_OBSERVATION records; staging 22 DIRECT_OBSERVATION and 6 MEASURED; historical beat records 0.
- Gate policy: pieces/p6_stage1_staging.py line 16 accepts only DIRECT_OBSERVATION and MEASURED. Any other level is a block. Changing the labels is therefore a policy change, not a label fix.
- No change applied.

## 5. 18-module coverage reconciliation
- The coverage CSV (work/phase1/roadmap_audit/18_MODULE_COVERAGE.csv, 234 rows) was reconciled with the beat files in the earlier audit. It was not regenerated in this phase, and no new evidence was added.
- Under the frozen rules, the held-out videos remain HELDOUT_LOCKED except metadata (M01).

## 6. Story and scene evidence (what the packets contain)
- Review 1: 10 beats from 7434a0f7. Each has an AI-proposed interpretation with default and an UNKNOWN option. The packet says the proposals are not verified.
- Review 2: 6 spans (10 records) from 7a1e2b26, with tool output kept separate.
- Human labels collected: 0. The packets ask the reviewer to approve or correct, not to create labels from nothing.

## 7. Incomplete items at this moment (reported, not declared passed)
1. Frozen annotation structural file: test-review-open (quality findings). Its gaps are covered by the additive file.
2. None from the additive test (done). The frozen structural file remains test-review-open; its four gaps are covered by the additive file, not by editing the frozen file.
3. Human review itself: not done (the owner's sitting).

## 8. Boundaries kept
- Step 5 deferred and exposed.
- Held-out beats not inspected by this phase.
- Step 4 frozen detector unchanged.
- Historical evidence and builds 001-005 unchanged.
- No global D4 label replacement.
- No F4 change; no GranthStudio production change; no Kimi call; no build_006.

## 9. Owner correction: 16-department coverage is not complete (applied 2026-10-31)
- The 20-record pilot is NOT comprehensive validation of the 16 departments.
- Department coverage ledger (full paths): work/phase1/coverage_16/DEPARTMENT_VIDEO_LEDGER_16x13.csv (208 rows); work/phase1/coverage_16/DEPARTMENT_SUMMARY_16.csv; work/phase1/coverage_16/COVERAGE_16_REPORT.md.
- Counts over the 10 non-protected videos (160 cells): NEVER_EXAMINED 88; MODEL_ONLY 47; PARTIAL_MEASUREMENT 1; HUMAN_VERIFIED_PARTIAL 3 (specific owner-reviewed items only); UNKNOWN 21. Held-out: 48 cells, HELDOUT_PROTECTED, not read.
- Departments 1, 2, 3, 4, 6, 12, 14, 15 are NEVER_EXAMINED in every non-protected video.

## 10. Parallel loop results (2026-10-31, 15:35-15:47)
| Job | Scope | Result |
|---|---|---|
| p6_ledger_invariants | 16x13 ledger structure | PASSED (exit 0) |
| p6_heldout_guard | held-out ids absent from bundle and pilot | PASSED (exit 0), 3 READY |
| p6_review_bundle | approval-sheet structure, headings, no pre-ticked boxes | PASSED (exit 0) |
| p6_d4_table | D4 summary and table wording | OPEN: test-review-open. Valid finding (codex): a bare "NO" check passes without the AI-audit gate default being NOT APPROVED. Ultra HIGH findings about the 7434a0f7 filename are not valid (the filename is correct). Frozen test findings block acceptance, so the job remains open. |

## 11. Status of this readiness report
- Human review: not done. Decisions are pending the single sitting.
- The D4 structural test remains open; the D4 proposal itself is unchanged and ON HOLD.

## 12. Pre-human-review status (2026-10-31, final pass; supersedes section 7 for status)
Labels: CLOSED = checked and resolved, with the evidence named. OPEN = not resolved; the affected row is named. DEFERRED = held by owner decision. HUMAN_REQUIRED = needs the owner's sitting; nothing here is approved.

| Item | Status | Basis |
|---|---|---|
| Engine full suite (pieces/) | CLOSED | 1819 passed, 26 subtests, 0 failed (run in the final pass). Earlier record 1745 passed (work/phase1/roadmap_audit_tests_2026-10-31.txt). |
| Targeted packet, ledger, detector, annotation tests (10 files, 92 tests) | CLOSED | All passed in the final pass. |
| Ledger invariants, coverage invariants (12), held-out guard, review bundle structure | CLOSED | Each passed (loop jobs and the final pass). |
| Additive annotation source-reference test | CLOSED | Passed. |
| Frozen annotation structural test (pieces/test_annotation_protocol.py) | OPEN | Remains test-review-open; findings in _loop/p6_annotation_protocol/TEST_FINDINGS.md. It is not validation. |
| D4 structural test (pieces/test_d4_table.py) | OPEN | Codex's bare-NO finding is valid (line 63 checks only "NO" in the summary). Ultra's hard-coded-hash findings are not valid (the file names are correct). |
| D4 label change (overlay, staging, records) | DEFERRED | ON HOLD in work/phase1/roadmap_audit/DECISION_RECORD_2026-10-31.md. No change applied. |
| Step 4 freeze (five code-file hashes) | CLOSED | All five SHA-256 values in STEP4_FREEZE_MANIFEST.json match the current files. Verdict recorded as CONDITIONAL PASS. |
| Step 4 cut list vs packet (1.88 s, 3.04 s, 9.96 s; total count 33 / 36 / 75) | OPEN | See the discrepancy log in HUMAN_REVIEW_2_VISUAL_STORY.md (D-1 to D-4). |
| Freeze manifest wording "Step 5 has not been run" | OPEN | Manifest is frozen and is not edited. Detector predictions on the 24 windows were printed (exposure record item 4). Clarify in a later record. |
| Zero-length beats 7434a0f7 shot_001 and shot_004 | CLOSED | Confirmed in source (start = end; frames 0-0 and 270-270). Flagged; excluded from duration scoring; source kept. |
| Overlapping records (7434a0f7 and 7a1e2b26) | CLOSED | Match source. Read as one span with two records. |
| Packet wording, Review 1 | CLOSED | Checked against source; six wording corrections logged in the packet. |
| Packet wording, Review 2 | CLOSED for wording; OPEN for cut rows | Timings verified. Cut rows OPEN (D-1 to D-4). |
| Packet wording, Review 3 and D1-D9 | CLOSED for wording | Compared with OWNER_DECISIONS_REQUIRED.md and DECISION_RECORD_2026-10-31.md. Decisions themselves: HUMAN_REQUIRED. |
| Held-out exposure disclosure | CLOSED | Explicit statement added: all 24 frozen predictions were printed before any human label existed. Step 5 DEFERRED. |
| Held-out ids in human-review packets | CLOSED | None found (text search of the bundle). |
| Historical reference correction index | CLOSED for the index; the references are OPEN | work/phase1/roadmap_audit/HISTORICAL_REFERENCE_CORRECTION_INDEX.md lists 74 unresolved references (23 with no file of that name, 41 unique name matches, 10 ambiguous). No historical document was edited. |
| 16-department coverage | OPEN | Not complete. The pilot covers 2 of 13 videos and 2 of 16 departments in a limited way. See work/phase1/coverage_16/COVERAGE_16_REPORT.md. |
| Annotation protocol v1 acceptance | HUMAN_REQUIRED | Default changed to DEFER. |
| Pilot acceptance as draft evidence | HUMAN_REQUIRED | Default YES in the sheet, with zero-length warnings. Owner decides. |
| All approvals, corrections, labels, signatures (Reviews 1-3, A1-A5, B1, D1-D9) | HUMAN_REQUIRED | Every field is blank. No approval has been entered by the agent. |
| Step 5 labels and scoring | DEFERRED | Exposed; not passed, not failed. |
| F4 policy, Kimi integration, build_006, GranthStudio production changes | DEFERRED | On HOLD per the owner's decision record. Not changed. |
