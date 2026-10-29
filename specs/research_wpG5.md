# SPEC G5: FIX `research/pieces/test_g2_autoloop_cli.py` (ONE file, tests only; the code in g1_autoloop.py and g2_autoloop_cli.py is correct and must NOT be changed)

The module g2_autoloop_cli.py now supports `build_deps(repo, tools, runner, reviews_dir, sleep=time.sleep)` and returns all six deps (get_state, relaunch, run_reviewers, apply_findings, escalate, sleep). Two newly added tests are wrong:

1. `test_end_to_end_run_cycles_with_build_deps_calls_sleep` (and one more test near line 817-854) fail with `NameError: name 'run_cycles' is not defined`: add the missing import at the top of the test file: `from g1_autoloop import run_cycles` (the test file already inserts research/pieces on sys.path the same way for the other g1 imports; follow that pattern).
2. `test_escalation_reset_on_passed_and_green_tests` fails with `KeyError: 'wpX'` because `wpX` is not in MODULE_OF. Use a REAL id from MODULE_OF such as "wpA1" (module a1_queue) everywhere that test uses "wpX", including its tmp state file and status.json folder name.

Keep every other test exactly as it is. Do not weaken or delete any test. All tests in the file must pass: run mentally against the current module.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY this one block, no other text: the line `FILE: research/pieces/test_g2_autoloop_cli.py` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/test_g2_autoloop_cli.py
```python
<complete test source>
```
