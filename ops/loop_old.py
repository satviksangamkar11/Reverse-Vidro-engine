"""Orchestration helper (not product code): spec -> Nemotron codes -> tests -> 2x GLM review.
usage: loop.py code <wp>   | loop.py review <wp>
Reads _loop/<wp>.spec.md; context files listed on a 'CONTEXT:' line (comma separated, relative to tool dir)."""
import re, shutil, subprocess, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from nvidia_scheduler import NvidiaScheduler
T = Path(__file__).parent.parent
L = Path(__file__).parent
keys = [p.read_text().strip() for p in sorted((T.parent / "secrets/nvidia").glob("nvidia_api_key*.txt"))][:14]
import os
CODER, GLM = os.environ.get("CODER", "nvidia/nemotron-3-ultra-550b-a55b"), "z-ai/glm-5.3-flash"
MINIMAX = "minimaxai/minimax-m3.1-flash"
MUSE = "meta/muse-glimmer-30b"
def llm(model, prompt, mt=14000):
    import requests
    def post(url, json=None, **kw):
        json = dict(json, chat_template_kwargs={"enable_thinking": False})
        return requests.post(url, json=json, **kw)
    s = NvidiaScheduler(keys, model=model, read_timeout=900, max_calls=3, post=post)
    r = s.call(prompt, max_tokens=mt)
    if r["status"] != "OK": sys.exit(f"{model}: {r['status']} {r.get('error')}")
    return r["text"]
def stage(wp):
    d = L / "stage" / os.environ.get("STAGE", wp)
    if d.exists(): shutil.rmtree(d)
    shutil.copytree(T, d, ignore=shutil.ignore_patterns("_loop", "__pycache__", "WhatsApp*", "animation_research", "*.mp4"))
    return d
NEMO = ["nvidia/nemotron-3-ultra-550b-a55b"]
def first_nemo(prompt, mt):
    return "[reviewer: %s] " % NEMO[0] + llm(NEMO[0], prompt, mt)
wp, mode = sys.argv[2], sys.argv[1]
spec = (L / f"{wp}.spec.md").read_text(encoding="utf-8")
if mode == "fix":
    d = L / "stage" / os.environ.get("STAGE", wp)
    extra = sys.argv[3] if len(sys.argv) > 3 else ""
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=short"], cwd=d, capture_output=True, text=True)
    want = (L / f"{wp}.files").read_text().split()
    code = "\n".join("=== FILE: %s ===\n%s" % (n, (d / n).read_text(encoding="utf-8")) for n in want)
    out = llm(CODER, "Fix the failing tests/defects (fix the test if the test is wrong). Output ONLY complete changed files as '=== FILE: name ===' blocks, no fences, no prose.\n\nSPEC:\n%s\n\nPYTEST:\n%s\n\nREVIEW NOTES:\n%s\n\nFILES:\n%s" % (spec, r.stdout[-6000:], extra, code))
    for m in re.finditer(r"=== FILE: (.+?) ===\n(.*?)(?=\n=== FILE: |\Z)", out, re.S):
        (d / m.group(1).strip()).write_text(re.sub(r"^```\w*\n|\n```$", "", m.group(2).strip()) + "\n", encoding="utf-8"); print("fixed", m.group(1).strip())
    r = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=d, capture_output=True, text=True); print(r.stdout[-1200:])
elif mode == "code":
    ctx = re.search(r"^CONTEXT:(.*)$", spec, re.M)
    files = [f.strip() for f in ctx.group(1).split(",") if f.strip()] if ctx else []
    body = "\n".join(f"=== FILE: {f} ===\n{(T/f).read_text(encoding='utf-8')}" for f in files)
    prompt = f"You are the coder. Implement the spec. Write tests too (unittest, no network, no real downloads). Output ONLY complete files, each as:\n=== FILE: <relative path> ===\n<full content>\nNo markdown fences, no prose.\n\nSPEC:\n{spec}\n\nEXISTING FILES:\n{body}"
    out = llm(CODER, prompt)
    (L / f"{wp}.raw.txt").write_text(out, encoding="utf-8")
    d = stage(wp)
    for m in re.finditer(r"=== FILE: (.+?) ===\n(.*?)(?=\n=== FILE: |\Z)", out, re.S):
        p = d / m.group(1).strip(); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(re.sub(r"^```\w*\n|\n```$", "", m.group(2).strip()) + "\n", encoding="utf-8"); print("wrote", p.relative_to(d))
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x"], cwd=d, capture_output=True, text=True)
    print(r.stdout[-2500:], r.stderr[-800:])
else:
    from concurrent.futures import ThreadPoolExecutor
    d = L / "stage" / os.environ.get("STAGE", wp)
    names = (L / f"{wp}.files").read_text().split()
    code = "\n".join("=== %s ===\n%s" % (n, (d / n).read_text(encoding="utf-8")) for n in names if (d / n).is_file())
    lenses = ["security and file/zip/path handling, trust boundaries", "edge cases, failure handling, resumability, atomic writes, encoding", "spec compliance: go through EVERY numbered spec bullet and confirm it is implemented", "test quality: missing cases, trivially true assertions, tests that never exercise the claim"]
    if mode in ("glm", "mm"): lenses = ["overall correctness against the spec, concrete defects only"]
    if mode == "gate": lenses = ["overall correctness against the spec, concrete defects only"] * 2
    def one(i_lens):
        i, lens = i_lens
        model = [GLM, MUSE][i - 1] if mode == "gate" else GLM if mode == "glm" else MINIMAX if mode == "mm" else CODER
        try:
            rv = llm(model, "Review this code against the spec. Lens: %s. List concrete defects only, ranked HIGH/MED/LOW, each with file/line and fix. Reply exactly PASS if no HIGH or MED defects.\n\nSPEC:\n%s\n\nCODE:\n%s" % (lens, spec, code), 16000 if mode in ("glm", "mm", "gate") else 8000)
        except BaseException as e:
            rv = "REVIEW_ERROR %s" % e
        (L / f"{wp}.{mode}{i}.txt").write_text(rv, encoding="utf-8"); return "--- lens %d: %s ---\n%s" % (i, lens, rv)
    with ThreadPoolExecutor(len(lenses)) as ex:
        print("\n".join(ex.map(one, enumerate(lenses, 1))))
