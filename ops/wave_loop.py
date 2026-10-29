"""Ops driver (the automatic loop): waves of  bulk review (Codex Luna + Haiku)  ->  apply findings (Nemotron fix jobs through apply_review.py)  ->  wait  ->  repeat.
No Kimi. State: _loop/wave_state.json. A piece whose findings were applied 4 times without ever going clean is flagged (_loop/reviews/NEEDS_CLAUDE_<id>.flag) and skipped:
the supervising Claude then takes over (Sonnet medium diagnosis). usage: wave_loop.py [--max-iter 60] [--sleep 90] [ids...]"""
import json, re, subprocess, sys, time
from pathlib import Path
R = Path(r"D:\aai work\granthstudio"); REV = R / "_loop" / "reviews"; TOOLS = Path(r"D:\aai work\animation_research_tool\_loop")
ALL = [f"wp{w}{n}" for w in "ABCDE" for n in "123"] + ["wpF1", "wpF2", "wpF3", "wpF4"]
args = sys.argv[1:]; max_iter, sleep_s = 60, 90
if "--max-iter" in args: k = args.index("--max-iter"); max_iter = int(args[k + 1]); del args[k:k + 2]
if "--sleep" in args: k = args.index("--sleep"); sleep_s = int(args[k + 1]); del args[k:k + 2]
ids = args or ALL
SP = R / "_loop" / "wave_state.json"
state = json.loads(SP.read_text(encoding="utf-8")) if SP.is_file() else {}
def save(): SP.write_text(json.dumps(state, indent=1), encoding="utf-8")
def job_state(i):
    sj = R / "_loop" / f"research_{i}" / "status.json"
    if not sj.is_file(): return "running"          # job dir removed by a relaunch and not finished yet
    try: return json.loads(sj.read_text(encoding="utf-8")).get("state", "running")
    except Exception: return "running"
def has_findings(i):
    c = REV / f"combined_{i}.md"
    if not c.is_file(): return False
    body = re.sub(r"^## .*\n?", "", c.read_text(encoding="utf-8")).strip()
    return bool(re.search(r"\b(HIGH|MED)\b", body))
def unapplied(i):
    c, sj = REV / f"combined_{i}.md", R / "_loop" / f"research_{i}" / "status.json"
    return has_findings(i) and sj.is_file() and sj.stat().st_mtime < c.stat().st_mtime
def clean(i):
    c, sj = REV / f"combined_{i}.md", R / "_loop" / f"research_{i}" / "status.json"
    return c.is_file() and sj.is_file() and not has_findings(i) and job_state(i) != "running" and c.stat().st_mtime > sj.stat().st_mtime - 1
def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)
for it in range(1, max_iter + 1):
    log(f"--- wave iteration {it}")
    for i in ids:
        if job_state(i) == "running" or i in state.get("flagged", []): continue
        if unapplied(i):
            n = state.setdefault("applies", {}).get(i, 0) + 1
            if n > 4:
                (REV / f"NEEDS_CLAUDE_{i}.flag").write_text("4 apply rounds without going clean", encoding="utf-8")
                state.setdefault("flagged", []).append(i); save(); log(i, "FLAGGED for Claude (4 rounds)"); continue
            r = subprocess.run([sys.executable, str(TOOLS / "apply_review.py"), str(REV / f"combined_{i}.md"), i], capture_output=True, text=True)
            state["applies"][i] = n; save(); log(i, "applied round", n, (r.stdout or r.stderr).strip()[-60:]); time.sleep(8)
    waiting = [i for i in ids if job_state(i) == "running" and i not in state.get("flagged", [])]
    if waiting: log("fix jobs running:", waiting)
    # review every iteration: bulk_review itself skips pieces whose fix job is still running, so finished pieces never wait for slow ones
    r = subprocess.run([sys.executable, str(TOOLS / "bulk_review.py")], capture_output=True, text=True, cwd=str(R))
    log("bulk review:", (r.stdout.strip().splitlines() or ["(nothing to review)"])[0][:120])
    done = [i for i in ids if clean(i)]
    state["done"] = done; save(); log("clean:", len(done), "of", len(ids), "| flagged:", state.get("flagged", []))
    if len(done) + len(state.get("flagged", [])) >= len(ids): log("ALL PIECES CLEAN OR FLAGGED"); break
    time.sleep(sleep_s)
