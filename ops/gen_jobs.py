"""Config generator (not product code): converts the 20 research specs into fix_loop jobs inside D:\\aai work\\granthstudio.
Seeds each job's files from the existing stage code so progress is kept. No API calls."""
import json, re, shutil
from pathlib import Path
R = Path(r"D:\aai work\granthstudio")
L = Path(__file__).parent
ids = [f"wp{w}{n}" for w in "ABCDE" for n in "123"] + ["wpD4", "wpF1", "wpF2", "wpF3", "wpF4"]
(R / "research" / "pieces").mkdir(parents=True, exist_ok=True)
(R / "_loop" / "jobs").mkdir(parents=True, exist_ok=True)
out = []
for i in ids:
    spec = (L / f"{i}.spec.md").read_text(encoding="utf-8")
    m = re.search(r"^REQUIRED:(.*)$", spec, re.M)
    names = m.group(1).split() if m else []
    if len(names) != 2:
        out.append((i, "NO REQUIRED LINE")); continue
    files = [f"research/pieces/{n}" for n in names]
    body = re.sub(r"^(CONTEXT|REQUIRED):.*$\n?", "", spec, flags=re.M)
    body += ("\n\nHARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; "
             "no network; no Kimi; do not import other pieces' modules; do not drop public functions. "
             f"Module file: {files[0]}; test file: {files[1]} (tests import the module by its plain file name, e.g. `from {names[0][:-3]} import ...`).\n\n"
             f"Reply with only the FILE blocks:\nFILE: {files[0]}\nFILE: {files[1]}\n")
    sp = R / "docs" / "pilot" / "nemotron_specs" / f"research_{i}.md"
    sp.write_text(body, encoding="utf-8")
    sd = L / "stage" / f"{i}_ultra"
    seeded = 0
    for n, f in zip(names, files):
        src = sd / n
        if src.is_file():
            shutil.copy2(src, R / f); seeded += 1
    job = {"name": f"research_{i}", "spec": f"docs/pilot/nemotron_specs/research_{i}.md", "files": files, "tests": [files[1]], "reference": [],
           "max_rounds": 3, "review": True, "review_rounds": 4, "reviewers": ["glm", "codex"]}
    (R / "_loop" / "jobs" / f"research_{i}.json").write_text(json.dumps(job, indent=1), encoding="utf-8")
    out.append((i, f"job ok, seeded {seeded}/2"))
for o in out: print(*o)
