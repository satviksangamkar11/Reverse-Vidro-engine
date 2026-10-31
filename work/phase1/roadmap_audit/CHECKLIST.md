# Roadmap audit checklist (2026-10-31)

Each item has one status: DONE (file exists and was checked), LOOP (closed through the Haiku loop, with reviewer gate), OWNER (needs an owner decision), BLOCKED (cannot proceed without a stated dependency), DEFERRED (held by the owner, not failed).

## Owner-required deliverables (from the audit brief)
| # | Item | File | Status |
|---|---|---|---|
| 1 | Master plan audit | work/phase1/roadmap_audit/MASTER_PLAN_AUDIT.md | DONE |
| 2 | 18-module per-video coverage (234 rows) | work/phase1/roadmap_audit/18_MODULE_COVERAGE.csv | DONE (generator in scratchpad; invariants test: see item 19) |
| 3 | Module implementation map (16 departments to 18 dimensions) | work/phase1/roadmap_audit/MODULE_IMPLEMENTATION_MAP.md | DONE |
| 4 | Cross-video lesson inventory | work/phase1/roadmap_audit/CROSS_VIDEO_LESSON_INVENTORY.md | DONE |
| 5 | Story and scene direction gaps | work/phase1/roadmap_audit/STORY_AND_SCENE_DIRECTION_GAPS.md | DONE (written in this session) |
| 6 | F4 and delivery blockers | work/phase1/roadmap_audit/F4_AND_DELIVERY_BLOCKERS.md | DONE (written in this session) |
| 7 | Provenance and test audit | work/phase1/roadmap_audit/PROVENANCE_AND_TEST_AUDIT.md | DONE (written in this session) |
| 8 | Next execution plan | work/phase1/roadmap_audit/NEXT_EXECUTION_PLAN.md | DONE (written in this session) |
| 9 | Owner decisions required | work/phase1/roadmap_audit/OWNER_DECISIONS_REQUIRED.md | DONE (written in this session) |
| 10 | Checklist update (docs/REVERSE_VIDEO_CHECKLIST.md) | docs/REVERSE_VIDEO_CHECKLIST.md | DONE (section appended; history kept) |

## Audit tasks
| Task | Item | Status |
|---|---|---|
| 1 | Audit every historical plan and checklist, assign statuses, traceability matrix | DONE (MASTER_PLAN_AUDIT.md section 4) |
| 2 | Per-video 18-dimension record (provenance, IDs, verification, missing work) | DONE as CSV; per-cell detail limited to what the historical files contain |
| 3 | 13-video coverage (what was extracted, which dimensions have evidence, AI-only, verified, lessons, missing, recoverable without new model calls) | DONE (CSV and MODULE_IMPLEMENTATION_MAP.md summary) |
| 4 | Cross-video technique inventory | DONE (CROSS_VIDEO_LESSON_INVENTORY.md) |
| 5 | Seven blocked lessons: failure table and A/B/C/D separation | DONE (F4_AND_DELIVERY_BLOCKERS.md; from STEP7_F4_ROOT_CAUSE.md) |
| 6 | GranthStudio read-only: writer and director paths, presets, asset registry | DONE for director and presets (STEP7 reports); writer path traced (prompts.py inputs); asset registry: not found as a separate file |
| 7 | Engineering defects list | DONE (PROVENANCE_AND_TEST_AUDIT.md) |
| 8 | Independent reviewer on the audit | LOOP (see item 18) |

## Engineering items
| # | Item | Status |
|---|---|---|
| 11 | video_id on Step 6 added events | DONE: none missing (checked in STEP7_PROVENANCE_AUDIT.md) |
| 12 | Verification-level behaviour | DONE: no error found; a message wording issue noted |
| 13 | 27.6 s non-dark transition retained | DONE: retained as a note |
| 14 | Four measured dark dips and regression coverage | DONE: test_p6_stage1_measured.py (gate passed) |
| 15 | Test discovery and totals | DONE: 1745 passed, 0 failed (engine); Loop repo 189 passed, 3 pre-existing guard failures |
| 16 | Three baseline Loop guard failures | OWNER: pre-existing, they check files that exist only in the engine repo; a fix would change what the guard checks |
| 17 | Broken references in checklists | DONE: two found (docs/pilot/REVIEW_PROMPT_STAGE1_FINAL.md, pieces/p1_chain.py); not repaired, recorded |
| 18 | Coverage invariants regression test (CSV: 234 rows, 13 videos, 18 modules, held-out locked) | DONE via LOOP: job p6_coverage_invariants passed round 0; tests/test_coverage_invariants.py 12 passed, no skips; reviewers codex, groq, ultra all READY |
| 19 | Independent review of the audit documents (six owner questions) | DONE (read-only review, not a loop job: the loop reviews job code). Codex FIX FIRST: two findings, both fixed (GranthStudio evidence location and hashes added to STEP7_KIMI_CONSUMER_TRACE.md; stale status in NEXT_EXECUTION_PLAN.md). Groq FIX FIRST: asks for new implementations, out of scope, not applied. Ultra READY. Scratchpad: audit_review/ |
| 20 | Step 5 | DEFERRED, not passed, not failed |
| 21 | build_006, held-out inspection, Kimi calls, F4 change, GranthStudio change | NOT DONE (boundary) |

## Phase 2 (owner, 2026-10-31): story and scene evidence preparation
| # | Item | Status |
|---|---|---|
| P2-1 | Held-out exposure record | DONE (HELDOUT_EXPOSURE_RECORD.md); exposure disclosed; Step 5 must state it |
| P2-2 | D4 proposed change table (file by file, record by record) | DONE (D4_PROPOSED_CHANGE_TABLE.md); corrected earlier claims: no historical beat record contains DIRECT_OBSERVATION; gate OBSERVED_OK makes relabelling a policy change |
| P2-3 | D4 change | HOLD (not applied) |
| P2-4 | Story and scene annotation protocol v1 | DONE (story_annotation/ANNOTATION_PROTOCOL.md) |
| P2-5 | Pilot evidence sheets and blank label form (7434a0f7 and 7a1e2b26, first 10 beats each) | DONE (story_annotation/pilot/); zero-length beat shot_001 in 7434a0f7 flagged |
| P2-6 | Protocol structure test via loop (p6_annotation_protocol) | LOOP, in progress |
| P2-7 | Human labels for the pilot | WAITING FOR HUMAN LABELLERS |
| P2-8 | New independent held-out set | RECOMMENDED, owner decision, not created |
| P2-9 | Step 5 | DEFERRED, exposed; must disclose |


## D16 department research (updated 2026-10-31)
Ticked only where a file or test was checked in this pass. Human verification is not implied by any tick.

- [x] Matrix: 208-row 16x13 matrix generated and checked (work/phase1/departments_16/DEPARTMENT_VIDEO_MATRIX.csv)
- [x] Teacher candidates JSON generated from current code (2,147 candidates, AI_OBSERVATION_UNVERIFIED)
- [x] Teacher loop repair accepted by supervisor check (24 tests; Groq HIGH dismissed with evidence)
- [x] Granth compatibility JSON regenerated (11 presets, 13 techniques, 7 lessons, 124 consumer hits); accepted under adjudication (12 passed, 1 skipped UNVERIFIED)
- [x] Matrix loop passed (reviews READY from Ultra and Codex; Groq NONE recorded as no review; 23 tests)
- [x] Lifecycle module passed as an isolated module (14 tests; raw-byte freeze); NOT wired into the live loop
- [x] Judge-READY fix in scripts/source/fix_loop.py applied and committed locally (157498d); 79 loop tests pass; not pushed
- [x] Full suite spec-lint failure fixed (REAL FACTS heading added to phase1_loop_lifecycle.md); re-run needed for a final full-suite count
- [x] Phase E reports written: DEPARTMENT_MASTER_STATUS, STORY_NARRATIVE_DIRECTION, SHOT_COMPOSITION_EDITING, ANIMATION_PERFORMANCE_VFX, COLOUR_SOUND_GRAPHICS_PACING, PRODUCTION_EXECUTION_COMPATIBILITY, UNVERIFIED_EVIDENCE_REGISTER, DEPARTMENT_TEST_REPORT, FINAL_PRE_HUMAN_READINESS
- [ ] Media repair passes and is checked by supervisor (review-open; caption NameError; invalid UTF-8 gap handling; protected-row checks)
- [ ] Media colour, caption, pacing and audio summaries regenerated from the repaired module (quarantined outputs are NOT evidence)
- [ ] Phase E reports for departments 12 to 15 updated after media passes
- [ ] Owner decision on the cut-count conflict (33 / 36 / 75)
- [ ] Lifecycle wired into the live loop (set aside by owner; not started)
- [ ] Full engine suite re-run after the lifecycle spec fix
- [ ] Human review (not started; begins after the boxes above that gate it are ticked)
