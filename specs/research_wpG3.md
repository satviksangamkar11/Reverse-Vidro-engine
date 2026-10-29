# SPEC G3: FIX `research/pieces/g1_autoloop.py` and `research/pieces/g2_autoloop_cli.py` (+ their two test files) so the autonomous cycle matches REAL fix_loop states

OBSERVED BUG (reproduced on the real repo): `uv run python research/pieces/g2_autoloop_cli.py --dry-run` prints {"action": "REVIEW"} for ALL 20 pieces. It must not: wpD4 has no job directory and 2 failing tests (expected RELAUNCH), wpD2 has a RUNNING job (expected WAIT), pieces with job "passed-no-review" and green tests that have no current review (expected REVIEW), pieces with job "escalate" (expected ESCALATE).

REAL status.json states written by fix_loop (the only ones that exist): "running", "passed", "passed-no-review", "escalate", "failed". A missing status.json / missing job directory = "missing". `passed-no-review` means the coder finished and the tests passed; it is NOT a review verdict.

REQUIRED BEHAVIOUR for `decide(state)` (keep the priority order WAIT, RELAUNCH, ESCALATE, FIX_TESTS, REVIEW, APPLY, DONE):
1. job == "running" -> WAIT.
2. job in ("missing", "failed") -> RELAUNCH.
3. job == "escalate" -> ESCALATE.
4. job in ("passed", "passed-no-review") and tests_green False -> FIX_TESTS.
5. tests_green True and (last_review is None or changed_since_review) -> REVIEW.
6. tests_green True, review current, any reviewer FINDINGS -> APPLY.
7. tests_green True, review current, no FINDINGS, at least one PASS -> DONE; all NO_REVIEW -> REVIEW.
Normalise the job string to lower-case/stripped; an UNKNOWN job string must raise ValueError (never silently default to REVIEW).

`get_state` in g2 must set `job` from status.json "state" exactly as above and must NOT default `changed_since_review` to True when the module/test file mtime is older than the stored review time; with no stored review, last_review is None.

`--dry-run` must print for each piece the state it read (job, tests_green) next to the action, as one JSON object: {"wpD4": {"job": "missing", "tests_green": false, "action": "RELAUNCH"}, ...}.

NEW TESTS (use real-shaped data, tmp dirs, fake runner; no real subprocess): a table-driven test covering every (job, tests_green, review) combination above; a test that writes tmp status.json files with each real state and checks get_state + decide end to end; the exact D4/D2 scenarios from the observed bug; unknown job string raises ValueError.

HARD RULES: stdlib only; no network; no absolute drive paths; keep every existing public function and all currently passing tests passing (update an existing test ONLY where it asserts the old wrong behaviour, and keep it meaningful). The reply must contain ALL FOUR files complete.

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
