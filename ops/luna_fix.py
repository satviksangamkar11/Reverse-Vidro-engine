from pathlib import Path
import ast
L = Path(__file__).parent
s = (L / "loop.py").read_text(encoding="utf-8")
old = '["codex", "exec",'
assert old in s
s = s.replace(old, '[shutil.which("codex.cmd") or shutil.which("codex") or "codex.cmd", "exec",')
ast.parse(s); (L / "loop.py").write_text(s, encoding="utf-8")
r = (L / "race.py").read_text(encoding="utf-8")
r = r.replace('for rnd in range(3):\n    text = run("review").stdout', 'had_defects = False\nfor rnd in range(3):\n    text = run("review").stdout')
r = r.replace('    print(wp, "review round", rnd + 1, "defects", flush=True)', '    had_defects = True\n    print(wp, "review round", rnd + 1, "defects", flush=True)')
r = r.replace('status("NEEDS_REVIEW", "review defects remain after 3 rounds")', 'status("NEEDS_REVIEW", "review defects remain after 3 rounds" if had_defects else "NO_REVIEW: no valid review (Luna/quorum) in 3 rounds")')
ast.parse(r); (L / "race.py").write_text(r, encoding="utf-8")
print("ok", "had_defects" in r)
