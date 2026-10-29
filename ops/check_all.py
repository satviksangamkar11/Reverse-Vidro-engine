"""One-call status check (ops tool): job state + own-test result per research piece. Output is compact on purpose."""
import json, subprocess, sys, time
from pathlib import Path
R = Path(r"D:\aai work\granthstudio")
pieces = {"wpA1": "a1_queue", "wpA2": "a2_collect", "wpA3": "a3_cli", "wpB1": "a1_audio_io", "wpB2": "a2_transcribe", "wpB3": "a3_align",
          "wpC1": "c1_cluster", "wpC2": "c2_review", "wpC3": "c3_state", "wpD1": "d1_beat_schema", "wpD2": "d2_recipe_compiler",
          "wpD3": "d3_deliverables", "wpD4": "d4_reconstruct", "wpE1": "a1_scene_selection", "wpE2": "a2_recipe_prompts",
          "wpE3": "a3_blind_scoring", "wpF1": "f1_corpus", "wpF2": "f2_bias", "wpF3": "f3_publish", "wpF4": "f4_classify"}
rev = {}
for f in (R / "_loop" / "reviews").glob("*.md"):
    pass
green = 0
print(time.strftime("%H:%M"), "piece | job state (rounds) | own tests")
for i, m in pieces.items():
    sj = R / "_loop" / f"research_{i}" / "status.json"
    st, n = "no-status", 0
    if sj.is_file():
        d = json.loads(sj.read_text(encoding="utf-8")); st = d.get("state"); n = len(d.get("rounds") or [])
    r = subprocess.run(["uv", "run", "python", "-m", "pytest", "-q", "--tb=no", f"research/pieces/test_{m}.py"], cwd=R, capture_output=True, text=True, timeout=300)
    last = (r.stdout.strip().splitlines() or ["?"])[-1]
    ok = r.returncode == 0
    green += ok
    print(f"{i} | {st} ({n}) | {'OK ' if ok else 'FAIL '}{last[:40]}" + ("  <ESCALATE.md>" if st == "escalate" else ""))
print(f"tests green: {green}/20")
