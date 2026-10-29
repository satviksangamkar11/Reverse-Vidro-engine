# reverse-video-engine

A **teacher for Kimi**: it reverse-engineers reference videos (Instagram reels, MP4s, ZIPs of frames) into evidence-backed filmmaking knowledge for a two-stage animation director.

- **Stage 1 (directing):** what the viewer should see, shot choices, character performance, image briefs, justified sound.
- **Stage 2 (animation selection):** which existing presets and JSON arrangements execute the approved shots; `NEED_NEW` when a capability is missing.

Outputs (written by the engine): `MASTER_REPORT.md` (evidence), `MASTER_TECHNIQUES.json` (structured knowledge), `KIMI_ANIMATION_PLAYBOOK.md` (practical guidance for Kimi). Research hints are read-only: canon, schema and owner approvals always win.

## Layout
- `engine/` the working pipeline: frame extraction, shot/motion selection, Nemotron vision review with an NVIDIA key scheduler (14 keys, 10 calls/key/min), audio silence evidence, Instagram import (queue only until told to run).
- `pieces/` hardened building blocks written by Nemotron through a fix loop: link queue, zip-safe ingestion, audio DSP, motion-window coverage, beat schema, recipe compiler, deliverable writer, corpus ledger, evidence counts, snapshot publishing, classification, offline A/B harness. Each has its own tests.
- `specs/` the specs those pieces were generated from. `ops/` the loop scripts (wave loop, bulk Codex+Haiku reviewer). `docs/` the system doc and checklist.
- `queue/instagram_links.txt` links recorded for later; nothing is downloaded unless the owner says run.

## Rules
No Kimi calls in the research tool, no secrets in the repo (`.env` and key files are git-ignored), no copyrighted media committed. Paths in `ops/` are from the original Windows workstation (D:ai work\...); adjust them.

## Run (example)
`python engine/animation_research.py --input <videos> --output <out> --mode full --review --resume` (needs 14 NVIDIA keys in `.env` as NVIDIA_API_KEY_01..14).
