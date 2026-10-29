
# WP-E2: Recipe Selection & Prompt Building
# Atomic spec for recipe selection and A/B prompt construction

## Module: a2_recipe_prompts.py

### Function 1: select_recipes
**Signature:** `select_recipes(playbook_recipes: list[dict], scene: dict, limit: int = 5, max_chars: int = 2500) -> dict`

**Behavior:**
- `playbook_recipes`: list of dicts with keys `recipe_id` (str), `category` (str), `purpose` (str), `text` (str)
- `scene`: dict with keys `scene_id` (str), `category` (str)
- Selects recipes where `recipe.category == scene.category` OR `recipe.purpose` contains `scene.category` (case-insensitive substring)
- Sorts selected recipes by `recipe_id` for determinism
- Takes first `limit` recipes
- Compacts each recipe text to max 200 chars (truncate with "..." if longer)
- Concatenates compacted texts with "\n---\n" separator
- If total chars > `max_chars`, truncates last recipe text to fit (keeps separator)
- Returns selected recipe IDs and compacted text block

**Return shape:**
```python
{
    "status": "ok" | "error",
    "selected_recipe_ids": list[str] | None,
    "compact_text": str | None,
    "total_chars": int | None,
    "error": str | None
}
```

**Worked Example:**
```python
playbook_recipes = [
    {"recipe_id": "r1", "category": "dialogue", "purpose": "character speaking", "text": "Recipe 1: Detailed dialogue technique for character speaking scenes. " * 10},
    {"recipe_id": "r2", "category": "gesture", "purpose": "dialogue emphasis", "text": "Recipe 2: Gesture techniques for dialogue emphasis."},
    {"recipe_id": "r3", "category": "dialogue", "purpose": "subtext", "text": "Recipe 3: Subtext in dialogue."},
    {"recipe_id": "r4", "category": "action", "purpose": "fight choreography", "text": "Recipe 4: Fight scenes."}
]
scene = {"scene_id": "s1", "category": "dialogue"}
select_recipes(playbook_recipes, scene, limit=5, max_chars=2500)
# Expected output:
{
    "status": "ok",
    "selected_recipe_ids": ["r1", "r2", "r3"],
    "compact_text": "Recipe 1: Detailed dialogue technique for character speaking scenes. Recipe 1: Detailed dialogue technique for character speaking scenes. Recipe 1: Detailed dialogue technique for character speaking scenes. Recipe 1: Detailed dialogue technique for character speaking scenes. Recipe 1: Detailed dialogue technique for character speaking scenes. Recipe 1: Detailed dialogue technique for character speaking scenes. Recipe 1: Detailed dialogue technique for character speaking scenes. Recipe 1: Detailed dialogue technique for character speaking scenes. Recipe 1: Detailed dialogue technique for character speaking scenes. Recipe 1: Detailed dialogue technique for character speaking scenes....\n---\nRecipe 2: Gesture techniques for dialogue emphasis.\n---\nRecipe 3: Subtext in dialogue.",
    "total_chars": 547,
    "error": None
}
```

---

### Function 2: build_prompts
**Signature:** `build_prompts(base_prompt: str, recipes_result: dict) -> dict`

**Behavior:**
- `base_prompt`: string, the baseline prompt (A prompt)
- `recipes_result`: output dict from `select_recipes` (must have status "ok" and compact_text)
- `A_prompt` = `base_prompt` unchanged
- `B_prompt` = `base_prompt` + "\n\n=== READ-ONLY RESEARCH HINTS ===\n" + `recipes_result["compact_text"]` + "\n=== END RESEARCH HINTS ==="
- Token estimate: `extra_tokens = len(recipes_result["compact_text"]) // 4` (integer division)
- Returns both prompts and token estimate

**Return shape:**
```python
{
    "status": "ok" | "error",
    "A_prompt": str | None,
    "B_prompt": str | None,
    "extra_tokens_estimate": int | None,
    "error": str | None
}
```

**Worked Example:**
```python
base_prompt = "Create a shot plan for the scene."
recipes_result = {
    "status": "ok",
    "selected_recipe_ids": ["r1", "r2"],
    "compact_text": "Recipe 1 text.\n---\nRecipe 2 text.",
    "total_chars": 30,
    "error": None
}
build_prompts(base_prompt, recipes_result)
# Expected output:
{
    "status": "ok",
    "A_prompt": "Create a shot plan for the scene.",
    "B_prompt": "Create a shot plan for the scene.\n\n=== READ-ONLY RESEARCH HINTS ===\nRecipe 1 text.\n---\nRecipe 2 text.\n=== END RESEARCH HINTS ===",
    "extra_tokens_estimate": 7,  # 30 // 4 = 7
    "error": None
}
```

**Error Example (bad recipes_result):**
```python
recipes_result_bad = {"status": "error", "compact_text": None, "error": "no recipes"}
build_prompts("base", recipes_result_bad)
# Expected output:
{
    "status": "error",
    "A_prompt": None,
    "B_prompt": None,
    "extra_tokens_estimate": None,
    "error": "Invalid recipes_result: status=error"
}
```


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/a2_recipe_prompts.py; test file: research/pieces/test_a2_recipe_prompts.py (tests import the module by its plain file name, e.g. `from a2_recipe_prompts import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
Sonnet G1 review (wpB1, wpB3, wpE2)


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
Sonnet H4 review (wpE1, wpE2, wpE3)


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpE2
LUNA (gpt-6-luna medium):
I can’t access the repository files in this read-only session, and the supplied material doesn’t include the authoritative REVIEW FINDINGS or REVIEWER DECISIONS content. I can’t verify the fixes or provide the requested exact output format without those files.

SONNET (latest):
wpE2
Result: 0 HIGH, 2 MED. Round-1 findings NOT fixed (module and tests look unchanged).
- MED - a2_recipe_prompts.py:109-131 - overflow rebuild branch still uses negative slice: when remaining is 3 or 4 and i>0, text_avail=remaining-5 is negative, so ctext[:text_avail] returns almost the whole recipe. Reproduced: 3 recipes of 30 chars, max_chars=34 gives total_chars=64 (>max_chars). text_avail==0 also leaves a dangling separator with the id listed - fix: if text_avail <= 0 break without appending; only slice when text_avail >= 1, add "..." only when >= 4.
- MED - test_a2_recipe_prompts.py:37-49 - truncation test is vacuous (texts cap at 200, 200+5+200 < 500, nothing truncated); overflow branch a2:91-142 is untested - fix: max_chars=150 (single-recipe truncation) and a 3-recipe case where prefix exceeds max_chars; assert exact compact_text, ids, total_chars<=max_chars.
- LOW - a2_recipe_prompts.py:46-47,73 - category/purpose/text = None raises AttributeError/TypeError - fix: coerce with `or ""` / isinstance str.
- LOW - test_a2_recipe_prompts.py:2-4,18-28,76-81 - unused imports; spec worked example output never asserted exactly; stale comment about a guard.

HAIKU (low, stand-in):
Summary
- wpE2: HIGH 1 / MED 0 -> FAIL
- wpF2: HIGH 0 / MED 1 -> FAIL
- wpF4: HIGH 0 / MED 1 -> FAIL


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpE2
SONNET (latest):
wpE2
Result: 0 HIGH, 2 MED. Round-1 findings NOT fixed (module and tests look unchanged).
- MED - a2_recipe_prompts.py:109-131 - overflow rebuild branch still uses negative slice: when remaining is 3 or 4 and i>0, text_avail=remaining-5 is negative, so ctext[:text_avail] returns almost the whole recipe. Reproduced: 3 recipes of 30 chars, max_chars=34 gives total_chars=64 (>max_chars). text_avail==0 also leaves a dangling separator with the id listed - fix: if text_avail <= 0 break without appending; only slice when text_avail >= 1, add "..." only when >= 4.
- MED - test_a2_recipe_prompts.py:37-49 - truncation test is vacuous (texts cap at 200, 200+5+200 < 500, nothing truncated); overflow branch a2:91-142 is untested - fix: max_chars=150 (single-recipe truncation) and a 3-recipe case where prefix exceeds max_chars; assert exact compact_text, ids, total_chars<=max_chars.
- LOW - a2_recipe_prompts.py:46-47,73 - category/purpose/text = None raises AttributeError/TypeError - fix: coerce with `or ""` / isinstance str.
- LOW - test_a2_recipe_prompts.py:2-4,18-28,76-81 - unused imports; spec worked example output never asserted exactly; stale comment about a guard.

HAIKU (low, stand-in):
Summary

- wpE1: HIGH 0, MED 1 (FAIL)
- wpE2: HIGH 0, MED 1 (FAIL)
- wpF1: HIGH 0, MED 3 (FAIL)
- wpF2: HIGH 0, MED 1 (FAIL)


REVIEW FINDINGS (round 5, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpE2
SONNET (latest):
wpE2
Result: 0 HIGH, 2 MED. Round-1 findings NOT fixed (module and tests look unchanged).
- MED - a2_recipe_prompts.py:109-131 - overflow rebuild branch still uses negative slice: when remaining is 3 or 4 and i>0, text_avail=remaining-5 is negative, so ctext[:text_avail] returns almost the whole recipe. Reproduced: 3 recipes of 30 chars, max_chars=34 gives total_chars=64 (>max_chars). text_avail==0 also leaves a dangling separator with the id listed - fix: if text_avail <= 0 break without appending; only slice when text_avail >= 1, add "..." only when >= 4.
- MED - test_a2_recipe_prompts.py:37-49 - truncation test is vacuous (texts cap at 200, 200+5+200 < 500, nothing truncated); overflow branch a2:91-142 is untested - fix: max_chars=150 (single-recipe truncation) and a 3-recipe case where prefix exceeds max_chars; assert exact compact_text, ids, total_chars<=max_chars.
- LOW - a2_recipe_prompts.py:46-47,73 - category/purpose/text = None raises AttributeError/TypeError - fix: coerce with `or ""` / isinstance str.
- LOW - test_a2_recipe_prompts.py:2-4,18-28,76-81 - unused imports; spec worked example output never asserted exactly; stale comment about a guard.


REVIEW FINDINGS (round 6, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpE2
LUNA (gpt-6-luna medium):
MED - research/pieces/a2_recipe_prompts.py:91-101 - If the text before the last recipe plus its separator exactly fills `max_chars`, the code appends an empty last recipe, leaves a trailing separator, and includes that recipe’s ID; for example, two 30-character recipes with `max_chars=35` - When no characters remain for the last recipe, omit it and its ID.

HAIKU (low, stand-in):
MED - a2_recipe_prompts.py:126-133 - when `available == 0` (the prefix is exactly `max_chars`), the else branch emits the prefix with its trailing separator and keeps the last recipe id, so the id is listed with no text. Repro: two 30-char recipes with `max_chars=35` gives ids `["r1","r2"]` and a trailing `\n---\n`. `max_chars=0` with one recipe gives ids `["r1"]` and empty text. - Change line 90 `if available < 0:` to `if available <= 0:` so the rebuild branch handles it. Add a test: two 30-char recipes, `max_chars=35`, expect ids `["r1"]` and `compact_text == "A"*30`.
LOW - a2_recipe_prompts.py:46 - a non-string `category`, `purpose` or `text` (for example `5`) raises AttributeError or TypeError, since only None is coerced. Repro: `select_recipes([{"recipe_id":"r1","category":5,"purpose":"","text":"x"}], {"category":"dialogue"})` raises. - Coerce with `isinstance(value, str)` and fall back to `""`.


REVIEW FINDINGS (round 7, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpE2
LUNA (gpt-6-luna medium):
MED - research/pieces/a2_recipe_prompts.py:74-76 - With `max_chars=0`, the rebuild branch can include a recipe ID while returning empty text - omit recipes when no text can fit

LOW - research/pieces/a2_recipe_prompts.py:48-53 - Non-string category and purpose values are stringified, so malformed values can match recipes instead of being treated as empty - accept only strings and use `""` for other values

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/a2_recipe_prompts.py
```python
<complete module source>
```
FILE: research/pieces/test_a2_recipe_prompts.py
```python
<complete test source>
```
