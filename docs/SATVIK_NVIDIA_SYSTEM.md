# Satvik NVIDIA System: FINAL = the Wave Loop (rewritten 2026-10-29 19:40)

One sentence: **Nemotron writes all code and fixes; Codex Luna and Haiku review in bulk, in parallel; fixes run in parallel; a script repeats this in waves until the pieces are clean; Claude only supervises.** This is the final design. Earlier versions are kept as `SATVIK_NVIDIA_SYSTEM.previous.md` and `SATVIK_NVIDIA_SYSTEM.v2.md`.

Folder: `D:\aai work\granthstudio`. Run Python from that folder. Use SYSTEM Python (`C:\Python314\python.exe`) for the loop scripts, because the repo venv has no `requests`.

## 1. Why this is the design (measured, not guessed)
- **Fastest we measured:** bulk review of 6 pieces took about 3 minutes (Luna 33-59 s per call, Haiku 2-3 min). The earlier one-piece-at-a-time loop needed about 5 minutes per piece and applied fixes only after reviewing every piece. In waves, reviews and fix jobs overlap, so nothing sits idle.
- **Cheapest in Claude tokens:** all coding, fixing and applying run on free NVIDIA models and scripts. Claude reads one short status table per check. Paid usage is limited to Haiku (medium) and Codex (your Codex limit), batched 3-4 pieces per call, and a Sonnet diagnosis only for stuck pieces.
- **Most accurate (what is and is not claimed):** the tests are a hard gate and are the only thing counted as verified. Two independent reviewer families (Codex Luna, Haiku) must agree there are no HIGH/MED findings for a piece to count as clean; those are opinions, never proof. A piece that does not converge is handed to a stronger model (Sonnet medium) with the real failure evidence.

## 2. Hard rules (owner)
- NO Kimi, NO ElevenLabs, NO Opus. No paid action without the owner's go. Never print or read API keys.
- Coder = Nemotron 3 Ultra only; Nemotron is never a reviewer. Claude writes no product code (specs, job files and small ops scripts only).
- Instagram links are only recorded (`animation_research_tool/instagram_links.txt`) until the owner says run.
- Docs are changed only when the owner asks.

## 3. Roles and models
| Role | Model | Settings |
|---|---|---|
| Coder (module + tests, every fix) | Nemotron 3 Ultra 550B `nvidia/nemotron-3-ultra-550b-a55b` | free NVIDIA endpoint, 14 keys, thinking on, effort medium; job `fixers` must be `["nemotron","nemotron","nemotron"]` |
| Reviewer 1 (bulk, 3 pieces per call) | Codex Luna `gpt-6-luna` (NOT `gpt-6.1-luna`) | effort medium, read-only, via `codex.cmd` |
| Reviewer 2 (bulk, 4 pieces per call) | Haiku 5.5 | `claude -p --model haiku --effort medium`, no write/edit/bash tools (login must be valid: if it says OAuth expired, run `claude` then `/login`) |
| Optional reviewers | GLM 5.3 Flash, MiniMax M3.1 Flash (NVIDIA, thinking off) | currently return NO_REVIEW (timeouts/empty), so not used in the bulk reviewer; only in the older single-piece `luna_review.py` |
| Escalation | Sonnet 5.5 medium (Claude subagent, read-only diagnosis) | for a piece flagged after 4 apply rounds, or any job that escalates after 3 failed fix rounds |
Empty, timed-out or errored reviewer replies are NO_REVIEW (neither pass nor fail).

## 4. The wave loop, step by step
Script: `animation_research_tool/_loop/wave_loop.py`. Start (system Python, cwd = repo folder, log `_loop/wave_run.log`, state `_loop/wave_state.json`):
`C:\Python314\python.exe "D:\aai work\animation_research_tool\_loop\wave_loop.py"`
Each iteration (about every 90 seconds):
1. **Apply:** for every piece whose latest review has HIGH/MED findings that are not yet applied and whose fix job is not running, run `apply_review.py` (appends the findings to the piece's spec as REVIEW FINDINGS and relaunches its Nemotron fix job through `fix_loop_stable.py`). All pieces in parallel.
2. **Bulk review:** run `bulk_review.py` every iteration. It selects only pieces whose code or tests changed after their last review and whose fix job is NOT running, then calls Codex (3 pieces per call, parallel) and Haiku (4 pieces per call, parallel), and writes `_loop/reviews/combined_<id>.md` (headings `LUNA ...:` and `HAIKU ...:`; a file with only `## <id>` = no findings).
3. **Clean:** a piece is clean when its fix job has finished, the latest review is newer than the job, and it has no HIGH/MED findings.
4. **Flag:** findings applied 4 times without going clean -> `_loop/reviews/NEEDS_CLAUDE_<id>.flag`, the piece is skipped, and the supervising Claude diagnoses it with Sonnet medium and applies the diagnosis (`apply_review.py _loop/reviews/sonnet_med_<id>.md <id>`).
5. Stops when every piece is clean or flagged.

## 5. How one fix job works (Nemotron)
1. **Spec** `docs/pilot/nemotron_specs/<name>.md`. It MUST end with the FORMAT block: reply with ONLY `FILE: <path>` blocks, each followed by a fenced ```python block (without the fences the parser finds no files).
2. **Job** `_loop/jobs/<name>.json`: `{"name","spec","files":[module,test],"tests":[test],"reference":[],"max_rounds":3,"review":false,"reviewers":[],"fixers":["nemotron","nemotron","nemotron"]}`. Every test in `tests` must also be in `files`. ALWAYS dry-run before launching: `uv run python scripts/source/fix_loop_stable.py --job <job> --dry-run` and read its first line.
3. **Run:** `uv run python scripts/source/fix_loop_stable.py --job _loop/jobs/<name>.json` (the `_stable` copy is the unpatched loop so a half-edited `fix_loop.py` can never break jobs). Result: `_loop/<job>/status.json` (`running | passed | passed-no-review | escalate | failed`). `passed-no-review` = tests passed and the reviewers have not run.
4. pytest runs; real failures go back to Nemotron; up to 3 rounds; then it restores the original files and writes `ESCALATE.md`.
5. A spec that asks for a full rewrite plus fixtures in one reply fails (a 54 KB reply was dropped). Split into stages, each passing before the next (example: D4 -> wpD4a/b/c).

## 6. Files and tools
- Shared loop tools: `scripts/source/fix_loop.py` (do not edit casually), `scripts/source/fix_loop_stable.py` (unpatched copy used for every launch), `coder_run.py`, `nemotron_code.py` (parser; refuses any file that mentions 3D animation software), `review_run.py`, `codex_review.py`.
- Research code: `research/pieces/<module>.py` + `test_<module>.py` (20 pieces A1..F4, plus G1/G2). Specs `docs/pilot/nemotron_specs/research_<id>.md`; jobs `_loop/jobs/research_<id>.json`; results `_loop/research_<id>/`; reviews `_loop/reviews/` (`combined_<id>.md`, `sonnet_med_*.md`, flags).
- Ops scripts (`D:\aai work\animation_research_tool\_loop`): `wave_loop.py` (the loop), `bulk_review.py` (Codex + Haiku bulk reviewer), `apply_review.py` (add findings to a spec and relaunch the job), `check_all.py` (one-call table: job state + each piece's own pytest), `luna_review.py` (older single-piece reviewer).
- Older design, kept but NOT running: `research/pieces/g1_autoloop.py` + `g2_autoloop_cli.py` (73 tests pass). One piece at a time, so replaced by the wave loop. If ever used: start it with system Python, never `uv run`, and move a stale `_loop/autoloop_state.json` aside.
- Records: `_loop/PAUSED.md` (what is paused and why), `animation_research_tool/CHECKLIST_MASTER.md` (status snapshot: code-verified results first, reviewer opinions separate).

## 7. Supervision routine (few Claude tokens)
Every 8-10 minutes: tail `_loop/wave_run.log`, run `check_all.py`, read `_loop/wave_state.json`, look for `NEEDS_CLAUDE_*.flag` and `escalate` jobs. Restart the loop if its process died. Never read full coder replies or the code.

## 8. Lessons that cost hours (do not repeat)
- No fenced FILE format line = no files parsed = escalation. Default `fixers` includes Codex = empty replies: set Nemotron x3.
- Starting scripts with `uv run` puts them in the repo venv: reviewers that need `requests` then fail instantly and the loop does nothing. Use system Python and CHECK that child reviewer processes really run.
- A broken f-string once sent literal `{spec}` to the coder and it overwrote working code in 17 pieces: test any prompt/loop change on ONE piece first and keep a backup.
- `codex.cmd` (not `codex`) from Python on Windows. A job whose `tests` list names a file not in `files` is rejected at once.
- No second job on the same files while one runs; one merged review pass per piece.
- Reviewers can contradict a spec: the spec's REVIEWER DECISIONS section is binding and the supervisor settles conflicts in writing.

## 9. Status words
`DONE` = code-verified (tests green and latest reviews clean). `BUILT` = exists, not final. `OPEN` = not done. Reviewer opinions never count as DONE.

## 10. State at 19:40
- Wave loop running on 19 pieces (D4 excluded). Clean by reviewer opinion: A1, B2, C1, C3. Findings applied to 15 pieces; fix jobs running. 18 of 20 pieces pass their own tests at the last check (A2 and E3 mid-fix).
- Paused on purpose: D4 stages b and c (`_loop/d4_chain.py`), the `fix_loop.py` retry patch (job `fixloop_retry`; shared `fix_loop.py` and `tests/test_fix_loop.py` were restored to a 16:07 snapshot with 5 of 61 tests failing that pre-existed).
- Not done: integration/early smoke test, 1-2 reels (owner's go to download), Stage 1/2 compatibility check, one semantic audit of a reference video with audio (owner picks), final report. A real Kimi comparison needs the owner's approval.
