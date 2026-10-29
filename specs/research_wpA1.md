
# WP-A1: Link Queue Management (queue_links + queue_status)

## Data Shapes (plain dicts, no imports between atomic specs)
# Normalized URL: "https://www.instagram.com/reel/ABC123/"
# Queue file line: normalized URL string, or comment line starting with '#'
# Ledger entry (from instagram_import_log.json):
#   {"url": "https://www.instagram.com/reel/ABC123/", "status": "DOWNLOADED", "error": null, "timestamp": "2024-01-15T10:30:00Z"}
#   {"url": "https://www.instagram.com/reel/FAIL456/", "status": "FAILED_INACCESSIBLE", "error": "Private account", "timestamp": "2024-01-15T10:31:00Z"}

## Public Functions (≤3)

### 1. queue_links(urls, queue_file, normalize_reel_url, clock_now)
# urls: list[str] raw URLs
# queue_file: str path to queue file (may not exist)
# normalize_reel_url: callable(str) -> str | None  (returns normalized or None if invalid)
# clock_now: callable() -> str  (ISO timestamp for any future use, not used in return but injected)
# Returns: {"added": list[str], "already_queued": list[str], "rejected": list[{"url": str, "error": str}], "status": "ok"}

WORKED EXAMPLE:
Input:
  urls = [
    "https://instagram.com/reel/ABC123/",
    "https://www.instagram.com/reel/ABC123/?utm_source=ig",
    "https://instagram.com/reel/NEW789/",
    "not-a-url",
    "https://instagram.com/p/POST123/"
  ]
  queue_file = "test_queue.txt"  (initially contains:
    # comment line
    https://www.instagram.com/reel/ABC123/
  )
  normalize_reel_url = lambda u: "https://www.instagram.com/reel/ABC123/" if "ABC123" in u else ("https://www.instagram.com/reel/NEW789/" if "NEW789" in u else None)
  clock_now = lambda: "2024-01-15T10:30:00Z"

Output:
  {
    "added": ["https://www.instagram.com/reel/NEW789/"],
    "already_queued": ["https://www.instagram.com/reel/ABC123/"],
    "rejected": [
      {"url": "not-a-url", "error": "Invalid Instagram Reel URL"},
      {"url": "https://instagram.com/p/POST123/", "error": "Invalid Instagram Reel URL"}
    ],
    "status": "ok"
  }
  # queue_file now contains (order preserved, comments kept):
  # # comment line
  # https://www.instagram.com/reel/ABC123/
  # https://www.instagram.com/reel/NEW789/

### 2. queue_status(queue_file, ledger_path, read_text_file, parse_json_lines)
# queue_file: str path
# ledger_path: str path to instagram_import_log.json (JSON Lines)
# read_text_file: callable(str) -> str  (reads entire file)
# parse_json_lines: callable(str) -> list[dict]  (parses JSON Lines)
# Returns: {"items": list[{"url": str, "state": "QUEUED"|"DOWNLOADED"|"FAILED_INACCESSIBLE", "error": str|null}], "status": "ok"}

WORKED EXAMPLE:
Input:
  queue_file = "test_queue.txt"  (contains:
    # comment
    https://www.instagram.com/reel/ABC123/
    https://www.instagram.com/reel/NEW789/
    https://www.instagram.com/reel/FAIL456/
  )
  ledger_path = "test_log.jsonl"  (contains two lines:
    {"url": "https://www.instagram.com/reel/ABC123/", "status": "DOWNLOADED", "error": null, "timestamp": "2024-01-15T10:30:00Z"}
    {"url": "https://www.instagram.com/reel/FAIL456/", "status": "FAILED_INACCESSIBLE", "error": "Private account", "timestamp": "2024-01-15T10:31:00Z"}
  )
  read_text_file = lambda p: open(p).read()
  parse_json_lines = lambda s: [json.loads(l) for l in s.strip().split('\n') if l]

Output:
  {
    "items": [
      {"url": "https://www.instagram.com/reel/ABC123/", "state": "DOWNLOADED", "error": null},
      {"url": "https://www.instagram.com/reel/NEW789/", "state": "QUEUED", "error": null},
      {"url": "https://www.instagram.com/reel/FAIL456/", "state": "FAILED_INACCESSIBLE", "error": "Private account"}
    ],
    "status": "ok"
  }

### 3. read_queue_file(queue_file, read_text_file)
# queue_file: str path
# read_text_file: callable(str) -> str
# Returns: {"urls": list[str], "comments": list[str], "status": "ok"}  (urls in order, comments are lines starting with '#')

WORKED EXAMPLE:
Input:
  queue_file = "test_queue.txt"  (contains:
    # first comment
    https://www.instagram.com/reel/ABC123/
    # second comment
    https://www.instagram.com/reel/NEW789/
  )
  read_text_file = lambda p: open(p).read()

Output:
  {
    "urls": ["https://www.instagram.com/reel/ABC123/", "https://www.instagram.com/reel/NEW789/"],
    "comments": ["# first comment", "# second comment"],
    "status": "ok"
  }

## Test Requirements (test_a1_queue.py)
- test_queue_links_dedupe_and_rejects: covers worked example + empty input + all invalid + queue file missing
- test_queue_status_three_states: covers worked example + URL in queue but not in ledger = QUEUED, URL in ledger as DOWNLOADED, URL in ledger as FAILED_INACCESSIBLE with error text
- test_read_queue_file_preserves_comments_and_order
- test_add_link_cli_never_calls_downloader: mock normalize_reel_url, verify no network calls (stdlib only)
REVIEWER DECISIONS (resolve spec gaps; tests must follow these): every list in a result (added, already_queued, rejected) contains each URL AT MOST ONCE, even if the same URL appears several times in one input batch (first occurrence decides its bucket). Tests must NOT patch pathlib.Path methods (exists/read_text/write_text); to prove nothing is downloaded, patch a downloader/subprocess/requests entry point to raise if called, and use real tempfile directories.


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/a1_queue.py; test file: research/pieces/test_a1_queue.py (tests import the module by its plain file name, e.g. `from a1_queue import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpA1

**Verdict: TEST is wrong; CODE matches spec.**

Rounds 1-3 never ran tests: every coder call failed (`status=0, empty=True`, see status.json), so the loop re-ran the round-0 files three times. The escalation is an API/transport failure, not three failed fix attempts.

Real failure (reproduced under `uv run pytest`, the project venv): 12 pass, 1 fails.

- `test_add_link_cli_never_calls_downloader` fails with `ModuleNotFoundError: No module named 'requests'`. `patch("requests.get")` has to import `requests`, which is not a dependency (project deps: pyyaml, jsonschema, pytest; HARD RULES: stdlib only). It passes only on a system Python that happens to have requests installed.

Fix (test only):
1. Drop the `patch("requests.get")` line and its assertion entirely.
2. Keep `subprocess.run` and `urllib.request.urlopen` (both stdlib). Per REVIEWER DECISIONS, give them `side_effect=AssertionError("downloader called")` so a call raises, instead of only checking `assert_not_called()` afterwards. Optionally add `subprocess.Popen` and `http.client.HTTPSConnection` the same way.
3. Leave everything else unchanged. It already uses real tempfile dirs and does not patch pathlib.

Code check against spec: in-batch dedupe with first occurrence deciding the bucket (REVIEWER DECISIONS) is implemented, as are the worked examples, missing queue file, kept comments and order. Optional cleanup, not needed to pass: the unused `import json` in a1_queue.py.

Also fix the loop: a coder call that returns status 0 or an empty reply should retry or report "coder unreachable", not count as a fix round.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/a1_queue.py
```python
<complete module source>
```
FILE: research/pieces/test_a1_queue.py
```python
<complete test source>
```
