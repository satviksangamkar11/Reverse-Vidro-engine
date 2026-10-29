
# WP-C1: Event Clustering & Representative Selection
# Pure functions for grouping motion windows into similarity clusters and picking representative events for review.

## Data Shapes
# Event (from cinematic_analysis.analyze_source):
#   {"event_id": str, "shot": str, "start_frame": int, "end_frame": int,
#    "score": float, "uncertain": bool, "burst_frames": list[int], "disposition": str}
# Feature (optional per-event dict):
#   {"event_id": str, "mean_residual": float, "peak_residual": float,
#    "direction_hint": str, "region": str}
# Cluster:
#   {"cluster_id": str, "members": list[str], "signature": dict}
# Representative pick result:
#   {"best": str|None, "ambiguous": str|None, "failure": str|None}

## Public Functions (≤3)

### 1. cluster_windows(events, features=None) -> dict
# Groups every event into exactly one cluster by (shot-independent) similarity bands.
# Bands:
#   score_band: floor(score * 10) / 10  (0.0, 0.1, ..., 1.0)
#   duration_band: floor(duration_sec * 2) / 2  where duration_sec = (end_frame - start_frame) / 30.0
#   residual_band: floor(mean_residual * 10) / 10  (0.0 if missing)
#   direction_hint: feature["direction_hint"] or "none"
#   region: feature["region"] or "none"
# Cluster key = (score_band, duration_band, residual_band, direction_hint, region)
# cluster_id = "C_" + "_".join(str(k) for k in key)
# signature = {"score_band":..., "duration_band":..., "residual_band":..., "direction_hint":..., "region":...}
# Returns: {"status": "ok", "clusters": list[Cluster]}

# WORKED EXAMPLE
# Input:
events_ex = [
    {"event_id": "e1", "shot": "s1", "start_frame": 0, "end_frame": 30, "score": 0.92, "uncertain": False, "burst_frames": [0,15,30], "disposition": "PENDING_REVIEW"},
    {"event_id": "e2", "shot": "s1", "start_frame": 60, "end_frame": 90, "score": 0.88, "uncertain": True, "burst_frames": [60,75,90], "disposition": "PENDING_REVIEW"},
    {"event_id": "e3", "shot": "s2", "start_frame": 0, "end_frame": 15, "score": 0.45, "uncertain": False, "burst_frames": [0,7,15], "disposition": "PENDING_REVIEW"},
]
features_ex = [
    {"event_id": "e1", "mean_residual": 0.12, "peak_residual": 0.3, "direction_hint": "left", "region": "upper"},
    {"event_id": "e2", "mean_residual": 0.15, "peak_residual": 0.4, "direction_hint": "left", "region": "upper"},
    {"event_id": "e3", "mean_residual": 0.05, "peak_residual": 0.2, "direction_hint": "right", "region": "lower"},
]
# Output:
# {
#   "status": "ok",
#   "clusters": [
#     {"cluster_id": "C_0.9_1.0_0.1_left_upper", "members": ["e1","e2"], "signature": {"score_band":0.9,"duration_band":1.0,"residual_band":0.1,"direction_hint":"left","region":"upper"}},
#     {"cluster_id": "C_0.4_0.5_0.0_right_lower", "members": ["e3"], "signature": {"score_band":0.4,"duration_band":0.5,"residual_band":0.0,"direction_hint":"right","region":"lower"}}
#   ]
# }

### 2. pick_representatives(cluster, events) -> dict
# Selects up to 3 distinct event_ids from cluster["members"] using the full events list for metadata.
# Criteria (distinct ids, priority order):
#   best: highest score
#   ambiguous: uncertain=True, else score nearest 0.5 (tie-break: lower event_id)
#   failure: lowest score
# Returns: {"status": "ok", "representatives": {"best": str|None, "ambiguous": str|None, "failure": str|None}}

# WORKED EXAMPLE
# Input:
cluster_ex = {"cluster_id": "C_0.9_1.0_0.1_left_upper", "members": ["e1","e2"], "signature": {}}
events_ex2 = [
    {"event_id": "e1", "score": 0.92, "uncertain": False},
    {"event_id": "e2", "score": 0.88, "uncertain": True},
]
# Output:
# {"status": "ok", "representatives": {"best": "e1", "ambiguous": "e2", "failure": "e2"}}

### 3. fps_for(event) -> dict
# Determines re-extraction frame rate for an event.
# Rules: 8 fps if uncertain OR duration<0.5s OR score>=0.8 else 4 fps.
# duration_sec = (end_frame - start_frame) / 30.0
# Returns: {"status": "ok", "fps": int}

# WORKED EXAMPLE
# Input:
event_ex = {"event_id": "e1", "start_frame": 0, "end_frame": 30, "score": 0.92, "uncertain": False}
# duration = 1.0s, score>=0.8 -> 8 fps
# Output: {"status": "ok", "fps": 8}

# Input 2:
event_ex2 = {"event_id": "e3", "start_frame": 0, "end_frame": 15, "score": 0.45, "uncertain": False}
# duration = 0.5s, score<0.8, not uncertain -> 4 fps
# Output: {"status": "ok", "fps": 4}


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/c1_cluster.py; test file: research/pieces/test_c1_cluster.py (tests import the module by its plain file name, e.g. `from c1_cluster import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpC1

Rounds 0-1 were real Nemotron fix attempts (status 200, tests failed). Rounds 2-3 (codex) were API failures (status=0, empty), so no fixer ever ran on the final state. The spec has no REVIEWER DECISIONS section.

Root cause: the spec contradicts itself, and the test file is corrupted.
- The formula says score_band = floor(score*10)/10, but the worked example puts e2 (0.88) in band 0.9 with e1. Floor gives 0.8, so the example only holds with rounding. The module uses round(), which matches the example. The module also fixes pick_representatives to allow duplicates and fps_for to default a missing end_frame, both per the examples.
- test_c1_cluster.py is garbage. It holds only 2 tests, and from line 62 to the end it is Nemotron's leaked reasoning as comments, ending in a stray "FILE:" line. The ~26 tests the model mentioned are gone. test_clustering_without_features still expects the old floor outcome (2 clusters, bands {0.9, 0.8}). Under the worked example, 0.92 and 0.88 share a band, so that test is wrong and the module is right.

Verdict: TEST wrong, plus one CODE bug.
- Code bug: _round_to_step multiplies by 0.1, so score 0.3 gives cluster_id "C_0.30000000000000004_...". The floor helper has the same float problem (0.3/0.1 floors to 2, not 3). Fix: compute the rounded or floored integer, then divide by 10 or 2, not multiply by 0.1. Keep round() for score, so 0.45 gives 0.4 as in the example, and floor for duration and residual.
- Test fix: rewrite the whole file with no comments. Required tests:
  - The cluster worked example: ids, signatures and member order.
  - No features: one cluster with "none_none".
  - Empty events, and an event with no id being skipped.
  - Clean float ids for score 0.3 and residual 0.3.
  - Duration bands at 14 and 15 frames.
  - pick_representatives worked example: best e1, ambiguous e2, failure e2.
  - No uncertain event: nearest 0.5 with a lower-id tie-break.
  - Empty members give all None.
  - A single member gives the same id three times.
  - fps_for: both worked examples, score exactly 0.8, 14 frames giving 8, uncertain giving 8.


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpC1
LUNA (gpt-6-luna medium):
HIGH - research/pieces/c1_cluster.py:11 - `cluster_windows` uses banker’s rounding for `score_band`, but the spec requires `floor(score * 10) / 10`; for example, score `0.88` belongs in band `0.8`, not `0.9` - use the specified floor formula and update the worked-example expectations accordingly.


HAIKU (low, stand-in for GLM/MiniMax):
wpC1
Result: MED 1 (HIGH 0)
- MED - research/pieces/test_c1_cluster.py:162-171 (test_pick_representatives_no_uncertain_nearest_half, lines 135-146) - the tie-break case is not a real tie: abs(0.4-0.5) and abs(0.6-0.5) differ in floating point, so the lower-id rule is never exercised and a regression in dist_to_half tie-break would still pass - use two members with exactly equal distance (e.g. 0.25 and 0.75) and assert the lower event_id wins.
- LOW - research/pieces/test_c1_cluster.py:81-91 - the required "cluster worked example" check compares member sets, not member order - assert list order if order is part of the contract.
- Verified fixed: test file rewritten with no leaked reasoning; _score_band uses round(score*10)/10.0 and _duration_band/_residual_band use floor(x*10 or x*2)/divisor, so no 0.30000000000000004 ids (module lines 12-24; tests at 81-104); pick_representatives allows duplicates per worked example; fps_for defaults missing end_frame.


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpC1
LUNA (gpt-6-luna medium):
LOW - research/pieces/test_c1_cluster.py:21 - The worked-example test does not assert cluster ordering or ordered member lists, so it would miss a regression in the example’s expected order - assert the expected ordered cluster list and each cluster’s ordered members.


HAIKU (low, stand-in):
Summary

- wpC1: FAIL (HIGH 0, MED 2)
- wpC2: FAIL (HIGH 0, MED 2)
- wpC3: PASS (HIGH 0, MED 0)

DECISION: the spec's worked example is binding for band assignment; make the code match it and add the required 'no features -> one none_none cluster' test.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/c1_cluster.py
```python
<complete module source>
```
FILE: research/pieces/test_c1_cluster.py
```python
<complete test source>
```
