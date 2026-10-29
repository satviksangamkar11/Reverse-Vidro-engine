from pathlib import Path
L = Path(__file__).parent
def add(name, text):
    p = L / f"{name}.spec.md"
    p.write_text(p.read_text(encoding="utf-8").rstrip("\n") + "\n" + text.strip() + "\n", encoding="utf-8")

add("wpD1", """
GRAMMAR EXTENSION (owner requirement; keep <=3 public functions; no per-technique enums):
- BeatDict gains these optional-safe fields, validated by the existing validate function: `source_url` (str|None), `level_links` {"video_id","sequence_id","shot_ids":[str]} (a beat may span several shots), `verification_status` in ("UNVERIFIED","FRAME_CHECKED","AUDIO_CHECKED","BOTH_CHECKED"), `unknowns` list[str], `information_conveyed` str, and `department_findings`: dict keyed by department id "1".."16" (storytelling, narrative, direction, shot_planning, camera, composition, editing, animation_principles, performance, production, vfx, color_lighting, sound, captions, pacing, practical) -> list of finding dicts {"term": free-text technique name (no fixed enum; any evidence-supported term allowed), "status": "OBSERVED"|"NOT_OBSERVED"|"UNKNOWN", "observed": str, "evidence": [{"frame":int,"time":float}], "inferred_purpose": str|None, "alternatives": list[str], "contraindication": str|None, "confidence": "LOW"|"MEDIUM"|"HIGH"}. A department may be absent or empty: unobserved techniques stay unobserved and are never required.
- Validation rules in parse_beat/validate: any finding with status OBSERVED needs >=1 evidence entry; inferred_purpose is always a hypothesis (stored apart from observed); reject any text asserting editing software, camera lens/focal length, hidden rig or original screenplay wording as fact; if the supplied audio status is "UNAVAILABLE" (frame-only ZIP) every sound finding must have status UNKNOWN and no observed audio text, else reject.
""")
add("wpD2", """
GRAMMAR EXTENSION: recipes keep the cross-level link: each recipe carries `sequence_pattern` (ordered list of the purposes/terms of the beats that formed it, e.g. ["withhold","push_in","pause","hard_cut","reaction","hold"]) so the arrangement is kept, not six tags; `when_not_to_use` (str, from union of counterexamples/contraindications); `preset_id` (str|None) copied ONLY from a caller-supplied registry argument `registered_presets` (a set); a preset id not in that set is dropped and never generated. Recipes also expose `stage1_lessons` list for: narrative presentation, shot sequencing, performance, camera/composition, editing/continuity, artwork requirements, sound; and `stage2_lessons` for: approved preset, compatible assets, feasible alternatives, exact NEED_NEW gap (text only; no invented ids).
""")
add("wpD3", """
GRAMMAR EXTENSION: playbook_guard must also flag (as violations) playbook text that instructs Kimi to: rewrite or paraphrase EASY wording, invent story events or dialogue, assign timings in seconds/frames, name an unregistered preset id, emit animation code, or add music/background score to production (reference music may be described only as research with the words "reference only"). Violations raise ValueError from write_deliverables before any file is written. The playbook must state: reference music is research-only and prohibited in production; reference dialogue never alters EASY wording.
""")
(L / "wpD4.spec.md").write_text("""CONTEXT:
REQUIRED: d4_reconstruct.py test_d4_reconstruct.py
# WP-D4: full-sequence reconstruction + mechanical truth check (pure; no network/model/Kimi calls). Model text is injected as data.
Goal: turn validated beats (from D1 BeatDict shape, plain dicts) plus audio evidence into the 8-part reconstruction of ONE video, and mechanically check it against the evidence so it teaches more than independent shot descriptions.
1. `reconstruct_sequence(beats, audio_evidence)` -> dict with keys: "narrative_progression" (ordered beat summaries using information_conveyed), "shots_and_transitions" (per shot id: start/end, terms from department_findings 4,5,6,7), "performance" (departments 8,9), "sound_image" (department 13 findings plus audio_evidence; if audio status is UNAVAILABLE or NO_AUDIO_STREAM the section is exactly {"status":"UNAVAILABLE"}), "techniques" (departments 10,11,12,14), "why_it_may_work" (list of {"hypothesis": inferred_purpose, "based_on_beat_ids":[...], "confidence"}), "simplest_reproduction" (reproduction.status/artwork_needed/simplest_method of each beat, NEED_NEW preserved), "unknowns" (union of beats' unknowns + NOT_OBSERVED/UNKNOWN findings) and "relationships" (list of {"from_beat","to_beat","pattern"} for consecutive beats with the sequence_pattern, so order and setup->payoff links are kept).
2. `verify_reconstruction(reconstruction, beats)` -> {"ok": bool, "problems": [str]}. Mechanical checks only: every OBSERVED claim cites an evidence frame/time that exists in a source beat; every hypothesis is in why_it_may_work (never in observed sections); no sound claim exists when audio is UNAVAILABLE; at least one relationship entry exists when there are >=2 beats; no field asserts editing software, lens, hidden rig or screenplay text; no preset id appears that is not in the beats' reproduction data.
Worked example: 3 beats (withhold close-up -> reveal wide cut -> reaction hold) give relationships [{"from_beat":"b1","to_beat":"b2",...},{"from_beat":"b2","to_beat":"b3",...}], why_it_may_work entries are hypotheses with based_on_beat_ids, and a frame-only video gives sound_image == {"status":"UNAVAILABLE"}; deleting one evidence entry makes verify_reconstruction return ok False naming the claim.
""", encoding="utf-8")
(L / "CHECKLIST_GRAMMAR_FINAL.md").write_text("""# Grammar coverage resolution (code-checked specs; reviewer opinions in grammar_review_*.txt)
Ultra's first checklist proposed per-technique enums, 6-12 public functions per piece and a change to frozen F4. GLM and muse-glimmer flagged the F4 change and cap violations; GLM flagged that enums force unobserved techniques. Resolution:
- 16 departments -> D1 `department_findings` (free-text terms, OBSERVED/NOT_OBSERVED/UNKNOWN, evidence required when OBSERVED). No enums, nothing mandatory.
- 4 analysis levels with relationships -> D1 `level_links`; D2 `sequence_pattern`; D4 `relationships`.
- Evidence fields (source URL, timestamps+frames, observed vs inferred, alternatives, confidence, verification status, contraindications) -> D1.
- Prohibitions (software/lens/rig/screenplay; frame-only ZIP audio) -> D1 validation, D4 verify.
- Kimi permissions (EASY, events, timings, ids, code, music) -> D3 playbook_guard; ids only from registry (D2, F4 unchanged).
- Stage 1 / Stage 2 guidance -> D2 stage1_lessons / stage2_lessons; F4 views unchanged (frozen).
- Acceptance reconstruction (8 parts + check) -> D4. The real acceptance run on one reference with audio happens after integration.
- F1-F4 untouched; no new subsystem; no Kimi calls.
""", encoding="utf-8")
print("patched")
