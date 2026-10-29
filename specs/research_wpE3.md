
# WP-E3: Blind Pairing, Scoring & Verdict
# Atomic spec for blind A/B assignment, plan scoring, and promotion verdict

## Module: a3_blind_scoring.py

### Function 1: blind_pairs
**Signature:** `blind_pairs(results_a: list[dict], results_b: list[dict], seed: int) -> dict`

**Behavior:**
- `results_a`: list of dicts with key `scene_id` (str) - baseline results
- `results_b`: list of dicts with key `scene_id` (str) - research-enhanced results
- Both lists must have same length and same scene_ids in same order
- `seed`: integer for reproducible randomization
- For each scene, randomly assigns A->X, B->Y or A->Y, B->X (50/50) using seeded random
- Returns `pairs` for reviewers (labels X/Y only, no A/B) and `key` mapping (scene_id -> {"X": "A|B", "Y": "A|B"})
- Uses `random.Random(seed)` for determinism

**Return shape:**
```python
{
    "status": "ok" | "error",
    "pairs": list[dict] | None,  # each: {"scene_id": str, "X": dict, "Y": dict}
    "key": dict | None,  # scene_id -> {"X": "A|B", "Y": "A|B"}
    "error": str | None
}
```

**Worked Example:**
```python
results_a = [{"scene_id": "s1", "plan": "plan_a1"}, {"scene_id": "s2", "plan": "plan_a2"}]
results_b = [{"scene_id": "s1", "plan": "plan_b1"}, {"scene_id": "s2", "plan": "plan_b2"}]
blind_pairs(results_a, results_b, seed=42)
# Expected output (with seed=42, random choices: s1->A=X,B=Y; s2->A=Y,B=X):
{
    "status": "ok",
    "pairs": [
        {"scene_id": "s1", "X": {"scene_id": "s1", "plan": "plan_a1"}, "Y": {"scene_id": "s1", "plan": "plan_b1"}},
        {"scene_id": "s2", "X": {"scene_id": "s2", "plan": "plan_b2"}, "Y": {"scene_id": "s2", "plan": "plan_a2"}}
    ],
    "key": {
        "s1": {"X": "A", "Y": "B"},
        "s2": {"X": "B", "Y": "A"}
    },
    "error": None
}
```

---

### Function 2: score_plan
**Signature:** `score_plan(plan: dict, validator: callable, assets: dict) -> dict`

**Behavior:**
- `plan`: dict with key `shots` (list of shot dicts)
- Each shot dict has: `shot_id`, `composition`, `movement`, `purpose`, `preset`, `asset`, `sfx`, `justification`
- `validator(plan) -> dict`: injected function returning `{"unsupported_facts": list, "continuity_errors": list}`
- `assets`: dict with keys `presets` (set of str), `assets` (set of str) - available preset/asset names
- Computes metrics:
  - `canon_fidelity`: count of `validator(plan)["unsupported_facts"]`
  - `coverage`: count of distinct `shot["purpose"]` values
  - `continuity_errors`: count of `validator(plan)["continuity_errors"]`
  - `repetition`: count of repeated (composition, movement) pairs across shots (pair counted once per duplicate occurrence)
  - `executability`: fraction of shots where `shot["preset"] in assets["presets"]` AND `shot["asset"] in assets["assets"]` (NEED_NEW counted separately)
  - `need_new_count`: count of shots where preset or asset not in available sets
  - `sound_judgment`: count of shots with `sfx` present but `justification` empty/missing
  - `justified_silence_count`: count of shots with no `sfx` AND `justification` present explaining silence

**Return shape:**
```python
{
    "status": "ok" | "error",
    "metrics": {
        "canon_fidelity": int,
        "coverage": int,
        "continuity_errors": int,
        "repetition": int,
        "executability": float,  # 0.0 to 1.0
        "need_new_count": int,
        "sound_judgment": int,
        "justified_silence_count": int
    } | None,
    "error": str | None
}
```

**Worked Example:**
```python
plan = {
    "shots": [
        {"shot_id": "sh1", "composition": "close_up", "movement": "static", "purpose": "emotion", "preset": "preset1", "asset": "asset1", "sfx": "heartbeat", "justification": "tension"},
        {"shot_id": "sh2", "composition": "wide", "movement": "pan_left", "purpose": "establishing", "preset": "preset2", "asset": "asset2", "sfx": "", "justification": "silence for focus"},
        {"shot_id": "sh3", "composition": "close_up", "movement": "static", "purpose": "emotion", "preset": "preset3", "asset": "asset3", "sfx": "whoosh", "justification": ""},
        {"shot_id": "sh4", "composition": "medium", "movement": "zoom_in", "purpose": "reaction", "preset": "NEED_NEW", "asset": "asset4", "sfx": None, "justification": None}
    ]
}

def mock_validator(plan):
    return {"unsupported_facts": ["fact1", "fact2"], "continuity_errors": ["error1"]}

assets = {"presets": {"preset1", "preset2"}, "assets": {"asset1", "asset2", "asset3", "asset4"}}

score_plan(plan, mock_validator, assets)
# Expected output:
{
    "status": "ok",
    "metrics": {
        "canon_fidelity": 2,
        "coverage": 3,  # emotion, establishing, reaction
        "continuity_errors": 1,
        "repetition": 1,  # (close_up, static) appears twice -> 1 duplicate
        "executability": 0.5,  # 2 of 4 shots have both preset+asset available
        "need_new_count": 2,  # sh3 (preset3 missing), sh4 (NEED_NEW)
        "sound_judgment": 1,  # sh3 has sfx but no justification
        "justified_silence_count": 1  # sh2 has no sfx but has justification
    },
    "error": None
}
```

---

### Function 3: summarize
**Signature:** `summarize(scores_a: list[dict], scores_b: list[dict], cost: dict) -> dict`

**Behavior:**
- `scores_a`: list of metric dicts from `score_plan` for A (baseline) - one per scene
- `scores_b`: list of metric dicts from `score_plan` for B (research) - one per scene, same order
- `cost`: dict with keys `kimi_calls_a`, `kimi_calls_b`, `tokens_a`, `tokens_b`, `timeouts_a`, `timeouts_b`, `retries_a`, `retries_b`, `owner_corrections_a`, `owner_corrections_b` (all ints)
- Computes per-metric averages across scenes for A and B, then deltas (B - A)
- Returns summary table with all metrics, deltas, and cost data

**Return shape:**
```python
{
    "status": "ok" | "error",
    "summary": {
        "metrics_a": dict,  # averaged metrics for A
        "metrics_b": dict,  # averaged metrics for B
        "deltas": dict,     # B - A for each metric
        "cost": dict        # passed through
    } | None,
    "error": str | None
}
```

**Worked Example:**
```python
scores_a = [
    {"canon_fidelity": 2, "coverage": 3, "continuity_errors": 1, "repetition": 1, "executability": 0.5, "need_new_count": 2, "sound_judgment": 1, "justified_silence_count": 1},
    {"canon_fidelity": 1, "coverage": 4, "continuity_errors": 0, "repetition": 0, "executability": 0.75, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 2}
]
scores_b = [
    {"canon_fidelity": 1, "coverage": 4, "continuity_errors": 0, "repetition": 0, "executability": 0.75, "need_new_count": 1, "sound_judgment": 0, "justified_silence_count": 2},
    {"canon_fidelity": 1, "coverage": 5, "continuity_errors": 0, "repetition": 0, "executability": 1.0, "need_new_count": 0, "sound_judgment": 0, "justified_silence_count": 2}
]
cost = {
    "kimi_calls_a": 10, "kimi_calls_b": 12,
    "tokens_a": 5000, "tokens_b": 6200,
    "timeouts_a": 0, "timeouts_b": 1,
    "retries_a": 1, "retries_b": 2,
    "owner_corrections_a": 2, "owner_corrections_b": 1
}
summarize(scores_a, scores_b, cost)
# Expected output:
{
    "status": "ok",
    "summary": {
        "metrics_a": {"canon_fidelity": 1.5, "coverage": 3.5, "continuity_errors": 0.5, "repetition": 0.5, "executability": 0.625, "need_new_count": 1.5, "sound_judgment": 0.5, "justified_silence_count": 1.5},
        "metrics_b": {"canon_fidelity": 1.0, "coverage": 4.5, "continuity_errors": 0.0, "repetition": 0.0, "executability": 0.875, "need_new_count": 0.5, "sound_judgment": 0.0, "justified_silence_count": 2.0},
        "deltas": {"canon_fidelity": -0.5, "coverage": 1.0, "continuity_errors": -0.5, "repetition": -0.5, "executability": 0.25, "need_new_count": -1.0, "sound_judgment": -0.5, "justified_silence_count": 0.5},
        "cost": cost
    },
    "error": None
}
```

---

### Function 4: promotion_verdict
**Signature:** `promotion_verdict(summary: dict, owner_approved: bool, animatic_compared: bool) -> dict`

**Behavior:**
- `summary`: output from `summarize` (must have status "ok" and summary.deltas)
- `owner_approved`: boolean flag (required for promotion)
- `animatic_compared`: boolean flag (required for promotion)
- Promotion rules (ALL must pass for PROMOTE):
  1. `owner_approved == True`
  2. `animatic_compared == True`
  3. `deltas["canon_fidelity"] <= 0` (B no worse on canon fidelity)
  4. `deltas["continuity_errors"] <= 0` (B no worse on continuity)
  5. At least two of these metrics improved (delta < 0 for error metrics, delta > 0 for positive metrics):
     - `coverage` (higher better)
     - `repetition` (lower better)
     - `executability` (higher better)
     - `need_new_count` (lower better)
     - `sound_judgment` (lower better)
     - `justified_silence_count` (higher better)
  5. Cost increase < 25%: `(cost["tokens_b"] - cost["tokens_a"]) / cost["tokens_a"] < 0.25` (if tokens_a > 0)
- Returns verdict with reasons if HOLD

**Return shape:**
```python
{
    "status": "ok",
    "verdict": "PROMOTE" | "HOLD",
    "reasons": list[str]  # empty if PROMOTE, list of failed conditions if HOLD
}
```

**Worked Example (PROMOTE):**
```python
summary = {
    "status": "ok",
    "summary": {
        "metrics_a": {"canon_fidelity": 2.0, "coverage": 3.0, "continuity_errors": 1.0, "repetition": 1.0, "executability": 0.5, "need_new_count": 2.0, "sound_judgment": 1.0, "justified_silence_count": 1.0},
        "metrics_b": {"canon_fidelity": 1.0, "coverage": 5.0, "continuity_errors": 0.0, "repetition": 0.0, "executability": 1.0, "need_new_count": 0.0, "sound_judgment": 0.0, "justified_silence_count": 2.0},
        "deltas": {"canon_fidelity": -1.0, "coverage": 2.0, "continuity_errors": -1.0, "repetition": -1.0, "executability": 0.5, "need_new_count": -2.0, "sound_judgment": -1.0, "justified_silence_count": 1.0},
        "cost": {"tokens_a": 5000, "tokens_b": 6000, "kimi_calls_a": 10, "kimi_calls_b": 12, "timeouts_a": 0, "timeouts_b": 0, "retries_a": 0, "retries_b": 0, "owner_corrections_a": 0, "owner_corrections_b": 0}
    }
}
promotion_verdict(summary, owner_approved=True, animatic_compared=True)
# Expected output:
{
    "status": "ok",
    "verdict": "PROMOTE",
    "reasons": []
}
```

**Worked Example (HOLD - missing owner_approved):**
```python
promotion_verdict(summary, owner_approved=False, animatic_compared=True)
# Expected output:
{
    "status": "ok",
    "verdict": "HOLD",
    "reasons": ["owner_approved flag is False"]
}
```

**Worked Example (HOLD - cost increase too high):**
```python
summary_high_cost = {
    "status": "ok",
    "summary": {
        "metrics_a": {"canon_fidelity": 2.0, "coverage": 3.0, "continuity_errors": 1.0, "repetition": 1.0, "executability": 0.5, "need_new_count": 2.0, "sound_judgment": 1.0, "justified_silence_count": 1.0},
        "metrics_b": {"canon_fidelity": 1.0, "coverage": 5.0, "continuity_errors": 0.0, "repetition": 0.0, "executability": 1.0, "need_new_count": 0.0, "sound_judgment": 0.0, "justified_silence_count": 2.0},
        "deltas": {"canon_fidelity": -1.0, "coverage": 2.0, "continuity_errors": -1.0, "repetition": -1.0, "executability": 0.5, "need_new_count": -2.0, "sound_judgment": -1.0, "justified_silence_count": 1.0},
        "cost": {"tokens_a": 5000, "tokens_b": 7000, "kimi_calls_a": 10, "kimi_calls_b": 12, "timeouts_a": 0, "timeouts_b": 0, "retries_a": 0, "retries_b": 0, "owner_corrections_a": 0, "owner_corrections_b": 0}
    }
}
promotion_verdict(summary_high_cost, owner_approved=True, animatic_compared=True)
# Expected output:
{
    "status": "ok",
    "verdict": "HOLD",
    "reasons": ["Cost increase 40.0% exceeds 25% threshold"]
}
```

---

### Function 5: render_review_note
**Signature:** `render_review_note() -> dict`

**Behavior:**
- Returns a static reminder note about animatic/render comparison requirement
- No parameters (pure function)

**Return shape:**
```python
{
    "status": "ok",
    "note": str
}
```

**Worked Example:**
```python
render_review_note()
# Expected output:
{
    "status": "ok",
    "note": "REMINDER: Animatic/render comparison is required. JSON validity alone is insufficient. Verdict must include animatic_compared field and cannot be PROMOTE if False."
}
```


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/a3_blind_scoring.py; test file: research/pieces/test_a3_blind_scoring.py (tests import the module by its plain file name, e.g. `from a3_blind_scoring import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpE3 (a3_blind_scoring.py)
- MED - a3_blind_scoring.py:30 - `rng.random() < 0.5` gives s1 B=X, s2 A=X for seed=42 (draws 0.639, 0.025); the spec worked example for seed=42 is s1 A=X, s2 B=X (the opposite). No test pins the worked example, so the mismatch is hidden - use `>= 0.5` for the A=X branch (reproduces the example) and add a seed=42 test asserting the spec key.
- LOW - a3_blind_scoring.py:42 - duplicate scene_ids silently collapse in `key` (pairs list keeps both) - return error on duplicate scene_id.
- LOW - test_a3_blind_scoring.py:15 - no test that each pair's X/Y content agrees with `key`, nor that pairs expose no A/B labels - add.
- LOW - a3_blind_scoring.py:69,87 - validator exceptions, non-dict shots, unhashable preset/asset raise instead of returning status error - wrap.
Verdict: no HIGH. 1 MED.


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpE3
LUNA (gpt-6-luna high):
MED - research/pieces/a3_blind_scoring.py:233 - An `ok` summary with favorable deltas but missing `canon_fidelity`, `continuity_errors`, or token cost fields can default those safeguards to zero and still return `PROMOTE` - validate the required delta and cost fields before evaluating promotion; return HOLD for an incomplete summary.

SONNET (latest):
wpE3
Result: PASS (0 HIGH, 0 MED). Round-1 MED fixed (>= 0.5; verified seed=42 -> s1 A=X, s2 B=X, pinned by test at 71); duplicate scene_id error added and tested; key/pairs agreement test added; validator exceptions, non-dict shots, unhashable preset/asset handled and tested. All 59 tests across the three pieces pass.
- LOW - a3_blind_scoring.py:165 - executability divides by len(shots) including skipped non-dict shots - fix: divide by the count of dict shots.
- LOW - a3_blind_scoring.py:7,15,65,225 - non-dict plan/results items/summary or non-dict assets raise instead of returning status error.
- LOW - a3_blind_scoring.py:203 - summarize: non-numeric metric values raise; cost keys unvalidated.


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpE3
Why it failed: round 0 files parsed but its pytest failed (output not kept; the model rewrote ~42 KB of module+tests at once). Round 1 returned only the module block (12 KB), so the test file was missing. Rounds 2-3 were codex API failures (status 0, empty reply), so no fix was ever tested. The restored code already has the round-1 fixes (>= 0.5 branch, duplicate scene_id error, validator/unhashable guards); only the round-2 items remain.

Fixes still needed (HIGH first):
1. HIGH (Luna MED) promotion_verdict: validate before judging. If summary.deltas lacks canon_fidelity or continuity_errors, or cost lacks numeric tokens_a/tokens_b, return HOLD with a reason ("incomplete summary"), never default to 0. Test: favorable deltas minus canon_fidelity must be HOLD.
2. MED score_plan: executability must divide by the count of dict shots, not len(shots); all-skipped gives 0.0.
3. LOW input type guards: score_plan with non-dict plan or non-dict assets, blind_pairs with non-dict items, and promotion_verdict with non-dict summary should return status error (or HOLD) rather than raise.
4. LOW summarize: non-numeric metric values and missing cost keys return status error.

Drop: nothing is wrong or duplicated; the round-1 MED and the three round-1 LOWs are already applied, so strike them from the spec. Operationally: send only this short list, ask for the full file pair (both FILE blocks), and fix the codex invocation first.


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpE3
LUNA (gpt-6-luna medium):
LOW - research/pieces/a3_blind_scoring.py:41 - A matching non-string or unhashable `scene_id` is accepted or raises during duplicate checking, despite the spec requiring string IDs - validate each ID is a string and return an error otherwise

LOW - research/pieces/a3_blind_scoring.py:125 - Missing or non-list validator result fields are silently scored as zero, which can hide invalid validator output - return status error unless both fields are lists

LOW - research/pieces/a3_blind_scoring.py:252 - Missing score metrics default to zero, so incomplete score entries produce valid averages and deltas - require every metric key in each score entry

LOW - research/pieces/a3_blind_scoring.py:213 - `summarize` passes through cost without checking the required cost keys or that their values are integers - validate all specified cost fields and return status error when missing or invalid

LOW - research/pieces/a3_blind_scoring.py:308 - Non-dict `deltas` or `cost` values can raise instead of returning HOLD for an incomplete summary - validate both values are dictionaries before field checks

SONNET (latest):
wpE3
Why it failed: round 0 files parsed but its pytest failed (output not kept; the model rewrote ~42 KB of module+tests at once). Round 1 returned only the module block (12 KB), so the test file was missing. Rounds 2-3 were codex API failures (status 0, empty reply), so no fix was ever tested. The restored code already has the round-1 fixes (>= 0.5 branch, duplicate scene_id error, validator/unhashable guards); only the round-2 items remain.

Fixes still needed (HIGH first):
1. HIGH (Luna MED) promotion_verdict: validate before judging. If summary.deltas lacks canon_fidelity or continuity_errors, or cost lacks numeric tokens_a/tokens_b, return HOLD with a reason ("incomplete summary"), never default to 0. Test: favorable deltas minus canon_fidelity must be HOLD.
2. MED score_plan: executability must divide by the count of dict shots, not len(shots); all-skipped gives 0.0.
3. LOW input type guards: score_plan with non-dict plan or non-dict assets, blind_pairs with non-dict items, and promotion_verdict with non-dict summary should return status error (or HOLD) rather than raise.
4. LOW summarize: non-numeric metric values and missing cost keys return status error.

Drop: nothing is wrong or duplicated; the round-1 MED and the three round-1 LOWs are already applied, so strike them from the spec. Operationally: send only this short list, ask for the full file pair (both FILE blocks), and fix the codex invocation first.


REVIEW FINDINGS (round 5, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpE3
LUNA (gpt-6-luna medium):
MED - research/pieces/a3_blind_scoring.py:303 - `promotion_verdict` defaults missing secondary metric deltas to zero, so an incomplete summary can still be promoted when two other metrics improve - require all six secondary deltas and validate them before evaluating promotion

HAIKU (low, stand-in):
MED - research/pieces/a3_blind_scoring.py:promotion_verdict - only `canon_fidelity` and `continuity_errors` deltas are type-checked, so a non-numeric value such as `coverage: None` reaches `> 0` / `< 0` and raises TypeError instead of HOLD - check that all eight delta fields are numeric before judging and return HOLD "incomplete summary" otherwise. Add a test.
LOW - research/pieces/a3_blind_scoring.py:score_plan (coverage) - an unhashable `purpose` (e.g. a list) goes straight into a set and raises TypeError, while preset, asset and composition are guarded - guard it the same way.
LOW - research/pieces/a3_blind_scoring.py:summarize (cost and metric checks) and promotion_verdict (token checks) - `bool` passes `isinstance(x, int)` / `(int, float)`, so `True` is accepted as a cost or metric value - exclude bool.
LOW - research/pieces/a3_blind_scoring.py:summarize (avg_metrics) - NaN and infinite metric values are accepted and propagate into averages and deltas - reject non-finite numbers.
LOW - research/pieces/test_a3_blind_scoring.py:imports - `tempfile`, `os` and `json` are unused - remove them.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/a3_blind_scoring.py
```python
<complete module source>
```
FILE: research/pieces/test_a3_blind_scoring.py
```python
<complete test source>
```
