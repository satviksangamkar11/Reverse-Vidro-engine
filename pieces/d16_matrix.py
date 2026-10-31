import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HELD = {"354a38a0", "37745d70", "baf59433"}
DEV = {"10151cce", "264e48c4", "585b32de", "5c93ec37", "69a00a0f", "7434a0f7", "7a1e2b26", "85c38505", "a44aef0b", "caf6fb64"}
MEASURED_VIDEOS = {"7434a0f7", "7a1e2b26"}
MEASURED_DEPTS = {5, 7}
BLOCKED_VIDEO = "5c93ec37"
CATEGORIES = {"NEVER_EXAMINED", "MODEL_ONLY", "PARTIAL_MEASUREMENT", "HUMAN_VERIFIED_PARTIAL", "UNKNOWN", "HELDOUT_PROTECTED"}
LEDGER = "work/phase1/coverage_16/DEPARTMENT_VIDEO_LEDGER_16x13.csv"
MODULES = "work/phase1/roadmap_audit/18_MODULE_COVERAGE.csv"
MEASUREMENTS = "work/phase1/step4/STEP4_MEASUREMENTS.json"
OUT = "work/phase1/departments_16/DEPARTMENT_VIDEO_MATRIX.csv"
OUT_PATH = os.path.join(ROOT, *OUT.split("/"))
DEPT_MODULES = {1: ["M02", "M03", "M04"], 2: ["M02", "M04", "M07"], 3: ["M05", "M06", "M07"], 4: ["M05", "M09"], 5: ["M11"], 6: ["M10", "M15"], 7: ["M09", "M13"], 8: ["M12"], 9: ["M08"], 10: ["M12", "M16"], 11: ["M16"], 12: ["M15"], 13: ["M17"], 14: ["M18"], 15: ["M14"], 16: ["M16"]}
JUSTIFIED = {12: "brightness summary from media, if media exists", 13: "speech timing from the cached transcript when present", 14: "caption text already in observations", 15: "durations and rhythm from beat timings"}
DETECTOR_NOTE = "NOT_JUSTIFIED: frozen detector output exists only for 7434a0f7 and 7a1e2b26 (existing read-only measurement); no measurement exists for this video; Step 5 deferred; no re-run"
TEACH = {"MEASUREMENT": "measured camera or transition fact for this interval only; no meaning attached", "AI_OBSERVATION": "AI reading of this video only; teach only after human verification", "TRANSCRIPT_UNVERIFIED": "speech timing only; wording unverified", "NONE": "nothing teachable from this record", "NONE_NOT_READ": "none (protected)"}
REMAIN = {"AI_OBSERVATION": "human verification of listed beats", "MEASUREMENT": "human check of meaning", "TRANSCRIPT_UNVERIFIED": "transcript verification", "NONE": "new evidence or method required", "NONE_NOT_READ": "protected; Step 5 only"}
COLUMNS = ["dept", "dept_name", "video_id", "set", "ledger_category", "research_status", "evidence_type", "measured", "observed_beat_count", "observed_beat_ids", "observed_time_min", "observed_time_max", "unknown_beat_count", "not_examined_beat_count", "missing_beat_count", "extraction_performed", "sources_read", "implemented_capability", "human_verified_items_count", "further_offline_analysis", "teachable_to_writer_director", "remaining_validation"]


def _p(root, rel):
    return os.path.join(root, *rel.split("/"))


def _beat_rel(vid):
    return "work/phase1/v4/audit_%s/beats_%s.json" % (vid, vid)


def _audio_rel(vid):
    return "work/phase1/v4/audit_%s/audio_%s.json" % (vid, vid)


def _hv(cell):
    s = cell.strip()
    return 1 if s and s != "0" else 0


def load_ledger(root):
    out = {}
    with open(_p(root, LEDGER), newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["category"] not in CATEGORIES:
                raise ValueError("unknown ledger category %r for %s dept %s" % (r["category"], r["video_id"], r["dept"]))
            out[(int(r["dept"]), r["video_id"])] = r
    return out


def load_beats(root, video_id):
    if video_id in HELD:
        raise ValueError("held-out video, not read: " + video_id)
    with open(_p(root, _beat_rel(video_id)), encoding="utf-8") as f:
        return json.load(f)["beats"]


def findings_for(beat, dept):
    d = beat.get("department_findings", {})
    k = str(dept)
    if k not in d:
        return []
    if not isinstance(d[k], list):
        raise ValueError("department_findings[%s] is not a list" % k)
    return d[k]


def status_summary(beats, dept):
    s = {"observed": 0, "unknown": 0, "not_examined": 0, "missing": 0}
    for b in beats:
        items = findings_for(b, dept)
        if not items:
            s["missing"] += 1
            continue
        sts = {i.get("status") for i in items}
        s["observed"] += "OBSERVED" in sts
        s["unknown"] += "UNKNOWN" in sts
        s["not_examined"] += "NOT_EXAMINED" in sts
    return s


def observed_beats(beats, dept):
    return [b for b in beats if any(i.get("status") == "OBSERVED" for i in findings_for(b, dept))]


def audio_facts(root, video_id):
    with open(_p(root, _audio_rel(video_id)), encoding="utf-8") as f:
        a = json.load(f)
    return {"transcript_status": a.get("transcript_status"), "speech_segment_count": len(a.get("speech_segments", [])), "sound_classes": a.get("sound_classes")}


def capability_text(root, module_ids, video_id):
    with open(_p(root, MODULES), newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for mid in module_ids:
        for r in rows:
            if r["module_id"] == mid and r["video_id"] == video_id:
                return r["existing_code"]
    return "NONE_RECORDED"


def _measured_keys(root):
    with open(_p(root, MEASUREMENTS), encoding="utf-8") as f:
        return set(json.load(f))


def _research(vid, dept, cat):
    if vid == BLOCKED_VIDEO and dept == 13:
        return "BLOCKED_BY_SOURCE"
    if cat == "NEVER_EXAMINED":
        return "NOT_EXAMINED"
    if cat in ("MODEL_ONLY", "PARTIAL_MEASUREMENT", "HUMAN_VERIFIED_PARTIAL"):
        return "PARTIAL_RESEARCH"
    return "UNKNOWN"


def _further(dept):
    if dept in (5, 7):
        return DETECTOR_NOTE
    if dept in JUSTIFIED:
        return "JUSTIFIED_NON_MODEL: " + JUSTIFIED[dept]
    return "NOT_JUSTIFIED_WITHOUT_HUMAN_OR_NEW_MODEL: no non-model source defined for this department"


def build_rows(root):
    led = load_ledger(root)
    rows = []
    for dept, vid in sorted(led):
        r = led[(dept, vid)]
        cat = r["category"]
        base = {"dept": dept, "dept_name": r["dept_name"], "video_id": vid, "set": r["set"], "ledger_category": cat, "human_verified_items_count": _hv(r["human_verified_items"])}
        if vid in HELD:
            rows.append(dict(base, research_status="BLOCKED_BY_SOURCE", evidence_type="NONE_NOT_READ", measured="N", observed_beat_count=0, observed_beat_ids="", observed_time_min="", observed_time_max="", unknown_beat_count=0, not_examined_beat_count=0, missing_beat_count=0, extraction_performed="none (protected; not read)", sources_read=LEDGER, implemented_capability="NONE_RECORDED (protected; not read)", further_offline_analysis="NOT_ALLOWED: protected", teachable_to_writer_director=TEACH["NONE_NOT_READ"], remaining_validation=REMAIN["NONE_NOT_READ"]))
            continue
        mods = DEPT_MODULES[dept]
        beats = load_beats(root, vid)
        obs = observed_beats(beats, dept)
        st = status_summary(beats, dept)
        speech = audio_facts(root, vid)["speech_segment_count"] if dept == 13 else 0
        measured = vid in MEASURED_VIDEOS and dept in MEASURED_DEPTS and vid in _measured_keys(root)
        n = len(obs)
        if measured:
            ev = "MEASUREMENT"
        elif n:
            ev = "AI_OBSERVATION"
        elif dept == 13 and speech:
            ev = "TRANSCRIPT_UNVERIFIED"
        else:
            ev = "NONE"
        parts = []
        if n:
            parts.append("vision-report text read per beat (department_findings)")
        if measured:
            parts.append("frozen Step 4 detector measurement (existing output, read only)")
        if dept == 13 and speech:
            parts.append("cached speech-to-text transcript read (unverified)")
        if not parts:
            parts.append("none (status NOT_EXAMINED on every beat)" if cat == "NEVER_EXAMINED" else "none")
        src = [LEDGER, _beat_rel(vid)] + ([_audio_rel(vid)] if dept == 13 else []) + [MODULES] + ([MEASUREMENTS] if measured else [])
        rows.append(dict(base, research_status=_research(vid, dept, cat), evidence_type=ev, measured="Y" if measured else "N", observed_beat_count=n, observed_beat_ids=";".join(str(b["beat_id"]) for b in obs), observed_time_min=min((b["start_time"] for b in obs), default=""), observed_time_max=max((b["end_time"] for b in obs), default=""), unknown_beat_count=st["unknown"], not_examined_beat_count=st["not_examined"], missing_beat_count=st["missing"], extraction_performed=" + ".join(parts), sources_read=";".join(src), implemented_capability="modules " + ", ".join(mods) + ": " + capability_text(root, mods, vid), further_offline_analysis=_further(dept), teachable_to_writer_director=TEACH[ev], remaining_validation=REMAIN[ev]))
    return rows


def write_matrix(root, out_path):
    rows = build_rows(root)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def main(argv=None):
    out = argv[0] if argv else OUT_PATH
    n = write_matrix(ROOT, out)
    print(n)
    return n


if __name__ == "__main__":
    main(sys.argv[1:])
