# SPEC LCYC: NEW `pieces/finding_lifecycle.py` and `pieces/test_finding_lifecycle.py` (isolated finding-lifecycle module for the Loop System; not wired into fix_loop.py yet)

GOAL: a pure, stdlib-only module that tracks reviewer findings across rounds with stable ids, dispositions and an append-only ledger, and decides whether a job may be accepted. It does not call any model and does not touch any other file. Wiring into the loop is a later, separate step.

REAL FACTS: the module takes no external data. Its inputs are the review reports a job writes and the job's own ledger and frozen-test files, all inside the job folder.

RULES THE MODULE ENFORCES:
- A finding has a stable id derived from (job, reviewer, file, line, normalized summary). The same finding in a later round gets the same id.
- Findings are never deleted. The ledger is append-only: each status change is a new event line. The history of every finding is preserved.
- Statuses: OPEN, RESOLVED, DISMISSED.
- A finding can become RESOLVED only with evidence: a dict containing a test id and passed == True. A RESOLVED without such evidence is refused (ValueError).
- A finding can become DISMISSED only with an adjudication: a non-empty text and a non-empty evidence_ref. For HIGH and MED findings the text must start with "EVIDENCE:" AND must contain a concrete reference: a test name matching test_\w+ or a file and line reference matching \S+\.py:\d+. Text such as "EVIDENCE: fake.py x" is refused. A missing or empty evidence_ref is refused for every severity.
- blocking_findings(ledger) returns the OPEN findings whose severity is HIGH or MED. LOW findings never block.
- can_accept(ledger, judge_verdict) returns False when blocking_findings is non-empty, whatever the judge verdict is. A judge READY never overrides an open HIGH or MED.
- Retries are bounded: attempts_allowed(max_attempts) returns False once the recorded attempt count is at or above max_attempts; record_attempt increments the count.
- Test freezing: freeze_tests(job_dir, paths) writes job_dir/frozen_tests.json with the SHA-256 of each path, and returns the dict. verify_frozen(job_dir) returns the list of paths whose current SHA-256 differs from the recorded one (an empty list when all match, or when there is no recorded file it raises ValueError).

FUNCTIONS:
- parse_findings(report_text, reviewer, round_no) -> list of dicts with keys id, reviewer, round, severity, file, line, summary. Parse only lines that begin with HIGH, MED, MEDIUM, or LOW, followed by " - ". Lines that do not match are ignored. MEDIUM is treated as MED. A line with no file and line keeps file "" and line 0.
- stable_id(job, reviewer, file, line, summary) -> string "F-" + first 12 hex characters of SHA-256 over the joined normalized fields (lowercased, whitespace collapsed). The reviewer name is included, so two reviewers reporting the same thing have two ids; the id does not depend on the round.
- Ledger file: <job_dir>/findings_ledger.jsonl, one JSON object per line: {"event": "OPENED"|"RESOLVED"|"DISMISSED", "id", "job", "reviewer", "round", "severity", "file", "line", "summary", "evidence" (or null), "adjudication" (or null), "at" (ISO time)}.
- load_ledger(job_dir) -> dict id -> current record (the last event decides the status). Missing file gives an empty dict.
- open_findings(job_dir, reviewer, round_no, report_text) -> appends one OPENED event per parsed finding whose id is not yet in the ledger, and returns the list of ids it appended. A finding already in the ledger is not appended again.
- resolve(job_dir, finding_id, evidence) -> appends a RESOLVED event. evidence must be a dict with non-empty "test" and "passed": True; otherwise ValueError.
- dismiss(job_dir, finding_id, adjudication) -> appends a DISMISSED event. adjudication must be a dict with non-empty "text" and non-empty "evidence_ref". For HIGH or MED, the text must start with "EVIDENCE:". Otherwise ValueError.
- blocking_findings(job_dir) -> list of OPEN records with severity HIGH or MED.
- can_accept(job_dir, judge_verdict) -> bool, as in RULES.
- record_attempt(job_dir) and attempts_allowed(job_dir, max_attempts) -> bool.
- freeze_tests(job_dir, paths) and verify_frozen(job_dir) as in RULES. Paths are relative to the repository root given by the parameter root; the function takes root as its first argument: freeze_tests(root, job_dir, paths) and verify_frozen(root, job_dir).

HARD RULES:
- Standard library only: json, hashlib, os, re, datetime. No network, no subprocess, no model call.
- Writes only inside the job_dir passed in. Never write outside it.
- No absolute drive path in the module or tests. Tests use tmp_path.
- Do not write the seven-letter name of the 3D software tool anywhere.
- No comment may begin with a tool name followed by a colon.

TESTS for `pieces/test_finding_lifecycle.py` (pytest, tmp_path only; each test must FAIL for a deliberately wrong implementation; for each rule above include one test that would catch its violation):
1. parse_findings reads a sample report with one HIGH, one MEDIUM, one LOW and one non-finding line; returns three findings with severities HIGH, MED, LOW. For each finding the test asserts the exact file, line and summary values; a located finding has its file and line; an unlocated finding has file "" and line 0. A wrong file, line or summary must fail the test.
2. stable_id is identical for the same finding in two rounds and differs between two reviewers reporting the same text.
3. open_findings appends each finding once: calling it twice with the same report appends zero the second time.
4. A RESOLVED without evidence raises ValueError; with evidence {"test": "t", "passed": False} raises ValueError; with {"test": "t", "passed": True} appends the event and the status becomes RESOLVED.
5. A DISMISSED of a MED without "EVIDENCE:" text raises ValueError; with "EVIDENCE:" text and an evidence_ref it appends.
6. Ledger history is kept: after RESOLVED, the ledger file has both the OPENED and the RESOLVED lines.
7. blocking_findings returns only OPEN HIGH and MED; a LOW OPEN finding is not blocking; a RESOLVED HIGH is not blocking.
8. can_accept is False when a MED is OPEN, even with judge_verdict "READY"; True when no blocking finding is OPEN.
9. attempts_allowed is True below max, False at max; record_attempt increments the count and persists it.
10. freeze_tests then verify_frozen returns [] before any change; after changing one frozen file, verify_frozen returns that path.
11. verify_frozen raises ValueError when no frozen_tests.json exists.
RAW-BYTE FREEZE (added 2026-10-31, after Codex review; a false-PASS otherwise): the freeze digest is the SHA-256 of the file's raw bytes. Line endings are NOT normalised. A test writes a frozen file, rewrites the same text with CRLF line endings, and asserts that verify_frozen reports that path. A content change is also reported.
HIGH DISMISSAL (added 2026-10-31, Opus final review; single item): a dismissal of a HIGH finding is tested exactly like a MED one. dismiss() of a HIGH finding with adjudication text "EVIDENCE: fake.py x" raises ValueError, and the same HIGH with text "EVIDENCE: test_real_check" and a non-empty evidence_ref appends the DISMISSED event. A HIGH finding can never be dismissed without a concrete reference.
12. Nothing is written outside job_dir: after a full sequence of calls, every new file under tmp_path is inside the job_dir.

REPLY RULE: return the complete source of both files. Do not add any other text.
REPLY PARSER TRAP: no line of any file you write may start with the letters F-I-L-E followed by a colon.
FORBIDDEN-WORD TRAP: the loop refuses any file containing the seven-letter name of the 3D software tool. Never type it.

OUTPUT FORMAT (mandatory): reply with ONLY these two blocks, no other text. Each block starts with the line `FILE: <path>` directly followed by a fenced code block starting with ```python on its own line and ending with ``` on its own line:
FILE: pieces/finding_lifecycle.py
```python
<complete source>
```
FILE: pieces/test_finding_lifecycle.py
```python
<complete source>
```
