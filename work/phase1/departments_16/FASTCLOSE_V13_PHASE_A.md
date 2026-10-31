# Fast-Close V1.3, Phase A (2026-11-01)

Status: EXPERIMENTAL. No Kimi, VLM, Kaggle or production call was made. GranthStudio was read only (its working tree already had two unrelated modified files, `scripts/source/fix_loop.py` and `tests/test_codex_review.py`; not touched). F4 eligibility unchanged. Lessons, notes and plan: `FASTCLOSE_V13_TEACHING_PACK.json` (same folder).

## 1. Baseline Kimi outputs found

| Output | File | Result |
|---|---|---|
| Story split, Adhyay 1 (writer) | `granthstudio/canon/director_runs/a1_kimi_plan2/macro_A1.json` | VALID; later revised by code to rev9 (9 scenes, 59 shots, NOT approved) |
| Scene shot plan, ovi 108-112 (director) | `.../a1_s4_kimi_one/a01_scene4.json` | VALID, Nemotron PASS, $0.0724, 5 shots |
| Scene shot plan, ovi 84-96 (director, older prompt) | `.../a1_kimi_run1/a01_scene1.json` | INVALID (missing `needs`), 6 shots |

Only one valid scene plan exists. The writer split has no demonstrated filmmaking weakness of its own; writer-side weaknesses below come from the scene plans' `goal`, `turn` and `performance` fields, which the director call writes.

## 2. Demonstrated baseline deficiencies (11 shots, 2 scenes)

| # | Deficiency | Measured in the baseline |
|---|---|---|
| W1 | Camera monotony; no held frame | 11/11 shots move; 9/11 are push-in or dolly-in; 0 held. Silent beats A1:110 and A1:112 also get pushes. |
| W2 | Turn told, not shown | S4 turn A1:112 (visitors' satisfaction): no shot shows the visitors' faces; S4-4 is Maharaj's close-up while "the narrator begins the visitors' satisfaction". No entrance staged as a reveal. |
| W3 | Same opening every time | Both scenes open on 01_establishing_shot. |
| W4 | Performance carried by narration | 5/11 performance fields defer to the narrator (S4: 4/5). |
| W5 | Production mismatch | Layered presets 01, 02, 07, 08 in 6/11 shots; the 59 finals are flat (Codex, `CODEX_FULL_ARCHITECTURE.md` l.21). Nine invented image ids in S4 (l.18). |
| W6 | Transitions carry no structure | 10 cuts, 1 slide inside a scene (S1-3). |

Not shown in the baseline (so not taught): canon errors (validator found 0 in S4), dialogue errors, macro split structure.

## 3. Lessons (8, all EXPERIMENTAL)

| Id | Team | Weakness | Evidence (video, time, provenance) | Kimi behaviour | GranthStudio | Fit |
|---|---|---|---|---|---|---|
| L1 | Director | W3 | 7a1e2b26 0-1.88 s bit ECU, 2-3 s hands, 3.5-4 s first wide; owner R2 | Open on the key named object, establish second | 10 or 03 on flat inserts | SUPPORTED |
| L2 | Director | W5 | 7434a0f7 0.5-4.5 s, 5-8.5 s slow zoom on one flat frame, no pan; owner B03/B04/B06, confirmed | Default 03 on complete flat images | 03 (motion.py) | SUPPORTED |
| L3 | Director | W1 | 7434a0f7 strong zoom 11.7-12.8 s at "Marry me."; owner-confirmed paste B10 | Closest framing on the turn shot only | Framing via image; zooms fixed | PARTIAL |
| L4 | Writer | W2 | 7434a0f7 3-4.5 s woman's hand then man's; 5-6.5 s sage's hand then standing figure; owner's words B04/B05 | Cause shot, then response shot | Two held poses, cut | SUPPORTED |
| L5 | Writer | W2 | 7434a0f7 9.5-11 s Devayani enters, arm out, reveal YES; owner B09 | Entrance as before/after frames | Cut between two images; no walking | SUPPORTED (cut only) |
| L6 | Writer | W4 | 7a1e2b26 6-7.5 s calm close-up, 3.5-4 s boy's mouth closed: no reaction; owner R2 S03/S05 | Performance names what is visible | 07 or 03 on close images | SUPPORTED |
| L7 | Director | W6 | 7434a0f7 dips to dark 8.97…46.9 s (frozen, CONFIRMED) + owner "blackout then next scene"; 4.93 s and 12.9 s OPEN | Cut inside scenes; slide/pan_bridge only on place change | No dip-to-black transition | PARTIAL |
| L8 | Director | W1 | 7a1e2b26 static between cuts (owner round 3, owner-reported; rough check 0 px) | Least-moving preset on silent beats; no push after push | No static preset (03 always pushes) | PARTIAL / NOT SUPPORTED as true hold |

Canon safety for every lesson: technique only; no character, event, object, dialogue, motive or miracle from a reference video; every claim keeps its ovi/PACKET source; STAGING still needs the owner; owner notes win.

Incompatible (recorded, not taught): fast cutting (clay shots about 1.2-2 s) against fixed 6 s shots; the 1.5 s beat median (segmentation artifact).

## 4. Teaching packs

- Writer (L4, L5, L6): `writer_notes` in the JSON. Story, scene purpose, performance.
- Director (L1, L2, L3, L7, L8): `director_notes` in the JSON. Shot choice, framing, emphasis, transitions, production translation.
- Each line is labelled "EXPERIMENTAL TEACHING (not the owner's canon notes; owner notes win)".

## 5. GranthStudio compatibility

- Existing prompt slot: `direction_notes` in `canon/story_split_edits/A1_rev1.json`, placed by `director_test.py` `split_scene_override` under "DIRECTION NOTES (the owner's)". No new API needed.
- Injection needs authorization, one of: (a) a temporary, reverted owner-approved edit of that file's `direction_notes`; or (b) a one-line `--edits` flag passing `edits_path` to the existing `load_split()` (GranthStudio code change).
- Hard limits: 6 s shots, code-owned timing; transitions cut/slide/pan_bridge; no limb, walk, lip or face motion; flat finals suit 03, 10 and 11; layered presets need cut-outs.
- Result: 5 SUPPORTED, 3 PARTIAL, 1 observation incompatible.

## 6. Three-scene A/B screening plan (not run)

- Split: rev9 (`a1_split_rev9`, hash 285046ad…). It is NOT approved; the owner approves it (or a successor) first.
- Screening (never directed before): S3 ovi 97-105 (6 shots, debate and test), S5 ovi 113-118 (7 shots, meal), S8 ovi 134-137 (5 shots, trough vs vetiver water).
- Confirmation (previously unused, run only if screening passes): S6 ovi 119-122, S7 ovi 123-133, S9 ovi 138-144.
- Conditions: A = current prompt and owner notes; B = A plus the teaching pack lines. Same split, audio and timing plans, model, `--one-call --effort low --max-tokens 16000`, same reviewer. Order randomised per scene.
- Code-measured scores (no model call): VALID; flat-compatible preset share (03/10/11); push-after-push count; a shot whose held_pose shows the turn's stated response; performance fields deferring to the narrator; mid-scene slide/pan_bridge; validator errors and STAGING warnings.
- Owner blind preference per scene, plus a canon check (zero new canon errors allowed).
- Pass rule: B preferred in at least 2 of 3 screening scenes, no extra canon errors, no worse VALID rate. Then the confirmation set.
- Cost: the S4 call was 13,287 in / 4,586 out = $0.0724. Expect about $0.07-0.12 per call: screening 6 calls about $0.45-0.70; confirmation another 6 calls about $0.45-0.70. P4 cap had $0.315 left after S4; the screening needs a raised cap.

## 7. Sixteen-department coverage

| Dept | Phase E status | Useful evidence now | Used | Needs more analysis |
|---|---|---|---|---|
| 1 Storytelling | NOT_EXAMINED | Owner R1 story answers; approved 13-scene table (7434a0f7 only) | L4-L6 indirectly | Yes: other videos |
| 2 Narrative | NOT_EXAMINED | 13-scene table (7434a0f7) | no | Yes |
| 3 Direction | NOT_EXAMINED | Owner B04/B05 order, B09 entrance | L4, L5 | Yes |
| 4 Shot planning | NOT_EXAMINED | Owner B08-B10, S01-S03 shot types | L1, L3 | Yes |
| 5 Camera | PARTIAL | Owner zoom reads, 7434a0f7 | L2, L3 | 47.5-53 s OPEN |
| 6 Composition | NOT_EXAMINED | One paste note (B10 framing) | no | Yes |
| 7 Editing | PARTIAL | Frozen dips; clay cuts 33/36 | L7, L8 | 4.93/12.9 s OPEN |
| 8 Animation principles | PARTIAL (AI only) | none human-checked | no | Yes |
| 9 Performance | PARTIAL (AI only) | Owner S03, S05 | L6 | Yes |
| 10 Production | UNKNOWN | none | no | Mostly unobservable |
| 11 VFX | PARTIAL (AI only) | Owner: 2.93/3.83 s sparks, not cuts | no | Yes |
| 12 Colour | PARTIAL (measured) | Brightness/saturation, 6 videos | no | Interpretation |
| 13 Sound | PARTIAL | Speech timing, unverified transcripts | no | Sound classes |
| 14 Captions | PARTIAL (AI only) | 599 AI caption readings | no | Verification |
| 15 Pacing | PARTIAL | Clay cut times; 1.5 s artifact excluded | no (6 s shots) | True cut intervals |
| 16 Practical | PARTIAL | This compatibility table; presets | all | Static/dip presets are owner decisions |

## 8. Missing evidence and model-call estimate (not authorised)

- Human-confirmed evidence covers 2 of 10 development videos. Depts 1-4 and 6 need scene-level reading of the other 8 videos.
- Using existing keyframes, one VLM call per scene (about 10-15 scenes per video): about 80-120 calls for 8 videos, plus an owner spot-check sample. Cached AI observations in the v4 beat files can be re-read offline first at 0 calls.
- Kimi: 6 screening calls, then 6 confirmation calls.
- Kaggle GPU: not needed for Phase A or the screening.
