"""Ops script: owner asked (2026-10-29) to update SATVIK_NVIDIA_SYSTEM.md with the current system. Replaces the section '## Satvik NVIDIA System' to the end."""
from pathlib import Path
p = Path(r"D:\aai work\granthstudio\docs\pilot\SATVIK_NVIDIA_SYSTEM.md")
t = p.read_text(encoding="utf-8")
i = t.index("## Satvik NVIDIA System (named 2026-10-29)")
new = """## Satvik NVIDIA System (current, updated 2026-10-29 15:45)
The owner's NVIDIA-first fix loop. Claude writes only short specs and runs scripts; NVIDIA's free model writes all code and tests; a script loops until the tests pass. Claude writes no code.

### Hard rules
No Kimi, no ElevenLabs, no Haiku, no Opus. No paid action without the owner's go. Never print or read API keys. Do not edit this doc unless the owner asks. Instagram links are only recorded, never downloaded, until the owner says run.

### Steps
1. **Spec:** one `.md` per piece in `docs/pilot/nemotron_specs/`. It must end with the FORMAT line: reply with only `FILE: <path>` blocks, each followed by a fenced ```python block. Without fences the parser finds no files.
2. **Job file:** `_loop/jobs/<name>.json` (spec path, module + test paths, `max_rounds` 3, `review` false).
3. **Coder:** Nemotron 3 Ultra 550B (`nvidia/nemotron-3-ultra-550b-a55b`), free NVIDIA endpoint, 14 keys. It is the only coder.
4. **Test:** `fix_loop.py` runs pytest. On failure the real pytest output goes back to the coder, up to 3 fix rounds.
5. **Escalate:** after 3 failed rounds the job stops, restores the original files and writes `ESCALATE.md`. A **Sonnet 5.5 medium** reviewer (Claude subagent, read-only) diagnoses it; the diagnosis goes into the spec and the job reruns, then the loop continues.
6. **Run:** `uv run python scripts/source/fix_loop.py --job _loop/jobs/<name>.json`. Result: `_loop/<job>/status.json` (running, passed-no-review, escalate, failed).

### Reviewers (after the tests pass, in this order)
1. **Codex Luna:** `gpt-6-luna`, **medium** effort, read-only: `codex.cmd exec -m gpt-6-luna -c model_reasoning_effort=medium --sandbox read-only --skip-git-repo-check -` (prompt on stdin; on Windows use `codex.cmd`, plain `codex` fails from Python).
2. **GLM 5.3 Flash** (`z-ai/glm-5.3-flash`) and **MiniMax M3.1 Flash** (`minimaxai/minimax-m3.1-flash`) via NVIDIA, thinking off, 240 s deadline.
3. **Sonnet 5.5 medium:** Claude subagent, read-only, writes a report file.
Findings from all reviewers are merged into the spec as REVIEW FINDINGS, Ultra fixes them in one pass, and the job reruns. An empty, timed-out or errored reviewer reply is NO_REVIEW (neither pass nor fail). Done = tests green and the latest reviews have no HIGH/MED defects.

### Tools (in `D:\\aai work\\animation_research_tool\\_loop`)
`check_all.py` (one-call status table), `luna_review.py <ids>` (Luna + GLM + MiniMax, writes `_loop/reviews/combined_<id>.md`), `apply_review.py <report> <id>` (adds findings to the spec and relaunches the job).

### Routine
Check every 15 minutes with the one-call table; read only status.json and ESCALATE.md, never full coder replies or code. Keep code-verified results and reviewer opinions separate in the checklist.
"""
p.write_text(t[:i] + new, encoding="utf-8")
print("system doc updated")
