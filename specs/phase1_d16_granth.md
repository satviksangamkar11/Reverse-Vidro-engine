# SPEC D16GRA: NEW `pieces/d16_granth.py` and `pieces/test_d16_granth.py` (department 16, practical execution: READ-ONLY compatibility check against GranthStudio)

GOAL: write work/phase1/departments_16/PRODUCTION_EXECUTION_COMPATIBILITY.json. For each candidate technique and each lesson, record: whether a registered GranthStudio preset matches, which assets the preset needs and whether they exist, whether the technique needs an existing preset, a new capability, or stays UNKNOWN; separate the story and directing guidance from renderer executability; and list the GranthStudio files that could carry Kimi writer or director input. This module reads GranthStudio and writes only to the Reverse-Video repository.

ABSOLUTE RULE: GranthStudio is READ-ONLY. Never write, create, rename, delete, or import any file there. Never execute any GranthStudio code. Never call Kimi or any model. Text search and JSON reads only.

PATH RULE (amended 2026-10-31 after review): no absolute drive path appears anywhere in the module or the test. Paths are derived from the file location:
- ROOT = the repository root: os.path.dirname(os.path.dirname(os.path.abspath(__file__))).
- GS_ROOT = os.environ.get("GRANTH_ROOT") or os.path.join(os.path.dirname(ROOT), "granthstudio").
Every function that needs GranthStudio takes gs_root as an explicit parameter. No function reads the global GS_ROOT.

REAL FACTS (verified 2026-10-31):
- Preset index: <gs_root>/assets/v5_presets/index.json, a JSON LIST of 11 dicts with keys preset (e.g. "01_establishing_shot"), use (text), assets (list of asset names, e.g. ["fg","fx","mid","sky"]), simplest_renderer (text value copied verbatim from the data). The folder also has README.md and 11 preset JSON files named <preset>.json.
- Asset files: no file is registered in index.json. An asset counts as found when a file in <gs_root>/assets/v5_presets/ or <gs_root>/assets/pilot_refs/ (non-recursive) has the exact asset name, or starts with the asset name followed by "." or "_". Otherwise it is not found. asset_status per asset is "found" or "not found".
- assets_available for a preset is True only when the assets list is non-empty and every asset is found; otherwise False.
- F4 diagnosis: <ROOT>/work/phase1/f4_diagnosis_v2.json. Key diagnoses is a list of 13 dicts with keys id, classification, executability, bucket, reasons (list), technique (dict with preset_id and assets_available). All 13 have preset_id null and assets_available false. Reasons include NO_PRESET_ID for all 13, NEED_NEW for 12 of them, and MISSING_ASSET for 1.
- Lesson file: <ROOT>/work/phase1/overlays/lesson_candidates_7434a0f7.json, key lessons (list of 7 dicts with lesson_id, title, status, technique_tags (empty), observed_events).
- Consumer search (text only): search <gs_root>/scripts and <gs_root>/src for the strings "v5_presets", "index.json" and "preset". Record every matching file and line number (path relative to gs_root, line number, excerpt of at most 120 characters). Ignore __pycache__ folders and .pyc files.

FUNCTIONS (standard library and json only; no network; no model calls):
- load_presets(gs_root) -> list of 11 preset dicts from index.json, copied verbatim, plus asset_status (dict asset -> "found" or "not found") and assets_available (bool) computed by the rule above.
- load_techniques(root) -> list of 13 dicts from the F4 file with ONLY the raw keys id, classification, executability, bucket, reasons, preset_id, assets_available. It never contains need or preset_match.
- load_lessons(root) -> list of 7 lesson dicts from the lesson file.
- preset_match(technique) -> "NO_REGISTERED_PRESET" when technique preset_id is null; otherwise the preset_id value.
- classify_need(technique) -> "NEEDS_NEW_CAPABILITY" when executability is "NEED_NEW"; otherwise "NEEDS_EXISTING_PRESET" when preset_id is not null; otherwise "UNKNOWN". (With the current data every technique gives NEEDS_NEW_CAPABILITY or UNKNOWN.)
- lesson_compatibility(lesson) -> dict with lesson_id, title, status, technique_tags, preset_match "NO_REGISTERED_PRESET" (no technique tags exist), story_directing_guidance (the lesson title, copied, plus the text "candidate; not verified"), renderer_executability "NOT_EXECUTABLE_WITHOUT_PRESET", need "UNKNOWN" (no technique id on the lesson).
- consumer_search(gs_root) -> list of {file, line, excerpt, mentions}. mentions is a sorted list of the matched strings on that line. Skip any file that raises OSError or UnicodeDecodeError (catch both, continue).
- build_output(root, gs_root) -> dict with keys boundary_note (text: "GranthStudio read-only; no file modified; no model call"), presets, techniques, lessons, consumers, counts. techniques is exactly [dict(t, need=classify_need(t), preset_match=preset_match(t)) for t in load_techniques(root)]. counts holds the integer counts of presets, techniques, lessons and consumers.
- write_output(root, gs_root, out_path) -> the ONLY function allowed to open a file for writing. Rules, in order: (1) if os.path.islink(out_path) raise ValueError; (2) out_real = os.path.realpath(out_path) and allowed = os.path.realpath(os.path.join(root, "work", "phase1", "departments_16")); (3) if out_real does not start with allowed + os.sep raise ValueError (do not use os.path.commonpath); (4) os.makedirs(os.path.dirname(out_real), exist_ok=True); (5) write json.dump(build_output(root, gs_root), f, indent=2, sort_keys=True) with encoding utf-8.
- main(argv): argv[0] optional output path (default ROOT/work/phase1/departments_16/PRODUCTION_EXECUTION_COMPATIBILITY.json); calls write_output(ROOT, GS_ROOT, out_path) and prints the counts.

HARD RULES:
- Standard library plus json, os, re, ast only. Do not import shutil, subprocess, urllib, requests, http, socket, openai, anthropic, or any module whose name contains "kimi".
- Reads from GranthStudio use open(path, "r", encoding="utf-8") or os.path functions only. The only write-mode open is inside write_output.
- Do not print or read any file under the secrets folder or any .env file.
- Do not write the seven-letter name of the 3D software tool anywhere in code, tests or comments. Copy renderer values from the data at runtime.
- No comment may begin with a tool name or a word followed by a colon such as "ponytail:". Use plain comments or docstrings.

TESTS for `pieces/test_d16_granth.py` (pytest; read the real files; use tmp_path for output). Use ROOT and GS_ROOT computed exactly as in PATH RULE; do not hard-code any drive path.
1. The index.json preset count is 11; the output presets list has the same 11 preset names in the same order.
2. For each preset, the output required assets equal the index assets list; each asset_status is "found" or "not found"; assets_available equals True only when the assets list is non-empty and every asset_status is "found".
3. Take the techniques from build_output(ROOT, GS_ROOT)["techniques"], NOT from load_techniques. The list has 13 entries. Each has preset_id None and assets_available False. Each need is exactly "NEEDS_NEW_CAPABILITY" when executability is "NEED_NEW" and exactly "UNKNOWN" otherwise. Each entry also has preset_match equal to "NO_REGISTERED_PRESET".
4. Every lesson in the output has renderer_executability "NOT_EXECUTABLE_WITHOUT_PRESET" and preset_match "NO_REGISTERED_PRESET".
5. Every consumer entry's file exists under gs_root and its line number is at least 1; mentions is non-empty.
6. The module source contains exactly one write-mode open call, located inside the function write_output (ast: find every open() call whose mode argument contains w, a, x or +).
7. The module does not import shutil, subprocess, urllib, requests, http, socket, openai, anthropic (ast check). No import name contains "kimi".
8. write_output(ROOT, GS_ROOT, tmp_path / "x.json") raises ValueError, because the path is outside work/phase1/departments_16/.
9. Success path: write_output(str(tmp_path), GS_ROOT, str(tmp_path / "work" / "phase1" / "departments_16" / "out.json")) must succeed (tmp_path is used as the repository root for this call only). The file must exist, and its JSON must contain the keys presets, techniques, lessons, consumers and counts, with len(presets) == 11 and len(techniques) == 13.
10. The GranthStudio tree is not modified: record the modification times of index.json and README.md before and after build_output and assert they are unchanged.
11. build_output run twice gives identical output (determinism).
12. A symlink target is refused: if os.symlink is available, create a symlink named "link.json" under tmp_path / "work/phase1/departments_16" pointing to a file outside it, and assert write_output raises ValueError. Skip only if os.symlink raises OSError on this system.

INDEPENDENT EXPECTATIONS (added 2026-10-31, owner decision: never derive expectations from module output):
- Asset availability: for each preset and each asset, the test lists the real files in <gs_root>/assets/v5_presets and <gs_root>/assets/pilot_refs with os.listdir (no recursion) and computes found = any file equal to the asset name, or starting with asset + "." or asset + "_". The expected assets_available is True only when assets is non-empty and every asset is found. The test compares this with the module's asset_status and assets_available; the test does NOT read asset_status to compute its expectation.
- Lesson fields: for every lesson, story_directing_guidance must equal the source lesson title followed by the text "candidate; not verified", and need must equal "UNKNOWN". Both are asserted exactly.
- Consumer results: the test runs its own os.walk over <gs_root>/scripts and <gs_root>/src (skipping __pycache__ and .pyc files), finds every line containing "v5_presets", "index.json" or "preset", and asserts that the set of (file, line) pairs in the output equals this independently computed set exactly. An empty output is a failure.
REAL-DATA NOTE: check each field name against the real files first. Open index.json and the F4 file in the test and assert the keys id, classification, executability, bucket, reasons, technique, preset, use, assets, simplest_renderer exist before relying on them.

REPLY RULE: return the complete source of both files. Do not add any other text.
REPLY PARSER TRAP: no line of any file you write may start with the letters F-I-L-E followed by a colon.
FORBIDDEN-WORD TRAP: the loop refuses any file containing the seven-letter name of the 3D software tool. Never type it.

OUTPUT FORMAT (mandatory): reply with ONLY these two blocks, no other text. Each block starts with the line `FILE: <path>` directly followed by a fenced code block starting with ```python on its own line and ending with ``` on its own line:
FILE: pieces/d16_granth.py
```python
<complete source>
```
FILE: pieces/test_d16_granth.py
```python
<complete source>
```
