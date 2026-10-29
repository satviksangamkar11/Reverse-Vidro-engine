from pathlib import Path
p = Path(__file__).parent / "race.py"
s = p.read_text(encoding="utf-8")
old = '    valid = [p for p in parts if not p.lstrip().startswith("REVIEW_ERROR")]\n'
assert old in s
new = old + '''    luna = parts[4] if len(parts) > 4 and not parts[4].lstrip().startswith("REVIEW_ERROR") else None
    if luna is None:  # GPT-6 Luna (high) has priority: its answer is required for a round to count
        print(wp, "review round", rnd + 1, "NO_REVIEW from Luna; retrying", flush=True); continue
    valid = [luna] + [p for p in valid if p is not luna]  # Luna's findings first and never truncated away
'''
s = s.replace(old, new)
p.write_text(s, encoding="utf-8")
import ast; ast.parse(s); print("luna priority ok")
