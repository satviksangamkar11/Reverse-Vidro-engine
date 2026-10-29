"""Ops tool: reviewers run BEFORE the Sonnet round: Codex Luna (gpt-6-luna, MEDIUM, read-only) + GLM 5.3 Flash + MiniMax (NVIDIA).
Merges their findings (Sonnet only if it is an escalation diagnosis) into _loop/reviews/combined_<id>.md. usage: luna_review.py <piece id> ... (no Kimi)"""
import re, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, r"D:\aai work\animation_research_tool")
import requests
from nvidia_scheduler import NvidiaScheduler
R = Path(r"D:\aai work\granthstudio"); REV = R / "_loop" / "reviews"; REV.mkdir(exist_ok=True)
MOD = {"wpA1": "a1_queue", "wpA2": "a2_collect", "wpA3": "a3_cli", "wpB1": "a1_audio_io", "wpB2": "a2_transcribe", "wpB3": "a3_align",
       "wpC1": "c1_cluster", "wpC2": "c2_review", "wpC3": "c3_state", "wpD1": "d1_beat_schema", "wpD2": "d2_recipe_compiler",
       "wpD3": "d3_deliverables", "wpD4": "d4_reconstruct", "wpE1": "a1_scene_selection", "wpE2": "a2_recipe_prompts",
       "wpE3": "a3_blind_scoring", "wpF1": "f1_corpus", "wpF2": "f2_bias", "wpF3": "f3_publish", "wpF4": "f4_classify"}
codex = shutil.which("codex.cmd") or shutil.which("codex") or "codex.cmd"
keys = [p.read_text().strip() for p in sorted((R.parent / "secrets/nvidia").glob("nvidia_api_key*.txt"))][:14]
GLM, MINIMAX = "z-ai/glm-5.3-flash", "minimaxai/minimax-m3.1-flash"
def prompt(i):
    m = MOD[i]
    spec = (R / "docs/pilot/nemotron_specs" / f"research_{i}.md").read_text(encoding="utf-8")
    code = (R / f"research/pieces/{m}.py").read_text(encoding="utf-8"); test = (R / f"research/pieces/test_{m}.py").read_text(encoding="utf-8")
    return ("Review this code against its spec (REVIEW FINDINGS / REVIEWER DECISIONS sections are authoritative: verify they are fixed). List concrete defects only, "
            "each as `HIGH|MED|LOW - file:line - defect - fix`; reply exactly PASS if no HIGH/MED. Check: every spec bullet, edge cases, vacuous tests, "
            "no Kimi/network calls, no absolute drive paths. No enhancements.\n\nSPEC:\n" + spec + f"\n\nMODULE {m}.py:\n" + code + f"\n\nTEST test_{m}.py:\n" + test)
def luna(p):
    for _ in range(2):
        try:
            r = subprocess.run([codex, "exec", "-m", "gpt-6-luna", "-c", "model_reasoning_effort=medium", "--sandbox", "read-only", "--skip-git-repo-check", "-"],
                               input=p, capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=str(R))
            if r.returncode == 0 and r.stdout.strip(): return r.stdout.strip()
        except Exception: pass
    return "NO_REVIEW"
def nv(model):
    def go(p):
        def post(url, json=None, **kw): return requests.post(url, json=dict(json, chat_template_kwargs={"enable_thinking": False}), **kw)
        try:
            r = NvidiaScheduler(keys, model=model, read_timeout=240, max_calls=2, post=post).call(p, max_tokens=16000)
            return r["text"].strip() if r["status"] == "OK" and r["text"].strip() else "NO_REVIEW"
        except Exception: return "NO_REVIEW"
    return go
def latest_sonnet(i):
    best = ""
    for f in sorted(REV.glob("sonnet_*.md"), key=lambda p: p.stat().st_mtime):
        for part in re.split(r"(?m)^#{1,4} ", f.read_text(encoding="utf-8")):
            if re.search(i, part[:120], re.I): best = part
    return best
def isfind(t): return t != "NO_REVIEW" and not re.match(r"\s*\**PASS", t)
def one(i):
    p = prompt(i)
    with ThreadPoolExecutor(3) as ex:
        fs = {"LUNA (gpt-6-luna medium)": ex.submit(luna, p), "GLM 5.3 Flash": ex.submit(nv(GLM), p), "MiniMax M3.1 Flash": ex.submit(nv(MINIMAX), p)}
        out = {k: f.result() for k, f in fs.items()}
    s = latest_sonnet(i)
    body = "".join(f"{k}:\n{v}\n\n" for k, v in out.items() if isfind(v))
    sb = f"SONNET (latest):\n{s.strip()}\n" if re.search(r"\b(HIGH|MED)\b", s) else ""
    (REV / f"combined_{i}.md").write_text(f"## {i}\n" + body + sb, encoding="utf-8")
    return i, {k: ("NO_REVIEW" if v == "NO_REVIEW" else "PASS" if not isfind(v) else "findings") for k, v in out.items()}
with ThreadPoolExecutor(4) as ex:
    for i, res in ex.map(one, sys.argv[1:]):
        print(i, "REVIEWED", res, flush=True)
