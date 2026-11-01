# Kimi failure inventory: Fast-Close V1.3 outputs (zero-budget phase, 2026-11-01)

Scope: the six stored Kimi K3.1 Pro shot plans from Fast-Close V1.3 (Adhyay 1 rev9, scenes S3 97-105, S6 119-122, S8 134-137; arm A = baseline, arm B = baseline plus five lessons). Nothing was regenerated. No model API was called. The stored files match the hashes in `runs/RUN_LOG.json`, so they have not changed since the run.

Sources read:
- The plans: `granthstudio-artifacts/fastclose_v13_ab/{A_baseline,B_lessons}/canon/director_runs/ab_*`.
- The exact prompts Kimi saw: `runs/prompts/`, including the PACKET, the owner's notes and the narration plan.
- The registered preset files: `assets/v5_presets/*.json`.
- The two AI reviews: `opus_review/` and `ai_ratings/`.
- The offline validator re-run: `OFFLINE_VALIDATION_REPORT.md`.

## Classification key

| Class | Meaning |
|---|---|
| V-DET | Verified by code: the existing validator, the fc13 compliance counts, the preset JSON or the structure counts in the offline report. |
| V-TEXT | Verified by the supervisor reading the plan against the exact ovi text, PACKET, owner notes or narration plan that Kimi was given. |
| AI-OP | An opinion of the Opus or Gemini reviewer that no source settles. It is not a verified error. |
| ARTIFACT | A reviewer finding that the source contradicts. The reviewer did not have that source, so this is not a Kimi error. |
| OWNER | The current rules allow this, but whether it is wanted is the owner's decision. |

Severity: HIGH = wrong story or canon; MED = a buildability or clarity problem; LOW = wording or minor.

## Attribution rule (lessons)

- There is one draw per arm per scene, and Kimi's output varies between calls.
- No item below is attributed to the injected lessons.
- Where an arm-B item touches a lesson's topic, it is marked "possible link, untested". Proving a link needs repeated draws (see `FUTURE_AB_PROTOCOL.md`).

## 1. Story and scene clarity

| ID | Plan | Finding | Evidence | Class | Sev |
|---|---|---|---|---|---|
| F-01 | B S3-6 | Performance says "their decision to test his conduct remains unresolved by observation". The brief says they "resolve to test". | Plan text vs the S3 brief. The wording can mean "the test has no result yet". | AI-OP (Opus), wording ambiguous | LOW |
| F-02 | A and B S3 | Neither plan shows the act that astonishes the two men ("हा प्रकार", 97); both show Gajanan only seated among the leaf plates. | The ovi refers back to the previous scene's action. The owner notes put the grain-picking at 93-94 (S2), not S3. | OWNER (should S3 re-show the act?) | MED |
| F-03 | A and B S3-3 | Ovis 99-102 are packed into one 6-second shot. | Code-fixed timeline: the narration plan has no core line for 100-101, so the timing plan starts 99 and 102 in shot 3. | ARTIFACT (upstream timing, not Kimi) | — |
| F-04 | A S6 goal | "...and receives him as Shegaon's Yogirav" puts the 122 praise next to Bankatlal's actions in the goal. All shots keep 122 with the narrator. | Owner note: 122 keeps an unclear speaker. | OWNER (goal wording only) | LOW |
| F-05 | A and B S6 | Hari's gift of desirelessness (122, "निरिच्छा ... दिला हरीनें") is not conveyed. | The owner's narration line S6-L5 for ovi 122 does not contain it either. The plans follow the fixed narration. | ARTIFACT (upstream script) | — |
| F-06 | B S8 turn | "Damodarpant stops Maharaj from putting the muddy water to his mouth". Opus calls this a misordering because he has already drunk (135). | Ovi 136 itself says "do not put that muddy water to your mouth", and the plan line says "पिऊ नका". | AI-OP, contested by the source | LOW |

## 2. Canon fidelity

| ID | Plan | Finding | Evidence | Class | Sev |
|---|---|---|---|---|---|
| F-07 | B S3-1 | "walk together toward the seated Gajanan": the direction is not in the source. | Ovi 97 and line S3-L1 say only that he was walking along the road. | V-TEXT | LOW |
| F-08 | A S6-2 | Arjuna is shown "still, withdrawn". Ovi 120 also says "करुं लागला भलभलतें" (began doing all sorts of odd things). | The ovi text. The pose shows half of the ovi and contradicts the other half. | V-TEXT (Opus raised it; the source supports it) | MED |
| F-09 | all six | The added words "great", "stop!" and "watch carefully" were flagged by the reviewers. | They are the owner's approved EASY lines (S6-L2 "मोठी चूक", S8-L4 "थांबा!", S3-L7 "नीट पाहूया"), and the validator forces an exact copy. | ARTIFACT | — |
| F-10 | A and B S8 | "brass gadva" flagged as not in the source. | PACKET: "material not named in the text; video prop choice: brass". | ARTIFACT | — |
| F-11 | A and B S3 | "used leaf plates" flagged as untraceable. | PACKET: used leaf plates on the road (ovi 87). | ARTIFACT | — |
| F-12 | A and B S6 | Gemini docked the old bandi, gourd and clay chilim. | Owner dress note (88-90). Gemini was not given it (supervisor's omission). | ARTIFACT | — |
| F-13 | B S3-5 | Validator error on "Shri Gajanan Maharaj seated calmly". | PACKET has "calm posture" (ovi 90). The word check matches exact tokens, so "calm" passes and "calmly" fails. This is a format slip against the claim contract, not a canon error. | V-DET (format), not canon | LOW |
| F-14 | all six | Unclear speakers kept: 103-104 and 122 are not given to a named person in any dialogue. | Validator speaker check; the stored owner-note flags are empty. | V-DET (no error) | — |
| F-15 | all six | No plan shows Gajanan drinking the water Damodarpant brought. | Earlier flags re-read: every hit is a negation or refers to the trough water. | V-TEXT (no error) | — |

## 3. Unsupported locations or actions

| ID | Plan | Finding | Evidence | Class | Sev |
|---|---|---|---|---|---|
| F-16 | A S6-2 | A cutaway to a "Dwarka courtyard" pictures Bankatlal's comparison (120). | Valid under the current rules: Dwarka and Arjuna are named in 120 and the courtyard is a STAGING proposal. Both AI raters penalised it. | OWNER (may a comparison be pictured?) | MED |
| F-17 | B S6-3; A S8-3 | Invented gestures: "lowered open palm" and "stopping hand". | Both are declared as STAGING poses, which rule F3/F5 allows for the owner to approve. | OWNER | LOW |
| F-18 | A S3-5 | A STAGING light "Soft close-up halo" on 08. | It honestly declares the fixed halo of 08. Rule F4 forbids glow that suggests an invented cause. | OWNER (see F-28) | LOW |

## 4. Shot progression

| ID | Plan | Finding | Evidence | Class | Sev |
|---|---|---|---|---|---|
| F-19 | B S3 | 02_environmental_parallax used in shots 1, 3 and 4. There is no close framing. A slide splits one ovi (shots 3 and 4 both list A1:102). | Structure counts. Whether it reads poorly is AI-OP (both raters). | V-DET structure; AI-OP effect | MED |
| F-20 | B S3 | The full place is established only in the last shot (01 at S3-6). | Structure. Possible link to lesson L1 (opening), untested. | V-DET; AI-OP effect | MED |
| F-21 | B S8-5 | Repeats shot 3's preset (09) and its exact image pair. | Asset maps are identical. Shot 5 is a visual-only shot that continues 137. B S6-6 also repeats S6-1, as a deliberate bookend its staging names. | V-DET; quality AI-OP | LOW |
| F-22 | A S6 | A slide moves from the 121 conclusion into the 122 praise in the same place. | Structure. Legal transition. | V-DET (no rule broken) | — |

## 5. Character reactions

| ID | Plan | Finding | Evidence | Class | Sev |
|---|---|---|---|---|---|
| F-23 | all six | Compliance C3 "turn shot has an ovi-sourced pose" is false in all six. | Rule F3 makes held poses STAGING, so an ovi-sourced pose is rarely possible. This is a metric limit, not a plan failure. | V-DET (metric limit) | — |
| F-24 | A S6 | Damodarpant, the listener, gets no visible reaction. | Ovi 119-121 states none, so showing none is correct. | AI-OP | LOW |
| F-25 | A S3-5 vs B S3 | A gives the 103-104 doubt a two-face close-up (08); B keeps all six shots wide. | Structure. The effect on quality is AI-OP. | V-DET; AI-OP effect | LOW |

## 6. Camera repetition

| ID | Plan | Finding | Evidence | Class | Sev |
|---|---|---|---|---|---|
| F-26 | A S6 | 3 strong-push pairs and 01 used three times; every camera line reads "push in". | Compliance C2; plan text. | V-DET | MED |
| F-27 | A S3, B S3 | 1 strong-push pair each; B S3 also has 1 same-preset pair. | Compliance C2. | V-DET | LOW |
| F-28 | all six | No "same preset 3 times in a row" warning fired in any plan. | Validator warnings. | V-DET (no warning) | — |

## 7. Preset and asset feasibility

| ID | Plan | Finding | Evidence | Class | Sev |
|---|---|---|---|---|---|
| F-29 | B S8-2 | The camera asks for "a pan from Maharaj ... to Damodarpant and back". | 02_environmental_parallax has one segment (x -0.12 → +0.12): one direction only. The validator does not check direction. | V-DET (not buildable as written) | MED |
| F-30 | A and B | Fixed warm halo: presets 01, 04, 06 and 08 always add a halo (`backdrop.halo`, intensity 0.18-0.30). Halo shots: A 7 (S3: 2, S6: 3, S8: 2), B 4 (S3: 1, S6: 2, S8: 1). | Preset JSON. | V-DET | MED |
| F-31 | A S8-1; B S3-6, S6-1, S6-6, S8-1 | These halo shots have an fx image whose description says "no glow / no rays / no miracle glow". | Image descriptions in the plans. The prompt says prose cannot switch a fixed effect off. | V-DET + V-TEXT (internal contradiction) | MED |
| F-32 | B S6-6 | "Slow closing dolly across" on 01, which is a fixed push-in (1.00 → 1.28). | Preset JSON. | V-TEXT | LOW |
| F-33 | A S3-5 | 08 has one "face" role; the plan puts both friends' faces in one combined close-up image. | Preset roles. Buildable as one image. | V-DET (feasible) | LOW |
| F-34 | all six | New images needed: A 11 / 15 / 9 (35); B 10 / 11 / 10 (31). Flat-compatible preset share (03/10/11): A 0.33 / 0.33 / 0.40; B 0.33 / 0.17 / 0.20. | quality_facts. Layered presets need cut-out layers. | V-DET | MED (production cost) |
| F-35 | all six | Opus's "no images_needed or assets declared" (it capped Q6 for all six). | The blinded view removed those fields; every plan declares them. | ARTIFACT | — |

## 8. Schema and validator errors

| ID | Plan | Finding | Evidence | Class | Sev |
|---|---|---|---|---|---|
| F-36 | B S3-5 | 1 validator error (F-13). Result INVALID. Reproduced offline exactly; same error under the A-arm prompt context. | `OFFLINE_VALIDATION_REPORT.md`. | V-DET | LOW (format) |
| F-37 | all six | Schema valid, finish "stop", no truncation; dialogue is the exact planned lines; shot counts and timeline match. | Validator; RUN_LOG. | V-DET (no error) | — |
| F-38 | A and B | The validator passes items that break the prompt's own rules (details in the offline report): | Supplementary structure counts. | V-DET (validator gap) | MED |

The items in F-38:
- Shots with no pose claim (rule F5): A 1 (S8-1, animals only); B 8 (S3-1, 3-4, 3-6; S8-1 to 8-5).
- Claims citing an ovi that is not in the shot's own ovi_ids: A 10, B 2. These are allowed for non-event claims.
- Two-way camera text: B 1.
- Halo against "no glow" text: A 1, B 4.

## Summary

| Class | Count (IDs) |
|---|---|
| Verified plan problems (V-DET / V-TEXT, LOW or higher) | F-07, F-08, F-13/F-36, F-19, F-20, F-21, F-26, F-27, F-29, F-30, F-31, F-32, F-34, F-38 |
| AI opinions only | F-01, F-06, F-24, and the "reads worse" effect in F-19, F-20, F-25 |
| Reviewer input artifacts (not Kimi errors) | F-03, F-05, F-09, F-10, F-11, F-12, F-35 |
| Owner decisions needed | F-02, F-04, F-16, F-17, F-18, plus whether the fixed 01 halo is acceptable (F-30) |

- No HIGH canon error was found in any of the six plans.
- The largest verified problems are buildability and contract issues: one-way presets, the fixed halo, missing pose claims, and the layered-image cost.
- They are not story errors. Most "canon" deductions by the AI raters trace to inputs those raters did not have.

## Lesson attribution (possible links, all untested)

| Arm-B item | Lesson topic | Status |
|---|---|---|
| F-20 delayed establishing (B S3) | L1 opening ("01 is one option, not a rule") | possible link, untested |
| F-21 repeated 09 (B S8) | L5 restraint names 09 as the least distracting | possible link, untested |
| No cutaway in B S6 (raters liked it) | none of the lessons forbids cutaways; L1 says "show nothing the ovis or PACKET do not name" | no clear link |
| Missing pose claims (B 8 shots) | no lesson touches claims | no link expected |
| F-36 "seated calmly" | no lesson touches claim format | no link expected |
