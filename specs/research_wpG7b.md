# SPEC G7b: PATCH `research/pieces/g2_autoloop_cli.py` (+ `test_g2_autoloop_cli.py`): reuse a fresh review instead of re-running it

PROBLEM: reviews can be produced in bulk by another tool, which writes `_loop/reviews/combined_<id>.md` (headings `LUNA (gpt-6-luna medium):`, `GLM 5.3 Flash:`, `MiniMax M3.1 Flash:`, `HAIKU (low, stand-in):`; only reviewers WITH findings appear; a file with just the heading `## <id>` means no findings). The loop must not re-run a review that is already fresh.

CHANGE (g2 only; g1 is NOT changed):
1. In `build_deps(...)`, `run_reviewers(id)` first checks `<reviews_dir>/combined_<id>.md`. It is FRESH when it exists and its mtime is newer than BOTH `research/pieces/<module>.py` and `research/pieces/test_<module>.py` (module from MODULE_OF). If fresh, parse it WITHOUT calling the runner: return {"luna": text, "glm": text, "minimax": text, "haiku": text} where a reviewer with a heading section gets its text, and a reviewer without one gets "PASS" (file exists and is fresh, so absence means no findings). If not fresh or missing, behave exactly as today (call luna_review.py through the runner).
2. g1's `merge_findings` already orders Luna, GLM, MiniMax then others alphabetically; the extra "haiku" key must therefore flow through unchanged (check build_deps passes it on; do not edit g1).
3. NEW TESTS (tmp dirs, fake runner recording argv, os.utime to control mtimes): (a) fresh combined file -> runner NOT called, sections parsed, missing reviewer -> "PASS", haiku section parsed; (b) combined file older than the module or the test file -> runner called as before; (c) missing combined file -> runner called; (d) a heading-only fresh file -> all reviewers "PASS"; (e) all existing tests keep passing.

HARD RULES: stdlib only; no network; no absolute drive paths; keep every public function and signature and every currently passing test. The reply must contain BOTH files complete.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/g2_autoloop_cli.py
```python
<complete module source>
```
FILE: research/pieces/test_g2_autoloop_cli.py
```python
<complete test source>
```
