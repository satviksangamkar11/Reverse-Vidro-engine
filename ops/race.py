"""race.py <wp>: Ultra-only coder loop with bounded repair controls.
States in <wp>.status.json: RUNNING | BLOCKED | NEEDS_REVIEW | GREEN_REVIEWED | GREEN_TEST_EDITS_PENDING_REVIEW.
Rules: required dependency missing => BLOCKED; coding step crash => stop; same failure signature max 3 repairs, then one recorded
test-edit pass, then NEEDS_REVIEW; fix step crashing twice => NEEDS_REVIEW; max 3 review rounds."""
import json, os, re, subprocess, sys, time
from collections import Counter
from pathlib import Path
L = Path(__file__).parent; wp = sys.argv[1]; st = f"{wp}_ultra"; SD = L / "stage" / st
def status(state, reason=""):
    for _ in range(8):
        try:
            (L / f"{wp}.status.json").write_text(json.dumps({"state": state, "reason": reason, "time": time.time()}), encoding="utf-8"); break
        except OSError: time.sleep(0.5)
    print(wp, state, reason, flush=True)
def run(mode, *a, edit=False):
    env = dict(os.environ, STAGE=st)
    if edit: env["ALLOW_TEST_EDIT"] = "1"
    return subprocess.run([sys.executable, str(L / "loop.py"), mode, wp, *a], cwd=L.parent, env=env, capture_output=True, text=True)
def files():
    f = L / f"{wp}.files"
    return f.read_text().split() if f.is_file() else []
def pytest():
    tests = [n for n in files() if n.startswith("test_")]
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=no", "-rfE", *tests], cwd=SD, capture_output=True, text=True)
def signature():
    r = pytest()
    return "|".join(sorted(l.strip() for l in r.stdout.splitlines() if l.startswith(("FAILED", "ERROR")))) or ("rc%d" % r.returncode)
def green():
    fl = files()
    if not SD.is_dir() or not any(n.startswith("test_") and (SD / n).is_file() for n in fl): return False
    srcs = [str(SD / n) for n in fl if n.endswith(".py") and (SD / n).is_file()]
    if srcs and "undefined name" in subprocess.run([sys.executable, "-m", "pyflakes", *srcs], capture_output=True, text=True).stdout: return False
    return pytest().returncode == 0
resume = bool(os.environ.get("RESUME")) and SD.is_dir() and files()
status("RUNNING", "resuming from existing stage" if resume else "coding")
class _R: returncode = 0; stdout = ""; stderr = ""
r = _R() if resume else run("code")
if not resume: (L / f"{wp}.code.log").write_text(r.stdout + r.stderr[-1500:], encoding="utf-8")
if r.returncode == 3: status("BLOCKED", "required dependency missing; see code log"); sys.exit(0)
if r.returncode != 0 or not SD.is_dir(): status("NEEDS_REVIEW", "coding step crashed"); sys.exit(0)
if not resume: (L / f"{wp}.files").write_text(" ".join(re.findall(r"^wrote (.+)$", r.stdout, re.M)) or (L / f"{wp}.files").read_text() if (L / f"{wp}.files").is_file() else " ".join(re.findall(r"^wrote (.+)$", r.stdout, re.M)))
seen, crashes, edited = Counter(), 0, False
while not green():
    sig = signature(); seen[sig] += 1
    if seen[sig] > 3:
        if edited: status("NEEDS_REVIEW", "same failure after test-edit pass: " + sig[:300]); sys.exit(0)
        edited = True; seen.clear(); print("test-edit pass (recorded in", f"{wp}.testedits.diff)", flush=True)
        r = run("fix", edit=True)
    else:
        pf = subprocess.run([sys.executable, "-m", "pyflakes", *[str(SD / n) for n in files() if n.endswith(".py") and (SD / n).is_file()]], capture_output=True, text=True).stdout
        if sig.startswith("rc0") and pf.strip():  # tests pass but static check fails (e.g. undefined names in a test): tell the coder, allow test edit
            r = run("fix", "STATIC CHECK FAILURES (pyflakes) - fix them, including missing imports in test files:\n" + pf[:3000], edit=True)
        else:
            r = run("fix")
    crashes = crashes + 1 if r.returncode else 0
    if crashes >= 2: status("NEEDS_REVIEW", "fix step crashing: " + r.stderr[-300:]); sys.exit(0)
    print(wp, "repair", sum(seen.values()), flush=True)
status("RUNNING", "tests green; reviewing")
had_defects, stale, rnd = False, Counter(), 0
while True:
    rnd += 1
    if rnd > 15: status("NEEDS_REVIEW", "runaway guard: 15 review rounds"); sys.exit(0)
    text = run("review").stdout
    parts = re.split(r"--- lens \d: .*? ---", text)[1:]
    valid = [p for p in parts if not p.lstrip().startswith("REVIEW_ERROR")]
    luna = parts[4] if len(parts) > 4 and not parts[4].lstrip().startswith("REVIEW_ERROR") else None
    if luna is None:  # GPT-6 Luna (high) has priority: its answer is required for a round to count
        print(wp, "review round", rnd, "NO_REVIEW from Luna; retrying", flush=True)
        stale["NOLUNA"] += 1
        if stale["NOLUNA"] >= 3: status("NEEDS_REVIEW", "NO_REVIEW: Luna gave no valid review 3 times"); sys.exit(0)
        continue
    valid = [luna] + [p for p in valid if p is not luna]
    if len(valid) < 2:
        print(wp, "review round", rnd, "NO_REVIEW (quorum); retrying", flush=True)
        stale["NOQ"] += 1
        if stale["NOQ"] >= 3: status("NEEDS_REVIEW", "NO_REVIEW: quorum not reached 3 times"); sys.exit(0)
        continue
    if all(re.match(r"\s*\**PASS", p) for p in valid): break
    had_defects = True
    sig = hash("|".join(sorted(l.strip()[:70] for p in valid for l in p.splitlines() if re.search(r"\b(HIGH|MED)\b", l))))
    stale[sig] += 1
    print(wp, "review round", rnd, "defects (same set seen %d times)" % stale[sig], flush=True)
    if stale[sig] >= 3: status("NEEDS_REVIEW", "same HIGH/MED defect set 3 times: reviewers and coder disagree; needs owner/Claude decision"); sys.exit(0)
    run("fix", chr(10).join(valid)[:9000])
    if not green(): run("fix")
status("GREEN_TEST_EDITS_PENDING_REVIEW" if (L / f"{wp}.testedits.diff").is_file() else "GREEN_REVIEWED", "")
