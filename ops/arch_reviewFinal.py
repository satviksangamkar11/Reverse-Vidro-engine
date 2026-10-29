import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(Path(__file__).parent.parent))
from nvidia_scheduler import NvidiaScheduler
import requests
L = Path(__file__).parent
keys = [p.read_text().strip() for p in sorted((L.parent.parent / "secrets/nvidia").glob("nvidia_api_key*.txt"))][:14]
ctx = (L / "arch_context.txt").read_text(encoding="utf-8")
def post(url, json=None, **kw): return requests.post(url, json=dict(json, chat_template_kwargs={"enable_thinking": False}), **kw)
def go(m):
    try:
        r = NvidiaScheduler(keys, model=m, read_timeout=900, max_calls=3, post=post).call(ctx, max_tokens=8000)
        t = r["text"] if r["status"] == "OK" else "ERROR " + r["status"]
    except BaseException as e: t = "ERROR %s" % e
    (L / ("archFinal_" + m.split("/")[-1] + ".txt")).write_text(t, encoding="utf-8"); return m, len(t)
with ThreadPoolExecutor(5) as ex:
    for x in ex.map(go, ["nvidia/nemotron-3-ultra-550b-a55b", "z-ai/glm-5.3-flash", "meta/muse-glimmer-30b", "minimaxai/minimax-m3.1-flash"]): print(x, flush=True)
