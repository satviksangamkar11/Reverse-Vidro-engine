# Shot, composition and editing (departments 5 to 7)

Department 5, camera language: PARTIAL_RESEARCH.
- AI observations: 8 cells; 532 teacher candidates (AI reading, unverified).
- Frozen Step 4 measurement: 2 videos (7434a0f7, 7a1e2b26). Read-only output; the detector was not run or changed.
- Human-verified (specific items only): 7434a0f7 zoom and move reads at 0.5-4.5, 11.5-12.5, 24.5-27.5, 31.0-33.9, 34-35 and 37.5-39 s. The 47.5-53 s window has conflicting owner answers, so it is NOT counted as verified.
- Missing: camera meaning and framing relative to story. Lens and focal-length claims are not established.

Department 6, composition: NOT_EXAMINED. No composition, framing, eyeline, look-room or spatial-continuity observation was recorded. The tutorial's rule-of-thirds and eyeline notes are reference concepts only.

Department 7, editing and transitions: PARTIAL_RESEARCH. Corrected 2026-10-31 to match `CUT_COUNT_RECONCILIATION.md` and `OWNER_RESPONSE_LEDGER_2026-10-31.md`.

Clay video 7a1e2b26 (hard cuts):
- Frozen detector: 33 hard_cut events (`work/phase1/step4/STEP4_MEASUREMENTS.json`, produced by `pieces/p6_measure_track.py`). Traceable to a saved event list.
- Owner-approved count: 36 cuts (37 shots). Approved on the owner's cross-check. Only the first 10 s were checked frame by frame; the other 30 cuts were checked at 1 frame per second.
- Complete reproduction of the 36: NOT VERIFIED. The scene-detection tool and settings are not named in the repo. The 36 does not replace the 33, and the 33 does not replace the 36.
- Historical 75 (`work/phase1/step4/cut_events_7a1e2b26.json`, written 01:55): SUPERSEDED. No producer in the repo. Entries sit on a dense 0.25 s grid from 1.00 s. Kept with its source and definition for the record; not evidence.
- Cuts at 1.88 s and 3.04 s: owner-confirmed observations. They are not hard_cut events in the frozen output.
- Cut at 9.96 s: owner-confirmed observation. It is not a hard_cut event in the frozen output either.
- Not claimed: that all 36 cuts were individually frame-verified.

Illustrated video 7434a0f7:
- Frozen detector, hard-cut rule (`hard_cut_min` 40.0 and `hard_cut_ratio` 20 times the median): 0 hard cuts. This zero holds under that rule only. It is not a human-verified total, and it does not claim the clip has no cuts.
- Frozen transitions in the same file: 10 `dip_to_dark` (CONFIRMED, through black, at 4.93, 8.97, 12.9, 18.47, 21.77, 24.3, 29.93, 36.13, 40.8 and 46.9 s). 7 `UNCLASSIFIED_SPIKE` (REJECTED, below 40.0) at 2.93, 3.83, 25.23, 27.6, 43.47, 43.67 and 43.87 s.
- `work/phase1/step4/cut_events_7434a0f7.json`: the same 17 events, with the 7 spikes relabelled `hard_cut`. SUPERSEDED: no producer, and the labels contradict the frozen threshold.
- Owner readings (not counts, not resolved):
  - 2.93 s and 3.83 s: not cuts (owner).
  - 4.93 s and 12.9 s: "real cuts" in the approved analysis; "lighting effect" and "blackout" in the round-2 visual read. OPEN.
  - 27.6 s: "transition, not through black" (round 2). The frozen file has a rejected spike here, and the overlays call it a dip or a fade. OPEN.
  - 43.5 to 46.5 s: transition (A8 and A9).
  - 47.5 to 53.0 s motion: detector UNKNOWN (MIXED_MOTION_SIDE_ZOOM). Owner round 2 "zoom out" (retained); round 3 "sliding down". OPEN.
- No owner-approved total boundary count exists for 7434a0f7.

Eight cells are NOT_EXAMINED.

Teachable now: measured hard-cut and dip facts for the two videos only, with no claim about meaning.
