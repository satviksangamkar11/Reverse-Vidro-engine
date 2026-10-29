
import os, subprocess, sys, time
from pathlib import Path
L = Path("_loop")
for i, resume in [("wpA2",1),("wpA3",1),("wpB2",1),("wpB3",1),("wpC1",1),("wpC2",1),("wpC3",1),("wpD2",1),("wpD3",1),("wpE1",1),("wpE2",1),("wpF1",1),("wpF2",1),("wpF3",0)]:
    for x in (f"{i}.status.json", f"{i}.history.txt"): (L/x).unlink(missing_ok=True)
    env = dict(os.environ)
    if resume: env["RESUME"] = "1"
    subprocess.Popen([sys.executable, str(L/"race.py"), i], stdout=open(L/f"race_{i}.log","w"), stderr=subprocess.STDOUT, env=env, creationflags=0x08000000)
    time.sleep(6)
