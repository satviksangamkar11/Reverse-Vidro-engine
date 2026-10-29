# SPEC: NEW `research/pieces/g1_autoloop.py` + NEW `research/pieces/test_g1_autoloop.py` (autonomous review/fix cycle, pure logic with injected callables; no network, no model calls, no Kimi)

Goal: replace the manual supervision of the Satvik NVIDIA System. The coder (Nemotron Ultra) and the fix loop already exist; this module only decides the next action per piece and runs cycles through INJECTED functions so it is fully testable offline.

Piece state dict: {"id": str, "job": "running"|"passed"|"passed-no-review"|"escalate"|"failed"|"missing", "tests_green": bool, "changed_since_review": bool, "last_review": {"luna": "PASS"|"FINDINGS"|"NO_REVIEW", "glm": same, "minimax": same} or None, "findings_text": str, "escalations": int}

1. `decide(state)` returns one of "WAIT" (job running), "RELAUNCH" (job missing or failed), "ESCALATE" (job == "escalate"), "FIX_TESTS" (job passed but tests_green False), "REVIEW" (tests_green and (last_review is None or changed_since_review)), "APPLY" (tests_green, review current, and at least one reviewer verdict is FINDINGS), "DONE" (tests_green, review current, no FINDINGS, and at least ONE reviewer returned PASS; if all three are NO_REVIEW the result is "REVIEW" again, because NO_REVIEW is neither pass nor fail). Priority order: WAIT, RELAUNCH, ESCALATE, FIX_TESTS, REVIEW, APPLY, DONE.
2. `merge_findings(reviews, minimum_len=20)` takes a dict reviewer-name -> text. Returns one string with a `NAME:` heading per reviewer whose text is not "NO_REVIEW" and not a reply starting with PASS and has at least `minimum_len` characters; reviewers are ordered Luna first, then GLM, then MiniMax, then others alphabetically. Returns "" if nothing qualifies. Never drops a HIGH/MED line.
3. `run_cycles(ids, deps, max_cycles=50, sleep_s=60)` where `deps` is a dict of callables: `get_state(id)->state dict`, `relaunch(id)`, `run_reviewers(id)->dict reviewer->text`, `apply_findings(id, text)`, `escalate(id)`, `sleep(seconds)`. Each cycle visits every id not yet DONE, calls decide(), performs the matching action once (RELAUNCH->relaunch, ESCALATE->escalate with the per-piece escalation counter incremented, REVIEW->run_reviewers then stores reviews, APPLY->apply_findings(merge_findings(...)), FIX_TESTS->relaunch, WAIT and DONE do nothing), then calls deps["sleep"](sleep_s) once per cycle. A piece escalated more than 2 times is marked "STUCK" (no more actions, reported). Stops when all pieces are DONE or STUCK or max_cycles reached. Returns {"done": [ids], "stuck": [ids], "cycles": n, "log": [(cycle, id, action)]}. Exceptions raised by a dep for one piece are caught, logged as (cycle, id, "ERROR:<type>") and never stop the other pieces.

Tests (unittest/pytest, tmp dirs only, pure fakes): every decide() branch and its priority; NO_REVIEW from all three reviewers -> REVIEW again; one PASS and two NO_REVIEW -> DONE; merge_findings ordering, NO_REVIEW/PASS filtering, empty result; run_cycles finishing, STUCK after 3 escalations, an exception in one piece not stopping others, max_cycles bound, sleep called once per cycle with the given seconds.

HARD RULES: pure Python stdlib; no network; no absolute drive paths; do not import other pieces. Module file: research/pieces/g1_autoloop.py; test file: research/pieces/test_g1_autoloop.py (tests import `from g1_autoloop import ...`).

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/g1_autoloop.py
```python
<complete module source>
```
FILE: research/pieces/test_g1_autoloop.py
```python
<complete test source>
```
