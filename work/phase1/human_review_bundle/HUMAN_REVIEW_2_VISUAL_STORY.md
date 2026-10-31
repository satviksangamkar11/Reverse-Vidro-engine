# HUMAN REVIEW 2 — Clay video: editing, sequencing, performance, reactions, pacing (video 7a1e2b26, first 10 development beats)

Source: clayrified-DfF8Z8tMVhK (clay video, 24 fps; development video, not held out). Evidence sheet: sheet_7a1e2b26_first10.jpg (8 frames per beat, times on frames). Beats: work/phase1/v4/audit_7a1e2b26/beats_7a1e2b26.json.

KEEP TWO THINGS SEPARATE
- TOOL OUTPUT (not ground truth). In work/phase1/step4/STEP4_MEASUREMENTS.json, 4.29, 5.88 and 7.62 s are hard_cut events. The times 1.88 and 3.04 s are NOT hard_cut events in STEP4_MEASUREMENTS.json or STEP4_RESULTS.json; they are OPEN (see the discrepancy log at the end). The owner individually confirmed only the 9.96 s cut; other cut answers in the owner file were relayed from a model and are not counted as human checks. The total cut count is UNRESOLVED: 36 (owner file), 33 (STEP4_MEASUREMENTS.json and STEP4_RESULTS.json), 75 (cut_events_7a1e2b26.json). No count is used in this packet.
- HUMAN GROUND TRUTH: only what you approve or correct on this page. Nothing here is human-verified until you approve it.

HOW TO READ
- "Observable action" = the AI vision report, an AI reading of frames; confirm or correct on the frames.
- Each proposed field is an AI proposal with a default; UNKNOWN where the evidence is inadequate.
- One approval field per beat: APPROVE, CORRECT, or UNKNOWN.

TIMESTAMP FLAGS
- Overlapping pairs (same interval, two records): shot_001 and event_001 (0.0-1.5); shot_002 and event_002 (2.0-3.0); shot_004 and event_003 (4.5-5.5); shot_005 and event_004 (6.0-7.5). Read each pair as one time span with two records. Do not count them as two events.
- No zero-length beat appears in this window. The earlier zero-length beats are in 7434a0f7 (see Review 1).
- Known tool/timing note: the cut times 1.88 s and 3.04 s lie just outside the spans 0.0-1.5 and 2.0-3.0 (1.88 s is between the first two spans; 3.04 s is just after the second). A cut is a boundary, not a shot duration. Use the frames.

---

## shot_001 and event_001 — 0.0 to 1.5 (same span)
- Frames: sheet row 1.
- Observable (AI): static camera; wood shavings appear around the drill bit between frames; subtitle changes from "A hand drill bites..." (readable on frames).
- Editing / sequencing (proposal): opening shot of the sequence; shot type CLOSE_UP (drill and hands). Scene boundary at start: YES (first beat).
- Story progression (proposal): SETUP (the drilling act is introduced by subtitle). Confidence LOW.
- Character performance: NONE visible (no character performance; hands and tool only). Reaction: ABSENT.
- Pacing: UNKNOWN (a single 1.5 s span).
- Approval: [ ] APPROVE  [ ] CORRECT: ____________  [ ] UNKNOWN

## shot_002 and event_002 — 2.0 to 3.0 (same span)
- Observable (AI): static shot; hands grip and turn the wooden drill handle; the bit rotates and drills deeper; the subtitle "of a crowded boat," stays fixed; no particle or light change.
- Editing: cut times 1.88 s (before this span) and 3.04 s (just after). Not verified by a human for this span. 1.88 s and 3.04 s are OPEN (not detector hard_cut events in the measurement file; see the discrepancy log).
- Story progression (proposal): SETUP continues (the act is shown). LOW confidence.
- Character performance: hands only; legs and torso fixed. Reaction: ABSENT.
- Pacing (proposal): a 1-second drilling action; rhythm: UNKNOWN.
- Approval: [ ] APPROVE  [ ] CORRECT: ____________  [ ] UNKNOWN

## shot_003 — 3.5 to 4.0
- Observable (AI): static shot of the boat; the man in yellow shifts his upper body and arms slightly; the boy's mouth opens (AI reading); yellow subtitle at the bottom.
- Editing: hard cut (detector: 3.04 s before, 4.29 s after) — tool output, not verified for this span.
- Character performance (proposal): small postural shifts; reaction: POSSIBLE (mouth open) — LOW confidence; UNKNOWN whether it is speech or an expression.
- Story progression: UNKNOWN (the boat scene's meaning needs the subtitle text, not fully readable in the report).
- Approval: [ ] APPROVE  [ ] CORRECT: ____________  [ ] UNKNOWN

## shot_004 and event_003 — 4.5 to 5.5 (same span)
- Observable (AI): static shot; wood shavings accumulate around a stationary bit; the character's feet and shoes stay still; the drill descends into the wood.
- Editing: hard cut at 4.29 s (before) and 5.88 s (after): tool output.
- Pacing (proposal): accumulation is a gradual visual build over the span; pace: UNKNOWN.
- Character performance: NONE (feet and shoes stationary).
- Approval: [ ] APPROVE  [ ] CORRECT: ____________  [ ] UNKNOWN

## shot_005 and event_004 — 6.0 to 7.5 (same span)
- Observable (AI): the character's eyes shift gaze downward; the head tilts slightly; the left arm moves minimally; subtitle changes from "He's drilling a hole" to "right between his own" (readable on frames).
- Character performance (proposal): gaze shift and head tilt. Reaction: POSSIBLE — LOW confidence (could be ordinary clay animation of a held pose).
- Story progression (proposal): SETUP (subtitle describes the drilling). LOW.
- Editing: a hard cut at 5.88 s (before) and 7.62 s (after): tool output.
- Approval: [ ] APPROVE  [ ] CORRECT: ____________  [ ] UNKNOWN

## shot_006 — 8.0 to 9.5
- Observable (AI): static shot; the hands adjust their grip on the wooden drill handle; the bit stays in wood shavings; subtitle changes to "feet, in the middle" and "of a wide river" (readable on frames).
- Editing: hard cut at 7.62 s (before); the owner confirmed a cut at 9.96 s (after this span). It is not a hard_cut event in the detector output files (see the discrepancy log).
- Story progression (proposal): SETUP → a location change in the subtitle ("wide river") — UNKNOWN whether the scene changes here; scene boundary: UNKNOWN.
- Pacing: UNKNOWN (no duration reference beyond the span).
- Approval: [ ] APPROVE  [ ] CORRECT: ____________  [ ] UNKNOWN

---

## Summary for this packet
- Cut boundaries inside or next to this window (tool output): 4.29, 5.88 and 7.62 s are detector hard_cut events; 1.88 and 3.04 s are OPEN; the 9.96 s cut is owner-confirmed only.
- Character performance: mostly hands and tools; a gaze shift (shot_005) and a possible mouth change (shot_003) are LOW-confidence readings.
- Reactions: none reliably observed in this window.
- Story progression: a drilling act with subtitle narration; scene boundaries mostly UNKNOWN.
- Shot sequencing: close-up hands, then a wide boat shot, then close-ups of the drill: proposed MEDIUM confidence as a pattern, UNKNOWN as a rule.

## What this review cannot establish
- Verified story structure; the subtitle text is the only narration and it is not verified.
- Whether any AI reading of a gaze or mouth change is a real performance choice or an animation artefact.
- The meaning of the wide-river subtitle for the story.

---

## Pre-review check log and discrepancy log (2026-10-31)
Checked against work/phase1/v4/audit_7a1e2b26/beats_7a1e2b26.json and work/phase1/step4/STEP4_MEASUREMENTS.json. Source records are unchanged.

Verified (PASS):
- The 10 records and their timings match the source: shot_001 and event_001 0.0-1.5 (frames 0-36); shot_002 and event_002 2.0-3.0 (frames 48-72); shot_003 3.5-4.0 (frames 84-96); shot_004 and event_003 4.5-5.5 (frames 108-132); shot_005 and event_004 6.0-7.5 (frames 144-180); shot_006 8.0-9.5 (frames 192-228).
- The 6 spans and the 10 records are correct. No zero-length record is in this window.
- Detector hard_cut events 4.29, 5.88 and 7.62 s are present in STEP4_MEASUREMENTS.json.

Corrected packet wording (source not changed):
- The shot_002/event_002 subtitle is "of a crowded boat," and it stays fixed. The packet said the subtitle changes; corrected.
- Overlap wording for shot_004/event_003 corrected (it said 4.5-5.5 twice).

OPEN (not resolved here; recorded for the owner):
- D-1: cut at 1.88 s. Not a hard_cut event in STEP4_MEASUREMENTS.json or STEP4_RESULTS.json. The earlier baseline (work/phase1/step4/STEP4_D0_BASELINE.md) lists 1.88 s as a cut hidden by the old detector. Affects the boundary between spans 1 and 2 and the shot_002/event_002 editing field. Owner has not confirmed it.
- D-2: cut at 3.04 s. Same status as D-1. Affects shot_002/event_002 and shot_003 editing fields.
- D-3: cut at 9.96 s. The owner confirmed it (OWNER_VISUAL_READ_ROUND2_2026-10-31.md, item 6). It is not a hard_cut event in the detector output files; the nearest event is an UNCLASSIFIED_SPIKE at 9.88 s. Affects the shot_006 "after" field.
- D-4: total cut count. Three files give different counts: 36 (owner file, "tool-detected"), 33 (STEP4_MEASUREMENTS.json and STEP4_RESULTS.json), 75 (cut_events_7a1e2b26.json). The packet does not use any count. Unresolved.
- D-5: owner round-2 file says the other cut answers were relayed from a model and are not counted as human checks. The packet now says so.

Effect: until D-1 to D-4 are resolved, the cut boundaries in this packet are not confirmed evidence. They are approved only if the owner approves them on the sheet.
