import subprocess, time
from pathlib import Path
R = Path(r"D:\aai work\granthstudio")
ids = [f"wp{w}{n}" for w in "ABCDE" for n in "123"] + ["wpD4", "wpF1", "wpF2", "wpF3", "wpF4"]
for i in ids:
    log = open(R / "_loop" / f"research_{i}.run.log", "w")
    subprocess.Popen(["uv", "run", "python", "scripts/source/fix_loop.py", "--job", f"_loop/jobs/research_{i}.json"], cwd=R, stdout=log, stderr=subprocess.STDOUT, creationflags=0x08000000)
    time.sleep(10)
