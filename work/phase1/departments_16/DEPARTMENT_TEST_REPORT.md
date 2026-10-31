# Department test report (2026-10-31)

Full engine suite (pieces/), run in this pass: 1914 passed, 1 skipped, 1 failed, 26 subtests passed. The failure was the spec-lint check on phase1_loop_lifecycle.md (missing REAL FACTS heading). That heading was added in this pass; the suite must be re-run to confirm the result.

Module tests run in this pass:
- Matrix: 23 passed (test_d16_matrix.py and test_d16_matrix_extra.py).
- Granth: 12 passed, 1 skipped (test_symlink_target_refused, UNVERIFIED on this Windows system).
- Teacher: 24 passed.
- Media: 18 passed. These tests do NOT reach the caption branch that the review found broken (undefined AI_VERIFY_LABEL), so a pass here does not mean media is correct.
- Finding lifecycle (set aside, not wired): 14 passed.
- Loop review and judge tests (fix_loop): 79 passed, after the judge-READY fix.

Test gaps still open:
- Media: the caption branch is untested; protected-row status fields are not checked; invalid UTF-8 gap handling is untested.
- Teacher: the lesson-count and event-key checks were added in this pass.
- Matrix: a few LOW notes (mapping and capability copying) are logged.

Frozen tests: no frozen test was edited by the supervisor. A media test diff from the coder is recorded in _loop/d16_media/test_edits and needs sign-off.
