# ONE-ROUND APPROVAL SHEET (single sitting, three reviews)

Deadline: 4:15 PM IST. Human review limit: 3 reviews. Approval rounds: 1.
Complete this sheet in one sitting. Each review below points to its packet. You do not need any other report.

Pilot scope (read before signing):
- This sitting covers 2 of the 13 development videos (7434a0f7 and 7a1e2b26) and 20 records in total (10 per review, Reviews 1 and 2).
- It is NOT comprehensive validation of the 16 filmmaking departments. Departments 1-4, 6, 12, 14 and 15 are not validated for any video. See work/phase1/coverage_16/COVERAGE_16_REPORT.md.
- No human labels have been entered yet. Every approval and signature field is blank.
- Held-out videos are not used in any review.

Rules you are approving:
- Only what you check here is approved. Everything else is DEFERRED or UNKNOWN.
- A default means "accept this if you sign off without changing it". It is not approval by silence.
- Corrections are written in the blank lines. A correction replaces the default for that item.

---

## REVIEW 1 — Story and scene, video 7434a0f7 (first 10 beats)
Packet: HUMAN_REVIEW_1_STORY_SCENE.md. Sheet: sheet_7434a0f7_first10.jpg.
Ten beats. Each beat has APPROVE / CORRECT / UNKNOWN.
Two beats are flagged zero-length (shot_001, shot_004): do not use them for duration scoring.

| Beat | Approve | Correct | Unknown |
|---|---|---|---|
| shot_001 (0.0-0.0, FLAG) | [ ] | ______ | [ ] |
| shot_002 (0.5-4.5) | [ ] | ______ | [ ] |
| event_001 (1.0-2.5) | [ ] | ______ | [ ] |
| event_002 (3.0-4.5) | [ ] | ______ | [ ] |
| event_003 (5.0-6.5) | [ ] | ______ | [ ] |
| shot_003 (5.0-8.5) | [ ] | ______ | [ ] |
| event_004 (7.0-8.5) | [ ] | ______ | [ ] |
| shot_004 (9.0-9.0, FLAG) | [ ] | ______ | [ ] |
| event_005 (9.5-11.0) | [ ] | ______ | [ ] |
| shot_005 (9.5-12.5) | [ ] | ______ | [ ] |

Default for all ten: APPROVE the observable action only. Story function, scene purpose and reveal remain AI PROPOSALS until you approve them individually.

---

## REVIEW 2 — Clay video, 7a1e2b26 (first 10 beats: editing, sequencing, performance, pacing)
Packet: HUMAN_REVIEW_2_VISUAL_STORY.md. Sheet: sheet_7a1e2b26_first10.jpg.
Overlapping pairs (shot/event with the same span) are read as one span with two records.

| Span | Approve | Correct | Unknown |
|---|---|---|---|
| 0.0-1.5 (shot_001 and event_001) | [ ] | ______ | [ ] |
| 2.0-3.0 (shot_002 and event_002) | [ ] | ______ | [ ] |
| 3.5-4.0 (shot_003) | [ ] | ______ | [ ] |
| 4.5-5.5 (shot_004 and event_003) | [ ] | ______ | [ ] |
| 6.0-7.5 (shot_005 and event_004) | [ ] | ______ | [ ] |
| 8.0-9.5 (shot_006) | [ ] | ______ | [ ] |

Default: APPROVE the observable action only. Tool cut times are DETECTOR OUTPUT, not human ground truth, unless you approve them. 4.29, 5.88 and 7.62 s are detector hard_cut events. 1.88 and 3.04 s are OPEN (not hard_cut events in the detector output files). The owner confirmed only 9.96 s, and it is not a hard_cut event in those files.

---

## REVIEW 3 — Owner decisions (one sheet)
Packet: HUMAN_REVIEW_3_OWNER_DECISIONS.md.

| Item | YES | NO | DEFER | Default |
|---|---|---|---|---|
| A1 measured dips (six overlay records) to MEASURED | [ ] | [ ] | [ ] | DEFER |
| A2/A3 AI-audit records to AUDITOR_FRAME_INSPECTION (kept separate, original preserved) | [ ] | [ ] | [ ] | DEFER |
| A4 withdrawn arm snaps to UNKNOWN and INACTIVE | [ ] | [ ] | [ ] | YES |
| A5 27.6 s record marked SUPERSEDED (original kept) | [ ] | [ ] | [ ] | YES |
| B1 AI-audit level accepted by the staging gate (POLICY) | [ ] | [ ] | [ ] | NO |
| C-D8 L3 end fade moved to a note | [ ] | [ ] | [ ] | YES |
| Accept annotation protocol v1 (structure only) | [ ] | [ ] | [ ] | DEFER |
| Accept 20-beat pilot as draft (zero-length warnings) | [ ] | [ ] | [ ] | YES |
| D1 art style, D2 creators, D3 experimental packets, D5 delivery, D6 preset mapping, D7 loop guard | [ ] | [ ] | [ ] | DEFER (all) |
| D9 Step 5 labels and a new independent held-out set | [ ] | [ ] | [ ] | DEFER |

Closed regardless: F4 change, Kimi integration and delivery, build_006, GranthStudio production changes, global D4 label replacement.

Annotation protocol status (for the protocol row above):
- The frozen structural test pieces/test_annotation_protocol.py remains test-review-open.
- The additive regression pieces/test_annotation_source_refs.py passed.
- Neither status is human validation, and neither approves the protocol. The default is DEFER.

Corrections: ______________________________________________

---

## Signature
Reviewer name: ______________________   Date/time (IST): ______________
Note: writing a name here records that you made these choices. The agent has not filled in any approval.
