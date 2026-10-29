# WP-F1: cumulative corpus ledger (no network, no model calls, no Kimi). Each test uses tmp dirs.
Immutable per-video results + one ledger. Ledger JSON: {"schema":1,"videos":{sha256:{...}}}.
1. `corpus_add(ledger_path, entry)` -> {"status":"ADDED"|"UPDATED"|"DUPLICATE","video_key":sha256}. entry keys: sha256, kind ("video"|"image_sequence"), analysis_path, analyzed_at, versions {"analysis":str,"prompt":str,"model":str}, sources [{"source":str,"origin":"local"|"instagram","url":str|None,"creator_id":str|None}], tags dict. Key is the CONTENT hash; source identity is separate: a second entry with the same sha256 but a different url/source APPENDS to that video's "sources" list (status DUPLICATE) so attribution is kept. Same sha256 + same versions + same sources => UPDATED no-op. Atomic write (tmp+replace), utf-8; corrupt ledger raises ValueError, never silently resets.
2. `corpus_status(ledger_path, queue_urls)` -> {"analyzed":n,"queued_not_analyzed":[urls with no ledger source],"failed":[urls given in a failed list param default []],"total":n}. Queued links are never counted as analyzed.
3. `stale_entries(ledger_path, current_versions)` -> sorted list of sha256 whose versions.analysis or versions.prompt differ from current_versions (model change alone => not stale unless flag strict=True). Rebuild after reporting-rule-only change needs no re-analysis.
Worked example: add A(sha "aa", url u1), add B("bb", u2), add "aa" again with url u3 => ADDED, ADDED, DUPLICATE and A has 2 sources; corpus_status(queue [u1,u4]) => queued_not_analyzed ["u4"]; stale_entries with analysis version "2" vs stored "1" => ["aa","bb"].
ADDITIONS (reviewer-agreed):
4. sha256 = hash of the raw video file bytes; for image_sequence = sha256 of the ORDERED frame manifest defined in FINAL CORRECTION below. Normalize URLs (lowercase host, strip query and trailing slash) before comparing sources; dedupe sources by normalized url (or by `source` path when url is None) so a deleted-URL source is not collapsed with another.
5. Same sha256 with DIFFERENT versions => replace the analysis fields (analysis_path, versions, analyzed_at, tags), union sources, status "UPDATED", and push the prior {analyzed_at, analysis_path, versions} onto a `history` list. `corpus_add` returns also "sources_added": n. stale_entries returns [{"sha256","reason"}].
FINAL CORRECTION: image_sequence identity MUST preserve temporal order. Sort frames by numeric frame index parsed from the filename (natural sort), then sha256 an ordered manifest of lines "<position>:<frame_content_sha256>". Filenames do not matter beyond ordering. Tests: A-B-C and C-B-A give DIFFERENT identities; identical ordered content under different filenames gives the SAME identity. Raw-file sha256 stays for exact MP4 dedupe; it is NOT perceptual duplicate detection (a re-encoded video is a different video here, say so in the docstring).


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/f1_corpus.py; test file: research/pieces/test_f1_corpus.py (tests import the module by its plain file name, e.g. `from f1_corpus import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF1 (f1_corpus.py, test_f1_corpus.py)
Verdict: 0 HIGH, 2 MED, 4 LOW
- MED - f1_corpus.py:261-297 - same sha256 + SAME versions + no new sources but different analysis_path/analyzed_at/tags is treated as an analysis change: it pushes a history record, overwrites the analysis, and returns DUPLICATE with sources_added 0. Spec: replacement and history happen only when versions differ; same versions+same sources is an UPDATED no-op; DUPLICATE is for a new source. Re-adding an identical analysis with a fresh timestamp bloats history and rewrites the ledger. - Fix: compute analysis_fields_changed from versions_changed only; when versions equal, only union sources (no history, no overwrite); return UPDATED no-op if no new sources.
- MED - f1_corpus.py:282-285 - when a duplicate entry adds a new source with the same versions, the code still overwrites analysis_path/analyzed_at/tags of the stored analysis with the incoming entry's. Same root cause as above; attribution add should leave the immutable analysis alone. Not tested. - Fix: as above plus a test (add same sha, same versions, different analysis_path + new url; assert analysis_path unchanged, history empty).
- LOW - f1_corpus.py:112 - query stripping makes every `youtube.com/watch?v=ID` collapse to one URL (spec mandates stripping; scheme not lowercased). Noted only.
- LOW - f1_corpus.py:91 - frames whose natural-sort keys tie (frame_01 vs frame_1, Frame_1 vs frame_1) are ordered by iterdir order, so identity is nondeterministic. - Fix: add the filename as a tiebreaker.
- LOW - f1_corpus.py:169-174 - tmp file is leaked if json.dump raises (non-serializable tags); no fsync. - Fix: try/except unlink.
- LOW - test_f1_corpus.py:211-217 - test_atomic_write only checks the file is valid JSON; it does not test atomicity (no leftover .tmp / replace failure). No test for history-with-unchanged-versions, kind mismatch, or the exact worked-example sequence (u1,u2,u3 then status queue [u1,u4]).


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF1
LUNA (gpt-6-luna high):
MED - research/pieces/f1_corpus.py:162-171 - A ledger with malformed nested data such as `"versions": null` passes loading, then `stale_entries` raises `AttributeError` instead of the required `ValueError` - Validate nested ledger field types and raise `LedgerError` for invalid data.

MED - research/pieces/f1_corpus.py:239-246 - `corpus_add` accepts and stores malformed sources such as `{}`, despite the required source fields and allowed `origin` values - Validate each source’s fields and types before deduping or storing it.

LOW - research/pieces/f1_corpus.py:184-185 - If `json.dump` fails, `tmp_path` is still `None`, so the exception handler cannot remove the temporary file - Assign the temp path before dumping, then verify cleanup on serialization failure.

LOW - research/pieces/f1_corpus.py:93 - Names differing only by case have identical sort keys, leaving their order dependent on directory iteration and making the sequence hash nondeterministic - Use the exact filename as a final tiebreaker.

LOW - research/pieces/test_f1_corpus.py:248-254 - `test_atomic_write_cleans_up_on_error` is a `pass`, so it provides no evidence that failed writes clean up temporary files - Simulate a dump or replace failure and assert the temporary file is removed.

SONNET (latest):
wpF1
Prior MED/LOW findings verified fixed: history/overwrite only when versions differ; same-versions + new source leaves analysis untouched (tests at test_f1_corpus.py:311,332); natural-sort tiebreak on filename (f1_corpus.py:93); tmp file cleaned on error (:187-193); worked-example, kind-mismatch, A-B-C vs C-B-A tests present.
- LOW - f1_corpus.py:296-299 - stored `versions`/`tags` are the caller's dict objects (aliasing); later caller mutation changes the in-memory entry before save. - Fix: copy.deepcopy on store.
- LOW - f1_corpus.py:175-193 - no fsync before os.replace. - Fix: flush+os.fsync in the tmp write.
PASS


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF1
LUNA (gpt-6-luna medium):
MED - research/pieces/f1_corpus.py:148-161 - Source validation does not check that `source` and `origin` are strings; malformed values can be stored, or an unhashable `source` can raise `TypeError` during deduplication instead of being rejected as invalid - Validate both field types before deduping or storing sources.

SONNET (latest):
wpF1
Prior MED/LOW findings verified fixed: history/overwrite only when versions differ; same-versions + new source leaves analysis untouched (tests at test_f1_corpus.py:311,332); natural-sort tiebreak on filename (f1_corpus.py:93); tmp file cleaned on error (:187-193); worked-example, kind-mismatch, A-B-C vs C-B-A tests present.
- LOW - f1_corpus.py:296-299 - stored `versions`/`tags` are the caller's dict objects (aliasing); later caller mutation changes the in-memory entry before save. - Fix: copy.deepcopy on store.
- LOW - f1_corpus.py:175-193 - no fsync before os.replace. - Fix: flush+os.fsync in the tmp write.
PASS

HAIKU (low, stand-in):
Summary

- wpE1: HIGH 0, MED 1 (FAIL)
- wpE2: HIGH 0, MED 1 (FAIL)
- wpF1: HIGH 0, MED 3 (FAIL)
- wpF2: HIGH 0, MED 1 (FAIL)


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF1
LUNA (gpt-6-luna medium):
MED - research/pieces/f1_corpus.py:148 - `_validate_source` does not require `source` and `origin` to be strings; an unhashable `source` with `url=None` can raise `TypeError` during deduplication instead of being rejected as invalid - Validate both field types before deduplication or storage.

SONNET (latest):
wpF1
Prior MED/LOW findings verified fixed: history/overwrite only when versions differ; same-versions + new source leaves analysis untouched (tests at test_f1_corpus.py:311,332); natural-sort tiebreak on filename (f1_corpus.py:93); tmp file cleaned on error (:187-193); worked-example, kind-mismatch, A-B-C vs C-B-A tests present.
- LOW - f1_corpus.py:296-299 - stored `versions`/`tags` are the caller's dict objects (aliasing); later caller mutation changes the in-memory entry before save. - Fix: copy.deepcopy on store.
- LOW - f1_corpus.py:175-193 - no fsync before os.replace. - Fix: flush+os.fsync in the tmp write.
PASS


REVIEW FINDINGS (round 5, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF1
HAIKU (low, stand-in):
MED - research/pieces/f1_corpus.py:264-283, 306 and 348 - `corpus_add` does not validate `sha256` (must be a non-empty str) or `tags` (must be a dict). A non-str sha256 or `tags=None` is written, and then `_load_ledger` rejects the whole ledger on every later call ("Video key mismatch" / "Invalid tags"). - Validate `sha256` as a non-empty str and `tags` and `versions` as dicts before touching the ledger, raising ValueError, with a test.
LOW - research/pieces/f1_corpus.py:119 - A root URL keeps its trailing slash (`https://example.com/` stays as is), so it does not dedupe with `https://example.com`. - Strip trailing `/` from the final path.
LOW - research/pieces/f1_corpus.py:48 - `urlparse` and `urlunparse` are imported but unused. - Delete the import.
LOW - research/pieces/f1_corpus.py:89-94 - An empty frame directory yields a valid identity (sha256 of an empty manifest), so unrelated empty sequences collapse to one key. - Raise ValueError when no frames are found.
LOW - research/pieces/test_f1_corpus.py:370-374 - No test covers malformed sources (`{}`, non-str `source`, unhashable `source`), although the code now rejects them. - Add a loop over these cases asserting the error.
LOW - research/pieces/test_f1_corpus.py:477-493 - `test_worked_example_sequence` never asserts the first two statuses (ADDED, ADDED). - Assert them.
LOW - research/pieces/test_f1_corpus.py:612-621 - `test_raw_video_sha256_not_perceptual` only checks that different bytes hash differently, which is a sha256 property, so it does not test the docstring claim. - Remove it, or assert that the module docstring states the not-perceptual limit.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/f1_corpus.py
```python
<complete module source>
```
FILE: research/pieces/test_f1_corpus.py
```python
<complete test source>
```
