import sys, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.argv = ["x", "code", "wpA"]
L = Path(__file__).parent
src = (L / "loop.py").read_text(encoding="utf-8").split('mode, wp = sys.argv[1]')[0]
exec(compile(src, "loop_head", "exec"), globals())
req = (L / "GRAMMAR_REQUIREMENT.md").read_text(encoding="utf-8")
ids = [f"wp{w}{n}" for w in "ABCDE" for n in "123"] + ["wpF1", "wpF2", "wpF3", "wpF4"]
specs = "\n".join(f"=== {i} ===\n" + (L / f"{i}.spec.md").read_text(encoding="utf-8") for i in ids)
ctx = req + "\n\nCURRENT SPECS (19 pieces; F1-F4 FROZEN):\n" + specs
(L / "GRAMMAR_CONTEXT.txt").write_text(ctx, encoding="utf-8")
task = ("TASK: produce CHECKLIST_GRAMMAR.md. For EACH of the 16 departments, the 4 analysis levels, the mandatory questions, each evidence field, "
        "the output/Kimi rules and each of the 8 acceptance items, give a table row: ITEM | STATUS (COVERED/PARTIAL/GAP) | EVIDENCE (spec id + quoted function or field name, or none) | "
        "IF PARTIAL/GAP: minimal addition to an existing NON-frozen spec (name the spec id; never F1-F4; no new module). Be literal: COVERED only if the spec text actually implements it. "
        "Markdown table, then the additions grouped by spec id.")
out = llm(CODER, ctx + "\n\n" + task, 24000)
(L / "CHECKLIST_GRAMMAR.md").write_text(out, encoding="utf-8"); print("checklist", len(out), flush=True)
rv = ("Cross-check this coverage checklist against the requirement and the specs. Report ONLY: (1) rows marked COVERED that the spec text does not actually implement (quote), "
      "(2) requirement items missing from the checklist, (3) proposed additions that would modify frozen F1-F4 or add a new subsystem, (4) contradictions. No enhancements. Max 400 words. Reply PASS if none.\n\n"
      + ctx + "\n\nCHECKLIST:\n" + out)
def go(m):
    try: t = llm(m, rv, 12000)
    except BaseException as e: t = "ERROR %s" % e
    (L / ("grammar_review_" + m.split("/")[-1] + ".txt")).write_text(t, encoding="utf-8"); return m, len(t)
with ThreadPoolExecutor(4) as ex:
    for x in ex.map(go, [CODER, GLM, MUSE, MINIMAX]): print(x, flush=True)
