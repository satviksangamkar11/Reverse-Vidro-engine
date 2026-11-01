# Offline validation report: the six stored Fast-Close V1.3 plans (2026-11-01)

Zero-budget phase. No model call and no network: the run blocked `socket.connect` before importing anything. No frozen file was modified: every run file still matches its hash in `runs/RUN_LOG.json`. GranthStudio itself was not touched; the experiment copies were only read (imported with `python -B`, so no cache files were written).

## 1. What was run

| Check | Code (existing) | Input |
|---|---|---|
| Director validator | `validate_scene()` in `scripts/source/director_test.py` (experiment copies A_baseline and B_lessons; identical code) | Each stored `plan`. The context is rebuilt exactly as `direct_scene()` builds it: approved split `a1_split_rev9`, timing timeline, shot target, dialogue plan, speaker table, preset JSON, and `packet_text` = the user prompt. |
| Prompt identity | `build_prompt()` + `split_scene_override()` | The rebuilt system and user prompts compared with the archived request bodies in `runs/prompts/`. |
| Cross-context | the same `validate_scene()` | Each plan also validated against the other arm's prompt (B's prompt contains the five lesson lines, which feed the PACKET word check). |
| Compliance and quality facts | `compliance()` and `quality_facts()` in `pieces/fc13_eval.py` | Stored results, registry gains, timing plan. |
| Structure facts (supplementary, not an existing validator) | plain counts by the supervisor | Fixed halo per preset (`backdrop.halo` in `assets/v5_presets/*.json`), pose claims, citations outside the shot, two-way camera text, repeated asset maps. |

The glue scripts are in the session scratchpad (`zb_revalidate.py`, `zb_facts.py`). They only call the functions above or count fields; they are not product code.

## 2. Results

| Plan | Stored result | Re-run errors | Re-run warnings | Reproduces stored | Prompt rebuilt = archive | Errors under the other arm's prompt |
|---|---|---|---|---|---|---|
| A S3 | UNREVIEWED | 0 | 8 | yes | yes | 0 |
| A S6 | UNREVIEWED | 0 | 13 | yes | yes | 0 |
| A S8 | UNREVIEWED | 0 | 8 | yes | yes | 0 |
| B S3 | INVALID | 1 | 4 | yes | yes | 1 (same) |
| B S6 | UNREVIEWED | 0 | 11 | yes | yes | 0 |
| B S8 | UNREVIEWED | 0 | 2 | yes | yes | 0 |

- The only error, B S3-5: `person 'Shri Gajanan Maharaj seated calmly' is not in the owner's research`.
- All warnings are "STAGING ... needs the owner's approval". No preset-run, close-up-run, coverage, turn or zoom-text warning appeared.
- Under the stored run's rules, UNREVIEWED means "passed the validator, no Nemotron cross-check". It is never VALID.

### fc13 compliance (descriptive only)

| Plan | Opening | Distinct presets | Same-preset pairs | Strong-push pairs | Close-up on turn | Quiet-beat gains | Flat share | Images |
|---|---|---|---|---|---|---|---|---|
| A S3 | 01 | 4 | 0 | 1 | no | 0.20 | 0.33 | 11 |
| A S6 | 01 | 3 | 1 | 3 | no | 0.20, 0.28 | 0.33 | 15 |
| A S8 | 01 | 4 | 0 | 0 | yes | 0.20 | 0.40 | 9 |
| B S3 | 02 | 3 | 1 | 1 | no | 0.28 | 0.33 | 10 |
| B S6 | 01 | 5 | 0 | 0 | no | 0.14, 0.28 | 0.17 | 11 |
| B S8 | 01 | 4 | 0 | 0 | no | 0.13 | 0.20 | 10 |

These match `runs/FINAL_DECISION.json`.

### Supplementary structure facts

| Plan | Halo shots (01/04/06/08) | Halo shot whose fx image says "no glow/rays" | Shots with no pose claim | Claims citing an ovi outside the shot | Two-way camera text | Repeated asset map |
|---|---|---|---|---|---|---|
| A S3 | 2 (1, 5) | 0 | 0 | 2 (scenery) | 0 | 0 |
| A S6 | 3 (1, 2, 6) | 0 | 0 | 6 (person) | 0 | 0 |
| A S8 | 2 (1, 3) | 1 (S8-1) | 1 (S8-1, animals only) | 2 | 0 | 0 |
| B S3 | 1 (6) | 1 (S3-6) | 3 (1, 4, 6) | 1 (person) | 0 | 0 |
| B S6 | 2 (1, 6) | 2 (S6-1, S6-6) | 0 | 0 | 0 | 1 (S6-6 = S6-1) |
| B S8 | 1 (1) | 1 (S8-1) | 5 (all) | 1 (prop) | 1 (S8-2 "and back") | 1 (S8-5 = S8-3) |

## 3. Validator limitations found (verified on these outputs)

| # | Limitation | Evidence | Effect |
|---|---|---|---|
| V1 | The PACKET check is an exact-token word check. Every word of 3+ letters must appear somewhere in the whole user prompt. | "calm" is in the PACKET ("calm posture", ovi 90), so it passes; "calmly" fails. "old torn vest" passes because both words appear in the PACKET. | It catches spelling form, not meaning. A true claim in a different word form fails; a false claim made of PACKET words passes. |
| V2 | The PACKET word list is the whole user prompt, including the owner's notes and, in arm B, the lesson lines. | The cross-context re-run changed no verdict here. | In a future arm, words that occur only in guardrail or lesson lines would count as "in the research". The future protocol must validate every arm against the arm-A prompt as well. |
| V3 | Pose claims are not required. | B S8 has 5 shots with held poses and no pose claim; the plan is still UNREVIEWED (passed). | Rule F5 ("every pose ... is listed") is not enforced. |
| V4 | A non-event claim may cite any ovi of the scene, not only the shot's own. | A S6: six person claims cite A1:119 in shots that show 120-122. | Weak provenance passes. |
| V5 | Camera direction is not checked against the preset's single segment. Only push/pull words are compared with the zoom. | B S8-2 "and back" passes. | An unbuildable move passes. |
| V6 | A fixed preset effect (the halo) is not checked against staging or image text. | 5 shots ask for "no glow" on a halo preset. | An internal contradiction passes. |
| V7 | Repeated identical images in non-adjacent shots are not reported. | B S8-3 and S8-5. | No effect on validity (may be intended). |
| V8 | The compliance metric C3 (ovi-sourced pose on the turn) is structurally almost always false, because rule F3 makes held poses STAGING. | 0 of 6. | The metric does not measure "visible reaction". Do not use it as a quality signal. |

These are reported only. No validator, detector or frozen result was changed (F4 and GranthStudio are untouched).

## 4. Not run, and why

| Check | Why not |
|---|---|
| Nemotron Ultra cross-check (`review_plan`) | It is a model API call (NVIDIA). Forbidden in this phase. |
| Render through the Builder | No images exist for these plans; the plans are drafts. |
| Human rating | No human-review round in this phase. |
| Re-scoring with Opus or Gemini given the full inputs | It would be a model call. |

## 5. Uncertainties

- The checks in section 3 are counts of text and structure. Whether a halo or a repeated image matters on screen was not seen; no render exists.
- The supplementary script is supervisor glue. If the owner wants these checks kept, they should be built as tested code through the loop (Nemotron writes; this is not authorised now).
