# SPEC G7a: PATCH `research/pieces/g1_autoloop.py` (+ `test_g1_autoloop.py`): apply findings in the SAME visit as the review

PROBLEM: `run_cycles` performs ONE action per piece per cycle. So a piece is reviewed in cycle 1 and its findings are applied only in cycle 2, after all other pieces were reviewed (about 95 minutes later). Fix jobs should start right after the review.

CHANGE (g1 only): in `run_cycles`, after a REVIEW action completes for a piece, re-evaluate `decide()` on the updated state inside the SAME visit; if the new action is APPLY, perform it immediately (log it as a second entry (cycle, id, "APPLY") in the log). At most TWO actions per piece per visit (REVIEW then APPLY); never loop further; WAIT and DONE still do nothing. All other behaviour, return shape, STUCK rule, exception handling per piece and the sleep call (once per cycle) stay exactly as they are.

NEW TESTS (pure fakes, no subprocess): (a) a REVIEW whose reviewers return FINDINGS is followed by exactly one APPLY in the same cycle with the merged text passed to apply_findings; (b) a REVIEW with all PASS is followed by no APPLY (piece becomes DONE next cycle as before); (c) a REVIEW with all NO_REVIEW is NOT followed by APPLY; (d) at most two actions per piece per cycle even if decide() would keep returning APPLY; (e) an exception in apply_findings is logged for that piece and does not stop others; (f) all existing tests keep passing (change one only where it asserts the old one-action-per-visit behaviour, and keep it meaningful).

HARD RULES: stdlib only; no network; no absolute drive paths; keep every public function and signature. The reply must contain BOTH files complete.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/g1_autoloop.py
```python
<complete module source>
```
FILE: research/pieces/test_g1_autoloop.py
```python
<complete test source>
```
