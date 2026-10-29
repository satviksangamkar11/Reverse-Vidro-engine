import sys, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.argv = ["x", "code", "wpA"]  # reuse llm() from loop without running a mode
L = Path(__file__).parent
src = (L / "loop.py").read_text(encoding="utf-8").split('mode, wp = sys.argv[1]')[0]
exec(compile(src, "loop_head", "exec"), globals())
RULES = """Split this work-package spec into 2-3 ATOMIC specs. Rules: each atomic spec has <=3 public functions, its own NEW module (name like a1_queue.py) and its own test file (test_a1_queue.py); atomic specs must not import each other except via plain dict shapes written out in the spec; ONE return shape per function (always a dict with a 'status' key where relevant); inject every path/clock/model call as a parameter (no absolute paths); include a WORKED EXAMPLE per function with exact input and exact expected output (concrete numbers/strings) so tests have a fixed target; keep every behaviour of the original spec somewhere (nothing silently dropped); no Kimi calls anywhere. Each atomic spec file MUST start with the lines 'CONTEXT: <comma-separated existing files it may need, or empty>' and 'REQUIRED: <module.py> <test_module.py>' and then the body. Output ONLY files as '=== FILE: wpA1.spec.md ===' blocks (use ids wpA1, wpA2, ... matching the package letter) ending with a line '=== END ==='."""
def go(w):
    spec = (L / "old_specs" / f"wp{w}.spec.md").read_text(encoding="utf-8")
    out = llm(CODER, f"{RULES}\n\nORIGINAL SPEC (package {w}):\n{spec}", 24000)
    got = {m.group(1).strip(): m.group(2).strip() + "\n" for m in re.finditer(r"=== FILE: (.+?) ===\n(.*?)(?=\n=== FILE: |\n=== END ===|\Z)", out, re.S)}
    for n, c in got.items(): (L / n).write_text(c, encoding="utf-8")
    return w, sorted(got)
with ThreadPoolExecutor(5) as ex:
    for x in ex.map(go, "ABCDE"): print(x, flush=True)
