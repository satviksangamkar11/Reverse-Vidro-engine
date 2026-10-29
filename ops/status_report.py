import json, re, subprocess, sys
from pathlib import Path
L = Path(__file__).parent
ids = [f"wp{w}{n}" for w in "ABCDE" for n in "123"] + ["wpD4", "wpF1", "wpF2", "wpF3", "wpF4"]
rows = []
for i in ids:
    sd = L / "stage" / f"{i}_ultra"
    st = "not started"
    sf = L / f"{i}.status.json"
    state = json.loads(sf.read_text(encoding="utf-8"))["state"] if sf.is_file() else ""
    tests = "-"
    if sd.is_dir():
        fl = (L / f"{i}.files").read_text().split() if (L / f"{i}.files").is_file() else []
        t = [n for n in fl if n.startswith("test_")]
        if t:
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=no", *t], cwd=sd, capture_output=True, text=True, timeout=120)
            m = re.findall(r"(\d+) (passed|failed|error)", r.stdout)
            tests = ", ".join(f"{n} {k}" for n, k in m) or "no tests ran"
        else:
            tests = "no own test file yet"
        st = "built"
    rows.append((i, state or st, tests))
done = sum(1 for _, s, t in rows if s in ("GREEN_REVIEWED", "GREEN_TEST_EDITS_PENDING_REVIEW"))
green_tests = sum(1 for _, s, t in rows if "failed" not in t and "passed" in t and "error" not in t)
out = ["| piece | loop state | own tests |", "|---|---|---|"] + [f"| {a} | {b} | {c} |" for a, b, c in rows]
out.append(f"\nPieces fully done (tests green + reviews passed): {done}/{len(ids)}; pieces with own tests all passing: {green_tests}/{len(ids)}")
print("\n".join(out))
(L / "STATUS_TABLE.md").write_text("\n".join(out), encoding="utf-8")
