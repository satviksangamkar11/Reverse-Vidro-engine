# HUMAN REVIEW 3 — Consolidated owner decision sheet (one round)

Nothing on this sheet is approved by default. Each item shows a RECOMMENDED DEFAULT (what I propose if you sign off quickly), and the consequences of YES, NO and DEFER. Teaching eligibility stays closed until a separate decision says otherwise.

Key distinction used below:
- MEASURED = a frozen detector measurement of brightness or frame difference, with the interval in work/phase1/step4/STEP4_MEASUREMENTS.json.
- AI AUDIT (AUDITOR_FRAME_INSPECTION) = a model's reading of frames. Not human, not measured.
- DIRECT OBSERVATION = the label used today. It implies an observer viewed the event. Today most of its 25 uses are NOT human views (see D4 below).
- WITHDRAWN = a claim the owner or the audit has retracted (for example arm snaps). Must stay inactive.

---

## PART A — D4 record-level changes (overlay work/phase1/overlays/lesson_candidates_7434a0f7.json, 25 DIRECT_OBSERVATION records)
Source table: work/phase1/roadmap_audit/D4_PROPOSED_CHANGE_TABLE.md (file and record level). Full evidence per row is there.

| Group | Records | Current | Proposed | Evidence | Affects teaching eligibility? |
|---|---|---|---|---|---|
| A1 measured dips | L3 shot_003, shot_004, shot_006, shot_007, shot_010, shot_013 | DIRECT_OBSERVATION | MEASURED | detector CONFIRMED dip_to_dark (4.93, 8.97, 12.9, 18.47, 29.93, 46.9 s) | YES if MEASURED is accepted by the gate (it already is); NO change in eligibility |
| A2 end fade (not a dip between scenes) | L3 shot_014; L7 shot_014 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | frames under the title | YES: the gate would BLOCK it unless the gate policy changes (Part B) |
| A3 AI-audit findings | L1 shot_002, shot_008; L4 event_004, event_011, event_020; L5 shot_002, shot_008, event_010; L6 shot_002, shot_011, shot_013; L7 shot_013, event_021, event_022 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | AI audit of frames | YES: the gate would BLOCK these unless Part B is approved |
| A4 withdrawn arm snaps | L4 event_001 (2.27 s snap), event_002 (3.2 s snap) | DIRECT_OBSERVATION | UNKNOWN and INACTIVE | owner: no arm movement at 0.6-1.1 s and 6.7-6.9 s; 2.27 s and 3.2 s not confirmed | NO. Must stay inactive; a new label must not reactivate them |
| A5 superseded dip | L3 shot_009 (27.6 s) | DIRECT_OBSERVATION as a dip | SUPERSEDED by a non-black transition note | detector non_black_transition UNKNOWN at 27.63 s; owner: transition, not through black | Already removed from staging; NO change in eligibility |

Consequences of the group decisions:
- YES to A1: the six overlay dips become MEASURED, matching the four dips already MEASURED in staging. No change in what is eligible.
- YES to A2 and A3 (as separate records): they keep their own provenance. They are blocked by the gate unless Part B is approved. This does NOT make them eligible.
- YES to A4: the withdrawn arm snaps are marked UNKNOWN and inactive. They are not deleted.
- YES to A5: the 27.6 s record is marked superseded with a pointer to the transition note.

RECOMMENDED DEFAULT for Part A:
- A1: DEFER until each interval is checked against its measurement (a per-record check is pending).
- A2, A3: DEFER (keep DIRECT_OBSERVATION in the original; a separate correction overlay records the AI-audit classification when approved).
- A4: YES (inactive).
- A5: YES (superseded, original kept).

Method: historical records are NOT rewritten. Any change goes into a separate, versioned correction overlay that names the original record, the old value, the new value, the source and the reason.

[ ] A1: YES  [ ] NO  [ ] DEFER (default)
[ ] A2 and A3: YES  [ ] NO  [ ] DEFER (default)
[ ] A4: YES (default)  [ ] NO  [ ] DEFER
[ ] A5: YES (default)  [ ] NO  [ ] DEFER

---

## PART B — Policy decision (separate from record corrections; NOT approved by default)
B1. Should AUDITOR_FRAME_INSPECTION (AI audit of frames) be an observation level accepted by the staging gate, which currently accepts only DIRECT_OBSERVATION and MEASURED (pieces/p6_stage1_staging.py line 16)?
- YES: AI-audit findings become eligible evidence for teaching. This widens what reaches Kimi, and AI readings would count as evidence.
- NO (default): the gate stays as it is. AI-audit findings stay blocked from teaching.
- DEFER: same effect as NO for now. It is not a second default.

[ ] YES  [ ] NO (default)  [ ] DEFER (same effect as NO)

---

## PART C — Other decisions (D1–D9), only those needed for the immediate next stage

| # | Decision | Needed now? | Recommended default | YES means | NO means | DEFER means |
|---|---|---|---|---|---|---|
| D1 | Art style per reel | No (teaching on hold) | DEFER | styles recorded (observed, named reviewer); F4 may change | styles stay empty; Stage 1 stays closed | nothing changes |
| D2 | Creator requirement | No | DEFER | GENERAL relaxed to the observation tier (owner option b; separate policy decision) | GENERAL stays (owner option a) | nothing changes |
| D3 | Experimental packets offline | No | DEFER | offline packets may be prepared (no Kimi) | no packets | nothing changes |
| D4 | Label change (Part A) | Yes | see Part A | records change (versioned) | records stay | records stay |
| D5 | Delivery path for lessons | No (Kimi on hold) | DEFER | a GranthStudio input is designed (separate work) | no delivery path | nothing changes |
| D6 | Preset asset mapping for the L2 candidate | No | DEFER | the owner maps assets for one candidate | nothing mapped | nothing changes |
| D7 | Loop baseline guard failures (3 tests) | No | DEFER | the guard is changed (recorded) | known failures stay | known failures stay |
| D8 | L3 end fade as an event | Yes (small) | YES: move to a note | the fade is a note, not a dip event | stays an event | stays an event (blocked by the gate, see B1) |
| D9 | Step 5 labels and new held-out set | Later | DEFER | a new independent set is reserved for a clean final test | the exposed set is used | Step 5 stays deferred and exposed |

Also decide:
- Accept the story and scene annotation protocol v1 as the structure for labelling? Default: DEFER (structure only; no labels). The frozen structural test pieces/test_annotation_protocol.py remains test-review-open; the additive regression pieces/test_annotation_source_refs.py passed. Neither status is human validation. YES / NO / DEFER.
- Accept the 20-beat pilot as draft evidence? Default: YES with zero-length warnings. YES / NO / DEFER.

---

## PART D — Items that stay closed regardless of your answers this round
- F4 policy: closed (HOLD).
- Kimi integration and delivery: closed (HOLD).
- Build 006 publication: closed (HOLD).
- GranthStudio production changes: closed.
- Step 5 pass or fail: not decided here; deferred and exposed.
- Any AI-audit finding becoming eligible: closed unless Part B is YES.

---

## Pre-review check log (2026-10-31)
- Default wording corrected: B1 had two defaults ("NO" and "DEFER"). It now has one default, NO. DEFER has the same effect as NO.
- Annotation protocol default changed from YES to DEFER (matches ONE_ROUND_APPROVAL_SHEET.md). The protocol remains structure only, with no labels.
- D2 YES wording corrected: "GENERAL target kept or relaxed" is now "GENERAL relaxed to the observation tier (owner option b)", as in work/phase1/roadmap_audit/OWNER_DECISIONS_REQUIRED.md.
- D1-D9 wording checked against OWNER_DECISIONS_REQUIRED.md and DECISION_RECORD_2026-10-31.md: all remaining items match. D9 here also names a new held-out set; the decision record marks that as recommended and not created.
- D4 status: ON HOLD in DECISION_RECORD_2026-10-31.md. Codex's test finding (a bare "NO" check) is still open in _loop/p6_d4_table/TEST_FINDINGS.md. D4 is OPEN.
- Nothing in this sheet is approved by default; blanks are never approvals.
