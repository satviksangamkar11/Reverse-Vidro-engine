"""Orchestration helper (not product code). Modes: code | fix | review | glm | mm | gate.
STAGE env = staging dir name; CODER env overrides coder. Tests are read-only in fix mode."""
import os, re, shutil, subprocess, sys
import requests
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from nvidia_scheduler import NvidiaScheduler
T = Path(__file__).parent.parent; L = Path(__file__).parent
keys = [p.read_text().strip() for p in sorted((T.parent / "secrets/nvidia").glob("nvidia_api_key*.txt"))][:14]
CODER = os.environ.get("CODER", "nvidia/nemotron-3-ultra-550b-a55b")
GLM, MINIMAX, MUSE = "z-ai/glm-5.3-flash", "minimaxai/minimax-m3.1-flash", "meta/muse-glimmer-30b"
END = "=== END ==="
def llm(model, prompt, mt=24000, timeout=900):
    def post(url, json=None, **kw): return requests.post(url, json=dict(json, chat_template_kwargs={"enable_thinking": False}), **kw)
    r = NvidiaScheduler(keys, model=model, read_timeout=timeout, max_calls=2 if timeout < 900 else 4, post=post).call(prompt, max_tokens=mt)
    if r["status"] != "OK": raise RuntimeError(f"{model}: {r['status']}")
    return r["text"]
mode, wp = sys.argv[1], sys.argv[2]
stage = os.environ.get("STAGE", wp); d = L / "stage" / stage
spec = (L / f"{wp}.spec.md").read_text(encoding="utf-8")
def files_of(out):
    return {m.group(1).strip(): re.sub(r"^```\w*\n|\n```$", "", m.group(2).strip()) + "\n" for m in re.finditer(r"=== FILE: (.+?) ===\n(.*?)(?=\n=== FILE: |\n=== END ===|\Z)", out, re.S)}
def pytest(extra=()):
    tests = [n for n in (L / f"{wp}.files").read_text().split() if n.startswith("test_")] if (L / f"{wp}.files").is_file() else []
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=short", *tests, *extra], cwd=d, capture_output=True, text=True)
def request_files(prompt, required):
    for _ in range(3):  # truncation guard: last file must arrive whole
        out = llm(CODER, prompt)
        got = files_of(out)
        if END in out and all(n in got for n in required): return got
        prompt += "\n\nYour previous answer was cut off or missing files. Resend ALL files completely and finish with a line '=== END ==='. Required: " + ", ".join(required)
    sys.exit("TRUNCATED: required files never arrived whole")
FMT = "Output ONLY complete files as '=== FILE: <name> ===' blocks, no fences, no prose, and finish with a line '=== END ==='."
if mode == "code":
    ctx = re.search(r"^CONTEXT:(.*)$", spec, re.M); req = re.search(r"^REQUIRED:(.*)$", spec, re.M)
    cf = [f.strip() for f in ctx.group(1).split(",") if f.strip()] if ctx else []
    required = req.group(1).split() if req else []
    body = "\n".join(f"=== FILE: {f} ===\n{(T/f).read_text(encoding='utf-8')}" for f in cf if (T/f).is_file())
    got = request_files(f"You are the coder. Implement the spec; write unittest tests (offline, tmp dirs, no absolute drive-letter paths, no network). Each numbered spec bullet needs at least one test. {FMT}\n\nSPEC:\n{spec}\n\nEXISTING FILES:\n{body}", required)
    if d.exists(): shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(T, d, dirs_exist_ok=True, ignore=shutil.ignore_patterns("_loop", "__pycache__", "WhatsApp*", "animation_research", "*.mp4", "*.pyc"))
    for n, c in got.items(): (d / n).write_text(c, encoding="utf-8"); print("wrote", n)
    if not required: (L / f"{wp}.files").write_text(" ".join(got))
    r = pytest(); print(r.stdout[-1500:])
elif mode == "fix":
    names = (L / f"{wp}.files").read_text().split(); notes = sys.argv[3] if len(sys.argv) > 3 else ""
    r = pytest(); (L / f"{wp}.lastrun.txt").write_text(r.stdout, encoding="utf-8")
    hist = (L / f"{wp}.history.txt").read_text(encoding="utf-8")[-1500:] if (L / f"{wp}.history.txt").is_file() else ""
    code = "\n".join(f"=== FILE: {n} ===\n{(d / n).read_text(encoding='utf-8')}" for n in names if (d / n).is_file())
    if os.environ.get("ALLOW_TEST_EDIT"):
        intro = "TEST-EDIT PASS: the same failures repeated. For each failing test decide using the SPEC (including its REVIEWER DECISIONS section) whether the code or the test is wrong. Correct wrong tests (output the full corrected test file) and wrong code (output the full code file); never weaken a test just to pass, a test may only change to match the spec. Explain each changed test in '=== FILE: TEST_ISSUE.txt ==='."
    else:
        intro = "Fix the CODE so the tests pass. The TEST files are read-only and define correct behaviour; do not output test_ files. If a test is truly impossible or contradicts the spec, output a file '=== FILE: TEST_ISSUE.txt ===' explaining which test and why, plus your best code."
    prompt = intro + " Output complete files (never partial, never drop existing public functions).\n" + FMT + "\n\nSPEC:\n" + spec + "\n\nFULL PYTEST OUTPUT:\n" + r.stdout[-9000:] + "\n\nPREVIOUS ROUNDS (do not repeat failed ideas):\n" + hist + "\n\nREVIEW NOTES:\n" + notes + "\n\nFILES:\n" + code
    assert "{spec}" not in prompt and "{code}" not in prompt  # guard against the f-string bug
    got = request_files(prompt, [n for n in names if not n.startswith("test_")][:1])
    bak = d / "_bak"; bak.mkdir(exist_ok=True)
    for n in names:
        if (d / n).is_file(): (bak / n).write_text((d / n).read_text(encoding="utf-8"), encoding="utf-8")
    for n, c in got.items():
        if n.startswith("test_") and not os.environ.get("ALLOW_TEST_EDIT"): continue
        if n.startswith("test_") and (d / n).is_file():
            import difflib
            with (L / f"{wp}.testedits.diff").open("a", encoding="utf-8") as fh: fh.write("".join(difflib.unified_diff((d / n).read_text(encoding="utf-8").splitlines(True), c.splitlines(True), n + " (before)", n + " (after)")))
        (d / n).write_text(c, encoding="utf-8"); print("fixed", n)
    r2 = pytest(); (L / f"{wp}.history.txt").open("a", encoding="utf-8").write("ROUND: " + re.sub(r"\s+", " ", r2.stdout[-400:]) + "\n"); print(r2.stdout[-800:])
else:  # review / glm / mm / gate
    names = (L / f"{wp}.files").read_text().split()
    code = "\n".join(f"=== {n} ===\n{(d / n).read_text(encoding='utf-8')}" for n in names if (d / n).is_file())
    lenses = ["security and file/zip/path handling, trust boundaries", "edge cases, failure handling, resumability, atomic writes, encoding", "spec compliance: go through EVERY numbered spec bullet and confirm it is implemented", "test quality: missing cases, trivially true assertions, tests that never exercise the claim"]
    models = [CODER] * 4
    if mode in ("glm", "mm"): lenses, models = lenses[2:3], [GLM if mode == "glm" else MINIMAX]
    if mode == "gate": lenses, models = lenses[2:3] * 2, [GLM, MUSE]
    if mode == "review":
        lenses = lenses + ["overall correctness against the spec; concrete defects only (GPT-6 Luna, high effort)"]
        models = models + ["LUNA"]
    def luna(prompt):
        r = subprocess.run([shutil.which("codex.cmd") or shutil.which("codex") or "codex.cmd", "exec", "-m", "gpt-6-luna", "-c", "model_reasoning_effort=high", "--sandbox", "read-only", "--skip-git-repo-check", "-"], input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=600, cwd=str(L))
        out = r.stdout.strip()
        if r.returncode or not out: raise RuntimeError("codex failed rc=%s" % r.returncode)
        return out
    def one(i):
        prompt = f"Review this code against the spec. Lens: {lenses[i]}. List concrete defects only, ranked HIGH/MED/LOW, each with file/line and fix. Reply exactly PASS if no HIGH or MED defects.\n\nSPEC:\n{spec}\n\nCODE:\n{code}"
        try: rv = luna(prompt) if models[i] == "LUNA" else llm(models[i], prompt, 16000, 240)
        except BaseException as e: rv = f"REVIEW_ERROR NO_REVIEW {e}"
        (L / f"{wp}.{mode}{i+1}.txt").write_text(rv, encoding="utf-8"); return f"--- lens {i+1}: {lenses[i]} ---\n{rv}"
    with ThreadPoolExecutor(len(lenses)) as ex: print("\n".join(ex.map(one, range(len(lenses)))))
