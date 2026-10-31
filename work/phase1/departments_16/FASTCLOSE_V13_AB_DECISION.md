# Fast-Close V1.3: Adhyay and scene decision for the Kimi A/B (2026-11-01)

Decision: Adhyay 1, scenes S3 (ovi 97-105), S8 (ovi 134-137) and S6 (ovi 119-122) on split rev9. Pre-flight: technical PASS, budget FAIL (P4 cap). Experiment folder: `D:/aai work/granthstudio-artifacts/fastclose_v13_ab/` (see `PREFLIGHT.md` there). No model call was made.

## 1. Adhyay 1 vs Adhyay 2 (from the GranthStudio repo, read only)

| Criterion | Adhyay 1 | Adhyay 2 |
|---|---|---|
| Canon and approvals | Ovis packet with MANIFEST (verified); owner direction notes; owner's EASY script `A1_full_script_simple.md`. Split rev9 NOT approved (S4 proof was run on it, owner: "choose what is best for the pipeline"). No `approvals.json` exists. | Ovis imported from the owner's docx (148). Script is a mechanical DRAFT, "NOT the owner's final script; speakers are all narrator". 3 proposed omissions (48, 142, 143) need the owner. No approvals. |
| Story and scene context | 9-scene split with briefs, audio plan and code-measured timing plan (split hash matches), dialogue table, glossary, final answers. | Nemotron Stage 1 trial only (12 scenes, 93 shots; 8 script lines and 7 visualised ovis in no shot). No audio, no timing. |
| Input structure | Legacy director path (`scripts/source/director_test.py --split-run`), hard-wired to `canon/packets/adhyay_01`; proven with one Kimi call. | New Stage 1 nine-document contract (`scripts/pipeline/stage1/`, `schemas/stage1_v2/`). Its runner refuses Kimi ("needs the credit ledger and the owner's go"); Stage 2 not built. |
| Assets and presets | 59 flat final images, `final_image_binding.json`, 11 presets. | No images. |
| Fit for the five director lessons | Good: reaction, reveal and quiet scenes exist with fixed shot counts. | Unknown until a final script and scenes exist. |
| Work before Kimi can run | None technically; a money-cap raise. | Owner final script, omissions approval, a Kimi path through Stage 1 (code change), audio and timing plans. |

Rejected: Adhyay 2 (needs canonical content from the owner and a code change). Mixing chapters (no common input path).

## 2. Implemented input structure used
The existing director contract: split macro + owner edits (`story_split_edits/A1_rev1.json`) + audio plan + timing plan + packet, built by `load_split()` and `split_scene_override()`. The owner's `direction_notes` reach the prompt under "DIRECTION NOTES (the owner's)". Nothing was rebuilt.

## 3. Scenes
- S3, ovi 97-105, 6 shots, character reaction: two men see him, debate mad or wise, decide to test; one Bankatlal line (102).
- S8, ovi 134-137, 5 shots, visual reveal: Gajanan at the cattle trough; Damodarpant returns with vetiver water and protests (136, 137).
- S6, ovi 119-122, 6 shots, quiet and emotional: Bankatlal's admission and reverence; two visual-only shots at the end; ovi 122 speaker unclear.
- Rejected:
  - S4 (108-112, quiet): already directed by Kimi; a second direction needs `--redo`, which the code reserves for the owner.
  - S1 (opening, 2 shots): too short.
  - S2: its plan from the old prompt exists.
  - S9 (11 shots): costlier.
  - S5 and S7: kept with S9 as the confirmation set.

## 4. Experiment-only edits
- Created two copies (A and B, about 2.4 MB each) outside the repo.
- In B only, five lines were appended to `direction_notes`. Owner notes are unchanged and first.
- No canon content, script, split or code changed.

## 5. Final five-lesson pack (director lessons; EXPERIMENTAL; F4 unchanged)
1. L1 Detail-first opening: insert on a named object, then establish (7a1e2b26 0-4 s; owner R2).
2. L2 Flat full frame plus slow push by default (7434a0f7 0.5-8.5 s; owner B03/B04/B06, confirmed).
3. L3 Closest framing on the turn shot only (7434a0f7 11.7-12.8 s; owner-confirmed B10).
4. L7 Cut inside a scene; slide or pan_bridge only on a place change (7434a0f7 frozen dips + owner reads).
5. L8 Least-moving preset on silent beats; no push after push (7a1e2b26; owner-reported).
Full evidence: `FASTCLOSE_V13_TEACHING_PACK.json`.

## 6. Offline validation
- 139 files compared: only `A1_rev1.json` differs.
- Packet MANIFEST check and `load_split` pass in both roots; same split hash.
- Real prompt builder: identical system prompt; user prompt +5 lesson lines, 0 removed, in all three scenes.
- Existing director tests: 179 passed.
- Ledger: no unreconciled reservation.

## 7. Calls and cost
- Six Kimi K3.1 Pro calls (3 scenes × 2 arms), one call each, effort low, max 16,000 output tokens.
- Input about 13.7-14.2k tokens; the lesson lines add about 460. Output about 5-6k.
- At $2/M in and $10/M out: about $0.08-0.09 per call, about $0.50-0.55 for the screening.
- Plus six free Nemotron Ultra reviews.
- Confirmation set (S5, S7, S9): six more calls, about $0.60-0.75 (S9 has 11 shots).

## 8. PRE-FLIGHT
- Technical: PASS.
- Budget: FAIL. P4 committed $0.6848 of $1.00; worst-case reservation about $0.19 per call, so only 2 calls fit.
- Spending go and a cap raise (about $1.40 for the screening, about $2.00 with confirmation) are the owner's decision.

## 9. Loop System
Not used. No code was written or changed, and validation used the existing tests and loaders, so a loop would only add model calls.
