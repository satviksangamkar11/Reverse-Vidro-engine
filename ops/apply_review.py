"""Config helper (not product code): usage apply_review.py <reportfile> <piece id> [<piece id> ...]
Appends the piece's section of a reviewer report to its spec as REVIEW FINDINGS and relaunches its Nemotron fix_loop job."""
import re, shutil, subprocess, sys, time
from pathlib import Path
R = Path(r"D:\aai work\granthstudio")
report = Path(sys.argv[1]).read_text(encoding="utf-8")
for i in sys.argv[2:]:
    parts = re.split(r"(?m)^#{1,4} ", report)
    sec = next((p for p in parts if re.search(i, p[:200], re.I)), "")
    if not sec.strip() or re.match(r"\s*\S*\s*\n*\**PASS", sec.split("\n", 1)[-1][:40] or ""):
        print(i, "no findings section / PASS; skipped"); continue
    sp = R / "docs" / "pilot" / "nemotron_specs" / f"research_{i}.md"
    t = sp.read_text(encoding="utf-8")
    t = re.sub(r"\nREVIEW FINDINGS \(round \d+\).*?(?=\nOUTPUT FORMAT)", "", t, flags=re.S)
    n = len(re.findall(r"REVIEW FINDINGS \(round", t)) + 1
    note = f"\nREVIEW FINDINGS (round {n}, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.\n{sec.strip()[:6000]}\n"
    k = t.rfind("OUTPUT FORMAT")
    t = t[:k] + note + "\n" + t[k:] if k != -1 else t + note
    sp.write_text(t, encoding="utf-8")
    shutil.rmtree(R / "_loop" / f"research_{i}", ignore_errors=True)
    log = open(R / "_loop" / f"research_{i}.run.log", "w")
    subprocess.Popen(["uv", "run", "python", "scripts/source/fix_loop_stable.py", "--job", f"_loop/jobs/research_{i}.json"], cwd=R, stdout=log, stderr=subprocess.STDOUT, creationflags=0x08000000)
    print(i, "findings applied; job relaunched"); time.sleep(8)
