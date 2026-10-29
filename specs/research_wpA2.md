
# WP-A2: Input Collection (collect_inputs)

## Data Shapes
# Video extensions: .mp4, .mov, .mkv, .webm (case-insensitive)
# Image-sequence extensions: .jpg, .jpeg, .png (case-insensitive)
# sha256_file: callable(str) -> str  (returns hex digest, from instagram_import)

## Public Functions (≤3)

### 1. collect_inputs(inputs, dest, sha256_file, copy_file, make_dirs, list_dir, is_file, is_dir, get_size, extract_zip_safe)
# inputs: list[str] paths (files, directories, or .zip files)
# dest: str destination directory
# sha256_file: callable(str) -> str
# copy_file: callable(src, dst) -> None
# make_dirs: callable(path) -> None
# list_dir: callable(path) -> list[str]  (returns full paths of entries)
# is_file: callable(path) -> bool
# is_dir: callable(path) -> bool
# get_size: callable(path) -> int  (file size in bytes)
# extract_zip_safe: callable(zip_path, dest_dir, max_total_size, max_members) -> {"extracted": list[str], "rejected": list[{"item": str, "error": str}]}
# Returns: {"copied": list[str], "duplicates": list[{"file": str, "duplicate_of": str}], "rejected": list[{"item": str, "error": str}], "status": "ok"}

WORKED EXAMPLE:
Input:
  inputs = [
    "/src/video.mp4",
    "/src/clips",           # directory containing clip1.mov, clip2.txt
    "/src/archive.zip"      # zip containing: video2.mp4, images/frame001.jpg, images/frame002.png, bad.exe
  ]
  dest = "/dest"
  sha256_file = lambda p: "aaaa" if "video.mp4" in p else ("bbbb" if "clip1.mov" in p else ("cccc" if "video2.mp4" in p else "dddd"))
  copy_file = lambda s, d: None
  make_dirs = lambda p: None
  list_dir = lambda p: ["/src/clips/clip1.mov", "/src/clips/clip2.txt"] if "clips" in p else ["/dest/archive/video2.mp4", "/dest/archive/images/frame001.jpg", "/dest/archive/images/frame002.png"]
  is_file = lambda p: not p.endswith("/clips") and not p.endswith("/archive.zip") and not p.endswith("/images")
  is_dir = lambda p: p.endswith("/clips") or p.endswith("/images")
  get_size = lambda p: 1000
  extract_zip_safe = lambda zp, dd, mts, mm: {"extracted": ["/dest/archive/video2.mp4", "/dest/archive/images/frame001.jpg", "/dest/archive/images/frame002.png"], "rejected": [{"item": "bad.exe", "error": "Not a video or image-sequence file"}]}

Output:
  {
    "copied": [
      "/dest/video.mp4",
      "/dest/clip1.mov",
      "/dest/archive/video2.mp4",
      "/dest/archive/images/frame001.jpg",
      "/dest/archive/images/frame002.png"
    ],
    "duplicates": [],
    "rejected": [
      {"item": "/src/clips/clip2.txt", "error": "Not a video or image-sequence file"},
      {"item": "bad.exe", "error": "Not a video or image-sequence file"}
    ],
    "status": "ok"
  }

### 2. extract_zip_safe(zip_path, dest_dir, max_total_size, max_members, open_zip, get_zip_info, extract_member, make_dirs)
# zip_path: str
# dest_dir: str
# max_total_size: int (4 * 1024**3)
# max_members: int (20000)
# open_zip: callable(str) -> zipfile.ZipFile-like (context manager)
# get_zip_info: callable(ZipFile) -> list[ZipInfo]
# extract_member: callable(ZipFile, ZipInfo, str) -> None
# make_dirs: callable(str) -> None
# Returns: {"extracted": list[str], "rejected": list[{"item": str, "error": str}], "status": "ok"}

WORKED EXAMPLE:
Input:
  zip_path = "/src/archive.zip"
  dest_dir = "/dest/archive"
  max_total_size = 4_000_000_000
  max_members = 20000
  # Zip contains:
  #   ZipInfo(filename="video.mp4", file_size=1000, is_dir=False)
  #   ZipInfo(filename="../escape.txt", file_size=100, is_dir=False)  # zip-slip
  #   ZipInfo(filename="/absolute.txt", file_size=100, is_dir=False)  # absolute
  #   ZipInfo(filename="images/frame.jpg", file_size=500, is_dir=False)
  #   ZipInfo(filename="symlink.txt", file_size=0, is_dir=False, external_attr=0xA1FF0000)  # symlink
  open_zip = lambda p: mock_zipfile  # yields ZipInfo list above
  get_zip_info = lambda zf: zf.infolist()
  extract_member = lambda zf, info, dest: None
  make_dirs = lambda p: None

Output:
  {
    "extracted": ["/dest/archive/video.mp4", "/dest/archive/images/frame.jpg"],
    "rejected": [
      {"item": "../escape.txt", "error": "Zip-slip attempt: path traversal"},
      {"item": "/absolute.txt", "error": "Absolute path not allowed"},
      {"item": "symlink.txt", "error": "Symlink entries not allowed"}
    ],
    "status": "ok"
  }

### 3. scan_for_media(root, video_exts, image_exts, list_dir, is_file, is_dir)
# root: str directory path
# video_exts: tuple[str] (e.g., (".mp4", ".mov", ".mkv", ".webm"))
# image_exts: tuple[str] (e.g., (".jpg", ".jpeg", ".png"))
# list_dir, is_file, is_dir: as above
# Returns: {"media_files": list[str], "status": "ok"}  (full paths, recursive)

WORKED EXAMPLE:
Input:
  root = "/src/clips"
  video_exts = (".mp4", ".mov", ".mkv", ".webm")
  image_exts = (".jpg", ".jpeg", ".png")
  list_dir = lambda p: ["/src/clips/clip1.mov", "/src/clips/clip2.txt", "/src/clips/sub/frame.png"]
  is_file = lambda p: not p.endswith("/sub")
  is_dir = lambda p: p.endswith("/sub")

Output:
  {
    "media_files": ["/src/clips/clip1.mov", "/src/clips/sub/frame.png"],
    "status": "ok"
  }

## Test Requirements (test_a2_collect.py)
- test_collect_inputs_copies_videos_and_images_recursive
- test_collect_inputs_zip_slip_rejection: absolute paths, '..', symlink entries rejected
- test_collect_inputs_zip_size_and_count_caps: total >4GiB or members >20000 rejected
- test_collect_inputs_duplicate_detection_via_sha256: byte-identical files reported as duplicates
- test_collect_inputs_no_overwrite: existing dest file skipped and reported as duplicate
- test_extract_zip_safe_rejects_malicious_entries
- test_scan_for_media_filters_extensions_case_insensitive
REVIEWER DECISIONS (resolve spec gaps; tests must follow these): tests use real tempfile directories and compare paths relative to dest (never literal strings like '/dest/...'). Validation order for a zip member or input item is: unsafe path (absolute, '..', ':' or backslash, symlink) is checked FIRST and reported with an error text containing 'Absolute path not allowed' / 'Unsafe path' / 'Symlink not allowed'; only then is the extension checked ('Not a video or image-sequence file'). Rejection of one member does not extract any member (all members validated before any extraction). Members are placed in dest/<zip stem>/<member path>.


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/a2_collect.py; test file: research/pieces/test_a2_collect.py (tests import the module by its plain file name, e.g. `from a2_collect import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpA2
Rounds: 0 and 1 were real Nemotron fixes (HTTP 200, tests still red); rounds 2 and 3 (codex) were API failures (status=0, empty), not fix failures. So the code never got a codex attempt.

Today pytest shows 4 failing, not 2. All have CODE as the root cause, except one that also needs a TEST edit.

1. test_absolute_path and test_extract_zip_safe_rejects_malicious_entries: CODE wrong. `_is_unsafe_path` uses `os.path.isabs`, which is False for "/absolute.txt" on Windows (no drive letter), so the entry falls through to the extension check ("Not a video..."). Fix: treat a name as absolute if it starts with "/" or "\\" or has a drive letter (test with both PurePosixPath and PureWindowsPath `.is_absolute()`), and split on both separators when looking for "..".
2. test_collect_inputs_zip_slip_rejection and test_collect_inputs_zip_size_and_count_caps: CODE wrong. In `collect_inputs` the `is_file(path)` branch runs before the ".zip" branch. A real .zip is a file, so it is rejected as "Not a video..." and extraction never runs (0 != 2, 1 != 20001). Fix: test `.lower().endswith(".zip")` before the is_file branch.
3. Size-cap half of the caps test: TEST wrong. It writes a 4 GiB+1 byte member into a zip (huge RAM and disk). Fix: the `extract_zip_safe_func` wrapper in the test should ignore the passed cap and call the real function with a small max_total_size (e.g. 1000) and a ~2000 byte member; assert the "Total size exceeds limit" error.
4. Latent CODE bug (no test catches it): the symlink check `external_attr & 0xA0000000` also flags ordinary files from real zips (0x81A40000). Fix: shift right 16 and compare the file-type bits to the symlink type (0o120000).

Spec ambiguity: "rejection of one member does not extract any member" contradicts the worked example (2 extracted, 3 rejected). Keep the current behaviour: validate all first, then extract the valid ones.

Test hygiene: real tempfile dirs are already used. Assertions mix `os.path.join(dest_dir, "images/frame.jpg")` with Windows separators, so compare normalised, relative-to-dest paths.


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpA2
LUNA (gpt-6-luna medium):
MED - research/pieces/a2_collect.py:152 - ZIP members are extracted directly into existing `dest/<zip stem>/...` paths, so collecting an archive can overwrite a preexisting destination file - check whether each target exists before extraction and report it as a duplicate without modifying it


HAIKU (low, stand-in for GLM/MiniMax):
Summary

- wpA1: PASS (LOW only)
- wpA2: HIGH 1, MED 2
- wpA3: HIGH 0, MED 1


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpA2
LUNA (gpt-6-luna medium):
FILE: research/pieces/a2_collect.py
```python
"""WP-A2: Input Collection (collect_inputs)"""
from __future__ import annotations

import os
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, List, Dict, Any, Tuple


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpA2
LUNA (gpt-6-luna medium):
MED - research/pieces/a2_collect.py:154 - A ZIP member colliding with an existing destination file is added to `rejected`, not `duplicates`, despite the no-overwrite duplicate requirement - return the collision as a duplicate from `collect_inputs`.

MED - research/pieces/test_a2_collect.py:181 - ZIP extraction tests compare full destination paths instead of paths relative to `dest`, contrary to the authoritative test decision - normalize extracted paths relative to `dest` before asserting.


REVIEW FINDINGS (round 5, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpA2
LUNA (gpt-6-luna medium):
MED - research/pieces/a2_collect.py:139 - Duplicate member names in one ZIP are both validated before extraction while the destination is still absent, so the later extraction can overwrite the earlier file - detect repeated destination paths during validation and report later entries as duplicates without extracting them

HAIKU (low, stand-in):
HIGH - research/pieces/a2_collect.py:144-149 - Two members with the same name both pass validation, because the `os.path.exists` check runs before any extraction and nothing records names already seen. Both are extracted to the same path, so the second overwrites the first. `collect_inputs` then hashes the final bytes for both entries, treats the second as a duplicate, and calls `os.remove` on the file. The archive's only copy is deleted while it is still reported as copied. - Track seen member paths in the validation loop and reject repeats. Add a test with two same-named members that asserts one is extracted, one is rejected, and the file still exists.
MED - research/pieces/test_a2_collect.py (`extract_member` wrappers in TestExtractZipSafe and TestCollectInputs, `lambda zf, info, d: zf.extract(info, os.path.dirname(d))`) - For `images/frame.jpg` this writes to `dest/images/images/frame.jpg`. The returned paths point at files that do not exist, and the sha256 mock keyed by basename hides this, so extraction placement is never checked. - Replace the wrapper with `with zf.open(info) as s, open(d, "wb") as t: shutil.copyfileobj(s, t)` and assert `os.path.isfile(p)` for every extracted path.
LOW - research/pieces/a2_collect.py:124-132 - The symlink check runs before the unsafe-path check, so a symlink named `../x` reports "Symlink not allowed" instead of the path error. The reviewer order puts the unsafe-path checks first. The `_is_unsafe_path` docstring also lists symlink, which that function does not check. - Run `_is_unsafe_path` first, then the symlink check, and fix the docstring.
LOW - research/pieces/test_a2_collect.py (TestExtractZipSafe) - No test covers a regular-file `external_attr` (0x81A40000). The latent symlink-detection bug was fixed in code only, so nothing guards it. - Add a member with `external_attr=0x81A40000` and assert it is extracted.
LOW - research/pieces/test_a2_collect.py (test_collect_inputs_duplicate_detection_via_sha256, test_collect_inputs_no_overwrite, test_collect_inputs_zip_no_overwrite_existing) - These compare full `str(dest/...)` paths, but the reviewer decision is dest-relative comparison. - Normalise with `os.path.relpath(p, self.dest)` before asserting.
LOW - research/pieces/a2_collect.py (single-file and directory branches of `collect_inputs`) - In `if existing_hash == file_hash:` both arms append the same duplicate entry, so the comparison does nothing. - Collapse to one duplicate append.


REVIEW FINDINGS (round 6, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpA2
Why it failed: not the findings. Rounds 0-1 were real Nemotron attempts (tests red at that time, fixed by the older code now on disk); round 2 dropped the a2_collect.py file from the reply; round 3 was an API failure (status=0, empty). The prompt is bloated (round 3 findings contain a pasted code dump; rounds 1-5 stack ~14 KB of findings, many already fixed or duplicated), so 40 KB replies (two whole files) are fragile. The restored code passes 34/34 tests today and already contains: zip-before-is_file, absolute-path check, correct symlink mask, zip no-overwrite -> duplicates.
Fixes still needed:
1. HIGH extract_zip_safe: two members with the same destination path pass validation, the second overwrites the first and collect_inputs then deletes the file as a hash duplicate. Track seen destination paths in the validation loop; reject (or report as duplicate) repeats. Add a two-same-named-members test asserting the file still exists.
2. MED test wrappers: the `extract_member` lambda extracts to dirname(d), producing dest/images/images/frame.jpg; replace with open-and-copy to d and assert each extracted path is a file.
3. LOW extract_zip_safe: run the unsafe-path check before the symlink check; add a test with external_attr 0x81A40000 that is extracted.
4. LOW tests: compare paths relative to dest (os.path.relpath).
5. LOW collect_inputs: collapse the identical if/else duplicate append.
Drop: the round-3 Luna "finding" (code dump, not a finding), the round-1 findings 1-4 (applied), the zip-no-overwrite MED (applied), round-4 first MED (applied). Send the fixer only items 1-5 and ask for one file per reply.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/a2_collect.py
```python
<complete module source>
```
FILE: research/pieces/test_a2_collect.py
```python
<complete test source>
```
