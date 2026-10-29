"""Config fix (not product code): make every research spec end with the exact fenced FILE-block format the loop's parser requires; reset failed jobs; relaunch."""
import json, re, shutil, subprocess, time
from pathlib import Path
R = Path(r"D:\aai work\granthstudio")
ids = [f"wp{w}{n}" for w in "ABCDE" for n in "123"] + ["wpD4", "wpF1", "wpF2", "wpF3", "wpF4"]
redo = []
for i in ids:
    job = json.loads((R / "_loop" / "jobs" / f"research_{i}.json").read_text(encoding="utf-8"))
    sp = R / job["spec"]
    t = sp.read_text(encoding="utf-8")
    t = t[: t.index("Reply with only the FILE blocks")] if "Reply with only the FILE blocks" in t else t
    mod, test = job["files"]
    t += (f"OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` "
          f"followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:\n"
          f"FILE: {mod}\n```python\n<complete module source>\n```\nFILE: {test}\n```python\n<complete test source>\n```\n")
    sp.write_text(t, encoding="utf-8")
    sj = R / "_loop" / f"research_{i}" / "status.json"
    state = json.loads(sj.read_text(encoding="utf-8")).get("state") if sj.is_file() else None
    if state in ("escalate", "failed", None):
        shutil.rmtree(R / "_loop" / f"research_{i}", ignore_errors=True)
        redo.append(i)
print("specs fixed; relaunching", redo)
for i in redo:
    log = open(R / "_loop" / f"research_{i}.run.log", "w")
    subprocess.Popen(["uv", "run", "python", "scripts/source/fix_loop.py", "--job", f"_loop/jobs/research_{i}.json"], cwd=R, stdout=log, stderr=subprocess.STDOUT, creationflags=0x08000000)
    time.sleep(10)
