import subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
L = Path(__file__).parent
ids = [f"wp{w}{n}" for w in "DEABC" for n in "123"] + ["wpD4"] + ["wpF1", "wpF2", "wpF3", "wpF4"]
def go(w):
    import shutil
    shutil.rmtree(L / 'stage' / f'{w}_ultra', ignore_errors=True)
    (L / f'{w}.files').unlink(missing_ok=True)
    for f in L.glob(f"{w}.*"): 
        if f.suffix in (".txt",) and ("history" in f.name or "lastrun" in f.name): f.unlink()
    log = (L / f"race_{w}.log").open("w"); subprocess.run([sys.executable, str(L / "race.py"), w], stdout=log, stderr=log, cwd=L.parent)
with ThreadPoolExecutor(6) as ex: list(ex.map(go, ids))
