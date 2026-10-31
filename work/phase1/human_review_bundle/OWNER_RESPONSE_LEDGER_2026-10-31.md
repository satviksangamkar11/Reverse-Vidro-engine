# Owner response ledger (2026-10-31)

Purpose: one place that maps each recorded owner answer to its review item, its source file, and its status. Written by the supervisor from recorded files. No answer is invented. A blank is UNKNOWN or DEFERRED.

## Provenance

- The owner's own messages are not in this session's transcript. The only copies are the files listed below. Each file was written from the owner's message at the time (R1 and R2 say so in their headers).
- R1 mapping (beat to answer) is the supervisor's mapping, marked "to confirm" in `OWNER_REVIEW_RESPONSES_R1.md`.
- R2 answers were recorded as approved on the owner's statement "i have cross checked apptoved", which approves the pasted analysis `clips/PASTED_ANALYSIS_2026-10-31_UNCONFIRMED.md`. The per-item S01 to S06 mapping is the supervisor's. The owner has not entered each item on a sheet.
- Later pasted analysis (2026-10-31, camera measurement): agrees with the owner's zoom-in answers for B03, B04 and B06, and with the B08 to B10 answers already recorded. It withdraws its own earlier "no push-in before about 11 s" claim. Its method is described in words only; no commands or output are in the paste. Owner confirmed this paste on 2026-10-31 ("i confirm the pasted things"). The confirmation covers its camera reading and its B03, B04, B06, B08, B09 and B10 answers. It does not approve any policy item. The supervisor's rough motion check on the source video (not a full measurement) is consistent with B03 and B04 and does not contradict them.
- Status key: RECORDED = owner words in a file. RECORDED-BY-STATEMENT = approved as a block by statement. DEFERRED = no answer. OPEN = conflicting answers, not resolved.

## Review 1: story and scene, 7434a0f7 (sheet `ONE_ROUND_APPROVAL_SHEET.md`)

Source: `clips/OWNER_REVIEW_RESPONSES_R1.md`. Clip index: `clips/REVIEW_CLIP_INDEX.md`.

| Beat | Records | Owner answer (recorded) | Status |
|---|---|---|---|
| B01 | shot_001, frame 0 (zero length) | "complete black screen": APPROVE the observable black frame | RECORDED for observable. Story fields UNKNOWN (not asked) |
| B02 | shot_002 0.5 to 4.5 s | "approve": APPROVE | RECORDED. Story fields not asked, DEFERRED |
| B03 | event_001 1.0 to 2.5 s | "zoom in"; later update: zoom in, no pan | RECORDED. Zoom in, no pan. Owner-confirmed via the later paste (2026-10-31). Earlier "no push-in before 11 s" claim withdrawn |
| B04 | event_002 3.0 to 4.5 s | zoom in, no pan; woman's hand first, then man's | RECORDED. Same as B03. Owner-confirmed via the later paste (2026-10-31) |
| B05 | event_003 5.0 to 6.5 s | "after 1000 years with the guru, Kacha was back"; sage's hand first, then standing character | RECORDED. Transcription ("gure", "kutch", "maharaj") to confirm |
| B06 | shot_003 5.0 to 8.5 s | story as B05; zoom in; Kacha walks right; no camera pan. Earlier "camera moves to right" withdrawn | RECORDED. No pan; Kacha walks right. Owner-confirmed via the later paste (2026-10-31). Earlier "only distance changes" claim withdrawn |
| B07 | event_004 7.0 to 8.5 s | "same as above" = B06 | RECORDED (same as B06) |
| B08 | shot_004, frame 270 (zero length) | wide/full shot, in a fade. Story and scene UNKNOWN; reveal UNKNOWN | RECORDED |
| B09 | event_005 9.5 to 11.0 s | Devayani walks in, arm already out; reveal YES; escalation acceptable | RECORDED |
| B10 | shot_005 9.5 to 12.5 s | red mark already at 9.0 s; zooms to medium from about 11.7 s; reveal YES; escalation accepted | RECORDED |

Review 1 summary: B03 to B10 owner-confirmed via the later paste (2026-10-31); B08 to B10 answers match the earlier R1 update. B01 story fields are NOT answered. No other story fields are DEFERRED beyond those marked above.

## Review 2: clay video 7a1e2b26 (S01 to S06)

Source: `clips/OWNER_REVIEW_RESPONSES_R2.md`, approved by the owner statement above.

| Item | Span | Recorded decision | Status |
|---|---|---|---|
| S01 | 0.0 to 1.5 s | CORRECT: extreme close-up of drill bit; shot ends 1.88 s | RECORDED-BY-STATEMENT |
| S02 | 2.0 to 3.0 s | APPROVE: cuts at 1.88 and 3.04 s are real | RECORDED-BY-STATEMENT |
| S03 | 3.5 to 4.0 s | CORRECT: first wide shot; boy's mouth closed | RECORDED-BY-STATEMENT |
| S04 | 4.5 to 5.5 s | CORRECT: bit turning and going deeper | RECORDED-BY-STATEMENT |
| S05 | 6.0 to 7.5 s | APPROVE: close-up of bearded man, calm focus | RECORDED-BY-STATEMENT |
| S06 | 8.0 to 9.5 s | APPROVE: next cut at 9.96 s is real | RECORDED-BY-STATEMENT |

Cut answers from Review 2: 9.96 s confirmed by owner (round 2, question 6). 1.88 and 3.04 s real on the cross-check. The 36-cut total for 7a1e2b26 is owner-approved on the same statement. The repo cannot reproduce 36 (see `departments_16/CUT_COUNT_RECONCILIATION.md`).

## Owner visual read, round 2 and round 3 (7434a0f7 and 7a1e2b26)

Source: `step4/OWNER_VISUAL_READ_ROUND2_2026-10-31.md`, `step4/OWNER_VISUAL_READ_7434a0f7.json`.

- A1 to A13 window readings are recorded in the JSON. A12 and A13 ("no arm movement" at 0.6 to 1.1 s and 6.7 to 6.9 s) are the factual basis for the withdrawn arm snaps (D4 row A4). Recorded as owner readings. The sheet disposition of A4 is DEFERRED.
- **OPEN:** 47.5 to 53.0 s. Round 2 says "zoom out" (retained). Round 3 says "sliding down". Not adopted. Both are kept as recorded.
- **OPEN:** 7434a0f7 dark moments and cut meaning. See `departments_16/CUT_COUNT_RECONCILIATION.md`, section "7434a0f7".
- 7a1e2b26: 9.96 s hard cut HUMAN-VERIFIED (owner statement). 36 hard cuts: owner-approved total, not verified cut by cut. Kept separate from the frozen detector's 33 hard_cut events (STEP4_MEASUREMENTS.json); the 33 is not replaced by the 36. No moving-camera segment besides cuts (owner round 3).
- 7434a0f7 47.5 to 53.0 s: detector motion classification UNKNOWN (MIXED_MOTION_SIDE_ZOOM), unchanged by the owner readings.

## Review 3: owner decisions

Source: `HUMAN_REVIEW_3_OWNER_DECISIONS.md` and `ONE_ROUND_APPROVAL_SHEET.md`. **No checkbox, default or signature was entered on either sheet.** Owner decisions come from `roadmap_audit/DECISION_RECORD_2026-10-31.md` (two tables, owner-dated 2026-10-31).

| Item | Recorded owner answer | Status |
|---|---|---|
| A1 measured dips to MEASURED | none on sheet | DEFERRED |
| A2/A3 AI-audit records | none on sheet | DEFERRED |
| A4 withdrawn arm snaps inactive | A12/A13 readings recorded (above) | DEFERRED for disposition |
| A5 27.6 s superseded | owner reading "transition, not through black" (round 2) | DEFERRED for disposition |
| B1 AI-audit as gate evidence | D1 to D9 "NOT APPROVED" (decision record) | NOT APPROVED (default NO) |
| C-D8 L3 end fade to note | not on sheet; D1 to D9 NOT APPROVED | DEFERRED |
| Annotation protocol v1 accepted | "GO" on labelling instructions and evidence sheets; protocol acceptance not stated | DEFERRED. Owner to confirm whether the GO covers this |
| 20-beat pilot accepted as draft | not on sheet | DEFERRED |
| D1, D2, D3, D5, D6, D7 | "NOT APPROVED" (decision record) | NOT APPROVED |
| D9 Step 5 labels; new held-out set | Step 5 DEFERRED and exposed; new set "recommended, not created" | DEFERRED; not created |
| F4, Kimi, build_006, GranthStudio, D4 | HOLD / NOT AUTHORIZED / closed | CLOSED |

## Decisions from the decision record (owner, 2026-10-31)

- ACCEPTED: roadmap and 18-module coverage audit; coverage invariants (12 tests); engine suite as reported; Codex documentation corrections; held-out exposure record; D4 correction note.
- DEFERRED: Groq proposals needing new implementations; Step 5.
- HOLD: D4 label change; historical label rewrite; F4 change; Kimi integration; build_006 publication.
- GO: human-labelling instructions and evidence sheets (`story_annotation/ANNOTATION_PROTOCOL.md`, `pilot/`). Pilot labelling on non-held-out videos waits for human labellers.
- PROHIBITED for the agent: held-out inspection.
- NOT CREATED: new independent held-out set (recommended only).

## Not answered (keep as UNKNOWN or DEFERRED)

- B01 story fields (story function, scene purpose, shot type, reveal): not asked.
- Story fields for B02 to B07 other than those given above: not asked, DEFERRED.
- Review 3 sheet, as a whole: no entries.
- Policy decisions D1 to D9: not approved.

## Do not ask again (answered)

B02 to B10 observable answers; S01 to S06; 9.96 s cut; 36-cut total for 7a1e2b26 (owner-approved on the statement); the decision-record table entries above.

## Still open (owner's word needed; do not infer)

1. Closed 2026-10-31: the owner confirmed the later paste, covering B03, B04, B06, B08, B09 and B10. The earlier "no push-in" claims are withdrawn.
2. 7434a0f7 4.93 s and 12.9 s: "real cut" (approved analysis) vs "lighting effect" / "blackout" (round 2).
3. 7434a0f7 47.5 to 53 s: "zoom out" (round 2, retained) vs "sliding down" (round 3).
4. B01 story fields.
5. Review 3 dispositions listed above.
