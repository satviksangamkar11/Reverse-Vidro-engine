# Reference-video research system: master checklist (single source of truth)
Updated 2026-10-29. Status words: DONE = code-verified; BUILT = exists but not final; OPEN = not done. Reviewer opinions never count as DONE.
Rules: Ultra is the only coder; no Kimi calls; GranthStudio untouched; F1-F4 SPEC TEXT frozen (their code is still being built); no new subsystems; links only recorded until the owner says run.

## A. Foundation (status DONE: 12 pre-existing tests pass; frame/review counts come from RUN_PLAN.json and the earlier session, not re-run today)
- [x] 9 unique videos from 10 MP4s, 1,596 sampled frames, storyboard + motion selection, 18 pilot reviews, NVIDIA scheduler, importer dry run
- [x] 30 Instagram reel links recorded (not downloaded); local reference set = 9 unique MP4s (separate from the links)

## B. The 20 pieces (each: own tests green, 4 Ultra lenses no HIGH/MED, test edits reviewed)
- [ ] A1 link queue/status  - [ ] A2 collect + zip safety  - [ ] A3 CLI
- [ ] B1 audio/DSP  - [ ] B2 transcribe/statuses  - [ ] B3 align/orchestrate
- [ ] C1 clustering  - [ ] C2 review plan  - [ ] C3 record/coverage
- [ ] D1 beat schema (NOT_EXAMINED, evidence rules, 16 department findings)  - [ ] D2 recipes (sequence pattern, when-not-to-use, registered presets only)  - [ ] D3 deliverables + playbook guard  - [ ] D4 reconstruction (structural_ok, semantic NOT_VERIFIED)
- [ ] E1/E2/E3 offline comparison harness (dry-run only, no Kimi)
- [ ] F1 ledger  - [ ] F2 evidence counts  - [ ] F3 lock + snapshot publish  - [ ] F4 classification + Stage1/2 views

## B2. Dependency table (used for step D.4 'retest only dependents')
A1,A2 -> A3 | B1 -> B2,B3 | C1 -> C2 -> C3 | D1 -> D2,D4 | D2 -> D3 | F1 -> F3,F4 | F2 -> F4 | D2+F4 feed Stage1/2 views | E1 -> E2 -> E3. A piece with no arrow is independent. (Interfaces between pieces are plain dict shapes written in each spec.)

## C. Loop safety
- [x] bounded repair: 3 per failure signature, one recorded test-edit pass, then NEEDS_REVIEW; coding crash stops piece; missing required dependency = BLOCKED
- [x] reviewer deadline 240 s; empty/timeout/server error = NO_REVIEW (never PASS/FAIL); quorum of 2 valid answers
- [ ] every recorded test-edit diff reviewed against its spec bullet (owner decides disputes)

## D. Execution order
1. [ ] finish pieces under bounded repair
2. [ ] review all test modifications
3. [ ] early SMOKE test: one local video, unfinished stages mocked, labelled SMOKE (not integration)
4. [ ] retest only affected pieces + dependents (dependency table)
5. [ ] full local-video integration (all 20 real)
6. [ ] 1-2 accessible reels incl. audio (download only after owner says run)
7. [ ] Stage 1/2 compatibility check (before the audit)
8. [ ] semantic audit of ONE audio reference (owner picks or signs off): story structure, shot planning, editing/continuity/pacing, animation (character/camera/effects), sound (narration/SFX/silence/sync), Kimi lessons without invented facts; every finding traceable to the video; critical finding = pipeline FAIL, repair and re-audit
9. [ ] final report: unit tests, integration tests, manually verified findings, reviewer opinions, blockers (separate)

## E. Requirements carried (owner)
- [ ] cumulative report over all videos/links, rebuilt from the ledger, queued links never counted as researched
- [ ] no bias by video type: honest counts, creators known vs UNKNOWN, GENERAL/STYLE_SPECIFIC/EXPERIMENTAL, research confidence separate from executability
- [ ] full cinematic grammar (16 departments as free-text findings, 4 levels with relationships, evidence per finding, no invented software/lens/rig/screenplay, no fabricated audio for frame-only ZIPs)
- [ ] Kimi gets no new permissions (EASY, events, timings, ids, code, music); Stage 2 never gets an invented preset
- [ ] claims kept apart: RESEARCH PIPELINE PASS vs KIMI IMPROVEMENT PROVEN (needs later owner-approved comparison)

<!-- SNAPSHOT_START -->
## Status snapshot 17:01 (code-verified: each piece's own pytest run; job state from fix_loop status.json)
```
17:00 piece | job state (rounds) | own tests
wpA1 | passed-no-review (1) | OK 13 passed in 0.13s
wpA2 | passed-no-review (1) | OK 18 passed in 0.80s
wpA3 | passed-no-review (4) | OK 16 passed in 0.13s
wpB1 | running (1) | FAIL 1 failed, 30 passed in 0.29s
wpB2 | passed-no-review (1) | OK 9 passed in 0.02s
wpB3 | passed-no-review (1) | OK 26 passed in 0.12s
wpC1 | passed-no-review (2) | OK 17 passed in 0.03s
wpC2 | passed-no-review (1) | OK 16 passed in 0.03s
wpC3 | passed-no-review (1) | OK 23 passed in 0.03s
wpD1 | passed-no-review (1) | OK 82 passed in 0.08s
wpD2 | no-status (0) | OK 37 passed in 0.04s
wpD3 | passed-no-review (1) | OK 41 passed in 0.12s
wpD4 | escalate (4) | OK 23 passed in 0.03s  <ESCALATE.md>
wpE1 | passed-no-review (1) | OK 11 passed in 0.04s
wpE2 | passed-no-review (1) | OK 22 passed in 0.03s
wpE3 | passed-no-review (1) | OK 48 passed in 0.05s
wpF1 | passed-no-review (1) | OK 43 passed in 0.16s
wpF2 | passed-no-review (2) | OK 22 passed in 0.03s
wpF3 | passed-no-review (2) | OK 32 passed in 0.62s
wpF4 | passed-no-review (3) | OK 34 passed in 0.03s
tests green: 19/20
```
Code-verified extra: G1 (autonomous-cycle decision logic) passed its own tests; fix_loop retry patch and G2 still building; D4 escalated again.
Reviewer opinions (NOT code-verified): round 3 (Luna medium + Haiku-low stand-in; GLM and MiniMax return NO_REVIEW): A1, B2, C3, D2 had no HIGH/MED from both; the other pieces got findings that Nemotron then applied; round 4 reviews are starting now. No piece is proven DONE until its latest fixes pass Luna and Haiku with no HIGH/MED.
<!-- SNAPSHOT_END -->
