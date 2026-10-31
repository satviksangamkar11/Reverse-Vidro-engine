# Pre-human-review handoff (2026-10-31)

Status: the automated preparation is finished and verified where stated below. The owner's human review sitting has NOT happened. No human approval, correction, label or signature has been entered by the agent. Every approval and signature field in the bundle is blank.

## 1. Review packets (locations)
- Approval sheet (one sitting, three reviews): [ONE_ROUND_APPROVAL_SHEET.md](ONE_ROUND_APPROVAL_SHEET.md)
- Review 1, story and scene, video 7434a0f7, first 10 beats: [HUMAN_REVIEW_1_STORY_SCENE.md](HUMAN_REVIEW_1_STORY_SCENE.md) (evidence sheet: [sheet_7434a0f7_first10.jpg](sheet_7434a0f7_first10.jpg))
- Review 2, clay video 7a1e2b26, 6 spans / 10 records: [HUMAN_REVIEW_2_VISUAL_STORY.md](HUMAN_REVIEW_2_VISUAL_STORY.md) (evidence sheet: [sheet_7a1e2b26_first10.jpg](sheet_7a1e2b26_first10.jpg))
- Review 3, owner decisions A1-A5, B1, protocol, pilot, D1-D9: [HUMAN_REVIEW_3_OWNER_DECISIONS.md](HUMAN_REVIEW_3_OWNER_DECISIONS.md)
- Supporting: [AUTOMATED_READINESS_REPORT.md](AUTOMATED_READINESS_REPORT.md) (section 12 has the status table), [DECISION_RECORD_TEMPLATE.md](DECISION_RECORD_TEMPLATE.md)

Pilot scope: 2 of 13 development videos, 20 records (10 per review). This is NOT comprehensive validation of the 16 departments. See work/phase1/coverage_16/COVERAGE_16_REPORT.md.

## 2. What was checked (and the result)

| # | Check | Result |
|---|---|---|
| 1 | Approval sheet: protocol default changed YES to DEFER | DONE. Also changed the same default in Review 3. |
| 2 | Approval sheet: states frozen structural test test-review-open, additive regression passed, neither is human validation | DONE |
| 3 | Approval sheet: pilot scope (2 of 13 videos, 20 records, not 16-department validation, no human labels) | DONE |
| 4 | Approval and signature fields blank; no ticked boxes in the bundle | PASS (0 ticked boxes across the bundle) |
| 5 | Five flagged filenames: resolved | PASS for the files (all exist at the paths below). The regex scan had flagged basenames that were tails of full paths. Section 9 of the readiness report now gives full paths. |
| 6 | Every path referenced in the three packets and the approval sheet exists | PASS (19 distinct paths, all exist; both evidence sheets exist in the bundle folder) |
| 7 | Zero-length beats 7434a0f7 shot_001 (0.0-0.0, frames 0-0) and shot_004 (9.0-9.0, frames 270-270) against source beats_7434a0f7.json | PASS. Both zero length in the source. Flagged; excluded from duration scoring; source kept. |
| 8 | Review 1: all 10 timings against source | PASS |
| 9 | Review 1: observable-action wording against source | FOUND 5 wording defects (plus the summary count in row 15); CORRECTED in the packet (log at the end of the packet). Source unchanged. |
| 10 | Review 2: all 10 records and 6 spans, timings and frame numbers against source beats_7a1e2b26.json | PASS for timings and grouping |
| 11 | Review 2: observable wording against source | FOUND 2 defects (subtitle at 2.0-3.0 said to change; overlap line garbled); CORRECTED. Source unchanged. |
| 12 | Review 2: detector cut times against STEP4_MEASUREMENTS.json | FAIL for 1.88 s, 3.04 s and 9.96 s (not hard_cut events in any detector output file). 4.29, 5.88, 7.62 s PASS. OPEN (D-1 to D-3). |
| 13 | Review 2: total cut count | FAIL / OPEN: 36 (owner file), 33 (STEP4_MEASUREMENTS.json and STEP4_RESULTS.json), 75 (cut_events_7a1e2b26.json). No count used in the packet. OPEN (D-4). |
| 14 | Review 2 packet claim "owner confirmed the clay cut identification in general" | FAIL. The owner file confirms only the 9.96 s cut. Corrected in the packet. |
| 15 | Review 1 story-function summary count | FAIL: 7 of 10 stated; the packet's own proposals give 6 of 10. Corrected. |
| 16 | Review 3 D1-D9 wording against OWNER_DECISIONS_REQUIRED.md and DECISION_RECORD_2026-10-31.md | PASS, with 2 wording corrections: B1 had two defaults (now one); D2 YES wording now matches owner option b. |
| 17 | D4: OPEN with Codex's bare-NO finding | PASS (kept OPEN). D4 structural test test-review-open. No label change applied. |
| 18 | Step 4 freeze: five code-file SHA-256 hashes vs STEP4_FREEZE_MANIFEST.json | PASS (all five match) |
| 19 | Step 4 freeze: two-run reproducibility (manifest) | Recorded as identical (manifest); not re-run in this pass |
| 20 | Step 4 manifest says "Step 5 has not been run" | OPEN. Detector predictions for the 24 windows were printed (exposure record item 4). Manifest is frozen; not edited. |
| 21 | Held-out exposure disclosure states all 24 frozen predictions were printed before any human label | DONE (explicit statement added to HELDOUT_EXPOSURE_RECORD.md) |
| 22 | Held-out ids in human-review packets and the pilot label form | PASS (no held-out video ids in the bundle; text search, and pieces/test_heldout_guard.py passed) |
| 23 | Historical reference correction index | DONE: work/phase1/roadmap_audit/HISTORICAL_REFERENCE_CORRECTION_INDEX.md. 74 unresolved references in 7 documents (23 with no file of that name, 41 unique name matches, 10 ambiguous). Original documents not edited. docs/PHASE1_PLAN_AND_CHECKLIST.md: pieces/p1_chain.py and docs/pilot/REVIEW_PROMPT_STAGE1_FINAL.md both have no file of that name in the repository. |
| 24 | Readiness statuses CLOSED / OPEN / DEFERRED / HUMAN_REQUIRED | DONE (readiness report section 12) |

## 3. Tests (verified)
- Full engine suite (pieces/), run in this pass: 1819 passed, 26 subtests passed, 0 failed.
- Earlier record: work/phase1/roadmap_audit_tests_2026-10-31.txt, 1745 passed, 0 failed (14:58). Step 4 manifest records 1711 passed (05:33 log work/phase1/step4/FULL_SUITE_FINAL_2026-10-31.txt). The later counts are higher because tests were added after those runs.
- Targeted tests run in this pass: 92 passed (annotation source refs, annotation protocol, review bundle, held-out guard, department ledger, coverage invariants, measure-track and side-zoom detector tests, p6 stage-1 measured additive test).
- D4 and staging tests run in this pass: 54 passed (test_d4_table, test_p6_stage1_staging (frozen), test_d4_relationships, test_d4_reconstruct).
- Not re-run in this pass: Loop System repo tests (manifest: 189 pass; 3 guard tests fail on the baseline, recorded as D7).

## 4. Files modified in this pass
- work/phase1/human_review_bundle/ONE_ROUND_APPROVAL_SHEET.md (pilot scope block; protocol default DEFER; protocol status note; cut-time default wording)
- work/phase1/human_review_bundle/HUMAN_REVIEW_1_STORY_SCENE.md (six wording corrections; summary count; correction log)
- work/phase1/human_review_bundle/HUMAN_REVIEW_2_VISUAL_STORY.md (cut-status wording; overlap wording; subtitle wording; discrepancy log D-1 to D-5)
- work/phase1/human_review_bundle/HUMAN_REVIEW_3_OWNER_DECISIONS.md (protocol default DEFER; B1 single default; D2 wording; check log)
- work/phase1/human_review_bundle/AUTOMATED_READINESS_REPORT.md (full paths in section 9; new section 12 status table)
- work/phase1/roadmap_audit/HELDOUT_EXPOSURE_RECORD.md (explicit statement added; existing items unchanged)

## 5. Files created in this pass
- work/phase1/human_review_bundle/PRE_HUMAN_REVIEW_HANDOFF.md (this file)
- work/phase1/roadmap_audit/HISTORICAL_REFERENCE_CORRECTION_INDEX.md

Not modified: source beat files, overlays, staging file, STEP4 measurements, the Step 4 frozen detector and its manifest, frozen test files (pieces/test_p6_stage1_staging.py, pieces/test_annotation_protocol.py, pieces/test_d4_table.py), D4 proposal tables, F4 policy, the held-out lock and records, GranthStudio, build_006.

## 6. Remaining defects (OPEN)
1. D-1: cut at 1.88 s is not a hard_cut event in STEP4_MEASUREMENTS.json or STEP4_RESULTS.json. Affects Review 2 boundary between spans 1 and 2, and the shot_002/event_002 editing field.
2. D-2: cut at 3.04 s, same status. Affects Review 2 shot_002/event_002 and shot_003 editing fields.
3. D-3: cut at 9.96 s is owner-confirmed, but not a hard_cut event in the detector output files (nearest UNCLASSIFIED_SPIKE at 9.88 s). Affects the Review 2 shot_006 "after" field.
4. D-4: total cut count is 36 / 33 / 75 across three files. No count is used in the packet.
5. Frozen annotation structural test: test-review-open (its four findings are in _loop/p6_annotation_protocol/TEST_FINDINGS.md). The additive regression covers the same points.
6. D4 structural test: test-review-open. Codex's bare-NO finding is valid. Ultra's hard-coded-hash findings are not valid.
7. Step 4 manifest wording "Step 5 has not been run" conflicts with the exposure record. Manifest is frozen; not edited.
8. 74 historical references do not resolve (see the index). None were changed.
9. The frame sheets (sheet_7434a0f7_first10.jpg, sheet_7a1e2b26_first10.jpg) were not inspected visually in this pass. The printed frame times are unverified.
10. Source information not in Review 1: event_003 and shot_003 are recorded as dip_to_dark (confirmed) in the beat file. The packet does not mention this.
11. 16-department coverage: not complete. Departments 1-4, 6, 12, 14 and 15 are NEVER_EXAMINED in every non-held-out video.
12. Step 5: DEFERRED and EXPOSED. Not passed, not failed.

## 7. Unresolved owner decisions (HUMAN_REQUIRED; nothing approved)
- Review 1: APPROVE / CORRECT / UNKNOWN for each of the 10 beats.
- Review 2: APPROVE / CORRECT / UNKNOWN for each of the 6 spans (the cut rows D-1 to D-3 need a decision too).
- Review 3: A1 measured dips (default DEFER); A2/A3 AI-audit records (default DEFER); A4 withdrawn arm snaps (default YES, inactive); A5 27.6 s record (default YES, superseded); B1 AI-audit gate policy (default NO; DEFER has the same effect); C-D8 L3 end fade (default YES); annotation protocol v1 (default DEFER); 20-beat pilot as draft evidence (default YES with zero-length warnings); D1-D7 (default DEFER); D9 Step 5 (default DEFER).
- Closed regardless of answers: F4 change, Kimi integration and delivery, build_006, GranthStudio production changes, global D4 label replacement.

## 8. Explicit statement
No human approval, correction, label, signature or decision has been entered by the agent. The approval sheet's approval, correction and signature fields are blank. Where a default exists, it is a proposal for the owner, not an approval. Blank answers are DEFERRED or UNKNOWN.
