# SPEC: NEW `research/pieces/g2_autoloop_cli.py` + NEW `research/pieces/test_g2_autoloop_cli.py` (real wiring for the autonomous cycle; every external call goes through an injectable `runner`; no model calls here except via the named scripts; no Kimi)

Goal: connect `g1_autoloop.run_cycles` to the real tools so the loop runs by itself with NO Claude tokens. Import g1 by path: `sys.path.insert(0, str(Path(__file__).parent))` then `from g1_autoloop import run_cycles, decide, merge_findings`.

Constants (all overridable by function arguments, never absolute drive paths hard-coded inside functions): REPO = Path(__file__).resolve().parents[2]; TOOLS = REPO.parent / "animation_research_tool" / "_loop"; MODULE_OF = dict mapping piece id -> module name (wpA1 a1_queue, wpA2 a2_collect, wpA3 a3_cli, wpB1 a1_audio_io, wpB2 a2_transcribe, wpB3 a3_align, wpC1 c1_cluster, wpC2 c2_review, wpC3 c3_state, wpD1 d1_beat_schema, wpD2 d2_recipe_compiler, wpD3 d3_deliverables, wpD4 d4_reconstruct, wpE1 a1_scene_selection, wpE2 a2_recipe_prompts, wpE3 a3_blind_scoring, wpF1 f1_corpus, wpF2 f2_bias, wpF3 f3_publish, wpF4 f4_classify).

1. `build_deps(repo, tools, runner, reviews_dir)` returns the deps dict for run_cycles:
   - `get_state(id)`: job = value of `<repo>/_loop/research_<id>/status.json` field "state" (or "missing" if the file does not exist or is unreadable); tests_green = `runner(["uv","run","python","-m","pytest","-q","--tb=no","research/pieces/test_<module>.py"], cwd=repo)` returncode == 0; last_review/changed_since_review/escalations are kept in a small json file `<repo>/_loop/autoloop_state.json` (atomic tmp+replace write, utf-8; a corrupt file raises ValueError, never silently resets); changed_since_review is True when the module or test file mtime is newer than the stored review time.
   - `relaunch(id)`: removes `<repo>/_loop/research_<id>` and starts `uv run python scripts/source/fix_loop.py --job _loop/jobs/research_<id>.json` through `runner(..., background=True)`.
   - `run_reviewers(id)`: runs `python <tools>/luna_review.py <id>` through runner (waits), then reads `<reviews_dir>/combined_<id>.md` and returns {"luna": text, "glm": text, "minimax": text} by splitting on the headings `LUNA`, `GLM 5.3 Flash`, `MiniMax M3.1 Flash`; a missing heading means that reviewer returned PASS or NO_REVIEW (the combined file only contains reviewers with findings), represented as "NO_REVIEW" if the run failed, else "PASS".
   - `apply_findings(id, text)`: writes the text to `<reviews_dir>/auto_<id>.md` and runs `python <tools>/apply_review.py <that file> <id>` through runner.
   - `escalate(id)`: reads `_loop/research_<id>/ESCALATE.md`, the spec `docs/pilot/nemotron_specs/research_<id>.md`, the module and test, calls the injectable `diagnose(prompt)->str` (default: Nemotron 3 Ultra via `animation_research_tool/nvidia_scheduler.NvidiaScheduler`, thinking on, medium; keys read from `<repo>/../secrets/nvidia/nvidia_api_key*.txt`, never printed or logged), writes the diagnosis to `<reviews_dir>/diag_<id>.md` and applies it with apply_review.py like apply_findings.
2. `main(argv, runner=None, diagnose=None)`: argparse with `--ids` (default all 20), `--max-cycles` (default 50), `--sleep` (default 60), `--dry-run`. With --dry-run it prints the decide() action per piece (via get_state + decide) as one JSON object and performs NO action. Otherwise it calls run_cycles(build_deps(...)) and prints the returned report as one JSON object to stdout; returns exit code 0 when no piece is stuck, 1 otherwise. Default `runner` runs subprocess.run (background=True uses Popen with creationflags 0x08000000 on Windows); it never uses shell=True.

Tests (tmp dirs, fake runner recording argv, fake diagnose; no real subprocess, no network): get_state from a tmp status.json (running/passed/escalate/missing), tests_green from fake returncodes, state file corrupt -> ValueError, relaunch removes the job dir and records the right argv with background=True, run_reviewers parsing a tmp combined file (findings reviewer, absent reviewer -> PASS, failed run -> NO_REVIEW), apply_findings writes auto file and calls apply_review argv, escalate calls diagnose with a prompt containing ESCALATE.md text and writes diag file, main --dry-run prints JSON and performs no runner call, main exit codes, no argv contains shell strings.

HARD RULES: stdlib only plus the optional nvidia_scheduler import inside the default diagnose; no network in tests; no absolute drive paths in code or tests; never print or log keys.


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpG2

Why 4 rounds failed (no import problem with g1; the sys.path insert is fine):
- Round 2 was a reply-format failure (files_ok False): the model dropped the module block. The reply is two large files (module plus 13 tests), so it is easy to truncate or mis-fence.
- Remaining 4 test failures are the spec's fault, not the code's:
  1. Dry-run says "performs NO action" and the test says "no runner call", but get_state itself calls the runner for pytest (tests_green). The spec contradicts itself; the one recorded call is that pytest.
  2. The spec never pins argv shapes. Tests check `"fix_loop.py" in argv` as list membership, but the real element is `scripts/source/fix_loop.py`. They also check apply_review.py at argv[0] or argv[-2], while the real argv is [python, <tools>/apply_review.py, file, id], so the script is argv[1] as a full path.
  3. Spec 12 says escalate applies the diagnosis "like apply_findings", yet the test looks for apply_review in different positions.

Prioritized SPEC changes:
1. Pin exact argv lists literally, e.g. relaunch: ["uv","run","python","scripts/source/fix_loop.py","--job","_loop/jobs/research_<id>.json"]; apply: [sys.executable, str(tools/"apply_review.py"), str(file), id]. Say tests compare whole lists or `Path(argv[1]).name`.
2. Fix the dry-run contradiction: dry-run MAY call the runner only for the pytest tests_green check, and the test must assert no background and no non-pytest calls. Or make dry-run skip pytest (tests_green=False).
3. Split into two jobs: wpG2a (build_deps with the state file, get_state, relaunch) and wpG2b (run_reviewers, apply_findings, escalate, main, default runner). Each stays under about 6 tests.
4. Move the default diagnose (NvidiaScheduler, keys) out of the tested path: spec it as a thin untested function behind `diagnose=None`, with tests always injecting a fake.
5. Give the combined_<id>.md format as a literal sample with the three headings, so the parsing test and code agree.
6. Shorten the output-format rule to one line plus the example, and tell the model to keep tests minimal (one assert focus each) so the reply is not truncated.

REVIEWER DECISIONS (binding, resolve the spec gaps): 
1. Pinned argv lists (tests assert these EXACT lists, with <id>/<module> substituted and Path objects passed as str):
   pytest: ["uv","run","python","-m","pytest","-q","--tb=no","research/pieces/test_<module>.py"] with cwd=repo
   relaunch: ["uv","run","python","scripts/source/fix_loop_stable.py","--job","_loop/jobs/research_<id>.json"] with cwd=repo and background=True
   reviewers: ["python", str(tools/"luna_review.py"), "<id>"]
   apply: ["python", str(tools/"apply_review.py"), str(reviews_dir/"auto_<id>.md"), "<id>"]
2. Dry-run: get_state may call the runner for the READ-ONLY pytest command; it must never call the runner for relaunch, reviewers, apply or escalate. Tests for --dry-run assert exactly that: only pytest argv appear in the recorded calls.
3. Every function must be written in the file; the reply must contain BOTH files in full.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/g2_autoloop_cli.py
```python
<complete module source>
```
FILE: research/pieces/test_g2_autoloop_cli.py
```python
<complete test source>
```
