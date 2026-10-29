import sys, time, json, requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
T = Path(__file__).parent.parent
keys = [p.read_text().strip() for p in sorted((T.parent / "secrets/nvidia").glob("nvidia_api_key*.txt"))][:14]
models = [m["id"] for m in requests.get("https://integrate.api.nvidia.com/v1/models", timeout=30).json()["data"]]
skip = ("embed", "guard", "safety", "reward", "parse", "clip", "vila", "neva", "kosmos", "fuyu", "deplot", "detector", "calibration", "translate", "nemoguard", "vision", "cosmos", "retriever", "llama2", "codellama", "sea-lion", "-2b", "-4b-", "-7b", "6.7b", "-8b")
cands = [m for m in models if not any(s in m for s in skip)]
code = (T / "_loop/stage/wpA_ultra/ingest.py").read_text(encoding="utf-8")
prompt = "Review this Python code for concrete defects only (zip-slip, resumability, edge cases). List up to 5 ranked defects with a line reference and a fix, or say PASS.\n\n" + code
def run(i_m):
    i, m = i_m; t = time.time()
    try:
        r = requests.post("https://integrate.api.nvidia.com/v1/chat/completions", headers={"Authorization": f"Bearer {keys[i % 14]}"}, json={"model": m, "messages": [{"role": "user", "content": prompt}], "max_tokens": 6000, "temperature": 0.2}, timeout=(15, 300))
        if r.status_code != 200: return m, f"HTTP {r.status_code}", round(time.time() - t, 1), 0
        txt = r.json()["choices"][0]["message"].get("content") or ""
        return m, "OK" if len(txt) > 150 else "EMPTY/SHORT", round(time.time() - t, 1), len(txt)
    except Exception as e:
        return m, type(e).__name__, round(time.time() - t, 1), 0
with ThreadPoolExecutor(len(cands)) as ex:
    res = sorted(ex.map(run, enumerate(cands)), key=lambda x: (x[1] != "OK", x[2]))
for r in res: print(*r, sep=" | ")
