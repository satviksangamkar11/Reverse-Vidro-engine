"""D16TCH: evidence-linked teacher candidate inventory.

One candidate record per supported AI observation in the development videos,
plus the 7434a0f7 lesson candidates with their status kept. Nothing is
promoted. Standard library plus json and os only; no network, no model calls.
"""

import json
import os

DEV = (
    "10151cce", "264e48c4", "585b32de", "5c93ec37", "69a00a0f",
    "7434a0f7", "7a1e2b26", "85c38505", "a44aef0b", "caf6fb64",
)
HELD = ("354a38a0", "37745d70", "baf59433")

DEPT_NAMES = {
    1: "Storytelling / screenwriting",
    2: "Narrative construction",
    3: "Direction",
    4: "Shot planning",
    5: "Camera language",
    6: "Composition / visual hierarchy",
    7: "Editing / transitions",
    8: "Animation principles",
    9: "Character performance",
    10: "Animation production",
    11: "VFX / compositing",
    12: "Colour / lighting / art direction",
    13: "Sound / audiovisual editing",
    14: "Captions / motion graphics",
    15: "Pacing / attention",
    16: "Practical execution",
}
STORY_DEPTS = {1, 2, 3, 4}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(
    ROOT, "work", "phase1", "departments_16", "CROSS_VIDEO_TEACHER_CANDIDATES.json"
)
LESSON_REL = ("work", "phase1", "overlays", "lesson_candidates_7434a0f7.json")
F4_REL = ("work", "phase1", "f4_diagnosis_v2.json")

OBSERVATION_SOURCE = "AI vision report (department_findings), unverified"
NOT_ASSESSED = "not assessed"
UNKNOWNS = [
    "creator not recorded",
    "art style not recorded",
    "vision report is model output with LOW confidence unless the item says otherwise",
]
F4_STATUS = "NOT_MAPPED (no technique id on this observation)"
CANDIDATE_ELIGIBILITY = "NOT_ELIGIBLE (F4 unchanged; no verified creators; no recorded art style)"
PRACTICAL = "NOT_CHECKED_IN_THIS_RECORD (see PRODUCTION_EXECUTION_COMPATIBILITY.json)"
LESSON_ELIGIBILITY = "NOT_ELIGIBLE (candidate; not promoted)"
WITHDRAWN_BEATS = ("event_001", "event_002")
WITHDRAWN_ELIGIBILITY = "WITHDRAWN_INACTIVE"
WITHDRAWN_STATUS = "UNKNOWN_INACTIVE"
F4_UNMAPPED = "UNMAPPED (technique_tags is empty)"
F4_NOT_ASSESSED = "MAPPING_NOT_ASSESSED (technique_tags present)"
F4_SOURCE_GAP = "SOURCE GAP (technique_tags missing)"
CREATED_NOTE = (
    "Teacher candidate inventory built from AI beat reports and lesson candidates. "
    "Nothing promoted; no candidate is eligible in this build."
)


def _read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _copy(obj):
    return json.loads(json.dumps(obj))


def _beat_path(root, video_id):
    return os.path.join(
        root, "work", "phase1", "v4", f"audit_{video_id}", f"beats_{video_id}.json"
    )


def load_beats(root, video_id):
    if video_id in HELD:
        raise ValueError(f"held-out video id must not be opened: {video_id}")
    return _read_json(_beat_path(root, video_id))["beats"]


def observation_items(beat):
    findings = beat.get("department_findings") or {}
    for dept in range(1, 17):
        for index, item in enumerate(findings.get(str(dept)) or []):
            text = item.get("observed")
            if item.get("status") == "OBSERVED" and isinstance(text, str) and text.strip():
                yield dept, index, item


def _load_dev_beats(root):
    return {vid: load_beats(root, vid) for vid in DEV}


def _videos_by_department(all_beats):
    seen = {}
    for vid, beats in all_beats.items():
        for beat in beats:
            for dept, _index, _item in observation_items(beat):
                seen.setdefault(dept, set()).add(vid)
    return seen


def _candidate(vid, beat, dept, index, item, videos_by_dept):
    unknowns = list(UNKNOWNS)
    if item.get("confidence") == "LOW":
        unknowns.append("item confidence is LOW")
    others = sorted(v for v in videos_by_dept.get(dept, ()) if v != vid)
    return {
        "candidate_id": f"D{dept}-{vid}-{beat['beat_id']}-{index}",
        "department_id": dept,
        "department_name": DEPT_NAMES[dept],
        "video_id": vid,
        "beat_id": beat["beat_id"],
        "start_time": beat["start_time"],
        "end_time": beat["end_time"],
        "direct_observation": item["observed"],
        "observation_source": OBSERVATION_SOURCE,
        "interpretation": NOT_ASSESSED,
        "directing_application": NOT_ASSESSED,
        "verification_status": "AI_OBSERVATION_UNVERIFIED",
        "narrative_scene_relevance": (
            "STORY_OR_DIRECTION" if dept in STORY_DEPTS else "PRODUCTION_OR_PRESENTATION"
        ),
        "distinct_video_count": 1,
        "independent_creator_count": 0,
        "other_videos_with_same_department_observation": others,
        "unknowns": unknowns,
        "f4_status": F4_STATUS,
        "eligibility": CANDIDATE_ELIGIBILITY,
        "practical_compatibility": PRACTICAL,
    }


def build_candidates(root):
    all_beats = _load_dev_beats(root)
    videos_by_dept = _videos_by_department(all_beats)
    out = []
    for vid in sorted(all_beats):
        for beat in all_beats[vid]:
            for dept, index, item in observation_items(beat):
                out.append(_candidate(vid, beat, dept, index, item, videos_by_dept))
    return out


def _f4_status(lesson):
    if "technique_tags" not in lesson:
        return F4_SOURCE_GAP
    if lesson["technique_tags"] == []:
        return F4_UNMAPPED
    return F4_NOT_ASSESSED


def _is_withdrawn(lesson_id, event):
    return (
        isinstance(lesson_id, str)
        and lesson_id.startswith("L4")
        and event.get("beat_id") in WITHDRAWN_BEATS
    )


def _event_entry(lesson_id, event):
    out = _copy(event)
    out["distinct_video_count"] = 1
    out["independent_creator_count"] = 0
    if _is_withdrawn(lesson_id, event):
        out["eligibility"] = WITHDRAWN_ELIGIBILITY
        out["status_override"] = WITHDRAWN_STATUS
    return out


def lesson_entry(lesson):
    lesson_id = lesson.get("lesson_id")
    out = _copy(lesson)
    out["f4_status"] = _f4_status(lesson)
    out["eligibility"] = LESSON_ELIGIBILITY
    out["observed_events"] = [
        _event_entry(lesson_id, event) for event in lesson.get("observed_events") or []
    ]
    return out


def build_lessons(root):
    data = _read_json(os.path.join(root, *LESSON_REL))
    return [lesson_entry(lesson) for lesson in data["lessons"]]


def _f4_reference(root):
    data = _read_json(os.path.join(root, *F4_REL))
    return {
        "by_classification": dict(data["summary"]["by_classification"]),
        "diagnosis_count": len(data["diagnoses"]),
    }


def build_output(root):
    candidates = build_candidates(root)
    lessons = build_lessons(root)

    per_dept = {str(d): 0 for d in range(1, 17)}
    per_video = {vid: 0 for vid in sorted(DEV)}
    for c in candidates:
        per_dept[str(c["department_id"])] += 1
        per_video[c["video_id"]] += 1

    withdrawn = sum(
        1
        for lesson in lessons
        for event in lesson["observed_events"]
        if event.get("eligibility") == WITHDRAWN_ELIGIBILITY
    )

    return {
        "schema": 1,
        "created_note": CREATED_NOTE,
        "summary": {
            "total_candidates": len(candidates),
            "candidates_per_department": per_dept,
            "candidates_per_video": per_video,
            "lesson_count": len(lessons),
            "withdrawn_event_count": withdrawn,
        },
        "candidates": candidates,
        "lessons": lessons,
        "f4_reference": _f4_reference(root),
    }


def write_output(root, out_path):
    out = build_output(root)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    return len(out["candidates"])


def main(argv=None):
    if argv:
        raise SystemExit("d16_teacher takes no arguments")
    print(write_output(ROOT, OUT_PATH))


if __name__ == "__main__":
    main()
