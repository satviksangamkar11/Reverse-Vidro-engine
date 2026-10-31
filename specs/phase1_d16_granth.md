# SPEC D16GRA: NEW `pieces/d16_granth.py` and `pieces/test_d16_granth.py` (department 16, practical execution: READ-ONLY compatibility check against GranthStudio)

GOAL: write work/phase1/departments_16/PRODUCTION_EXECUTION_COMPATIBILITY.json. For each candidate technique and each lesson, record: whether a registered GranthStudio preset matches, which assets the preset needs and whether they exist, whether the technique needs an existing preset, a new capability, or stays UNKNOWN; separate the story and directing guidance from renderer executability; and list the GranthStudio files that could carry Kimi writer or director input. This module reads GranthStudio and writes only to the Reverse-Video repository.

ABSOLUTE RULE: GranthStudio is READ-ONLY. Its root is D:/aai work/granthstudio. Never write, create, rename, delete, or import any file there. Never execute any GranthStudio code. Never call Kimi or any model. Text search and JSON reads only.

REAL FACTS (verified 2026-10-31):
- Preset index: D:/aai work/granthstudio/assets/v5_presets/index.json, a JSON LIST of 11 dicts with keys preset (e.g. "01_establishing_shot"), use (text), assets (list of asset names, e.g. ["fg","fx","mid","sky"]), simplest_renderer (text value copied verbatim from the data). The folder also has README.md and 11 preset JSON files named <preset>.json.
- Asset files: no file is registered in index.json. Check for files whose name starts with <asset>. or <asset>_ directly inside D:/aai work/granthstudio/assets/v5_presets/ and D:/aai work/granthstudio/assets/pilot_refs/ (non-recursive). Record found / not found.
- F4 diagnosis: work/phase1/f4_diagnosis_v2.json (repository). Key diagnoses is a list of 13 dicts with keys id, classification, executability, bucket, reasons (list), technique (dict with preset_id and assets_available). All 13 have preset_id null and assets_available false. Reasons include NO_PRESET_ID for all 13 and NEED_NEW for 12 of them, and MISSING_ASSET for 1.
- Lesson file: work/phase1/overlays/lesson_candidates_7434a0f7.json, key lessons (list of 7 dicts with lesson_id, title, status, technique_tags (empty), observed_events).
- Consumer search (text only): search D:/aai work/granthstudio/scripts and D:/aai work/granthstudio/src for the strings "v5_presets", "index.json" and "preset". Record every matching file and line number (file path relative to the granthstudio root, line number, excerpt of at most 120 characters). Ignore __pycache__ folders and .pyc files. Do not open any file for writing.

FUNCTIONS (standard library and json only; no network; no model calls):
- load_presets(gs_root) -> list of 11 preset dicts from index.json (copied verbatim, plus asset_files_found and assets_available computed by the rule above).
- load_techniques(root) -> list of 13 technique dicts from the F4 file (id, classification, executability, bucket, reasons, preset_id, assets_available).
- load_lessons(root) -> list of 7 lesson dicts from the lesson file.
- preset_match(technique) -> "NO_REGISTERED_PRESET" when technique preset_id is null; otherwise the preset_id value.
- classify_need(technique) -> one of "NEEDS_EXISTING_PRESET" (executability not NEED_NEW and preset not null), "NEEDS_NEW_CAPABILITY" (executability NEED_NEW), "UNKNOWN" (any other case).
- lesson_compatibility(lesson) -> dict with lesson_id, title, status, technique_tags, preset_match "NO_REGISTERED_PRESET" (no technique tags exist), story_directing_guidance (the lesson title, copied, plus the text "candidate; not verified"), renderer_executability "NOT_EXECUTABLE_WITHOUT_PRESET", need "UNKNOWN" (no technique id on the lesson).
- consumer_search(gs_root) -> list of {file, line, excerpt, mentions} where mentions is a sorted list of the matched strings in that line.
- build_output(root, gs_root) -> dict with keys boundary_note (text: "GranthStudio read-only; no file modified; no model call"), presets, techniques, lessons, consumers, counts. techniques is exactly [dict(t, need=classify_need(t), preset_match=preset_match(t)) for t in load_techniques(root)], so every entry has the keys need and preset_match. load_techniques itself returns only the raw F4 fields (id, classification, executability, bucket, reasons, preset_id, assets_available) and never contains need or preset_match.
- write_output(root, out_path) -> the ONLY function allowed to open a file for writing; it writes JSON with indent=2 and sort_keys=True; it refuses (raises ValueError) any out_path that is not inside root/work/phase1/departments_16/. Creates the folder with os.makedirs(exist_ok=True).
- main(argv): with no arguments writes to ROOT/work/phase1/departments_16/PRODUCTION_EXECUTION_COMPATIBILITY.json and prints the counts.

HARD RULES:
- Standard library plus json, os, re, ast only. Do not import shutil, subprocess, urllib, requests, http, socket, openai, anthropic, or any module whose name contains "kimi".
- Reads from GranthStudio use open(path, "r", encoding="utf-8") or os.path functions only. The only write-mode open is inside write_output.
- Do not print or read any file under D:\aai work\secrets or any .env file.
- Do not write the seven-letter name of the 3D software tool anywhere in code or tests. Copy renderer values from the data at runtime.

TESTS for `pieces/test_d16_granth.py` (pytest; read the real files; use tmp_path for output):
1. The index.json preset count is 11; the output presets list has the same 11 preset names in the same order.
2. For each preset, the output required assets equal the index assets list, and assets_available is False when no asset file is found.
3. Take the techniques from build_output(root, GS_ROOT)["techniques"], NOT from load_techniques. The list has 13 entries; each has preset_id None, assets_available False, and a need key. need is "NEEDS_NEW_CAPABILITY" when executability is NEED_NEW, and otherwise one of "NEEDS_EXISTING_PRESET" or "UNKNOWN". Each entry also has preset_match.
4. Every lesson in the output has renderer_executability "NOT_EXECUTABLE_WITHOUT_PRESET" and preset_match "NO_REGISTERED_PRESET".
5. Every consumer entry's file exists under the GranthStudio root and its line number is at least 1; mentions is non-empty.
6. The module source contains exactly one write-mode open call, located inside the function write_output (check with ast: find every open() call whose mode argument contains w, a, x or +).
7. The module does not import shutil, subprocess, urllib, requests, http, socket, openai, anthropic (ast check). No name in the module contains "kimi" in an import.
8. write_output(root, tmp_path / "x.json") raises ValueError (the path is outside work/phase1/departments_16/).
9. The GranthStudio tree is not modified by the test: record the modification times of index.json and the README before and after build_output and assert they are unchanged.
10. build_output run twice gives identical output (determinism).

REAL-DATA NOTE: check each field name against the real files first (open index.json and the F4 file in the test and assert the keys exist before relying on them).

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
