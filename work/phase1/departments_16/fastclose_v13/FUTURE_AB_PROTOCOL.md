# Future controlled Kimi test: three arms (prepared 2026-11-01, NOT RUN)

Status: a plan only. No model call has been made in this phase.
- Nothing here claims that arm B or arm C improves Kimi.
- The only Kimi evidence so far is Fast-Close V1.3: one draw per arm per scene, AI ratings only, verdict A_BETTER for those five lessons.
- Running this protocol needs the owner's explicit approval of the scenes, the number of calls and the money cap.

## 1. Question

1. Do direct GranthStudio guardrails (arm B), derived only from verified failures, reduce verified contract and buildability errors without making the direction worse than the baseline (arm A)?
2. Does adding ONE verified reference-video lesson on top of the guardrails (arm C) change the rated direction quality compared with B?

B vs A isolates the guardrails. C vs B isolates the one lesson.

## 2. The three arms (exact prompt differences)

All arms use the same director code, system prompt, split, audio and timing plans, owner notes, model, settings and validator. The only difference is the lines appended after the owner's `direction_notes` in an experiment copy of `canon/story_split_edits/A1_rev1.json`. This is the same slot and method as Fast-Close V1.3. GranthStudio itself is not modified.

**Arm A (baseline):** no added lines.

**Arm B (direct guardrails).** Five lines, each traced to a verified inventory item (`KIMI_FAILURE_INVENTORY.md`):
1. "EXPERIMENTAL GUARDRAIL 1 (format only; the owner's notes above always win): in a person claim the term names the person only (for example 'Shri Gajanan Maharaj'); put pose, mood or position words in a separate pose claim. A PACKET claim uses the research's own words unchanged (for example 'calm posture', not 'calmly')." (F-13/F-36)
2. "EXPERIMENTAL GUARDRAIL 2 (format only; the owner's notes above always win): every shot whose held_pose shows a person lists that pose as a pose claim (PACKET if the research names it, otherwise STAGING)." (F-38, rule F5)
3. "EXPERIMENTAL GUARDRAIL 3 (format only; the owner's notes above always win): each preset's camera moves in one direction only, as its fixed transform says; never ask for a move 'and back' or a second direction inside one shot; describe 01 and 03 as push-ins and 02 and 09 as sideways moves." (F-29, F-32)
4. "EXPERIMENTAL GUARDRAIL 4 (format only; the owner's notes above always win): 01_establishing_shot, 04_character_entrance, 06_blessing_gesture and 08_emotional_closeup always add a warm halo that cannot be switched off; never write 'no glow', 'no rays' or 'no radiance' for a shot or image that uses them; if a beat must have no glow, choose a preset without the halo." (F-30, F-31; wording depends on owner decision D2)
5. "EXPERIMENTAL GUARDRAIL 5 (format only; the owner's notes above always win): a claim that cites an ovi cites one of the shot's own ovi_ids that names that person, object or place; otherwise cite PACKET." (F-38)

Deliberately NOT in arm B. These are AI opinions or owner decisions, not verified errors:
- a ban on comparison cutaways (F-16);
- avoiding repeated images (F-21);
- avoiding STAGING gestures (F-17);
- "establish first";
- any rule on how many close-ups to use.

**Arm C (B plus one verified lesson).** Arm B's five lines plus:
6. "REFERENCE LESSON (technique only; the owner's notes above always win): when an ovi states an action or sight and a named person's response to it, show the cause first and the response second, each as its own held pose in shot order (or one held picture that already shows the response with its cause in frame). If the ovi states no response, do not invent one."

Why this lesson:
- It is DP1 in `DIRECTOR_KNOWLEDGE_PACK.md`, the only principle backed by the owner's own verbatim words (H1: B04, B05).
- It was not among the five lessons already tested.
- It applies to most Adhyay scenes.

## 3. Scenes

- **Primary set:** rev9 S5 (ovi 113-118, 7 shots), S7 (123-133, 9 shots), S9 (138-144, 11 shots).
  - Kimi has not directed any of them, so no `--redo` is needed.
  - Owner notes that bind them: 113 (unclear speaker), 118 (show the mixing of the dishes), 123-124 (unclear speaker), 133 (Damodarpant enters Devidas's house), 138-142 (keep the teaching complete), 143 (only ready to fall at his feet), 144 (runs with no destination).
- **Optional replication:** S3, S6 and S8 again. Directing them again needs `--redo`, which the code reserves for the owner. It would show how much a second draw differs from the stored one.
- rev9 is EXPERIMENT_ONLY (not approved). Results apply to rev9 only.

## 4. Draws, order, settings

| Option | Calls | Expected cost | What it can show |
|---|---|---|---|
| M (minimum) | 3 arms × 3 scenes × 1 draw = 9 | about $0.75-1.10 | Screening only. Same weakness as V1.3: one draw cannot separate the arm from chance. |
| R (recommended) | 3 arms × 3 scenes × 3 draws = 27 | about $2.25-3.25 | A per-scene majority over 3 draws per arm. Can show a consistent difference; cannot prove a small one. |

Basis for the cost:
- The six V1.3 calls cost $0.44341 in the ledger (mean $0.074 for 5-6 shot scenes).
- S5, S7 and S9 have 7-11 shots, so expect about $0.08-0.12 per call.
- The worst-case reservation is about $0.19-0.23 per call at max 16,000 output tokens.

Settings and order:
- `kimi-k3.1-pro`, `--one-call --effort low --max-tokens 16000 --reviewers ""`. The provider default temperature is the same in all arms.
- Every call starts a fresh context. There is no retry and no regeneration; an INVALID or truncated reply is a result.
- Order: for each draw, the three arms run in a rotated order per scene (A-B-C, B-C-A, C-A-B), so that no arm is always first.
- Before each call, the existing ledger gate applies: 0 unreconciled, and committed + worst-case reservation ≤ the approved cap. Otherwise stop.
- The P4 cap would be raised in the experiment copies only, as in V1.3.

## 5. Measures

**Deterministic (computed before any rating, never used to pick a winner alone):**
- Validator result and error count. Each plan is validated against its own prompt AND against the arm-A prompt, because the PACKET word check reads the whole prompt and so includes the guardrail and lesson lines (validator limit V2).
- Guardrail counts:
  - person terms carrying pose or mood words (G1);
  - shots with a held person and no pose claim (G2);
  - two-way or wrong-direction camera text (G3);
  - halo-preset shots with "no glow" text in the shot or its fx image (G4);
  - claims citing an ovi outside the shot (G5).
- fc13 compliance C1, C2 and C5, new-image count and flat-compatible share.
- C3 is reported but not interpreted (validator limit V8).
- These counts are supervisor glue today (`zb_facts.py`). If the owner wants them as tested code, they go through the loop first (Nemotron writes).

**Rated (blinded):**
- The frozen rubric Q1-Q6 (`EVAL_PROTOCOL.json`, sha f2365237...), so results compare with V1.3.
- The sensitivity reading on Q1, Q2, Q5 and Q6 is repeated.
- Primary rater: the owner (human). AI raters (Opus, Gemini) are secondary and labelled AI-assisted.
- Every rater gets the SAME complete pack. This fixes the V1.3 input artifacts F-09 to F-12 and F-35:
  - the ovis and brief;
  - all owner notes, including the dress note;
  - the narration plan lines (the owner's EASY Marathi);
  - the PACKET extract for the scene;
  - the preset facts (roles, one-way move, fixed halo);
  - each plan's `images_needed` and `assets`.
- Arm and condition names never appear. Anonymous ids are drawn from a sealed key opened only after every sheet is frozen and hashed.

## 6. Pre-registered decision

- **Per comparison (B vs A, C vs B), per scene:** apply the frozen `decide()` rule to each draw (win only with total ≥, Q5 ≥ and validator errors ≤ the other). The scene winner is the majority of draws (2 of 3); otherwise NO_CLEAR_DIFFERENCE.
- **Overall:** an arm is better only if it wins at least 2 of 3 scenes AND has no new canon error (verified as in the inventory) AND has a validator pass rate no lower.
- **Guardrail claim:** B "reduces verified errors" only if its total G1-G5 count is lower than A's in at least 2 of 3 scenes. That alone says nothing about direction quality.
- **Lesson claim:** C differs from B only through line 6. Any difference in ratings is reported as "with one draw set, on these scenes". It is never generalised to other Adhyays.
- If the owner does not rate, the result is labelled "AI-assisted screening" and cannot support production injection.

## 7. Owner decisions needed BEFORE any run

| # | Decision | Why it matters |
|---|---|---|
| D1 | Approve the option (M or R), the scenes and the money cap. | Spending. |
| D2 | Is the fixed halo of presets 01/04/06/08 acceptable in ordinary (non-miracle) scenes? | Sets the wording of guardrail 4. |
| D3 | May a spoken comparison (Arjuna, Dwarka) be pictured as a cutaway? | Both AI raters penalised it, but no rule forbids it (F-16). Raters must be told the ruling. |
| D4 | Are STAGING gestures (open palm, stopping hand) acceptable proposals? | Affects how raters score Q2 and Q5. |
| D5 | Will the owner rate (primary), or accept an AI-only screening? | Decides what the result can be used for. |

## 8. What this protocol does not do

- It does not change GranthStudio, the validator, F4, D4, the Step 4 detector, any frozen result or build_006.
- It does not use held-out videos.
- It does not add a new subsystem.
- It does not inject anything into production.
