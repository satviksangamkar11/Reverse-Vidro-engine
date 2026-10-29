# SPEC G4: FIX `research/pieces/g1_autoloop.py` and `research/pieces/g2_autoloop_cli.py` (+ their two test files): the real auto loop crashes with `KeyError: 'sleep'`

OBSERVED BUG on the real repo: `uv run python research/pieces/g2_autoloop_cli.py --ids wpA1 wpA2` ran one cycle and then died with `KeyError: 'sleep'` at `deps["sleep"](sleep_s)` in `run_cycles`, because `build_deps(...)` in g2 never puts a "sleep" callable into the deps dict (the tests used a fake deps dict that already had it).

CHANGES:
1. g2 `build_deps(repo, tools, runner, reviews_dir, sleep=time.sleep)` returns a deps dict containing ALL keys that run_cycles uses: get_state, relaunch, run_reviewers, apply_findings, escalate, sleep. `main` passes its own `sleep` through; the default is `time.sleep`.
2. g1 `run_cycles` validates up front that `deps` has every required key and raises ValueError("missing deps: <sorted names>") BEFORE doing any work or sleeping.
3. A piece's escalation counter (stored in `_loop/autoloop_state.json`) must be reset to 0 when its job state is "passed" or "passed-no-review" and tests are green (a successful run), so an old escalation count can never mark a healthy piece STUCK. Add this to g2 `get_state`/the state update path and test it with a tmp state file that starts with {"wpX": {"escalations": 4}}.
4. NEW TESTS (real wiring, fake runner, tmp dirs, no real subprocess): (a) `run_cycles(["wpA1"], build_deps(...), max_cycles=1)` with a fake runner and a recording fake sleep completes and calls sleep once with the given seconds; (b) a deps dict missing "sleep" raises ValueError naming it, with no runner call and no sleep; (c) the stale escalations=4 state file case above ends as non-STUCK; (d) all currently passing tests still pass.

HARD RULES: stdlib only; no network; no absolute drive paths; keep every public function and all current tests passing (change an old test only where it asserts the old wrong behaviour). The reply must contain ALL FOUR files complete.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these four blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/g1_autoloop.py
```python
<complete module source>
```
FILE: research/pieces/test_g1_autoloop.py
```python
<complete test source>
```
FILE: research/pieces/g2_autoloop_cli.py
```python
<complete module source>
```
FILE: research/pieces/test_g2_autoloop_cli.py
```python
<complete test source>
```
