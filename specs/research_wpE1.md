
# WP-E1: Scene Selection & Baseline Freezing
# Atomic spec for scene selection and baseline integrity checking

## Module: a1_scene_selection.py

### Function 1: select_scenes
**Signature:** `select_scenes(catalog: list[dict], n: int = 6) -> dict`

**Behavior:**
- Input `catalog`: list of dicts with keys `scene_id` (str) and `category` (str)
- Required categories (exactly 6): "dialogue", "interaction", "gesture", "environment", "discourse", "complex_transition"
- Picks exactly one scene per required category (first match in catalog order)
- `n` must equal 6 (number of required categories); raises ValueError if n != 6
- Raises ValueError if any required category is missing from catalog
- Returns dict with status and selected scenes mapping

**Return shape:**
```python
{
    "status": "ok" | "error",
    "selected": {"dialogue": "scene_id", "interaction": "scene_id", ...} | None,
    "error": str | None
}
```

**Worked Example:**
```python
catalog = [
    {"scene_id": "s1", "category": "dialogue"},
    {"scene_id": "s2", "category": "interaction"},
    {"scene_id": "s3", "category": "gesture"},
    {"scene_id": "s4", "category": "environment"},
    {"scene_id": "s5", "category": "discourse"},
    {"scene_id": "s6", "category": "complex_transition"},
    {"scene_id": "s7", "category": "dialogue"}  # duplicate category
]
select_scenes(catalog, n=6)
# Expected output:
{
    "status": "ok",
    "selected": {
        "dialogue": "s1",
        "interaction": "s2",
        "gesture": "s3",
        "environment": "s4",
        "discourse": "s5",
        "complex_transition": "s6"
    },
    "error": None
}
```

**Error Example:**
```python
catalog_missing = [
    {"scene_id": "s1", "category": "dialogue"},
    {"scene_id": "s2", "category": "interaction"}
]
select_scenes(catalog_missing, n=6)
# Expected output:
{
    "status": "error",
    "selected": None,
    "error": "Missing categories: gesture, environment, discourse, complex_transition"
}
```

---

### Function 2: freeze_baseline
**Signature:** `freeze_baseline(prompts_dir: str, out_json: str, read_file: callable, hash_func: callable) -> dict`

**Behavior:**
- `prompts_dir`: directory path containing baseline prompt files (injected as string)
- `out_json`: output JSON file path (injected as string)
- `read_file(path: str) -> str`: injected function to read file contents
- `hash_func(content: str) -> str`: injected function returning sha256 hex digest
- Reads three files from `prompts_dir`: "stage1_prompt.txt", "stage2_prompt.txt", "schema.json"
- Computes sha256 of each file's content
- Writes JSON to `out_json` with structure: `{"stage1_prompt": hash, "stage2_prompt": hash, "schema": hash}`
- Uses injected `read_file` and `hash_func` (no direct filesystem/hashlib calls)

**Return shape:**
```python
{
    "status": "ok" | "error",
    "hashes": {"stage1_prompt": str, "stage2_prompt": str, "schema": str} | None,
    "error": str | None
}
```

**Worked Example:**
```python
def mock_read_file(path):
    contents = {
        "/prompts/stage1_prompt.txt": "STAGE1 CONTENT",
        "/prompts/stage2_prompt.txt": "STAGE2 CONTENT",
        "/prompts/schema.json": '{"type": "object"}'
    }
    return contents[path]

def mock_hash(content):
    # Simplified deterministic hashes for example
    return {"STAGE1 CONTENT": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "STAGE2 CONTENT": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            '{"type": "object"}': "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"}[content]

freeze_baseline("/prompts", "/out/baseline_hashes.json", mock_read_file, mock_hash)
# Expected output:
{
    "status": "ok",
    "hashes": {
        "stage1_prompt": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "stage2_prompt": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "schema": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    },
    "error": None
}
```

---

### Function 3: check_baseline
**Signature:** `check_baseline(prompts_dir: str, baseline_json: str, read_file: callable, hash_func: callable) -> dict`

**Behavior:**
- `prompts_dir`: directory path containing current prompt files
- `baseline_json`: path to previously frozen baseline JSON
- `read_file(path: str) -> str`: injected file reader
- `hash_func(content: str) -> str`: injected hash function
- Reads current hashes of the three files (same as freeze_baseline)
- Reads baseline hashes from `baseline_json`
- Compares each hash; fails if any mismatch
- Returns ok with match status or error with details

**Return shape:**
```python
{
    "status": "ok" | "error",
    "matches": {"stage1_prompt": bool, "stage2_prompt": bool, "schema": bool} | None,
    "error": str | None
}
```

**Worked Example:**
```python
def mock_read_file(path):
    contents = {
        "/prompts/stage1_prompt.txt": "STAGE1 CONTENT",
        "/prompts/stage2_prompt.txt": "STAGE2 CONTENT",
        "/prompts/schema.json": '{"type": "object"}',
        "/out/baseline_hashes.json": '{"stage1_prompt": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "stage2_prompt": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "schema": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"}'
    }
    return contents[path]

def mock_hash(content):
    return {"STAGE1 CONTENT": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "STAGE2 CONTENT": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            '{"type": "object"}': "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"}[content]

check_baseline("/prompts", "/out/baseline_hashes.json", mock_read_file, mock_hash)
# Expected output:
{
    "status": "ok",
    "matches": {"stage1_prompt": True, "stage2_prompt": True, "schema": True},
    "error": None
}
```

**Drift Example:**
```python
def mock_read_file_drift(path):
    contents = {
        "/prompts/stage1_prompt.txt": "STAGE1 MODIFIED",  # changed
        "/prompts/stage2_prompt.txt": "STAGE2 CONTENT",
        "/prompts/schema.json": '{"type": "object"}',
        "/out/baseline_hashes.json": '{"stage1_prompt": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "stage2_prompt": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "schema": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"}'
    }
    return contents[path]

def mock_hash_drift(content):
    return {"STAGE1 MODIFIED": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
            "STAGE2 CONTENT": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            '{"type": "object"}': "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"}[content]

check_baseline("/prompts", "/out/baseline_hashes.json", mock_read_file_drift, mock_hash_drift)
# Expected output:
{
    "status": "error",
    "matches": {"stage1_prompt": False, "stage2_prompt": True, "schema": True},
    "error": "Baseline drift detected: stage1_prompt"
}
```


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/a1_scene_selection.py; test file: research/pieces/test_a1_scene_selection.py (tests import the module by its plain file name, e.g. `from a1_scene_selection import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpE1
LUNA (gpt-6-luna high):
HIGH - research/pieces/a1_scene_selection.py:67 - `freeze_baseline` suppresses output write failures and still returns `status: ok`, so callers can believe a baseline was saved when no file exists - Return an error when writing `out_json` fails.

MED - research/pieces/test_a1_scene_selection.py:84 - The test uses hard-coded paths instead of a temporary directory and never checks the saved JSON; a failed write is swallowed, so the test passes without verifying persistence - Use a temporary directory and assert the output file contains the expected JSON.

SONNET (latest):
wpE1
Result: PASS (0 HIGH, 0 MED). No prior findings listed. No network/Kimi; no absolute drive paths used for real IO (mock paths only).
- LOW - a1_scene_selection.py:63-68 - write failure of out_json is swallowed and status "ok" returned, so a baseline that was never written looks frozen - fix: return status error on OSError.
- LOW - a1_scene_selection.py:62 - open(out_json) bypasses the injected-IO rule (spec says no direct filesystem calls) but spec gives no injected writer; no test checks the file content written (tests use "/out/..." which silently fails) - fix: test with a tempfile dir and assert JSON contents.
- LOW - test_a1_scene_selection.py:67,121,136 - literal "/prompts", "/out/..." paths; select_scenes non-dict items would raise AttributeError.


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpE1
LUNA (gpt-6-luna medium):
FILE: research/pieces/a1_scene_selection.py
```python
import json
import os
from typing import Any, Callable


REQUIRED_CATEGORIES = [
    "dialogue",
    "interaction",
    "gesture",
    "environment",
    "discourse",
    "complex_transition",
]

FILE_KEY_MAP = {
    "stage1_prompt.txt": "stage1_prompt",
    "stage2_prompt.txt": "stage2_prompt",
    "schema.json": "schema",
}


def select_scenes(catalog: list[dict], n: int = 6) -> dict:
    if n != 6:
        raise ValueError("n must be 6")

    selected = {}
    seen_categories = set()

    for item in catalog:
        if not isinstance(item, dict):
            continue
        category = item.get("category")
        if category in REQUIRED_CATEGORIES and category not in seen_categories:
            selected[category] = item.get("scene_id")
            seen_categories.add(category)

    missing = [category for category in REQUIRED_CATEGORIES if category not in seen_categories]
    if missing:
        return {
            "status": "error",
            "selected": None,
            "error": f"Missing categories: {', '.join(missing)}",
        }

    return {"status": "ok", "selected": selected, "error": None}


def freeze_baseline(
    prompts_dir: str,
    out_json: str,
    read_file: Callable[[str], str],
    hash_func: Callable[[str], str],
) -> dict:
    hashes = {}

    try:
        for filename, key in FILE_KEY_MAP.items():
            path = os.path.join(prompts_dir, filename)
            hashes[key] = hash_func(read_file(path))

        with open(out_json, "w", encoding="utf-8") as output_file:
            json.dump(hashes, output_file)

        return {"status": "ok", "hashes": hashes, "error": None}
    except Exception as error:
        return {
            "status": "error",
            "hashes": None,
            "error": f"Failed to freeze baseline: {type(error).__name__}",
        }


def check_baseline(
    prompts_dir: str,
    baseline_json: str,
    read_file: Callable[[str], str],
    hash_func: Callable[[str], str],
) -> dict:
    current_hashes = {}

    try:
        for filename, key in FILE_KEY_MAP.items():
            path = os.path.join(prompts_dir, filename)
            current_hashes[key] = hash_func(read_file(path))

        baseline_data = json.loads(read_file(baseline_json))
        required_keys = list(FILE_KEY_MAP.values())
        for key in required_keys:
            if key not in baseline_data:
                raise KeyError(f"Missing key in baseline: {key}")

        matches = {
            key: current_hashes[key] == baseline_data[key]
            for key in required_keys
        }
        mismatched = [key for key in required_keys if not matches[key]]
        if mismatched:
            return {
                "status": "error",
                "matches": matches,
                "error": f"Baseline drift detected: {', '.join(mismatched)}",
            }

        return {"status": "ok", "matches": matches, "error": None}
    except Exception as error:
        return {
            "status": "error",
            "matches": None,
            "error": f"Failed to check baseline: {type(error).__name__}",
        }
```
FILE: research/pieces/test_a1_scene_selection.py
```python
import hashlib
import json
import os
import tempfile
import unittest

from a1_scene_selection import check_baseline, freeze_baseline, select_scenes


class TestSelectScenes(unittest.TestCase):
    def test_select_scenes_success_and_first_match(self):
        catalog = [
            {"scene_id": "s1", "category": "dialogue"},
            {"scene_id": "s2", "category": "interaction"},
            {"scene_id": "s3", "category": "gesture"},
            {"scene_id": "s4", "category": "environment"},
            {"scene_id": "s5", "category": "discourse"},
            {"scene_id": "s6", "category": "complex_transition"},
            {"scene_id": "s7", "category": "dialogue"},
        ]
        result = select_scenes(catalog, n=6)
        self.assertEqual(result, {
            "status": "ok",
            "selected": {
                "dialogue": "s1",
                "interaction": "s2",
                "gesture": "s3",
                "environment": "s4",
                "discourse": "s5",
                "complex_transition": "s6",
            },
            "error": None,
        })

    def test_select_scenes_missing_categories(self):
        result = select_scenes([
            {"scene_id": "s1", "category": "dialogue"},
            {"scene_id": "s2", "category": "interaction"},
        ])
        self.assertEqual(result, {
            "status": "error",
            "selected": None,
            "error": "Missing categories: gesture, environment, discourse, complex_transition",
        })

    def test_select_scenes_n_not_six_raises(self):
        with self.assertRaisesRegex(ValueError, "^n must be 6$"):
            select_scenes([], n=5)

    def test_select_scenes_non_dict_items_ignored(self):
        catalog = [
            "not a dict",
            {"scene_id": "s1", "category": "dialogue"},
            None,
            {"scene_id": "s2", "category": "interaction"},
            {"scene_id": "s3", "category": "gesture"},
            {"scene_id": "s4", "category": "environment"},
            {"scene_id": "s5", "category": "discourse"},
            {"scene_id": "s6", "category": "complex_transition"},
        ]
        self.assertEqual(select_scenes(catalog)["status"], "ok")


class TestFreezeBaseline(unittest.TestCase):
    def _create_prompts(self, prompts_dir):
        os.makedirs(prompts_dir)
        contents = {
            "stage1_prompt.txt": "STAGE1 CONTENT",
            "stage2_prompt.txt": "STAGE2 CONTENT",
            "schema.json": '{"type": "object"}',
        }
        for filename, content in contents.items():
            with open(os.path.join(prompts_dir, filename), "w", encoding="utf-8") as file:
                file.write(content)

    @staticmethod
    def _read_file(path):
    


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpE1
SONNET (latest):
wpE1
Result: PASS (0 HIGH, 0 MED). No prior findings listed. No network/Kimi; no absolute drive paths used for real IO (mock paths only).
- LOW - a1_scene_selection.py:63-68 - write failure of out_json is swallowed and status "ok" returned, so a baseline that was never written looks frozen - fix: return status error on OSError.
- LOW - a1_scene_selection.py:62 - open(out_json) bypasses the injected-IO rule (spec says no direct filesystem calls) but spec gives no injected writer; no test checks the file content written (tests use "/out/..." which silently fails) - fix: test with a tempfile dir and assert JSON contents.
- LOW - test_a1_scene_selection.py:67,121,136 - literal "/prompts", "/out/..." paths; select_scenes non-dict items would raise AttributeError.

HAIKU (low, stand-in):
Summary

- wpE1: HIGH 0, MED 1 (FAIL)
- wpE2: HIGH 0, MED 1 (FAIL)
- wpF1: HIGH 0, MED 3 (FAIL)
- wpF2: HIGH 0, MED 1 (FAIL)


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpE1
LUNA (gpt-6-luna medium):
FILE: research/pieces/a1_scene_selection.py
```python
import json
import os
from typing import Any, Callable, Dict, List


REQUIRED_CATEGORIES = [
    "dialogue",
    "interaction",
    "gesture",
    "environment",
    "discourse",
    "complex_transition",
]

FILE_KEY_MAP = {
    "stage1_prompt.txt": "stage1_prompt",
    "stage2_prompt.txt": "stage2_prompt",
    "schema.json": "schema",
}


def select_scenes(catalog: List[Dict[str, str]], n: int = 6) -> Dict[str, Any]:
    if n != 6:
        raise ValueError("n must be 6")

    selected = {}
    seen_categories = set()

    for item in catalog:
        if not isinstance(item, dict):
            continue
        category = item.get("category")
        if category in REQUIRED_CATEGORIES and category not in seen_categories:
            selected[category] = item.get("scene_id")
            seen_categories.add(category)

    missing = [category for category in REQUIRED_CATEGORIES if category not in seen_categories]
    if missing:
        return {
            "status": "error",
            "selected": None,
            "error": f"Missing categories: {', '.join(missing)}",
        }

    return {"status": "ok", "selected": selected, "error": None}


def freeze_baseline(
    prompts_dir: str,
    out_json: str,
    read_file: Callable[[str], str],
    hash_func: Callable[[str], str],
) -> Dict[str, Any]:
    hashes = {}

    try:
        for filename, key in FILE_KEY_MAP.items():
            path = os.path.join(prompts_dir, filename)
            hashes[key] = hash_func(read_file(path))

        with open(out_json, "w", encoding="utf-8") as output_file:
            json.dump(hashes, output_file)

        return {"status": "ok", "hashes": hashes, "error": None}
    except Exception as error:
        return {
            "status": "error",
            "hashes": None,
            "error": f"Failed to freeze baseline: {type(error).__name__}",
        }


def check_baseline(
    prompts_dir: str,
    baseline_json: str,
    read_file: Callable[[str], str],
    hash_func: Callable[[str], str],
) -> Dict[str, Any]:
    current_hashes = {}

    try:
        for filename, key in FILE_KEY_MAP.items():
            path = os.path.join(prompts_dir, filename)
            current_hashes[key] = hash_func(read_file(path))

        baseline_data = json.loads(read_file(baseline_json))
        required_keys = list(FILE_KEY_MAP.values())
        for key in required_keys:
            if key not in baseline_data:
                raise KeyError(f"Missing key in baseline: {key}")

        matches = {
            key: current_hashes[key] == baseline_data[key]
            for key in required_keys
        }
        mismatched = [key for key in required_keys if not matches[key]]
        if mismatched:
            return {
                "status": "error",
                "matches": matches,
                "error": f"Baseline drift detected: {', '.join(mismatched)}",
            }

        return {"status": "ok", "matches": matches, "error": None}
    except Exception as error:
        return {
            "status": "error",
            "matches": None,
            "error": f"Failed to check baseline: {type(error).__name__}",
        }
```
FILE: research/pieces/test_a1_scene_selection.py
```python
import hashlib
import json
import os
import tempfile
import unittest

from a1_scene_selection import check_baseline, freeze_baseline, select_scenes


class TestSelectScenes(unittest.TestCase):
    def test_select_scenes_success_and_first_match(self):
        catalog = [
            {"scene_id": "s1", "category": "dialogue"},
            {"scene_id": "s2", "category": "interaction"},
            {"scene_id": "s3", "category": "gesture"},
            {"scene_id": "s4", "category": "environment"},
            {"scene_id": "s5", "category": "discourse"},
            {"scene_id": "s6", "category": "complex_transition"},
            {"scene_id": "s7", "category": "dialogue"},
        ]
        result = select_scenes(catalog, n=6)
        self.assertEqual(result, {
            "status": "ok",
            "selected": {
                "dialogue": "s1",
                "interaction": "s2",
                "gesture": "s3",
                "environment": "s4",
                "discourse": "s5",
                "complex_transition": "s6",
            },
            "error": None,
        })

    def test_select_scenes_missing_categories(self):
        result = select_scenes([
            {"scene_id": "s1", "category": "dialogue"},
            {"scene_id": "s2", "category": "interaction"},
        ])
        self.assertEqual(result, {
            "status": "error",
            "selected": None,
            "error": "Missing categories: gesture, environment, discourse, complex_transition",
        })

    def test_select_scenes_n_not_six_raises(self):
        with self.assertRaisesRegex(ValueError, "^n must be 6$"):
            select_scenes([], n=5)

    def test_select_scenes_non_dict_items_ignored(self):
        catalog = [
            "not a dict",
            {"scene_id": "s1", "category": "dialogue"},
            None,
            {"scene_id": "s2", "category": "interaction"},
            {"scene_id": "s3", "category": "gesture"},
            {"scene_id": "s4", "category": "environment"},
            {"scene_id": "s5", "category": "discourse"},
            {"scene_id": "s6", "category": "complex_transition"},
        ]
        self.assertEqual(select_scenes(catalog)["status"], "ok")


class TestFreezeBaseline(unittest.TestCase):
    def _create_prompts(self, prompts_dir):
        os.makedirs(prompts_dir)
        contents = {
            "stage1_prompt.txt": "STAGE1 CONTENT",
            "stage2_prompt.txt": "STAGE2 CONTENT",
            "schema.json": '{"type": "object"}',
        }
        for filename, content in contents.items():
            with open(os.path.join(prompts_dir, filename), "w", encoding="utf-8") as file:
                file.write(conten

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/a1_scene_selection.py
```python
<complete module source>
```
FILE: research/pieces/test_a1_scene_selection.py
```python
<complete test source>
```
