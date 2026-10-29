# SPEC G6: ADD `--state-file` to `research/pieces/g2_autoloop_cli.py` (+ `test_g2_autoloop_cli.py`) so several auto loops can run in parallel without sharing state

PROBLEM: the auto loop keeps its per-piece state (last_review, changed_since_review, escalations) in the fixed file `<repo>/_loop/autoloop_state.json`. Two loop processes on different pieces would overwrite each other's entries. We want to run 4 loops in parallel, each on its own group of pieces.

CHANGES (g2 only; g1 is NOT changed):
1. `build_deps(repo, tools, runner, reviews_dir, sleep=time.sleep, state_path=None)`: all reads and writes of the autoloop state use `state_path` when given, else the existing default `<repo>/_loop/autoloop_state.json`. Atomic tmp+replace write, utf-8, corrupt file -> ValueError (unchanged behaviour).
2. `main(argv, ...)`: new optional argument `--state-file PATH` (default None) passed to build_deps as state_path. With --dry-run it is only read.
3. Two loops with different state files must never touch each other's file: test this with two tmp state files and fake runners (one piece each) and assert each file contains only its own piece.
4. NEW TESTS (tmp dirs, fake runner, no subprocess, no network): (a) custom state_path is used for read and write and the default file is NOT created; (b) default path behaviour unchanged when state_path is None; (c) `main` parses `--state-file`; (d) the two-loop isolation test above. All existing tests must keep passing.

HARD RULES: stdlib only; no absolute drive paths in code or tests; keep every public function and every currently passing test. The reply must contain BOTH files complete.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/g2_autoloop_cli.py
```python
<complete module source>
```
FILE: research/pieces/test_g2_autoloop_cli.py
```python
<complete test source>
```
