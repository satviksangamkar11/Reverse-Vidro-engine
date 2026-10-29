
# WP-C2: Review Planning & Frame Re-extraction Commands
# Functions for planning review jobs under budget and generating ffmpeg commands for frame re-extraction.

## Data Shapes
# Cluster (from c1_cluster):
#   {"cluster_id": str, "members": list[str], "signature": dict}
# Event (from cinematic_analysis):
#   {"event_id": str, "shot": str, "start_frame": int, "end_frame": int, "score": float, "uncertain": bool, "burst_frames": list[int], "disposition": str}
# Review Job:
#   {"event_id": str, "priority": int, "reason": str, "fps": int}
# Plan Result:
#   {"status": "ok", "jobs": list[ReviewJob], "inferred": list[dict], "pending": list[str]}
# Inferred Disposition Record:
#   {"event_id": str, "disposition": "INFERRED_FROM_CLUSTER", "basis_event_ids": list[str]}
# Re-extract Command Result:
#   {"status": "ok", "argv": list[str]}

## Public Functions (≤3)

### 1. plan_review(clusters, events, reviewed_ids, budget) -> dict
# Builds ordered review job list respecting budget.
# reviewed_ids: set of event_ids already reviewed (have verdict in state).
# For each cluster:
#   reps = pick_representatives(cluster, events)["representatives"] (best, ambiguous, failure)
#   reviewed_reps = [r for r in reps.values() if r in reviewed_ids]
#   If reviewed_reps have disagreeing verdicts (different verdict) OR any reviewed_rep has uncertain=True in event:
#       -> all unreviewed members become jobs (reason="DISAGREEMENT" or "UNCERTAIN")
#   Else (agreeing or no reviewed reps):
#       -> sample every 4th member (sorted by event_id), min 1, as verification jobs (reason="VERIFICATION")
#       -> remaining unreviewed members get INFERRED_FROM_CLUSTER with basis_event_ids = reviewed_reps (or all reps if none reviewed yet? spec says "basis_event_ids" from representatives)
# Jobs sorted: representatives first (by cluster_id then rep priority best/ambiguous/failure), then verification, then inferred/pending.
# budget: max total jobs. Overflow members (jobs beyond budget) stay PENDING_REVIEW (added to "pending" list).
# Returns: {"status": "ok", "jobs": [...], "inferred": [...], "pending": [...]}

# WORKED EXAMPLE
# Input:
clusters_ex = [
    {"cluster_id": "C_A", "members": ["e1","e2","e3","e4","e5"], "signature": {}},
    {"cluster_id": "C_B", "members": ["e6","e7"], "signature": {}},
]
events_ex = [
    {"event_id": "e1", "score": 0.9, "uncertain": False, "disposition": "REVIEWED"},
    {"event_id": "e2", "score": 0.5, "uncertain": True, "disposition": "PENDING_REVIEW"},
    {"event_id": "e3", "score": 0.4, "uncertain": False, "disposition": "PENDING_REVIEW"},
    {"event_id": "e4", "score": 0.3, "uncertain": False, "disposition": "PENDING_REVIEW"},
    {"event_id": "e5", "score": 0.2, "uncertain": False, "disposition": "PENDING_REVIEW"},
    {"event_id": "e6", "score": 0.8, "uncertain": False, "disposition": "REVIEWED"},
    {"event_id": "e7", "score": 0.7, "uncertain": False, "disposition": "PENDING_REVIEW"},
]
reviewed_ids_ex = {"e1", "e6"}  # e1 verdict POSE_SWAP, e6 verdict CAMERA_MOVE (different -> disagreement for C_A? No, different clusters)
# Cluster C_A: reps best=e1, ambiguous=e2, failure=e5. Reviewed reps: e1 (verdict POSE_SWAP). No disagreement (only one reviewed). e2 uncertain -> UNCERTAIN expansion? Spec: "clusters whose reviewed representatives DISAGREE or are uncertain". e2 is a rep and uncertain, but not reviewed. "reviewed representatives ... are uncertain" -> means the reviewed rep has uncertain=True? e1 uncertain=False. So no expansion. Agreeing cluster (only one reviewed rep). Sample every 4th: members sorted [e1,e2,e3,e4,e5] -> indices 0,4 -> e1 (reviewed), e5. Min 1 verification: e5. Inferred: e2,e3,e4 with basis [e1].
# Cluster C_B: reps best=e6, ambiguous=e7 (score near 0.5? 0.7), failure=e7. Reviewed reps: e6 (verdict CAMERA_MOVE). Agreeing. Sample every 4th: [e6,e7] -> e6 (reviewed), min 1 -> e7 verification. Inferred: none.
# Budget=3. Jobs: reps first: e1 (already reviewed, skip?), e2 (rep ambiguous), e5 (rep failure), e6 (reviewed), e7 (rep ambiguous/failure). Actually "representatives first" means rep jobs for unreviewed reps. So jobs: e2 (reason="REPRESENTATIVE_AMBIGUOUS"), e5 (REPRESENTATIVE_FAILURE), e7 (REPRESENTATIVE_AMBIGUOUS/FAILURE). Then verification: e5 (already job), e7 (already job). Budget 3 -> all 3 fit. Inferred: e3,e4 (C_A), none (C_B). Pending: none.
# Output:
# {
#   "status": "ok",
#   "jobs": [
#     {"event_id": "e2", "priority": 1, "reason": "REPRESENTATIVE_AMBIGUOUS", "fps": 8},
#     {"event_id": "e5", "priority": 2, "reason": "REPRESENTATIVE_FAILURE", "fps": 4},
#     {"event_id": "e7", "priority": 3, "reason": "REPRESENTATIVE_AMBIGUOUS", "fps": 8}
#   ],
#   "inferred": [
#     {"event_id": "e3", "disposition": "INFERRED_FROM_CLUSTER", "basis_event_ids": ["e1"]},
#     {"event_id": "e4", "disposition": "INFERRED_FROM_CLUSTER", "basis_event_ids": ["e1"]}
#   ],
#   "pending": []
# }
# Note: fps values derived from fps_for logic (e2 uncertain->8, e5 score0.2 dur1.0->4, e7 score0.7 dur0.5? assume 4 but spec says score>=0.8 for 8, so 4).

### 2. reextract_cmd(source, event, fps, out_dir) -> dict
# Returns ffmpeg argv list for re-extracting frames at given fps.
# source: path to video file (str)
# event: event dict with start_frame, end_frame (30fps reference)
# fps: target fps (4 or 8)
# out_dir: output directory (str)
# Frame indices: start_frame to end_frame inclusive at 30fps. At target fps, extract frames at times t = start_frame/30 + k/fps.
# ffmpeg: ffmpeg -y -ss <start_sec> -i <source> -vf "fps=<fps>" -frames:v <num_frames> <out_dir>/frame_%04d.png
# start_sec = start_frame / 30.0
# duration_sec = (end_frame - start_frame) / 30.0
# num_frames = ceil(duration_sec * fps) + 1
# Returns: {"status": "ok", "argv": list[str]}

# WORKED EXAMPLE
# Input:
source_ex = "/path/video.mp4"
event_ex = {"event_id": "e1", "start_frame": 0, "end_frame": 30}
fps_ex = 8
out_dir_ex = "/tmp/frames"
# start_sec=0.0, duration=1.0, num_frames=ceil(8)+1=9
# Output:
# {"status": "ok", "argv": ["ffmpeg", "-y", "-ss", "0.0", "-i", "/path/video.mp4", "-vf", "fps=8", "-frames:v", "9", "/tmp/frames/frame_%04d.png"]}

### 3. (No third function; budget logic inside plan_review)


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/c2_review.py; test file: research/pieces/test_c2_review.py (tests import the module by its plain file name, e.g. `from c2_review import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpC2

Rounds 0-1 were Nemotron (200 OK); round 1 only failed the file parser (test file missing from the reply). Rounds 2 and 3 were Codex calls that returned empty with status=0. Those two are API failures, not fix failures. The code on disk is round 0's.

The one failing test is `test_plan_review_worked_example`, at `assertEqual(result["pending"], [])`. It got `['e7']`. CODE is wrong; the test matches the spec worked example.

Cause: in cluster C_B the scores are e6=0.8 and e7=0.7. `pick_representatives` correctly returns best=e6, ambiguous=e7, failure=e7, so e7 holds two roles. The representative loop in `plan_review` adds one job per role with no dedup. That gives two e7 jobs, REPRESENTATIVE_AMBIGUOUS and REPRESENTATIVE_FAILURE, which makes 4 jobs. With budget=3 the second e7 job overflows and is reported as pending. I confirmed this by running `plan_review` with a large budget: it returns 4 jobs, with e7 listed twice.

Fix: in the representative loop of `plan_review`, skip a rep whose event_id is already in the jobs list. Roles are processed in the order best, ambiguous, failure, so the first role wins and e7 stays REPRESENTATIVE_AMBIGUOUS. This also guarantees an event is never both a job and pending. Add one assertion to the test: no duplicate event_ids in `jobs`.

Not exercised by the test: the sort is per cluster, but the spec says representatives come first across all clusters, then verification. Align this only if you want to follow the spec strictly.


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpC2
LUNA (gpt-6-luna high):
MED - research/pieces/c2_review.py:144 - Jobs are sorted by input cluster position, so an earlier cluster’s verification job can precede a later cluster’s representative; this also ignores the required `cluster_id` ordering - Sort all representative jobs first by `cluster_id` and representative role, then verification jobs.

MED - research/pieces/c2_review.py:194 - Formatting `start_sec` to three decimals loses precision for frame timestamps such as frame 1 (`0.033333…` becomes `0.033`), which can shift re-extraction - Preserve sufficient precision for the exact `start_frame / 30.0` timestamp.

LOW - research/pieces/test_c2_review.py:208 - The “fractional duration” case uses 0.5 seconds at 8 fps, an exact 4-frame product, so it does not exercise the required ceiling behavior - Use a duration whose product with fps is non-integral and assert the resulting frame count.

SONNET (latest):
wpC2
Earlier finding (duplicate e7 job / false pending) verified FIXED (dedup at c2_review.py:95-111, asserted at test:90-92). Earlier note on cross-cluster ordering NOT fixed.
- MED - c2_review.py:144-160 - sort key starts with cluster_idx, so cluster 1's verification jobs outrank cluster 2's representatives; with a tight budget representatives of later clusters become pending. Spec: representatives first (all clusters, by cluster_id then rep order), then expansion/verification - drop cluster_idx from position 0 of the key (use (group, cluster_idx, type_order, id)) and add a two-cluster budget test.
- MED - c2_review.py:47-49,66-69 - "verdict" is taken from event["disposition"], which is "REVIEWED" for every reviewed event in real data, so DISAGREEMENT can never trigger; the only test fakes verdicts via disposition strings - read event.get("verdict", disposition) (or accept a verdicts source) and test with real shape.
- MED - c2_review.py:194 - argv "-ss" value is f"{start_sec:.3f}" -> "0.000"; spec expected argv is "0.0" (str(start_frame/30.0)); test (test_c2_review.py:187,203) locks the non-spec string - use str(start_sec) and update tests.
- LOW - c2_review.py:171 - negative budget slices wrongly (all_jobs[:-1]) - clamp budget to >=0.
- LOW - c2_review.py:141 - basis_event_ids shares one list object across inferred records - copy with list().
- LOW - test_c2_review.py:3,5 - unused imports tempfile/Path.


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpC2
Why rounds failed: round 0 Nemotron API failure; round 1 Nemotron 200 but tests failed (the duplicate-e7 bug); rounds 2-3 Codex status=0 empty = API failures. The duplicate-rep dedup is already in the on-disk code, so wpC2 is near done; the escalation is mostly infrastructure, not code.
Fixes still needed:
1. MED plan_review sort: key must be (group, cluster_idx, type_order, event_id) with group 0 = representatives across ALL clusters, 1 = DISAGREEMENT/UNCERTAIN, 2 = VERIFICATION; add a two-cluster tight-budget test.
2. MED reextract_cmd: -ss must be str(start_frame/30.0) (spec shows "0.0"); update tests at lines ~187/203 that lock "0.000".
3. LOW: change the fractional-duration test to a non-integral duration*fps and assert ceil+1 frames.
4. LOW: clamp budget to >=0; copy basis_event_ids with list(...) per inferred record; drop unused tempfile/Path imports.
Drop: the "verdict from event[disposition]" MED (spec defines no verdict field; the worked example uses disposition and the spec comment is only prose; changing it risks breaking the tests); the dedup finding (fixed); the "preserve precision" Luna finding (superseded by item 2, str() already keeps it).


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpC2
LUNA (gpt-6-luna medium):
LOW - research/pieces/test_c2_review.py:222 - Re-extraction tests use hard-coded absolute paths instead of temporary directories as required - Use `tempfile` or `tmp_path` paths.

SONNET (latest):
wpC2
Why rounds failed: round 0 Nemotron API failure; round 1 Nemotron 200 but tests failed (the duplicate-e7 bug); rounds 2-3 Codex status=0 empty = API failures. The duplicate-rep dedup is already in the on-disk code, so wpC2 is near done; the escalation is mostly infrastructure, not code.
Fixes still needed:
1. MED plan_review sort: key must be (group, cluster_idx, type_order, event_id) with group 0 = representatives across ALL clusters, 1 = DISAGREEMENT/UNCERTAIN, 2 = VERIFICATION; add a two-cluster tight-budget test.
2. MED reextract_cmd: -ss must be str(start_frame/30.0) (spec shows "0.0"); update tests at lines ~187/203 that lock "0.000".
3. LOW: change the fractional-duration test to a non-integral duration*fps and assert ceil+1 frames.
4. LOW: clamp budget to >=0; copy basis_event_ids with list(...) per inferred record; drop unused tempfile/Path imports.
Drop: the "verdict from event[disposition]" MED (spec defines no verdict field; the worked example uses disposition and the spec comment is only prose; changing it risks breaking the tests); the dedup finding (fixed); the "preserve precision" Luna finding (superseded by item 2, str() already keeps it).

HAIKU (low, stand-in):
Summary

- wpC1: FAIL (HIGH 0, MED 2)
- wpC2: FAIL (HIGH 0, MED 2)
- wpC3: PASS (HIGH 0, MED 0)


REVIEW FINDINGS (round 5, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpC2
LUNA (gpt-6-luna medium):
LOW - research/pieces/test_c2_review.py:222 - Re-extraction tests use hard-coded absolute paths instead of temporary directories - Use `tempfile` or `tmp_path` paths.

SONNET (latest):
wpC2
Why rounds failed: round 0 Nemotron API failure; round 1 Nemotron 200 but tests failed (the duplicate-e7 bug); rounds 2-3 Codex status=0 empty = API failures. The duplicate-rep dedup is already in the on-disk code, so wpC2 is near done; the escalation is mostly infrastructure, not code.
Fixes still needed:
1. MED plan_review sort: key must be (group, cluster_idx, type_order, event_id) with group 0 = representatives across ALL clusters, 1 = DISAGREEMENT/UNCERTAIN, 2 = VERIFICATION; add a two-cluster tight-budget test.
2. MED reextract_cmd: -ss must be str(start_frame/30.0) (spec shows "0.0"); update tests at lines ~187/203 that lock "0.000".
3. LOW: change the fractional-duration test to a non-integral duration*fps and assert ceil+1 frames.
4. LOW: clamp budget to >=0; copy basis_event_ids with list(...) per inferred record; drop unused tempfile/Path imports.
Drop: the "verdict from event[disposition]" MED (spec defines no verdict field; the worked example uses disposition and the spec comment is only prose; changing it risks breaking the tests); the dedup finding (fixed); the "preserve precision" Luna finding (superseded by item 2, str() already keeps it).


REVIEW FINDINGS (round 6, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpC2
HAIKU (low, stand-in):
MED - research/pieces/c2_review.py:plan_review (verification block) - "min 1" is not enforced: when every sampled member (every 4th, starting at index 0) is reviewed or already a job, no VERIFICATION job is emitted even if unreviewed non-representative members remain - after sampling, if no verification job was added, add the first unreviewed sorted member that is not already a job.
LOW - research/pieces/c2_review.py:pick_representatives, fps_for - both are public, so the module exposes four public functions against the spec's ≤3 - rename to `_pick_representatives` and `_fps_for` and update the test imports.
LOW - research/pieces/c2_review.py:reextract_cmd - no validation: `end_frame < start_frame` yields `num_frames <= 0` (invalid `-frames:v`), and fps outside {4, 8} is accepted - return `{"status": "ERROR", ...}` for both cases.
LOW - research/pieces/test_c2_review.py:TestReextractCmd - `/path/video.mp4` and `/tmp/frames` are literal paths, against the tempfile rule - use a `TemporaryDirectory` for `out_dir`.
LOW - research/pieces/test_c2_review.py:test_reextract_cmd_fractional_duration - the expected count recomputes the implementation formula (`math.ceil(duration * 8) + 1`), so it cannot catch a formula error - assert the literal `"5"`.


REVIEW FINDINGS (round 7, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpC2
Why it failed: pure infrastructure. All four rounds returned status 0/500 with empty body (round_N.txt are 0 bytes); no fix was ever tried. The restored code passes all tests and already has: cross-cluster sort (group, cluster_idx, type_order, id), `-ss` as str(start_frame/30.0), budget clamp, per-record list copy, rep dedup. Findings are stale and repeated across six rounds.
Fixes still needed:
1. MED plan_review: enforce "min 1 verification": if sampling emitted no VERIFICATION job and unreviewed non-job members remain, add the first sorted one.
2. LOW reextract_cmd: return {"status":"ERROR",...} when end_frame < start_frame or fps not in {4, 8}.
3. LOW tests: use TemporaryDirectory for source/out_dir instead of /path/video.mp4 and /tmp/frames; fractional-duration test must assert the literal count (e.g. "5"), not recompute the formula; add the two-cluster tight-budget test.
Drop: the "verdict from disposition" MED (contradicts spec/test), the rename-to-private LOW (would break test imports for little gain), the sort/-ss/precision/budget/copy/dedup items (applied), and the Haiku summary line. Retry with the trimmed list; likely just rerun after the API recovers.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/c2_review.py
```python
<complete module source>
```
FILE: research/pieces/test_c2_review.py
```python
<complete test source>
```
