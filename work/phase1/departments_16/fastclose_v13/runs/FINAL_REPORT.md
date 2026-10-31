# Fast-Close V1.3 Kimi A/B: final report (2026-11-01)

Question: do five EXPERIMENTAL director lessons, added to Kimi K3.1 Pro's prompt, produce better scene direction for GranthStudio (Adhyay 1, S3, S6, S8)?

## Verdict
**A_BETTER (baseline) under the frozen rule, with both AI raters.** Screening only.
- Opus and Gemini, each scored blind and frozen before the key was opened, give the same verdict.
- The Q1/Q2/Q5/Q6 sensitivity reading gives the same verdict.
- This screening shows NO improvement from the lessons. The baseline was preferred in 2 of 3 scenes.
- Not proof either way: one sample per arm per scene, no human rating.

## Mapping (opened after both AI sheets were frozen)
B (with lessons) = P1 and A (baseline) = P2 in all three scenes.

## Per scene (frozen rule: the preferred arm wins only with total >= other, Q5 >= other, validator errors <= other)
| Scene | Opus winner (total A / B) | Gemini winner (total A / B) | Validator A / B |
|---|---|---|---|
| S3 reaction | A (23 / 22) | A (30 / 25) | passed / INVALID (1 error) |
| S6 quiet | **B** (22 / 23) | **B** (18 / 29) | passed / passed |
| S8 reveal | A (25 / 23) | A (29 / 27) | passed / passed |
| Verdict | A_BETTER | A_BETTER | |

Sensitivity reading (Q1, Q2, Q5, Q6 only): same winners in every scene, A_BETTER for both raters.

## What the raters saw (their notes; AI readings, not verified facts)
- S3: B kept wide group framing throughout, repeated lateral parallax, and only established the full place at the end. A opened on the place, moved to the debate and used a two-face close-up for the unclear-speaker ovis 103-104.
- S6: A cut away to an invented Dwarka courtyard for the Arjuna comparison (ovi 120). B stayed at the doorway and kept the comparison spoken.
- S8: both plans respected the canon. A was cleaner: one-way moves, a clear stopping gesture, a contrast of the two waters. B repeated 09_dialogue_composition and asked for a pan there and back.

## Lesson-relevant structure (compliance counts, descriptive only; never used in the decision)
| Plan | Opening preset | Strong push pairs | Same-preset pairs | Distinct presets | Close-up on turn | Quiet-beat gains |
|---|---|---|---|---|---|---|
| A S3 | 01 | 1 | 0 | 4 | no | 0.20 |
| B S3 | 02 | 1 | 1 | 3 | no | 0.28 |
| A S6 | 01 | 3 | 1 | 3 | no | 0.20, 0.28 |
| B S6 | 01 | 0 | 0 | 5 | no | 0.14, 0.28 |
| A S8 | 01 | 0 | 0 | 4 | yes | 0.20 |
| B S8 | 01 | 0 | 0 | 4 | no | 0.13 |

Reading:
- The lessons were received, not ignored. B's structure differs: fewer strong push pairs and more variety in S6, a gentler quiet-beat move in S8, and a non-establishing opening in S3.
- Where the lessons visibly changed structure, they helped once (S6) and hurt or did not help twice:
  - S3: the "open on the subject" reading delayed the place.
  - S8: the restraint choice repeated a preset.

## Audits
- B S3 validator error ("person 'Shri Gajanan Maharaj seated calmly' is not in the owner's research"):
  - A S3 passed with "Shri Gajanan Maharaj seated nearby" and "seated on the road". B S3 added the descriptor "calmly" to a person claim.
  - Classification: a claim-format slip against the contract (a pose word inside a person term). It is not a canon or source error. It still counts as a validator failure, as pre-registered.
- S8 owner-note flags (drinking near the brought water): FALSE FLAGS in both plans.
  - Every flagged sentence either refers to the trough drinking the ovi states (135) or explicitly says he is NOT shown drinking the brought water ("without showing him drinking it", "not for Maharaj to drink", "do not show Maharaj accepting or drinking").
  - No owner-note conflict in either S8 plan.
- Gemini input omission: Gemini was not given the owner's dress note. It docked canon props (old bandi; gourd and clay chilim) in S6. Even with those deductions removed, S6 stays a B win (Gemini totals 29 vs 18), so the verdict is unaffected.

## Cost and billing
- Kimi: 6 generation calls, 6 free token-count requests, 0 retries. Ledger actual $0.44341 (P4 now $1.1282 of the $2.00 cap in the experiment copies).
- Moonshot account: $10.8749 before; $10.7353 right after; $10.4633 on recheck. That is a drop of $0.4116, close to the ledger. The earlier gap was billing lag; $0.03 remains, likely still lagging or a small price difference.
- Opus review: 1 call, $0.583 at list price (Claude plan).
- Gemini review: run by the owner outside this pipeline.
- Loop jobs: 4 calls (2 Haiku, 2 Codex).

## Limitations (disclosed)
1. No human rating. The owner chose to finalize on two AI ratings (recorded before the key was opened: FINALIZATION_DEVIATION.md).
2. One sample per arm per scene. Kimi's output varies between calls, so a different draw could change the result.
3. S3 was partly unblinded to the owner before rating (B S3's failure was reported during the run).
4. The rubric's Q3 and Q4 are worded close to lessons L3 and L4. The sensitivity reading without them gives the same result.
5. Effort low only. No Nemotron review. The temperature was the provider default.
6. The adapter does not save the full HTTP response, the returned model string or cached tokens.

## What this result supports
- Do not inject these five lessons into production.
- The lessons changed Kimi's structure without improving the direction overall. The one win (S6) came from avoiding an invented cutaway and repeated pushes. The losses came from delayed establishing and preset repetition.
- No confirmation round, extra Kimi call or lesson rewrite was started. Any next step is the owner's decision.
