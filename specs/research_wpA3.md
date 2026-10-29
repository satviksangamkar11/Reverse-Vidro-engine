
# WP-A3: CLI Entry Point (ingest.py with subcommands add-link, collect, status)

## Data Shapes
# Uses functions from a1_queue and a2_collect via plain dict returns (no direct imports in spec; wiring in implementation)
# CLI args parsed via argparse (stdlib)

## Public Functions (≤3)

### 1. build_parser()
# Returns: argparse.ArgumentParser with subcommands:
#   add-link <url> [<url>...]
#   collect <input> [<input>...] --dest <dir>
#   status --queue-file <path> --ledger <path>
# Returns: {"parser": ArgumentParser, "status": "ok"}

WORKED EXAMPLE:
Input: (no args)
Output:
  {"parser": <ArgumentParser object>, "status": "ok"}
  # parser.parse_args(["add-link", "https://ig.com/reel/ABC/"]) -> Namespace(command="add_link", urls=["https://ig.com/reel/ABC/"])
  # parser.parse_args(["collect", "/src/vid.mp4", "--dest", "/dest"]) -> Namespace(command="collect", inputs=["/src/vid.mp4"], dest="/dest")
  # parser.parse_args(["status", "--queue-file", "q.txt", "--ledger", "log.jsonl"]) -> Namespace(command="status", queue_file="q.txt", ledger="log.jsonl")

### 2. run_add_link(urls, queue_file, queue_links_fn, normalize_reel_url, clock_now, write_text_file)
# urls: list[str]
# queue_file: str
# queue_links_fn: callable(urls, queue_file, normalize_reel_url, clock_now) -> dict (from a1_queue)
# normalize_reel_url: callable(str) -> str|None
# clock_now: callable() -> str
# write_text_file: callable(path, content) -> None
# Returns: dict (same as queue_links_fn return) + prints JSON to stdout

WORKED EXAMPLE:
Input:
  urls = ["https://instagram.com/reel/NEW789/"]
  queue_file = "test_queue.txt"
  queue_links_fn = lambda u, qf, nru, cn: {"added": ["https://www.instagram.com/reel/NEW789/"], "already_queued": [], "rejected": [], "status": "ok"}
  normalize_reel_url = lambda u: "https://www.instagram.com/reel/NEW789/"
  clock_now = lambda: "2024-01-15T10:30:00Z"
  write_text_file = lambda p, c: None

Output:
  {"added": ["https://www.instagram.com/reel/NEW789/"], "already_queued": [], "rejected": [], "status": "ok"}
  # stdout: {"added":["https://www.instagram.com/reel/NEW789/"],"already_queued":[],"rejected":[],"status":"ok"}

### 3. run_collect(inputs, dest, collect_inputs_fn, sha256_file, copy_file, make_dirs, list_dir, is_file, is_dir, get_size, extract_zip_safe)
# inputs: list[str]
# dest: str
# collect_inputs_fn: callable(...) -> dict (from a2_collect)
# other params: passed through to collect_inputs_fn
# Returns: dict (same as collect_inputs_fn return) + prints JSON to stdout

WORKED EXAMPLE:
Input:
  inputs = ["/src/video.mp4"]
  dest = "/dest"
  collect_inputs_fn = lambda **kw: {"copied": ["/dest/video.mp4"], "duplicates": [], "rejected": [], "status": "ok"}
  (other params: dummy callables)

Output:
  {"copied": ["/dest/video.mp4"], "duplicates": [], "rejected": [], "status": "ok"}
  # stdout: {"copied":["/dest/video.mp4"],"duplicates":[],"rejected":[],"status":"ok"}

### 4. run_status(queue_file, ledger_path, queue_status_fn, read_text_file, parse_json_lines)
# queue_file: str
# ledger_path: str
# queue_status_fn: callable(...) -> dict (from a1_queue)
# read_text_file, parse_json_lines: passed through
# Returns: dict (same as queue_status_fn return) + prints JSON to stdout

WORKED EXAMPLE:
Input:
  queue_file = "test_queue.txt"
  ledger_path = "test_log.jsonl"
  queue_status_fn = lambda **kw: {"items": [{"url": "https://www.instagram.com/reel/ABC123/", "state": "QUEUED", "error": null}], "status": "ok"}
  read_text_file = lambda p: ""
  parse_json_lines = lambda s: []

Output:
  {"items": [{"url": "https://www.instagram.com/reel/ABC123/", "state": "QUEUED", "error": null}], "status": "ok"}
  # stdout: {"items":[{"url":"https://www.instagram.com/reel/ABC123/","state":"QUEUED","error":null}],"status":"ok"}

### 5. main(argv, build_parser, run_add_link, run_collect, run_status, read_text_file, write_text_file, clock_now, normalize_reel_url, sha256_file, copy_file, make_dirs, list_dir, is_file, is_dir, get_size, extract_zip_safe, open_zip, get_zip_info, extract_member, parse_json_lines)
# argv: list[str] (sys.argv[1:])
# All dependencies injected
# Returns: {"exit_code": int, "status": "ok"}

WORKED EXAMPLE:
Input:
  argv = ["add-link", "https://instagram.com/reel/NEW789/"]
  (all other params: dummy callables that return worked-example outputs above)

Output:
  {"exit_code": 0, "status": "ok"}
  # stdout contains JSON from run_add_link

## Test Requirements (test_a3_cli.py)
- test_cli_add_link_calls_queue_links_and_prints_json
- test_cli_collect_calls_collect_inputs_and_prints_json
- test_cli_status_calls_queue_status_and_prints_json
- test_cli_add_link_never_calls_downloader: verify no network/import of downloader modules
- test_cli_invalid_subcommand_shows_usage
REVIEWER DECISIONS (resolve spec gaps; tests must follow these): every CLI subcommand prints EXACTLY ONE JSON object to stdout and nothing else (no banners, logs or prefixes; diagnostics go to stderr); main(argv) returns the exit code (0 ok, 1 when any rejected/failed item exists). Tests call main(argv) with contextlib.redirect_stdout on a StringIO, parse with json.loads, and use real tempfile directories and a queue file path passed as an argument (never the default path).


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/a3_cli.py; test file: research/pieces/test_a3_cli.py (tests import the module by its plain file name, e.g. `from a3_cli import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpA3 (a3_cli.py)
- HIGH - a3_cli.py:125-162 - main() never calls the real fns: it passes stub lambdas (`queue_links_fn=lambda **kw: {"added": []...}`, same for collect/status) and hardcodes `queue_file="queue.txt"`, so every subcommand prints an empty fake result and the REVIEWER DECISION (queue file path passed as an argument, no default path) is not met - add-link has no queue-file argument at all. Fix: add `--queue-file` to add-link (and wire real queue_links/collect_inputs/queue_status via injected params or defaulted kwargs on main).
- MED - a3_cli.py:12,15,20 - subparser names produce `command="add-link"`; spec says Namespace(command="add_link", ...) - use `set_defaults(command="add_link")` (and handle in main). Not tested.
- MED - a3_cli.py:134,151,162 - exit code ignores result["status"]=="error" and failed items (status never returns 1; add-link/collect return 0 on status error). Spec: 1 when any rejected/failed item exists.
- MED - test_a3_cli.py:193-312 - main tests inject Mock run_* so the stub lambdas/hardcoded path are never exercised; there is no test with a real tempfile queue path via main(), no build_parser Namespace test, and `never_calls_downloader` (l.54) only asserts mocks are not called (no import/network check) - trivially true.
- LOW - a3_cli.py:122-123 - `--help` SystemExit(0) returns status "error"; e.code may be None.
- LOW - a3_cli.py:34 - run_add_link ignores write_text_file (unused param).
Verdict: 1 HIGH, 3 MED.


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpA3
Verdict: mostly API failure; where the fixer did answer, the TEST was wrong, and the CODE still has one unfixed HIGH.
- Rounds: 0 coder status=0 (API failure), 1 nemotron status=200 files ok but pytest failed, 2 and 3 codex status=0 (API failures). Only one real fix attempt happened. The on-disk a3_cli.py/test file are the older seed (10 tests pass), so none of the Sonnet findings are applied.
- Round 1 output (checked by running it): code applied queue-file arg, set_defaults(command="add_link"), exit code 1 on status=="error", --help code handling. 9 of 18 tests failed, all TEST bugs: (a) test_a3_cli.py never imports argparse but asserts isinstance(..., argparse.ArgumentParser); (b) the 8 main() tests build a dummies dict that omits run_add_link/run_collect/run_status (some omit all) and then call main(argv, **dummies), so TypeError for missing positional args. Fix tests: pass the real a3_cli.run_* functions in the dict and add `import argparse`.
- Still wrong in CODE (HIGH not fixed): main() falls back to stub lambdas (`queue_links_fn is None` -> fake empty result), so the CLI can print fake results. Required behaviour: no stub defaults; queue_links_fn/collect_inputs_fn/queue_status_fn are required injected params (modules may not import other pieces), raise or exit 1 with a stderr message if missing. Tests must then inject real tempfile-based fakes and assert the queue file path from argv reaches queue_links_fn.
- Remaining MED: replace the trivial never_calls_downloader test with a check that a3_cli imports no downloader/network modules (inspect sys.modules or source imports); run_add_link ignores write_text_file (LOW, leave documented).
- Next run: rerun fix loop; it needs both the API failure retried and a prompt stating the exact test bugs above.


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpA3
LUNA (gpt-6-luna high):
MED - research/pieces/a3_cli.py:172-173 - A status result with an item in state `FAILED_INACCESSIBLE` still exits 0 when its top-level status is `"ok"`; return 1 when any item is failed.

MED - research/pieces/test_a3_cli.py:220-253 - The add-link main test replaces `run_add_link` with a mock, so it never verifies that `--queue-file` reaches the queue function or that the real command emits the JSON result; use the real runner with a temporary queue path and assert the forwarded path and parsed stdout.

MED - research/pieces/test_a3_cli.py:371-416 - The status main tests mock `run_status` and never check its JSON output or a failed item state; use the real runner and cover a `FAILED_INACCESSIBLE` result.

MED - research/pieces/test_a3_cli.py:55-62 - The downloader check only scans currently loaded module names containing `downloader` or `network`; imports such as `requests` or `urllib.request` pass undetected. Check `a3_cli`’s imports or otherwise assert the prohibited imports and network calls are absent.

SONNET (latest):
wpA3
HIGH 0, MED 2
- Earlier HIGH (stub lambdas) fixed: queue_links_fn/collect_inputs_fn/queue_status_fn are required params; --queue-file wired; command="add_link"; exit 1 on rejected/error; --help gives 0.
- MED - test_a3_cli.py:171-436 - every main() test injects Mock run_* and Mock *_fn, and none asserts that argv values reach them (queue_file from --queue-file reaching queue_links_fn; dest/inputs; ledger). The REVIEWER DECISION "real tempfile queue path passed via argv" is not tested; real run_* + a fake queue_links_fn writing to a tempdir file is missing - add one main() test per subcommand with real run_* and a tempfile queue path, asserting call kwargs and that stdout is exactly one JSON object.
- MED - test_a3_cli.py:55-62 - test_cli_add_link_never_calls_downloader is near-vacuous: the sys.modules scan is global (any unrelated "network" module breaks or hides it) and the rest only asserts a Mock was called - assert on a3_cli's own imports (e.g. ast of the module source or vars(a3_cli)) contain no subprocess/urllib/requests/http.
- LOW - a3_cli.py:38 - write_text_file param unused in run_add_link - document or drop.
- LOW - test_a3_cli.py:17,64,302 - hardcoded "/src", "/dest" paths and tempfile.gettempdir() shared file name; use TemporaryDirectory.
- LOW - a3_cli.py:130 - SystemExit with non-int, non-None code (e.g. string) maps to 0 - map to 1.


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpA3
SONNET (latest):
wpA3
HIGH 0, MED 2
- Earlier HIGH (stub lambdas) fixed: queue_links_fn/collect_inputs_fn/queue_status_fn are required params; --queue-file wired; command="add_link"; exit 1 on rejected/error; --help gives 0.
- MED - test_a3_cli.py:171-436 - every main() test injects Mock run_* and Mock *_fn, and none asserts that argv values reach them (queue_file from --queue-file reaching queue_links_fn; dest/inputs; ledger). The REVIEWER DECISION "real tempfile queue path passed via argv" is not tested; real run_* + a fake queue_links_fn writing to a tempdir file is missing - add one main() test per subcommand with real run_* and a tempfile queue path, asserting call kwargs and that stdout is exactly one JSON object.
- MED - test_a3_cli.py:55-62 - test_cli_add_link_never_calls_downloader is near-vacuous: the sys.modules scan is global (any unrelated "network" module breaks or hides it) and the rest only asserts a Mock was called - assert on a3_cli's own imports (e.g. ast of the module source or vars(a3_cli)) contain no subprocess/urllib/requests/http.
- LOW - a3_cli.py:38 - write_text_file param unused in run_add_link - document or drop.
- LOW - test_a3_cli.py:17,64,302 - hardcoded "/src", "/dest" paths and tempfile.gettempdir() shared file name; use TemporaryDirectory.
- LOW - a3_cli.py:130 - SystemExit with non-int, non-None code (e.g. string) maps to 0 - map to 1.

HAIKU (low, stand-in for GLM/MiniMax):
Summary

- wpA1: PASS (LOW only)
- wpA2: HIGH 1, MED 2
- wpA3: HIGH 0, MED 1

DECISION (reviewer conflict resolved): the spec's REVIEWER DECISIONS section is binding: main(argv) returns the integer exit code (0 ok, 1 on any rejected/failed item), not a dict.


REVIEW FINDINGS (round 5, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpA3
LUNA (gpt-6-luna medium):
MED - research/pieces/test_a3_cli.py:263-306 - The add-link main test forwards a temporary queue path but its fake queue function never writes to that file, so it does not verify the required tempfile queue-file behavior - have the fake write to the supplied path and assert the file contents.
MED - research/pieces/test_a3_cli.py:17,302,349,365 - Tests use hardcoded absolute POSIX paths such as `/src/...` and `/dest`, contrary to the requirement that tests use temporary directories - replace these paths with paths under `TemporaryDirectory` or `tmp_path`.
MED - research/pieces/test_a3_cli.py:55-69 - The import check does not prohibit `kimi`, so the no-Kimi requirement can regress without failing this test - include Kimi imports in the source check.

SONNET (latest):
wpA3
HIGH 0, MED 2
- Earlier HIGH (stub lambdas) fixed: queue_links_fn/collect_inputs_fn/queue_status_fn are required params; --queue-file wired; command="add_link"; exit 1 on rejected/error; --help gives 0.
- MED - test_a3_cli.py:171-436 - every main() test injects Mock run_* and Mock *_fn, and none asserts that argv values reach them (queue_file from --queue-file reaching queue_links_fn; dest/inputs; ledger). The REVIEWER DECISION "real tempfile queue path passed via argv" is not tested; real run_* + a fake queue_links_fn writing to a tempdir file is missing - add one main() test per subcommand with real run_* and a tempfile queue path, asserting call kwargs and that stdout is exactly one JSON object.
- MED - test_a3_cli.py:55-62 - test_cli_add_link_never_calls_downloader is near-vacuous: the sys.modules scan is global (any unrelated "network" module breaks or hides it) and the rest only asserts a Mock was called - assert on a3_cli's own imports (e.g. ast of the module source or vars(a3_cli)) contain no subprocess/urllib/requests/http.
- LOW - a3_cli.py:38 - write_text_file param unused in run_add_link - document or drop.
- LOW - test_a3_cli.py:17,64,302 - hardcoded "/src", "/dest" paths and tempfile.gettempdir() shared file name; use TemporaryDirectory.
- LOW - a3_cli.py:130 - SystemExit with non-int, non-None code (e.g. string) maps to 0 - map to 1.

HAIKU (low, stand-in):
wpA3
HIGH: none. MED: none. Verdict: PASS.
- LOW - research/pieces/a3_cli.py:186-188 - `else` branch is unreachable because the subparser is `required=True` - delete the branch or keep it with a comment.
- LOW - research/pieces/test_a3_cli.py:9 - `patch` and `MagicMock` imported and unused - remove them.
- LOW - research/pieces/test_a3_cli.py:82-92 - runtime half of test_cli_add_link_never_calls_downloader only asserts that a mock was called; the real check is the AST scan at :57-70, which is adequate - no change required, or drop the runtime half.
- LOW - research/pieces/test_a3_cli.py:273, 295, 367, 389, 497 - mock-only tests use literal "queue.txt", "q.txt", "/src/bad.mp4", "/dest" paths - harmless because run_* is mocked; switch to tempfile paths for consistency.
Checked and fixed: stub defaults removed (queue_links_fn, collect_inputs_fn, queue_status_fn are required params); --queue-file wired; command="add_link" via set_defaults at :15; exit 1 on rejected/error/FAILED_* items via _has_failed_items at :100-112; --help returns 0; real-runner tests with tempfile paths for all three subcommands exist (test_a3_cli.py:225, :316, :410, :454).


REVIEW FINDINGS (round 6, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpA3
LUNA (gpt-6-luna medium):
LOW - research/pieces/test_a3_cli.py:211 - Parser test uses hardcoded absolute `/src/vid.mp4` and `/dest` paths instead of temporary-directory paths - use paths created under `TemporaryDirectory` or `tmp_path`

SONNET (latest):
wpA3
HIGH 0, MED 2
- Earlier HIGH (stub lambdas) fixed: queue_links_fn/collect_inputs_fn/queue_status_fn are required params; --queue-file wired; command="add_link"; exit 1 on rejected/error; --help gives 0.
- MED - test_a3_cli.py:171-436 - every main() test injects Mock run_* and Mock *_fn, and none asserts that argv values reach them (queue_file from --queue-file reaching queue_links_fn; dest/inputs; ledger). The REVIEWER DECISION "real tempfile queue path passed via argv" is not tested; real run_* + a fake queue_links_fn writing to a tempdir file is missing - add one main() test per subcommand with real run_* and a tempfile queue path, asserting call kwargs and that stdout is exactly one JSON object.
- MED - test_a3_cli.py:55-62 - test_cli_add_link_never_calls_downloader is near-vacuous: the sys.modules scan is global (any unrelated "network" module breaks or hides it) and the rest only asserts a Mock was called - assert on a3_cli's own imports (e.g. ast of the module source or vars(a3_cli)) contain no subprocess/urllib/requests/http.
- LOW - a3_cli.py:38 - write_text_file param unused in run_add_link - document or drop.
- LOW - test_a3_cli.py:17,64,302 - hardcoded "/src", "/dest" paths and tempfile.gettempdir() shared file name; use TemporaryDirectory.
- LOW - a3_cli.py:130 - SystemExit with non-int, non-None code (e.g. string) maps to 0 - map to 1.


REVIEW FINDINGS (round 7, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpA3
HAIKU (low, stand-in):
MED - research/pieces/test_a3_cli.py (`test_cli_add_link_never_calls_downloader`, prohibited set) - The set omits `downloader` and `yt_dlp`, which the spec names, so importing a downloader module passes the check. Dynamic imports (`__import__`, `importlib`) are also not checked. - Add `downloader`, `yt_dlp` and `instaloader` to the prohibited set, and flag `__import__` and `importlib` calls in the AST scan.
LOW - research/pieces/a3_cli.py (`run_add_link`, `run_collect`, `run_status`, `json.dump` calls) - Default separators print `{"added": [...]}`, but the spec's stdout example is compact `{"added":[...]}`. - Use `json.dump(result, sys.stdout, separators=(",", ":"))`. The tests use `json.loads` and are unaffected.
LOW - research/pieces/a3_cli.py (`main`, `except SystemExit` branch) - `e.code if isinstance(e.code, int) else 1` maps `None` to 1, but `SystemExit(None)` means exit 0. - Map `None` to 0 and other non-int values to 1.
LOW - research/pieces/test_a3_cli.py (imports; `test_cli_add_link_never_calls_downloader`) - `import sys` is unused. `open(a3_cli.__file__).read()` leaves the handle open. The runtime half only asserts that a Mock was called, so the test name overstates what it checks. - Remove the unused import, read the source with `with open(...)`, and rename the test or drop the runtime half.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/a3_cli.py
```python
<complete module source>
```
FILE: research/pieces/test_a3_cli.py
```python
<complete test source>
```
