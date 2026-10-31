# Handoff — Loop System and D16 department research (2026-10-31)

Use this to resume in another session. Everything below was checked in this session unless marked otherwise.

## 1. Git state

Local commits on `main` (NOT pushed; the owner must decide on a push):
- `12af42b` — Loop system: d16 bench (Haiku 5.5 coder; Ultra, Groq GPT-OSS 120B and Codex reviewers; Haiku tie-breaker); d16 task specs; loop files committed.
- `cb7d876` — incomplete reviewer replies (NONE, truncated, timeout, error) are not counted; a single valid review goes to the Haiku tie-breaker; a missing required reviewer still blocks; AGENT_RULES bullet added.
- `157498d` — judge READY no longer clears a production FIX FIRST (fix_loop.py, the judge block near line 1147); the matching test in test_judge_tiebreak.py now expects "not passed". 79 loop tests pass.

Not yet committed (committed by this handoff step, see section 9): the D16 modules and tests, the finding-lifecycle module and tests, the lifecycle spec, the D16 specs, the D16 outputs and reports, the human-review text files, and the checklist.

The engine repo also has about 140 unrelated changed paths from earlier parallel work. They are NOT ours and must not be committed as part of this work.

## 2. Loop System (scripts/source/fix_loop.py and related)

Standing rules (owner, 2026-10-30 to 2026-10-31):
- Coder: Haiku 5.5 at high effort, via the Claude CLI, three fixer slots. Reviewers: Ultra, Groq (GPT-OSS 120B), Codex. Tie-breaker: Haiku 5.5 with job `judge_rules`.
- Spec reviews for tasks given to loops: Codex only (`tools/codex_review.py`).
- A valid HIGH or MED finding that lets incorrect output pass BLOCKS. A judge READY alone does not override an unresolved valid finding (applied in 157498d).
- LOW findings may be accepted with a documented exception in `work/phase1/departments_16/LOOP_OWNER_EXCEPTIONS.md`.
- Reviewer disagreement is resolved against the spec and test evidence, not by counting READY votes.
- A skipped test (platform cannot run it) is UNVERIFIED, not passed.
- Retries are bounded. Stop and report instead of looping.
- Concurrency cap: four loops at once. A fifth was approved for media only, as a one-off exception (recorded).
- Archive each loop folder to `_loop/archive/<job>_<HHMM>` before any restart. Earlier restarts deleted escalation and review logs; those cannot be recovered.

Finding-lifecycle module (isolated, NOT wired into the live loop; HOLD by owner):
- `pieces/finding_lifecycle.py` with `pieces/test_finding_lifecycle.py` (14 tests pass). Stable finding IDs; append-only ledger; RESOLVED needs passing test evidence; DISMISSED of a HIGH or MED needs an "EVIDENCE:" text with a concrete test or file:line reference; blocking = OPEN HIGH or MED; judge READY cannot override; bounded attempts; frozen tests hashed as raw bytes (CRLF-only changes detected).
- Loop state: `passed` (all three reviewers READY).
- Spec: `specs/phase1_loop_lifecycle.md`.

Loop state note: any loop run started BEFORE commit 157498d used the old judge path. Its "passed" state is not trusted without a supervisor check (this applied to media's earlier runs and the teacher repair run).

## 3. D16 department research — status per job

All checks below were done by the supervisor (reading reviews, running tests, reading code), not by the loop state alone.

| Job | Loop state | Supervisor position | Tests | Output |
|---|---|---|---|---|
| Matrix | passed | ACCEPTED. Reviews READY from Ultra and Codex; Groq NONE recorded as "no review". Size limits met (module 8,999 of 9,000 characters). | 23 passed | `work/phase1/departments_16/DEPARTMENT_VIDEO_MATRIX.csv`: 208 rows, 208 unique (dept, video) pairs, 48 held-out rows marked protected |
| Teacher | passed (after a supervisor-checked repair) | ACCEPTED by supervisor check. Groq HIGH (hard-coded DEV list) dismissed: all 10 DEV beat files exist. Both LOW exceptions (lesson count; stray event keys) closed by the repair spec. | 24 passed | `CROSS_VIDEO_TEACHER_CANDIDATES.json`: 2,147 candidates, 7 lessons, departments 5, 8, 9, 11 only, 10 videos. Candidates are AI observations, NOT verified knowledge. |
| Granth | test-review-open (loop) | ACCEPTED under owner adjudication. Groq MED and Ultra HIGHs dismissed with evidence. Symlink test SKIPPED / UNVERIFIED. | 12 passed, 1 skipped | `PRODUCTION_EXECUTION_COMPATIBILITY.json`: 11 presets, 13 techniques (none executable), 7 lessons, 124 consumer hits. Read-only; GranthStudio not modified. |
| Media | review-open (loop; NOT re-run after the repair) | PASS by supervisor closure. Shared key-gap check `_record_gap` (beats checked first, then audio), used by colour, pacing and captions. Opus review PASS. | 29 focused media tests; full suite 1926 passed, 1 skipped, 0 failed | Six CSVs in `work/phase1/departments_16/media/`, byte-identical to the pre-repair snapshot (real data has no key gaps). Held-out ids absent. Held-out reference timestamps labelled PROTECTED_HELDOUT. Quarantined earlier outputs in `_quarantine_2026-10-31_media_heldout_labels/`. |
| Lifecycle | passed (module only) | Not wired. Set aside by owner. | 14 passed | — |

Media file hashes (SHA-256, first 16 characters) at the time of closure:
- `pieces/d16_media.py`: f23f85a7ebb39f3b
- `pieces/test_d16_media.py`: cc3dd960c717f8e2
- `pieces/test_d16_media_gaps.py`: e1508464d8ace7662cd2

Media key-gap rule (as implemented): a beats gap or an audio gap blocks colour, pacing and captions for that video. Audio row stays `analysed Y` when only beats are incomplete (spec AUDIO-ROW RULE). Old behaviour was asymmetric; the two asymmetric fixtures fail on the old module and pass on the new one (demonstrated, module restored and hash verified).

## 4. Phase E (department research artifacts)

All 11 exist under `work/phase1/departments_16/`: DEPARTMENT_MASTER_STATUS.md, DEPARTMENT_VIDEO_MATRIX.csv, STORY_NARRATIVE_DIRECTION.md, SHOT_COMPOSITION_EDITING.md, ANIMATION_PERFORMANCE_VFX.md, COLOUR_SOUND_GRAPHICS_PACING.md, PRODUCTION_EXECUTION_COMPATIBILITY.md, CROSS_VIDEO_TEACHER_CANDIDATES.json, UNVERIFIED_EVIDENCE_REGISTER.md, DEPARTMENT_TEST_REPORT.md, FINAL_PRE_HUMAN_READINESS.md. Also CUT_COUNT_RECONCILIATION.md and LOOP_OWNER_EXCEPTIONS.md.

Department status (from the matrix; statuses use the owner's vocabulary):
- NOT_EXAMINED: 1, 2, 3, 4, 6, 14, 15 (and 12 for observations; see below)
- PARTIAL_RESEARCH: 5, 7, 8, 9, 11, 13, 16
- UNKNOWN: 10
- No department is RESEARCH_COMPLETE_FROM_AVAILABLE_EVIDENCE.
- No department is human-verified as a whole. Only owner-reviewed specific items (dept 5 and 7 items for 7434a0f7 and 7a1e2b26).

Still to update: departments 12–15 should be updated from the REPAIRED media CSVs (colour measured for 6 dev videos, BLOCKED for 4; audio analysed for 10; pacing and caption rows). The current 12–15 text was written while media was still pending and must be checked against the CSVs before it is used.

Cut counts for clay video 7a1e2b26 (`CUT_COUNT_RECONCILIATION.md`):
- 33: traceable to the frozen, repaired detector (saved event list). Unchanged.
- 36: owner-approved on the owner's cross-check; the scene-detection tool and settings are NOT named in the repo. Limitation recorded.
- 75: superseded (pre-repair file; no producer in the repo).
- D-1 (1.88 s), D-2 (3.04 s), D-3 (9.96 s): closed as real cuts on the owner's cross-check.
- 7434a0f7 conflict (7 cut entries in `cut_events_7434a0f7.json` vs 0 hard_cut events in the repaired measurements): OPEN.

## 5. Human-review package

Folder: `work/phase1/human_review_bundle/clips/`
- 14 MP4 clips (Review 1: B02–B07, B09, B10; Review 2: S01–S06) and 2 flagged frame images (B01 frame 0, B08 frame 270).
- `REVIEW_CLIPS.zip` (19 entries, integrity checked), `REVIEW_CLIP_INDEX.md`, `REVIEW_CONTACT_SHEET.jpg`, `REVIEW_INSTRUCTIONS_EN_HI_MR.md` (English, Hindi, Marathi).
- Clip rule: evaluated interval plus up to 1 s context on each side; the evaluated start offset is recorded in the index; original audio kept; no overlays, predictions or labels.
- Scripts: the clip generator is in the session scratchpad (not in the repo). Its inputs and outputs are recorded in `_clip_results.json` in the clips folder.

Owner answers (recorded in the files, not signed):
- Review 1 (`OWNER_REVIEW_RESPONSES_R1.md`): B01 complete black screen; B02 approve; B03 zoom in; B04 zoom in with woman's hand first, then man's; B05 story "after 1000 years with the guru, Kacha was back", sage's hand first, then standing character; B06 same story, camera moves right; B07 same as B06. B08, B09, B10 NOT answered. B01 story fields NOT answered.
- Review 2 (`OWNER_REVIEW_RESPONSES_R2.md`), approved on the owner's cross-check: S01 CORRECT (extreme close-up of drill bit only, no hands; shot ends 1.88 s); S02 APPROVE; S03 CORRECT (first wide shot; man drilling; boy's mouth closed); S04 CORRECT (bit turning and going deeper); S05 APPROVE; S06 APPROVE.
- Pasted scene-level analysis (`PASTED_ANALYSIS_2026-10-31_UNCONFIRMED.md`, status OWNER-APPROVED): 13-scene story table for 7434a0f7; owner approved it on the cross-check.

OPEN conflict: owner's B03, B04 and B06 answers (zoom in; camera moves right) vs the approved analysis (no push-in before about 11 s; only distance changes). One answer per item is needed.

Transcription readings to confirm: "gure" = guru; "kutch" = Kacha; "maharaj" = the seated sage.

No signature has been entered anywhere.

## 6. Instagram links

- Single file: `animation_research_tool/instagram_links.txt`, now 65 links.
- Added this session: `DfIIfphRMzu` and `DfJGEbDIhaa`. Recorded only; NOT downloaded.
- Tutorial YouTube link (`https://youtu.be/BFwMRVwrKcA`) recorded in `work/phase1/departments_16/REFERENCE_SOURCES.md`, reference only.

## 7. Items that remain OPEN

1. Owner: B03 / B04 / B06 zoom and camera answers (see section 5).
2. Owner: B08, B09, B10 (Review 1) and B01 story fields.
3. Phase E: update departments 12–15 from the repaired media CSVs.
4. Cut count 7434a0f7 conflict (7 vs 0).
5. Media loop state is review-open; the supervisor PASS has not been re-run through the loop. Decide whether to re-run.
6. Lifecycle wiring into the live loop: HOLD (owner).
7. Push of the local loop commits: owner must decide. Not pushed.
8. Teacher candidates are AI observations and remain unverified. Granth symlink test is UNVERIFIED on Windows.
9. Clay original in `reference_videos/instagram/` is not mapped by the media module (colour BLOCKED "no reference file mapped"). A mapping gap, not a missing source.
10. Tutorial concept map: spec not written (owner asked to set it aside).
11. Engine repo has ~140 unrelated changed paths from earlier parallel work; not committed by this work.

## 8. Hard boundaries (still in force)

- Held-out videos 354a38a0, 37745d70, baf59433: never inspected (no frames, predictions, vision text, or audio/beats content). Only their ids in filenames, and the 48 matrix rows marked protected.
- Step 5: DEFERRED and EXPOSED.
- F4, D4, Step 4 detector, and historical snapshots: NOT changed.
- GranthStudio: NOT modified (read-only).
- No Kimi calls. No build_006. No new human approval round started automatically.
- Human review: the owner's review answers are recorded; the sheet is not signed.

## 9. How to resume

1. Read this file, then `work/phase1/departments_16/FINAL_PRE_HUMAN_READINESS.md` and `LOOP_OWNER_EXCEPTIONS.md`.
2. Check git: `git log --oneline -6` and `git status --short`. Only commit the D16 and loop files listed in this handoff.
3. Run tests: `python -m pytest -q pieces -p no:cacheprovider` (about 3 minutes). Expected: 1926 passed, 1 skipped, 0 failed, as of the media closure.
4. Regenerate media only if its code changes: `python pieces/d16_media.py`. Compare the six CSVs with the snapshot in `_loop/archive/media_keygap_2144/csv_before`.
5. Ask the owner before any push, loop wiring, or new human-review round.
