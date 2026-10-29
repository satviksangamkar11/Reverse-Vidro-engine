from pathlib import Path
import ast
L = Path(__file__).parent
# ---- loop.py: tolerate locked stage dirs
s = (L / "loop.py").read_text(encoding="utf-8")
s = s.replace("if d.exists(): shutil.rmtree(d)", "if d.exists(): shutil.rmtree(d, ignore_errors=True)")
s = s.replace("shutil.copytree(T, d, ignore=", "shutil.copytree(T, d, dirs_exist_ok=True, ignore=")
ast.parse(s); (L / "loop.py").write_text(s, encoding="utf-8")
# ---- race.py
r = (L / "race.py").read_text(encoding="utf-8")
# status write retry
r = r.replace('''    (L / f"{wp}.status.json").write_text(json.dumps({"state": state, "reason": reason, "time": time.time()}), encoding="utf-8")''',
'''    for _ in range(8):
        try:
            (L / f"{wp}.status.json").write_text(json.dumps({"state": state, "reason": reason, "time": time.time()}), encoding="utf-8"); break
        except OSError: time.sleep(0.5)''')
# pyflakes-aware repair
r = r.replace('''    else:
        r = run("fix")
    crashes''', '''    else:
        pf = subprocess.run([sys.executable, "-m", "pyflakes", *[str(SD / n) for n in files() if n.endswith(".py") and (SD / n).is_file()]], capture_output=True, text=True).stdout
        if sig.startswith("rc0") and pf.strip():  # tests pass but static check fails (e.g. undefined names in a test): tell the coder, allow test edit
            r = run("fix", "STATIC CHECK FAILURES (pyflakes) - fix them, including missing imports in test files:\\n" + pf[:3000], edit=True)
        else:
            r = run("fix")
    crashes''')
# progress-based review loop (replaces fixed 3 rounds)
a = r.index("had_defects = False")
b = r.index('status("GREEN_TEST_EDITS_PENDING_REVIEW"')
new = '''had_defects, stale, rnd = False, Counter(), 0
while True:
    rnd += 1
    if rnd > 15: status("NEEDS_REVIEW", "runaway guard: 15 review rounds"); sys.exit(0)
    text = run("review").stdout
    parts = re.split(r"--- lens \\d: .*? ---", text)[1:]
    valid = [p for p in parts if not p.lstrip().startswith("REVIEW_ERROR")]
    luna = parts[4] if len(parts) > 4 and not parts[4].lstrip().startswith("REVIEW_ERROR") else None
    if luna is None:  # GPT-6 Luna (high) has priority: its answer is required for a round to count
        print(wp, "review round", rnd, "NO_REVIEW from Luna; retrying", flush=True)
        stale["NOLUNA"] += 1
        if stale["NOLUNA"] >= 3: status("NEEDS_REVIEW", "NO_REVIEW: Luna gave no valid review 3 times"); sys.exit(0)
        continue
    valid = [luna] + [p for p in valid if p is not luna]
    if len(valid) < 2:
        print(wp, "review round", rnd, "NO_REVIEW (quorum); retrying", flush=True)
        stale["NOQ"] += 1
        if stale["NOQ"] >= 3: status("NEEDS_REVIEW", "NO_REVIEW: quorum not reached 3 times"); sys.exit(0)
        continue
    if all(re.match(r"\\s*\\**PASS", p) for p in valid): break
    had_defects = True
    sig = hash("|".join(sorted(l.strip()[:70] for p in valid for l in p.splitlines() if re.search(r"\\b(HIGH|MED)\\b", l))))
    stale[sig] += 1
    print(wp, "review round", rnd, "defects (same set seen %d times)" % stale[sig], flush=True)
    if stale[sig] >= 3: status("NEEDS_REVIEW", "same HIGH/MED defect set 3 times: reviewers and coder disagree; needs owner/Claude decision"); sys.exit(0)
    run("fix", chr(10).join(valid)[:9000])
    if not green(): run("fix")
'''
r = r[:a] + new + r[b:]
ast.parse(r); (L / "race.py").write_text(r, encoding="utf-8")
print("convergence patch ok")
