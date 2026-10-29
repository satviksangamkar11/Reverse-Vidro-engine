# WP-F3: single aggregation writer + snapshot publication (up to 4 small public functions; cohesive, do not split artificially) (stdlib only; tmp dirs in tests)
1. `corpus_lock(lock_path)` context manager: OS-backed exclusive non-blocking lock exactly as defined in FINAL CORRECTION below; a second acquirer raises RuntimeError("LOCKED"); released on exit even after an exception.
2. `snapshot(ledger_path)` -> deep-copied dict of the ledger read once (so aggregation sees one consistent state); raises ValueError on corrupt JSON; returns videos sorted by sha256.
3. `publish(out_dir, files, validate=None, retries=5, sleep=time.sleep)`: files = {name: text}. Builds an IMMUTABLE snapshot folder out_dir/snapshots/build_NNN/ (NNN = next zero-padded number, never reused or modified afterwards), validates every file (non-empty; .json must parse; optional validate(name,text)->None or error str), and ONLY if all pass atomically replaces the single small pointer file out_dir/CURRENT.json ({"build":"build_NNN","files":[names],"published_at":str}) via tmp + os.replace, retrying on PermissionError/sharing violations up to `retries`. On any failure CURRENT.json is untouched (still points at the previous complete snapshot) and the half-built folder is removed or marked incomplete. Returns {"build":..., "published":[names]}.
4. `read_current(out_dir)` -> {"build","dir","files":{name:text}}: resolves CURRENT.json ONCE and loads all files from that same snapshot folder; raises ValueError if the pointed snapshot is missing a file. Readers never read loose files.
Worked example: publish #1 then publish #2 whose validation fails => read_current still returns build_001 with all three files. A simulated crash (exception raised after the snapshot folder is written, before the pointer replace) leaves read_current returning the previous complete build. Two threads call corpus_lock; second gets LOCKED. Rebuilding twice from one snapshot gives identical file text.
Note: os.replace on the pointer is the only publish step; do not claim stronger atomicity than that.
ADDITIONS (reviewer-agreed):
5. `publish` acquires corpus_lock itself (path out_dir/.lock) so snapshot->publish cannot race. Build numbers are max_existing+1 and never reused, even after a failed build (orphan folders without a complete manifest are ignored by read_current). Each snapshot contains manifest.json {"files":{name:sha256}}; read_current verifies it. Missing/corrupt CURRENT.json => ValueError("NO_SNAPSHOT").
FINAL CORRECTION: replace the custom stale-lock takeover with an OS-backed exclusive lock. Use msvcrt.locking (Windows) / fcntl.flock (POSIX) on an open lock file held for the whole `corpus_lock` context; the OS releases it when the process exits, so no stale recovery code exists. Only the holder may replace CURRENT.json: publish checks it is inside the lock context (raise RuntimeError("NOT_LOCK_HOLDER") otherwise). Second acquirer in another thread/process gets RuntimeError("LOCKED") immediately (non-blocking). Remove stale_seconds/uuid logic. Readers need no lock: they resolve CURRENT.json once and load every file from that one snapshot folder.


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/f3_publish.py; test file: research/pieces/test_f3_publish.py (tests import the module by its plain file name, e.g. `from f3_publish import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
Sonnet G4 review (wpF2, wpF3, wpF4). All 72 tests in the three files pass; findings below are spec/edge/test-quality defects.


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF3
LUNA (gpt-6-luna high):
MED - research/pieces/f3_publish.py:205 - A failed build is deleted, so its build number is reused on the next publish, contrary to the never-reuse rule. - Keep a failed build as an incomplete orphan or persist a build counter; update the test to expect the next unused number.

MED - research/pieces/f3_publish.py:93 - `snapshot` sorts `videos` only when it is a list; dictionary-shaped ledgers are returned unsorted. - Sort dictionary entries by SHA-256 key and add coverage for that ledger shape.

MED - research/pieces/f3_publish.py:168 - With `retries <= 0`, the replace loop never runs, yet `publish` returns success while `CURRENT.json` remains unchanged. - Reject nonpositive retries or ensure at least one replace attempt.

MED - research/pieces/f3_publish.py:148 - Text-mode writes translate newlines on Windows, so manifest hashes can differ from the published file text and `read_current` can reject a successful build. - Disable newline translation on writes and reads, and hash the exact UTF-8 bytes stored.

MED - research/pieces/f3_publish.py:117 - The lock-holder check is tautological inside `publish`’s own lock context, and the corresponding test is a bare `pass`; it does not verify the required rejection when the lock is not held. - Track ownership for the specific lock path and add a test that exercises the `NOT_LOCK_HOLDER` failure.

LOW - research/pieces/f3_publish.py:147 - File names are not constrained; a reserved `manifest.json` entry is overwritten by the generated manifest, and traversal names can write outside the snapshot. - Reject reserved names and path separators/traversal components.

LOW - research/pieces/f3_publish.py:234 - Valid JSON with a non-object top level for `CURRENT.json` raises `AttributeError` instead of `ValueError("NO_SNAPSHOT")`. - Validate the parsed value’s type before accessing fields.

LOW - research/pieces/test_f3_publish.py:263 - The lock-holder test contains no assertions and passes vacuously. - Replace the `pass` with an assertion that the non-holder case raises `RuntimeError("NOT_LOCK_HOLDER")`.

SONNET (latest):
wpF3
- MED - f3_publish.py:148,170 (and 154) - files are written with text mode `open(...,"w")` (no newline=""), so on Windows "\n" becomes "\r\n" on disk and any text containing "\r\n" becomes "\r\r\n" and reads back different; the manifest sha256 is computed on the original text, so read_current raises NO_SNAPSHOT for a snapshot that just published fine (verified: publish({'a.txt':'x\r\ny'}) then read_current -> NO_SNAPSHOT). - Fix: open(..., "w", encoding="utf-8", newline="") for writes and newline="" for reads in read_current.
- MED - f3_publish.py:168-200 - retries<=0 skips the loop; the for-else has last_err None so nothing is raised, CURRENT.json is never replaced, yet publish returns {"build":"build_002",...} (verified) while the pointer still names build_001, and the unreferenced build folder is kept. - Fix: use max(1,retries) attempts or raise ValueError if retries<1.
- MED - f3_publish.py:205 + test_f3_publish.py:229-237 - spec: build numbers "never reused, even after a failed build". On failure the build folder is rmtree'd, so the next publish reuses build_002; the test named "never_reused" asserts exactly that reuse (build_002). - Fix: on failure keep the folder (write an INCOMPLETE marker / no manifest; read_current already ignores it) or persist a counter, and change the test to expect build_003.
- MED - f3_publish.py:93 + test_f3_publish.py:77-99 - snapshot sorts only when ledger["videos"] is a list, but the F1 ledger schema is {"videos": {sha256: {...}}} (a dict); the dict is returned unsorted (verified order ['bb','aa']), and the test only covers an invented list shape. Spec requires videos sorted by sha256. - Fix: also handle dict (rebuild as dict(sorted(items))); add test with the real F1 dict shape.
- LOW - f3_publish.py:135-147 - file names are not checked, so "../x" or an absolute name writes outside build_dir (and manifest names can escape on read). - Fix: reject names with path separators / "..".
- LOW - f3_publish.py:234-236 - CURRENT.json valid JSON but not an object (list/null) raises AttributeError instead of ValueError("NO_SNAPSHOT"). - Fix: isinstance(dict) check.
- LOW - f3_publish.py:117 - NOT_LOCK_HOLDER check is tautological (set by corpus_lock a few lines earlier); the test at test_f3_publish.py:263 cannot show a real bypass. Noted only.


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF3
Why it failed: same pattern. Round 0 files parsed but pytest failed (output lost). Round 1 returned only the test file (f3_publish.py missing), so the format failed. Rounds 2-3 were codex status 0 API failures. The restored code is still the original: none of the 5 MED findings are applied. Seven findings plus the original spec made the rewrite too big for one reply.

Fixes still needed (HIGH first):
1. MED publish: on failure keep the build folder (no manifest, ignored by read_current) so the next publish gets build_003; change the test named never_reused to expect build_003.
2. MED publish and read_current: write with encoding utf-8 and newline="" and read with newline="" so text containing newlines hashes identically; add a test with "x\r\ny".
3. MED publish: raise ValueError if retries < 1 (before creating any folder).
4. MED snapshot: sort videos by sha256 when it is a dict (rebuild dict(sorted(items))) as well as a list; add a test with the real F1 dict shape.
5. LOW publish: reject file names that are manifest.json, contain path separators, "..", or are absolute; read_current: CURRENT.json that is not a dict raises ValueError("NO_SNAPSHOT").

Drop: the NOT_LOCK_HOLDER finding (both reviewers note it is tautological inside publish; keep the check, just replace the vacuous `pass` test with one that calls the check outside the lock, only if cheap). Sonnet and Luna list the same MEDs, so apply each once. Ask for both FILE blocks.


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF3
LUNA (gpt-6-luna medium):
LOW - research/pieces/f3_publish.py:277 - A malformed manifest with a non-object top level raises `AttributeError` at `manifest.get(...)` instead of `ValueError("NO_SNAPSHOT")`. - Validate the manifest and its `files` field types before accessing them.

LOW - research/pieces/f3_publish.py:268 - `read_current` joins the unvalidated `build` value from `CURRENT.json` to `snapshots`; a traversal value can resolve outside the snapshots directory. - Require a valid `build_NNN` name before resolving the snapshot path.

SONNET (latest):
wpF3
Why it failed: same pattern. Round 0 files parsed but pytest failed (output lost). Round 1 returned only the test file (f3_publish.py missing), so the format failed. Rounds 2-3 were codex status 0 API failures. The restored code is still the original: none of the 5 MED findings are applied. Seven findings plus the original spec made the rewrite too big for one reply.

Fixes still needed (HIGH first):
1. MED publish: on failure keep the build folder (no manifest, ignored by read_current) so the next publish gets build_003; change the test named never_reused to expect build_003.
2. MED publish and read_current: write with encoding utf-8 and newline="" and read with newline="" so text containing newlines hashes identically; add a test with "x\r\ny".
3. MED publish: raise ValueError if retries < 1 (before creating any folder).
4. MED snapshot: sort videos by sha256 when it is a dict (rebuild dict(sorted(items))) as well as a list; add a test with the real F1 dict shape.
5. LOW publish: reject file names that are manifest.json, contain path separators, "..", or are absolute; read_current: CURRENT.json that is not a dict raises ValueError("NO_SNAPSHOT").

Drop: the NOT_LOCK_HOLDER finding (both reviewers note it is tautological inside publish; keep the check, just replace the vacuous `pass` test with one that calls the check outside the lock, only if cheap). Sonnet and Luna list the same MEDs, so apply each once. Ask for both FILE blocks.


REVIEW FINDINGS (round 5, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF3
HAIKU (low, stand-in):
MED - f3_publish.py:publish (file-name checks) - a Windows drive-prefixed name such as `"C:evil.txt"` passes every check (no `/`, no `..`, not absolute), and `os.path.join(build_dir, "C:evil.txt")` on Windows resolves to `C:evil.txt` on drive C, outside the snapshot folder. - Reject any name containing `":"`, and add a test asserting `ValueError` for `{"C:evil.txt": "x"}`.
MED - test_f3_publish.py:test_publish_acquires_lock_internally - the two threads may run one after the other, since `publish` is fast and the barrier only aligns their start. Both can then succeed, so `assertEqual(len(errors), 1)` fails intermittently. - Make it deterministic: hold `corpus_lock(os.path.join(self.out_dir, ".lock"))` in the main thread, call `publish` from a worker thread, and assert it raises `RuntimeError("LOCKED")`.
LOW - f3_publish.py:read_current (`build_name.startswith`) - a non-string `build` (for example `5`) raises AttributeError instead of `ValueError("NO_SNAPSHOT")`. A non-hashable entry in `files` raises TypeError inside `set(...)`. Invalid UTF-8 raises UnicodeDecodeError, not NO_SNAPSHOT. - Check `isinstance(build_name, str)` and that `files` is a list of strings, and wrap the reads so decode errors become NO_SNAPSHOT.
LOW - f3_publish.py:read_current (manifest loop) - manifest keys are joined to `build_dir` without the name checks that publish applies, so a tampered manifest key such as `"../../x"` reads outside the snapshot. - Apply the same name validation on read.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/f3_publish.py
```python
<complete module source>
```
FILE: research/pieces/test_f3_publish.py
```python
<complete test source>
```
