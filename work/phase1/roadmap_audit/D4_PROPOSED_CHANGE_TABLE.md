# D4 proposed change table (proposal only; NO file is changed; D4 is ON HOLD)

Question D4 asks: how should the label DIRECT_OBSERVATION be classified, given that it currently covers measured dips, AI-audit observations and one withdrawn claim?

## 0. Corrections to the earlier D4 text
- The earlier text said the label appears "in historical beat records". It does not. grep finds 0 files under work/phase1/v4 with DIRECT_OBSERVATION. The historical beat files use OBSERVED and NOT_EXAMINED status values.
- The earlier text said "changes staging only". It does not: the lesson-candidate overlay (source), the code vocabulary, the gate and the specs are affected too.
- The gate (pieces/p6_stage1_staging.py line 16, OBSERVED_OK = DIRECT_OBSERVATION, MEASURED) BLOCKS any record with another level (line 130). A relabel that is not in OBSERVED_OK adds a block reason. This is a policy-relevant change, not a label fix.

## 1. Counts (exact, from files on disk)
- Overlay work/phase1/overlays/lesson_candidates_7434a0f7.json: 25 events with DIRECT_OBSERVATION (39 text lines).
- Staging work/phase1/step6/staging/STAGE1_STAGING_7434a0f7.json: 22 events DIRECT_OBSERVATION, 6 events MEASURED (the four added dips and two others).
- Code, specs, tests: see section 3.
- Historical beat files: 0.

## 2. Record-level proposal for the overlay (source) file
Proposed values follow three classes. Each proposal names the evidence that supports it. None is applied.

| Lesson | beat_id | Time (s) | Current | Proposed | Class | Source evidence | Reason |
|---|---|---|---|---|---|---|---|
| L3 | shot_003 | 5.0-8.5 | DIRECT_OBSERVATION | MEASURED | A dip | frozen detector CONFIRMED dip_to_dark at 4.93 s (work/phase1/step4/STEP4_MEASUREMENTS.json) | the dip is a brightness measurement; the text says "confirmed from frames and brightness" |
| L3 | shot_004 | 9.0 | DIRECT_OBSERVATION | MEASURED | A dip | detector 8.97 s | same |
| L3 | shot_006 | 13.0-18.0 | DIRECT_OBSERVATION | MEASURED | A dip | detector 12.9 s | same |
| L3 | shot_007 | 18.5 | DIRECT_OBSERVATION | MEASURED | A dip | detector 18.47 s | same |
| L3 | shot_009 | 28.0-29.5 | DIRECT_OBSERVATION | REMOVE as a dip; record as non-black transition note (UNKNOWN) | Correction | frozen detector (`work/phase1/step4/STEP4_MEASUREMENTS.json`, 7434a0f7): UNCLASSIFIED_SPIKE at 27.6 s, frame_diff 27.7, REJECTED. That file has no non_black_transition kind for 7434a0f7. Owner round 2: transition, not through black. Overlay conflict: `lesson_candidates_7434a0f7.json` line 190 says "dip through dark at about 27.6 s"; `overlay_7434a0f7.json` line 469 says "fade-up from dark at ≈27.6 s". Corrected 2026-10-31; label change NOT applied; D4 on HOLD | the overlay still counts 27.6 s as a dip; the staging already removes it |
| L3 | shot_010 | 30.0 | DIRECT_OBSERVATION | MEASURED | A dip | detector 29.93 s | same |
| L3 | shot_013 | 47.0-53.5 | DIRECT_OBSERVATION | MEASURED | A dip | detector 46.9 s | same |
| L3 | shot_014 | 53.77 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | C end fade | frames under the title; not a dip between scenes | a fade-out is not a dip between scenes (see D8) |
| L1 | shot_002 | 0.5-4.5 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | B AI audit | AI audit of frames (OPUS audit) | the statement is an AI reading of frames, not a human view |
| L1 | shot_008 | 19.0-27.5 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | B AI audit | same | same |
| L4 | event_001 | 1.0-2.5 | DIRECT_OBSERVATION | UNKNOWN | D withdrawn | owner: no arm movement at 0.6-1.1 s | arm-snap claim withdrawn; not confirmed |
| L4 | event_002 | 3.0-4.5 | DIRECT_OBSERVATION | UNKNOWN | D withdrawn | 2.27/3.2 s not confirmed by owner reading | same as above, pending owner |
| L4 | event_004 | 7.0-8.5 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | B AI audit | AI audit | "eyes constant" is an AI reading |
| L4 | event_011 | 26.0-27.5 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | B AI audit | AI audit | same |
| L4 | event_020 | 47.0-48.5 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | B AI audit | AI audit | same |
| L5 | shot_002 | 0.5-4.5 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | B AI audit | AI audit | particle colours read by an AI audit |
| L5 | shot_008 | 19.0-27.5 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | B AI audit | AI audit | same |
| L5 | event_010 | 24.0-25.5 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | B AI audit | AI audit | same |
| L6 | shot_002 | 0.5-4.5 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | B AI audit | AI audit; sync UNKNOWN | subtitle layout read by an AI audit |
| L6 | shot_011 | 30.5-36.0 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | B AI audit | AI audit | same |
| L6 | shot_013 | 47.0-53.5 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | B AI audit | AI audit | same |
| L7 | shot_013 | 47.0-53.5 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | B AI audit | AI audit | title card read by an AI audit |
| L7 | event_021 | 49.0-50.5 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | B AI audit | AI audit | same |
| L7 | event_022 | 52.0-53.5 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | B AI audit | AI audit | same |
| L7 | shot_014 | 53.77 | DIRECT_OBSERVATION | AUDITOR_FRAME_INSPECTION | C end fade | frames | same as L3 shot_014 |

Classes: A = measured by the frozen detector (brightness) and frame-checked; B = AI audit of frames (not human); C = fade or end state; D = withdrawn claim.

Important: the overlay's 25 DIRECT events do not contain a single human observation. Every class is either measurement or AI audit. "DIRECT_OBSERVATION" is therefore inaccurate for all 25 records, not only the dips.

## 3. Code, spec and test lines (affected by the label)
| File | Line | Current | Effect of a change | Proposed | Frozen? |
|---|---|---|---|---|---|
| pieces/p6_lessons.py | 118 | valid_levels includes DIRECT_OBSERVATION | validation rejects the new level unless added | add AUDITOR_FRAME_INSPECTION, keep DIRECT (history) | no (non-frozen; loop-built module; needs review) |
| pieces/p6_lessons.py | 176 | valid_basis includes DIRECT_OBSERVATION | same for basis | same | no |
| pieces/p6_stage1_staging.py | 16 | OBSERVED_OK = (DIRECT_OBSERVATION, MEASURED) | AUDITOR_FRAME_INSPECTION would BLOCK staged records | policy decision: add or not | no, but a POLICY decision |
| pieces/p6_stage1_staging.py | 130 | block reason text | wording only | update text if OBSERVED_OK changes | no |
| pieces/test_p6_lessons.py | 38, 56 | fixtures use DIRECT | fixtures only | keep | no |
| pieces/test_p6_stage1_staging.py | 26, 86, 87 | frozen round-0 test; accepts DIRECT or MEASURED | must not change | keep unchanged | YES (frozen) |
| pieces/test_p6_stage1_measured.py | 4, 26, 133 | rejects DIRECT for the four dips | passes if dips become MEASURED | keep | no |
| specs/phase1_p6_lessons.md | 7 | spec text | documentation | none unless D4 approved | no |
| specs/phase1_p6_stage1_staging.md | 12, 19 | spec text: "present with DIRECT_OBSERVATION" | documentation of an old decision | update only with a versioned spec note | no |

## 4. Staging file (generated, not hand-edited)
The staging file is generated by pieces/p6_stage1_staging.py from the overlay. A change must come from regenerating it after the overlay decision, not from editing its 36 lines by hand. The four added dips are already MEASURED in staging, so the overlay (DIRECT for the same dips) and the staging (MEASURED) are currently inconsistent. This inconsistency is itself a reason to decide D4.

## 5. Not changed (historical)
- Loop logs and reviews under _loop/ (contain DIRECT_OBSERVATION in round and review files): historical; never edit.
- Step 6 and Step 7 reports (documentation mentions): keep; add a pointer to this table.
- Frozen round-0 test file: never edit.

## 6. Decisions needed (for D4)
1. Confirm the class mapping in section 2 (A, B, C, D), record by record.
2. Decide whether AUDITOR_FRAME_INSPECTION is an eligible observation level in the staging gate (a POLICY decision; the gate currently allows only DIRECT_OBSERVATION and MEASURED).
3. Decide the historical approach: keep the overlay as the original and add a versioned correction overlay (recommended), not a global rewrite.
4. Decide whether to correct the overlay's 27.6 s dip (shot_009) through the correction overlay.

## 7. Status
ON HOLD. No change has been applied. The owner has not approved any row.
