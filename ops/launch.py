import os, subprocess, sys, time
from pathlib import Path
L = Path(__file__).parent
ids = [f"wp{w}{n}" for w in "ABCDE" for n in "123"] + ["wpD4", "wpF1", "wpF2", "wpF3", "wpF4"]
INTACT = {"wpD2", "wpE3"}  # verified intact after the prompt-bug damage; the rest rebuild from scratch
for i in ids:
    for x in (f"{i}.status.json", f"{i}.history.txt", f"{i}.testedits.diff"):
        (L / x).unlink(missing_ok=True)
    env = dict(os.environ)
    if i in INTACT: env["RESUME"] = "1"
    subprocess.Popen([sys.executable, str(L / "race.py"), i], stdout=open(L / f"race_{i}.log", "w"), stderr=subprocess.STDOUT, env=env, cwd=L.parent, creationflags=0x08000000)
    time.sleep(8)
