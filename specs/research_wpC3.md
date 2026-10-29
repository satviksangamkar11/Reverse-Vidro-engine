
# WP-C3: Result Recording, Coverage Accounting & Pattern Analysis
# Functions for validating review reports, updating event dispositions, computing coverage, and summarizing cluster patterns.

## Data Shapes
# State: dict mapping event_id -> {"disposition": str, "verdict": str|None, "evidence_frames": list[int], "counterexample": str, "artwork_needed": str, "basis_event_ids": list[str]|None}
# Report (input to record_result):
#   {"verdict": str, "evidence_frames": list[int], "counterexample": str, "artwork_needed": str}
# Valid verdicts: "POSE_SWAP","CAMERA_MOVE","ARTICULATION","LAYER_MOVE","EFFECT","NOT_MOTION","UNKNOWN"
# Coverage Result:
#   {"status": "ok", "counts": dict[str,int], "unaccounted": int}
# Patterns Result:
#   {"status": "ok", "patterns": list[dict]}  # per cluster: {"cluster_id": str, "verdict_distribution": dict[str,int], "when_it_fails": list[str]}

## Public Functions (≤3)

### 1. record_result(state, event_id, report) -> dict
# Validates report keys and verdict. If valid: updates state[event_id] with disposition="REVIEWED", verdict, evidence_frames, counterexample, artwork_needed, basis_event_ids=None. Returns {"status": "ok", "event_id": str}.
# If invalid (missing keys, bad verdict, evidence_frames not list of ints): state[event_id] stays/becomes PENDING_REVIEW with reason in "error" field (or disposition="PENDING_REVIEW" and add error). Returns {"status": "error", "event_id": str, "reason": str}.
# state is mutated in place.

# WORKED EXAMPLE
# Input:
state_ex = {"e1": {"disposition": "PENDING_REVIEW"}}
event_id_ex = "e1"
report_ex = {"verdict": "POSE_SWAP", "evidence_frames": [5, 10], "counterexample": "none", "artwork_needed": "mask"}
# Output:
# {"status": "ok", "event_id": "e1"}
# state_ex becomes: {"e1": {"disposition": "REVIEWED", "verdict": "POSE_SWAP", "evidence_frames": [5,10], "counterexample": "none", "artwork_needed": "mask", "basis_event_ids": None}}

# Invalid example:
report_bad = {"verdict": "INVALID", "evidence_frames": [5], "counterexample": "", "artwork_needed": ""}
# Output: {"status": "error", "event_id": "e1", "reason": "invalid verdict"}
# state_ex["e1"]["disposition"] = "PENDING_REVIEW" (unchanged), maybe add "error": "invalid verdict"

### 2. coverage(state, events) -> dict
# Counts events per disposition value in state (keys: REVIEWED, INFERRED_FROM_CLUSTER, PENDING_REVIEW, etc.).
# unaccounted = number of events in `events` list missing from state OR with disposition not in known set (REVIEWED, INFERRED_FROM_CLUSTER, PENDING_REVIEW).
# Returns: {"status": "ok", "counts": {"REVIEWED": int, "INFERRED_FROM_CLUSTER": int, "PENDING_REVIEW": int, ...}, "unaccounted": int}

# WORKED EXAMPLE
# Input:
state_ex = {
    "e1": {"disposition": "REVIEWED"},
    "e2": {"disposition": "INFERRED_FROM_CLUSTER"},
    "e3": {"disposition": "PENDING_REVIEW"},
}
events_ex = [{"event_id": "e1"}, {"event_id": "e2"}, {"event_id": "e3"}, {"event_id": "e4"}]
# Output:
# {"status": "ok", "counts": {"REVIEWED": 1, "INFERRED_FROM_CLUSTER": 1, "PENDING_REVIEW": 1}, "unaccounted": 1}  # e4 missing

### 3. assert_complete(state, events) -> dict
# Calls coverage. If unaccounted > 0 OR any event has disposition "PENDING_REVIEW": raises AssertionError with message.
# Returns: {"status": "ok"} if complete.

# WORKED EXAMPLE
# Input (complete):
state_ok = {"e1": {"disposition": "REVIEWED"}, "e2": {"disposition": "INFERRED_FROM_CLUSTER"}}
events_ok = [{"event_id": "e1"}, {"event_id": "e2"}]
# Output: {"status": "ok"} (no raise)

# Input (incomplete):
state_bad = {"e1": {"disposition": "PENDING_REVIEW"}}
events_bad = [{"event_id": "e1"}]
# Raises AssertionError("Incomplete: 1 PENDING_REVIEW, 0 unaccounted")

### 4. patterns_and_exceptions(state, clusters) -> dict
# For each cluster: collect verdicts of REVIEWED members (state[event_id]["verdict"]).
# verdict_distribution: dict verdict->count.
# when_it_fails: list of counterexample strings from REVIEWED members where verdict != "NOT_MOTION" (or all? spec: "when_it_fails list from counterexamples"). Use all counterexamples from reviewed members.
# Returns: {"status": "ok", "patterns": [{"cluster_id": str, "verdict_distribution": dict, "when_it_fails": list[str]}]}

# WORKED EXAMPLE
# Input:
state_ex = {
    "e1": {"disposition": "REVIEWED", "verdict": "POSE_SWAP", "counterexample": "occlusion"},
    "e2": {"disposition": "REVIEWED", "verdict": "POSE_SWAP", "counterexample": "fast_motion"},
    "e3": {"disposition": "INFERRED_FROM_CLUSTER"},
}
clusters_ex = [{"cluster_id": "C_A", "members": ["e1","e2","e3"]}]
# Output:
# {"status": "ok", "patterns": [{"cluster_id": "C_A", "verdict_distribution": {"POSE_SWAP": 2}, "when_it_fails": ["occlusion", "fast_motion"]}]}


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/c3_state.py; test file: research/pieces/test_c3_state.py (tests import the module by its plain file name, e.g. `from c3_state import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpC3
LUNA (gpt-6-luna high):
MED - research/pieces/test_c3_state.py:4 - tests require third-party pytest despite the stdlib-only hard rule - use unittest’s assertRaises instead

SONNET (latest):
wpC3 (c3_state.py)
- LOW - c3_state.py:78-83 - invalid report on an already REVIEWED/INFERRED event flips to PENDING_REVIEW but keeps stale verdict/evidence_frames/basis_event_ids - clear them or document.
- LOW - c3_state.py:37,99 - non-dict report or non-dict state record raises AttributeError instead of status error.
- LOW - c3_state.py:108-112 - `event_ids` computed in coverage() is dead code.
- LOW - test_c3_state.py - no test for bool frames rejected, non-dict report, or invalid report on a previously REVIEWED event.
Verdict: PASS (every spec bullet implemented, worked examples match, tests exercise them).


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpC3
LUNA (gpt-6-luna medium):
MED - research/pieces/c3_state.py:100-106 - `coverage()` counts dispositions from every entry in `state`, including events absent from the `events` argument, so its counts can include unrelated records - count dispositions only for event IDs present in `events.


HAIKU (low, stand-in):
Summary

- wpC1: FAIL (HIGH 0, MED 2)
- wpC2: FAIL (HIGH 0, MED 2)
- wpC3: PASS (HIGH 0, MED 0)

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/c3_state.py
```python
<complete module source>
```
FILE: research/pieces/test_c3_state.py
```python
<complete test source>
```
