"""Ops tool: BULK review (Haiku effort is MEDIUM since 2026-10-29 owner request; the heading text still says "low" so the loop parser stays unchanged). Codex Luna (gpt-6-luna medium, read-only) reviews 3 pieces per call and Haiku-low (claude -p) 4 pieces per call, in parallel,
then writes _loop/reviews/combined_<id>.md (same format luna_review.py writes: headings 'LUNA (gpt-6-luna medium):' and 'HAIKU (low, stand-in):'; a file with only '## <id>' = no findings).
usage: bulk_review.py [ids...]   (no ids = every piece whose code/tests changed after its combined file, skipping pieces whose job is mid-run). No Kimi."""
import re, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
R = Path(r"D:\aai work\granthstudio"); REV = R / "_loop" / "reviews"; REV.mkdir(exist_ok=True)
MOD = {"wpA1": "a1_queue", "wpA2": "a2_collect", "wpA3": "a3_cli", "wpB1": "a1_audio_io", "wpB2": "a2_transcribe", "wpB3": "a3_align",
       "wpC1": "c1_cluster", "wpC2": "c2_review", "wpC3": "c3_state", "wpD1": "d1_beat_schema", "wpD2": "d2_recipe_compiler",
       "wpD3": "d3_deliverables", "wpD4": "d4_reconstruct", "wpE1": "a1_scene_selection", "wpE2": "a2_recipe_prompts",
       "wpE3": "a3_blind_scoring", "wpF1": "f1_corpus", "wpF2": "f2_bias", "wpF3": "f3_publish", "wpF4": "f4_classify"}
codex = shutil.which("codex.cmd") or shutil.which("codex") or "codex.cmd"
claude = shutil.which("claude.cmd") or shutil.which("claude") or "claude"
def needs(i):
    c = REV / f"combined_{i}.md"
    m, t = R / f"research/pieces/{MOD[i]}.py", R / f"research/pieces/test_{MOD[i]}.py"
    sj = R / "_loop" / f"research_{i}" / "status.json"
    if not sj.is_file(): return False            # job dir missing = a fix job was just (re)launched and is still running
    if '"running"' in sj.read_text(encoding="utf-8"): return False
    return (not c.is_file()) or c.stat().st_mtime < max(m.stat().st_mtime, t.stat().st_mtime)
def block(i):
    m = MOD[i]
    spec = (R / "docs/pilot/nemotron_specs" / f"research_{i}.md").read_text(encoding="utf-8")
    return f"\n\n######## PIECE {i} ########\nSPEC:\n{spec}\n\nMODULE {m}.py:\n" + (R / f"research/pieces/{m}.py").read_text(encoding="utf-8") + f"\n\nTEST test_{m}.py:\n" + (R / f"research/pieces/test_{m}.py").read_text(encoding="utf-8")
def prompt(ids):
    return ("Review EACH piece below against its spec (REVIEW FINDINGS / REVIEWER DECISIONS sections are authoritative: verify they are fixed). For EACH piece output a section that starts with a line `## <piece id>` "
            "(e.g. `## wpA2`) followed by concrete defects only, each as `HIGH|MED|LOW - file:line - defect - fix`, or the single word PASS if it has no HIGH/MED. Check every spec bullet, edge cases, vacuous tests, "
            "no Kimi/network calls, no absolute drive paths. No enhancements. Output nothing before the first heading." + "".join(block(i) for i in ids))
def run_codex(p):
    for _ in range(2):
        try:
            r = subprocess.run([codex, "exec", "-m", "gpt-6-luna", "-c", "model_reasoning_effort=medium", "--sandbox", "read-only", "--skip-git-repo-check", "-"],
                               input=p, capture_output=True, text=True, encoding="utf-8", timeout=1200, cwd=str(R))
            if r.returncode == 0 and r.stdout.strip(): return r.stdout
        except Exception: pass
    return ""
def run_haiku(p):
    for _ in range(2):
        try:
            r = subprocess.run([claude, "-p", "--model", "haiku", "--effort", "medium", "--disallowedTools", "Write", "Edit", "Bash", "NotebookEdit"],
                               input=p, capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=str(R))
            if r.returncode == 0 and r.stdout.strip(): return r.stdout
        except Exception: pass
    return ""
def split(text, ids):
    out = {}
    for part in re.split(r"(?m)^#{1,3}\s*(?=wp[A-F]\d)", text):
        m = re.match(r"(wp[A-F]\d)\b", part)
        if m and m.group(1) in ids: out[m.group(1)] = part[m.end():].strip()
    return out
def isfind(t): return bool(t) and not re.match(r"\W*PASS\b", t) and bool(re.search(r"\b(HIGH|MED)\b", t))
ids = sys.argv[1:] or [i for i in MOD if i != "wpD4" and needs(i)]
print("bulk review of", ids, flush=True)
batches = lambda xs, n: [xs[k:k + n] for k in range(0, len(xs), n)]
jobs = [("LUNA (gpt-6-luna medium)", run_codex, b) for b in batches(ids, 3)] + [("HAIKU (low, stand-in)", run_haiku, b) for b in batches(ids, 4)]
res = {i: {} for i in ids}
def go(j):
    name, fn, b = j
    t = time.time(); out = split(fn(prompt(b)), b)
    return name, b, out, round(time.time() - t)
with ThreadPoolExecutor(8) as ex:
    for name, b, out, secs in ex.map(go, jobs):
        for i in b: res[i][name] = out.get(i, "NO_REVIEW")
        print(name.split()[0], b, "answered", sorted(out), f"{secs}s", flush=True)
for i in ids:
    body = "".join(f"{k}:\n{v}\n\n" for k, v in res[i].items() if isfind(v))
    (REV / f"combined_{i}.md").write_text(f"## {i}\n" + body, encoding="utf-8")
    print(i, {k.split()[0]: ("NO_REVIEW" if v == "NO_REVIEW" else "findings" if isfind(v) else "PASS") for k, v in res[i].items()}, flush=True)
