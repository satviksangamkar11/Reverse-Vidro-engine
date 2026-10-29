"""Ops/config script: split the escalated D4 job into three small sequential Nemotron jobs (same two files), then chain-launch them.
Each stage must pass its tests before the next starts. No model calls here."""
import json, re, subprocess, sys
from pathlib import Path
R = Path(r"D:\aai work\granthstudio")
base = Path(r"D:\aai work\animation_research_tool\_loop\wpD4.spec.md").read_text(encoding="utf-8")
base = re.sub(r"^(CONTEXT|REQUIRED):.*$\n?", "", base, flags=re.M)
SHAPE = ("D1 BEAT SHAPE (authoritative): a beat is a dict with keys beat_id, video_id, start_time {seconds,basis}, end_time {seconds,basis}, information_conveyed, "
         "department_findings = {\"1\"..\"16\": [ {term, status in OBSERVED|NOT_OBSERVED|UNKNOWN|NOT_EXAMINED, observed, evidence:[{frame:int,time:float}], "
         "inferred_purpose, alternatives:[str], contraindication, confidence} ]}, reproduction {status, artwork_needed, simplest_method}, unknowns:[str], sequence_pattern. "
         "department_findings values are LISTS of finding dicts (NOT one dict per department).")
FMT = ("\n\nHARD RULES: stdlib only; tests use tempfile/in-memory data, no absolute drive paths, no network; do not drop existing public functions "
       "(reconstruct_sequence, verify_reconstruction); keep every currently passing behaviour. The reply must contain BOTH complete files.\n\n"
       "OUTPUT FORMAT (mandatory): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block "
       "that starts with ```python on its own line and ends with ``` on its own line:\nFILE: research/pieces/d4_reconstruct.py\n```python\n<complete module source>\n```\n"
       "FILE: research/pieces/test_d4_reconstruct.py\n```python\n<complete test source>\n```\n")
stages = {
 "wpD4a": "STAGE 1 OF 3 (this job only): switch EVERY read of department_findings to the list shape above, rewrite ALL test fixtures to that shape, keep the supplied beat order (never sort by beat_id string; if sorting is needed use (start_time.seconds, original index)), and build why_it_may_work from each finding's inferred_purpose (with confidence and based_on_beat_ids). Do NOT add citations or audit logic yet.",
 "wpD4b": "STAGE 2 OF 3 (this job only): every claim in the reconstruction must carry its evidence citations (frame/time) copied from the finding; verify_reconstruction must check EACH cited frame/time exists in the source beat's finding evidence and return ok False naming the claim when one is missing or absent; add the regression test that deletes one evidence entry and expects ok False. Keep stage-1 behaviour and tests.",
 "wpD4c": "STAGE 3 OF 3 (this job only): audit and audio rules. semantic_status is ALWAYS exactly \"NOT_VERIFIED\"; add a separate field audited_status that is set ('AUDITED_' + verdict) ONLY when an `audit` dict with all four of auditor, video_id, verdict, notes is supplied, otherwise absent/None. Sound claims are rejected unless real audio evidence exists; when audio status is UNAVAILABLE or NO_AUDIO_STREAM the sound_image section is exactly {\"status\": \"UNAVAILABLE\"}. Unhashable values in unknowns/findings must not raise (report a problem instead). Keep stages 1-2 behaviour and tests.",
}
for name, scope in stages.items():
    (R / "docs/pilot/nemotron_specs" / f"research_{name}.md").write_text(f"# SPEC {name}: PATCH research/pieces/d4_reconstruct.py + test_d4_reconstruct.py\n\n{scope}\n\n{SHAPE}\n\nBASE REQUIREMENT (for context):\n{base}{FMT}", encoding="utf-8")
    job = {"name": f"research_{name}", "spec": f"docs/pilot/nemotron_specs/research_{name}.md",
           "files": ["research/pieces/d4_reconstruct.py", "research/pieces/test_d4_reconstruct.py"], "tests": ["research/pieces/test_d4_reconstruct.py"],
           "reference": ["research/pieces/d1_beat_schema.py"], "max_rounds": 3, "review": False, "reviewers": [], "fixers": ["nemotron", "nemotron", "nemotron"]}
    (R / "_loop/jobs" / f"research_{name}.json").write_text(json.dumps(job, indent=1), encoding="utf-8")
chain = '''
import subprocess, sys, json
from pathlib import Path
R = Path(r"D:\\aai work\\granthstudio")
for n in ("wpD4a", "wpD4b", "wpD4c"):
    r = subprocess.run(["uv","run","python","scripts/source/fix_loop_stable.py","--job",f"_loop/jobs/research_{n}.json"], cwd=R, capture_output=True, text=True)
    (R/"_loop"/f"research_{n}.run.log").write_text(r.stdout + r.stderr, encoding="utf-8")
    if r.returncode != 0: break
'''
(R / "_loop" / "d4_chain.py").write_text(chain, encoding="utf-8")
subprocess.Popen([sys.executable, str(R / "_loop" / "d4_chain.py")], creationflags=0x08000000 | 0x00000008, close_fds=True)
print("D4 split into 3 sequential jobs; chain started")
