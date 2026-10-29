from pathlib import Path
p = Path(__file__).parent / "loop.py"
s = p.read_text(encoding="utf-8")
a = s.index("    def one(i):")
b = s.index("    with ThreadPoolExecutor(len(lenses))")
new = '''    if mode == "review":
        lenses = lenses + ["overall correctness against the spec; concrete defects only (GPT-6 Luna, high effort)"]
        models = models + ["LUNA"]
    def luna(prompt):
        r = subprocess.run(["codex", "exec", "-m", "gpt-6-luna", "-c", "model_reasoning_effort=high", "--sandbox", "read-only", "--skip-git-repo-check", "-"], input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=600, cwd=str(L))
        out = r.stdout.strip()
        if r.returncode or not out: raise RuntimeError("codex failed rc=%s" % r.returncode)
        return out
    def one(i):
        prompt = f"Review this code against the spec. Lens: {lenses[i]}. List concrete defects only, ranked HIGH/MED/LOW, each with file/line and fix. Reply exactly PASS if no HIGH or MED defects.\\n\\nSPEC:\\n{spec}\\n\\nCODE:\\n{code}"
        try: rv = luna(prompt) if models[i] == "LUNA" else llm(models[i], prompt, 16000, 240)
        except BaseException as e: rv = f"REVIEW_ERROR NO_REVIEW {e}"
        (L / f"{wp}.{mode}{i+1}.txt").write_text(rv, encoding="utf-8"); return f"--- lens {i+1}: {lenses[i]} ---\\n{rv}"
'''
s = s[:a] + new + s[b:]
p.write_text(s, encoding="utf-8")
import ast; ast.parse(s); print("luna added")
