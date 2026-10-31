# Cut-count reconciliation (clay video 7a1e2b26; 7434a0f7 noted where relevant)

Scope: read-only. No frozen measurement was changed or rewritten. No detector was run. Held-out videos were not used.

## Sources checked
| Number | Source file | Written | Producer in repo | Event list saved | Verdict |
|---|---|---|---|---|---|
| 33 | work/phase1/step4/STEP4_MEASUREMENTS.json (7a1e2b26, transitions.events kind "hard_cut") | 2026-10-31 01:59 | yes: pieces/p6_measure_track.py (frozen; hash in STEP4_FREEZE_MANIFEST.json) | yes: 33 hard_cut and 42 UNCLASSIFIED_SPIKE entries | TRACEABLE. The only count with a saved event list from the frozen, repaired detector. |
| 33 (repeated) | work/phase1/step4/STEP4_RESULTS.json | 2026-10-31 01:59 | same run | yes | Same run as above; not a second source. |
| 36 | cited in roadmap_audit/CROSS_VIDEO_LESSON_INVENTORY.md (T5) and in owner notes (OWNER_VISUAL_READ_ROUND2, "tool-detected count") | no date in file | not found | NO. No saved file in the repo contains 36 hard_cut events (checked every JSON under work/phase1/step4). | UNTRACEABLE. Cited but not reproducible from the repo. |
| 75 | work/phase1/step4/cut_events_7a1e2b26.json | 2026-10-31 01:55 (before the repaired run) | NOT FOUND. No code in pieces, tools or scripts writes cut_events_*.json. | yes: 75 hard_cut entries, no UNCLASSIFIED entries | SUPERSEDED / UNTRACEABLE. Written by an earlier, unknown configuration. Its entries are on a dense 0.25 s grid from 1.00 s (1.00, 1.25, 1.50, 1.75, 2.00 ...), which is the pattern of spike-level candidates, not of distinct cuts. |

Also noted: work/phase1/step4/cut_events_7434a0f7.json has 7 hard_cut entries. STEP4_MEASUREMENTS.json has 0 hard_cut events for 7434a0f7. This conflict is recorded here and is not resolved in this pass.

## Why the numbers differ
- 33 vs 75: different detector configurations. The pre-fix configuration (documented in STEP4_D0_BASELINE.md: spike threshold, hard-cut thresholds, and a skip of 6 frames after every spike, defect D1) produced many spike-level entries labelled as cuts. The repaired detector separates 33 hard cuts from 42 unclassified spikes.
- 33 vs 36: the 36 has no saved event list, so the cause of the difference cannot be determined from the repo. It is not reproduced by any file in the repo.

## Decision for the record
- The measured count for 7a1e2b26 that has traceable evidence is 33 (repaired frozen detector, saved event list).
- 75 is SUPERSEDED. It is not used. It comes from a pre-repair configuration with no producer in the repo.
- 36 is UNRESOLVED. The owner's audit figure has no reproducible source. It must not replace 33 unless its source (event list, video, method and event definition) is produced.
- The 1.88 s, 3.04 s and 9.96 s cut times are not hard_cut events in the repaired output. 9.96 s remains owner-confirmed only.

## What would close the 36
- The original event list behind the 36 (video, method, event definition and deduplication rule), or a human frame-level check of the candidate cuts against the 33 detector events. The second needs a human judgment on each candidate and is not automated.

Status (superseded by the owner cross-check below): 33 traceable (use with the detector caveat); 36 was UNRESOLVED, now owner-approved; 75 SUPERSEDED; 7434a0f7 conflict OPEN.

## Owner cross-check (2026-10-31)
- D-1 (1.88 s), D-2 (3.04 s), D-3 (9.96 s): CLOSED as real cuts, on the owner's cross-check of the frame-level analysis (OWNER_REVIEW_RESPONSES_R2.md).
- Total for 7a1e2b26: 36 cuts (37 shots), owner-approved. Limitation: the scene-detection tool and settings are not named, and only the first 10 s were checked frame by frame (the other 30 cuts at 1 frame per second). The frozen detector's 33 is unchanged; the 3 cuts it missed are the D-1, D-2 and D-3 cuts.
- 7434a0f7 conflict (7 vs 0): source conflict resolved (see the section below). The owner total for 7434a0f7 is still OPEN.

## 7434a0f7: 7 vs 0, reconciled from the event definitions (2026-10-31)

Both files hold the same 17 events, with the same time, frame_diff and median_diff. They differ only in the kind label on 7 events.

| t (s) | frame_diff | cut_events_7434a0f7.json (01:55) | STEP4_MEASUREMENTS.json, frozen (01:59) |
|---|---|---|---|
| 2.93 | 33.7 | hard_cut | UNCLASSIFIED_SPIKE |
| 3.83 | 32.7 | hard_cut | UNCLASSIFIED_SPIKE |
| 25.23 | 31.3 | hard_cut | UNCLASSIFIED_SPIKE |
| 27.6 | 27.7 | hard_cut | UNCLASSIFIED_SPIKE |
| 43.47 | 9.0 | hard_cut | UNCLASSIFIED_SPIKE |
| 43.67 | 17.1 | hard_cut | UNCLASSIFIED_SPIKE |
| 43.87 | 13.2 | hard_cut | UNCLASSIFIED_SPIKE |

The 10 dip_to_dark events (4.93, 8.97, 12.9, 18.47, 21.77, 24.3, 29.93, 36.13, 40.8, 46.9 s) are the same in both files and are CONFIRMED.

Frozen rule (`pieces/p6_measure_track.py`, `_event`): a non-dark cluster is `hard_cut` only if its peak frame_diff is at least `hard_cut_min` (40.0) and at least `hard_cut_ratio` (20) times the median (0.69, so 13.8), and only one frame is large. All 7 labelled spikes fail the 40.0 minimum, so they are `UNCLASSIFIED_SPIKE`, REJECTED. The cut-events file's labels do not follow any single rule: 9.0 and 13.2 are below the 13.8 ratio too, and 17.1 passes the ratio but not the minimum.

Verdict:
- **0 hard cuts for 7434a0f7 under the frozen rule.** Producer in repo, saved event list, TRACEABLE.
- **cut_events_7434a0f7.json is SUPERSEDED.** It has no producer in the repo and its labels contradict the frozen threshold. Not used as evidence. Same status as the 75-event file for 7a1e2b26.
- **Frozen transitions for 7434a0f7:** 10 dips through black (CONFIRMED), 0 hard cuts, 7 rejected spikes.
- **Owner statements (not a count):**
  - Owner-provided analysis recorded in `OWNER_REVIEW_RESPONSES_R1.md` (update section, 2026-10-31): "real cuts" at 4.93 s and about 12.9 s; fade at about 8.97 s; sparks at 2.93 s and 3.83 s are not cuts.
  - Owner visual read round 2 (`OWNER_VISUAL_READ_ROUND2_2026-10-31.md`, `OWNER_VISUAL_READ_7434a0f7.json`): 4.9 s "lighting_effect"; 9.0 s and 12.9 s "blackout_then_next_scene"; 27.6 s "transition_not_through_black".
  - **Conflict, OPEN:** 4.93 s is a "real cut" in one owner input and a "lighting effect" in the other. 12.9 s is a "real cut" in one and a "blackout" in the other. The owner's word "cut" may mean any transition, not a hard cut. Only the owner can settle this.
  - 2.93 s and 3.83 s: owner says not cuts. Frozen rule also rejects them. Consistent.
  - 43.47 to 43.87 s: inside the owner's 43.5 to 46.5 s transition reading (A8/A9). No owner answer says these are hard cuts. Frozen rule rejects them.
  - 25.23 s: no owner answer found.
  - 27.6 s: owner says transition, not through black. Frozen rule gives UNCLASSIFIED_SPIKE (27.7). The D4 table cites a "non_black_transition UNKNOWN at 27.63 s" from the detector, but no such kind exists for 7434a0f7 in the current frozen file. Flagged for the D4 hold. D4 not changed.

Decision for the record: the repo-traceable hard-cut count for 7434a0f7 is 0. No owner-approved total exists for 7434a0f7. The 7-entry file is not used.

