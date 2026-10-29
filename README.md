# reverse-video-engine

**Objective: build a "teacher" for Kimi.** The engine reverse-engineers reference videos (Instagram reels, MP4 files, ZIPs of frames) into evidence-backed filmmaking knowledge that makes a two-stage AI animation director (Kimi) better at its job:

| Stage | Kimi's job | What the teacher gives it |
|---|---|---|
| **Stage 1: direction** | decide what the viewer sees: shots, framing, camera, character performance, image briefs, justified sound | lessons about shot sequencing, composition, performance, pacing, and when NOT to use a technique |
| **Stage 2: animation selection** | pick EXISTING presets and valid JSON arrangements for the approved shots; report `NEED_NEW` when something is missing | which arrangements reproduce an observed effect, the artwork each needs, and honest `NEED_NEW` capability gaps (never an invented preset) |

The teacher is three files, rebuilt from the evidence each time:
- `MASTER_REPORT.md`: the evidence (what happens in each video, with frame and time references).
- `MASTER_TECHNIQUES.json`: structured knowledge (techniques, requirements, counterexamples, classification).
- `KIMI_ANIMATION_PLAYBOOK.md`: short, practical Stage 1 and Stage 2 guidance.

**What it is not:** it does not build the film, does not call Kimi, and its hints are read-only: source canon, the output schema, approved presets and owner approvals always win. It never invents story events, dialogue, preset ids, editing software, lenses or screenplay text. Observed facts and inferred intent are kept apart.

## How it works
1. **Ingest:** local MP4/ZIP files or Instagram reel links (links are only queued until the owner says run).
2. **Local analysis:** extract frames, find shots and motion windows, detect silences in the audio.
3. **Vision review:** a vision model (Nemotron on NVIDIA, 14 keys, 10 calls per key per minute) reviews shots and motion windows and writes structured reports with frame evidence.
4. **Compile the teacher:** per-video digests, then a cross-video synthesis into recipes with evidence, Stage 1 and Stage 2 lessons, classification (general, style-specific, experimental) and honest `NEED_NEW` notes.
5. **Audit:** one reference video with audio is reconstructed in full and checked against the real video before the playbook is trusted.

## Status checklist (updated 2026-10-29, evening)
Legend: [x] done and verified by a real run or tests, [~] partly done, [ ] not done.

**Core pipeline**
- [x] Ingest, frame extraction, shot and motion selection on the 9 unique local videos (1,596 frames).
- [x] Full vision analysis of all 9 videos: 538 of 539 reviews complete (182 shot reviews, 307 motion-window reviews, 18 pilot reviews), rebuilt into `MASTER_REPORT.md`.
- [~] Teacher compiler (`pieces/h1_compile_teacher.py`): written by the build loop, tests being repaired. Until it runs, the playbook is only a thin draft from the pilot reviews.
- [ ] Audio understanding: today only silence is detected; narration (Marathi and Hindi), sound effects and music are NOT transcribed or aligned to cuts.
- [ ] One video reconstructed beat by beat (story, shots, transitions, animation, sound) and audited against the real video.
- [ ] 30 queued Instagram reels analyzed (waiting for the owner's go; none downloaded).
- [ ] Stage 1 and Stage 2 compatibility check of the finished playbook.
- [ ] Offline comparison of Kimi's decisions with and without the playbook (needs the owner's approval; no Kimi calls until then).

**Building blocks (`pieces/`, each with tests)**
- [~] 20 hardened modules: link queue, zip-safe ingestion, audio signal checks, motion-window coverage, beat schema, recipe compiler, deliverable writer with a playbook guard, corpus ledger, evidence counts, snapshot publishing, classification and Stage 1/2 views, offline A/B scoring harness. About 600 tests; 19 of 20 passed their own tests at the last check. Review rounds are not finished, so these are NOT yet called done.
- [ ] Wiring these blocks into one end-to-end runner (not needed for a first teacher).

**Build system**
- [x] Loop where Nemotron writes all code and tests and fixes failures; reviewers (Codex Luna, Haiku) review in bulk and in parallel (`ops/wave_loop.py`, `ops/bulk_review.py`; described in `docs/SATVIK_NVIDIA_SYSTEM.md`).

## Layout
- `engine/` the working analysis pipeline and the NVIDIA key scheduler.
- `pieces/` the tested building blocks. `specs/` the specs they were generated from.
- `ops/` the build-loop scripts. `docs/` the system description and the master checklist.
- `queue/` recorded links (not downloaded).
- Not in the repo: videos, extracted frames, API keys (`.env` is git-ignored).

## Known limits
- Reference reels are vertical and fast; the target film is 16:9 and slower. Techniques are adapted, not copied, and reel music and dramatic sound cues are research only.
- Reviewer opinions (language models) are not proof; only passing tests and real runs count as verified.
- Scripts in `ops/` contain paths from the original Windows workstation (`D:\aai work\...`); adjust them.

## Run (example)
`python engine/animation_research.py --input <videos> --output <out> --mode full --review --resume`
(needs 14 NVIDIA keys in a local `.env` as `NVIDIA_API_KEY_01..14`).
