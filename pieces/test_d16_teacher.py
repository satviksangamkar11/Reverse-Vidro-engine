"""Tests for pieces/d16_teacher.py. Every count, id list and classification is recomputed from the real files."""

import json
import os

import pytest

import d16_teacher as m

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HELD_IDS = ("354a38a0", "37745d70", "baf59433")
STORY_DEPTS = (1, 2, 3, 4)
WITHDRAWN_BEATS = ("event_001", "event_002")
OBS_SOURCE = "AI vision report (department_findings), unverified"
FIXED_UNKNOWNS = [
    "creator not recorded",
    "art style not recorded",
    "vision report is model output with LOW confidence unless the item says otherwise",
]
OVERRIDDEN = ("f4_status", "eligibility", "observed_events")
LESSON_ELIGIBILITY = "NOT_ELIGIBLE (candidate; not promoted)"


def _read_json(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return json.load(fh)


V4 = os.path.join(ROOT, "work", "phase1", "v4")


def _discovered_dev_ids():
    found = set()
    for name in os.listdir(V4):
        folder = os.path.join(V4, name)
        if not (name.startswith("audit_") and os.path.isdir(folder)):
            continue
        for fname in os.listdir(folder):
            if fname.startswith("beats_") and fname.endswith(".json"):
                found.add(fname[len("beats_"):-len(".json")])
    return found - set(HELD_IDS)


DEV_IDS = sorted(_discovered_dev_ids())
BEATS = {
    vid: _read_json("work", "phase1", "v4", f"audit_{vid}", f"beats_{vid}.json")["beats"]
    for vid in DEV_IDS
}
SRC_LESSONS = _read_json("work", "phase1", "overlays", "lesson_candidates_7434a0f7.json")["lessons"]
F4 = _read_json("work", "phase1", "f4_diagnosis_v2.json")


def _observed(beat):
    findings = beat.get("department_findings") or {}
    for dept in range(1, 17):
        for index, item in enumerate(findings.get(str(dept)) or []):
            text = item.get("observed")
            if item.get("status") == "OBSERVED" and isinstance(text, str) and text.strip():
                yield dept, index, item


def _expected_records():
    by_dept = {}
    for vid in DEV_IDS:
        for beat in BEATS[vid]:
            for dept, _index, _item in _observed(beat):
                by_dept.setdefault(dept, set()).add(vid)
    recs = []
    for vid in DEV_IDS:
        for beat in BEATS[vid]:
            for dept, index, item in _observed(beat):
                recs.append({
                    "candidate_id": f"D{dept}-{vid}-{beat['beat_id']}-{index}",
                    "video_id": vid,
                    "beat": beat,
                    "dept": dept,
                    "index": index,
                    "item": item,
                    "others": sorted(v for v in by_dept[dept] if v != vid),
                })
    return recs


EXPECTED = _expected_records()
EXPECTED_BY_CID = {r["candidate_id"]: r for r in EXPECTED}
EXPECTED_CIDS = sorted(r["candidate_id"] for r in EXPECTED)


def _withdrawn(lesson_id, event):
    return lesson_id.startswith("L4") and event.get("beat_id") in WITHDRAWN_BEATS


@pytest.fixture(scope="module")
def out():
    return m.build_output(ROOT)


@pytest.mark.parametrize("video_id", HELD_IDS)
def test_load_beats_refuses_held_out(video_id, tmp_path):
    with pytest.raises(ValueError):
        m.load_beats(str(tmp_path), video_id)


def test_dev_set_and_loader_match_disk():
    assert tuple(m.HELD) == HELD_IDS
    assert set(m.DEV) == set(DEV_IDS)
    for vid in DEV_IDS:
        assert m.load_beats(ROOT, vid) == BEATS[vid]


def test_output_has_no_held_out_ids(out):
    text = json.dumps(out, sort_keys=True)
    for vid in HELD_IDS:
        assert vid not in text


def test_candidate_count_matches_recount(out):
    assert len(out["candidates"]) == len(EXPECTED)


def test_candidate_source_links(out):
    for c in out["candidates"]:
        assert c["video_id"] in DEV_IDS
        beats = [b for b in BEATS[c["video_id"]] if b["beat_id"] == c["beat_id"]]
        assert beats, c["candidate_id"]
        assert any(
            b["start_time"] == c["start_time"] and b["end_time"] == c["end_time"]
            for b in beats
        )


def test_candidate_fields_match_source(out):
    seen = []
    for c in out["candidates"]:
        rec = EXPECTED_BY_CID.get(c["candidate_id"])
        assert rec is not None, c["candidate_id"]
        seen.append(c["candidate_id"])
        dept, beat, index = rec["dept"], rec["beat"], rec["index"]
        source_item = beat["department_findings"][str(dept)][index]

        assert c["department_id"] == dept
        assert c["department_name"] == m.DEPT_NAMES[dept]
        assert c["video_id"] == rec["video_id"]
        assert c["beat_id"] == beat["beat_id"]
        assert c["start_time"] == beat["start_time"]
        assert c["end_time"] == beat["end_time"]
        assert c["direct_observation"] == source_item["observed"]
        assert c["observation_source"] == OBS_SOURCE
        assert c["interpretation"] == "not assessed"
        assert c["directing_application"] == "not assessed"
        assert c["verification_status"] == "AI_OBSERVATION_UNVERIFIED"
        assert c["narrative_scene_relevance"] == (
            "STORY_OR_DIRECTION" if dept in STORY_DEPTS else "PRODUCTION_OR_PRESENTATION"
        )
        assert c["distinct_video_count"] == 1
        assert c["independent_creator_count"] == 0
        assert c["other_videos_with_same_department_observation"] == rec["others"]

        expected_unknowns = list(FIXED_UNKNOWNS)
        if source_item.get("confidence") == "LOW":
            expected_unknowns.append("item confidence is LOW")
        assert c["unknowns"] == expected_unknowns

        assert c["f4_status"] == "NOT_MAPPED (no technique id on this observation)"
        assert c["eligibility"].startswith("NOT_ELIGIBLE")
        assert c["practical_compatibility"] == (
            "NOT_CHECKED_IN_THIS_RECORD (see PRODUCTION_EXECUTION_COMPATIBILITY.json)"
        )
    assert sorted(seen) == EXPECTED_CIDS


def test_candidate_identity_multiset(out):
    got = sorted(c["candidate_id"] for c in out["candidates"])
    assert got == EXPECTED_CIDS


def test_no_eligible_values(out):
    values = [c["eligibility"] for c in out["candidates"]]
    values += [lesson["eligibility"] for lesson in out["lessons"]]
    values += [
        e["eligibility"]
        for lesson in out["lessons"]
        for e in lesson["observed_events"]
        if "eligibility" in e
    ]
    assert values
    for v in values:
        assert v != "ELIGIBLE" and not v.startswith("ELIGIBLE ")


def test_lesson_events_and_lessons_not_eligible(out):
    for lesson in out["lessons"]:
        assert lesson["eligibility"] == LESSON_ELIGIBILITY
        for e in lesson["observed_events"]:
            assert e["distinct_video_count"] == 1
            assert e["independent_creator_count"] == 0


def test_l4_withdrawn_events(out):
    l4_out = [l for l in out["lessons"] if l["lesson_id"].startswith("L4")]
    l4_src = [l for l in SRC_LESSONS if l["lesson_id"].startswith("L4")]
    assert len(l4_out) == len(l4_src) == 1
    src_text = {e["beat_id"]: e["event"] for e in l4_src[0]["observed_events"]}
    found = set()
    for e in l4_out[0]["observed_events"]:
        if e.get("beat_id") in WITHDRAWN_BEATS:
            found.add(e["beat_id"])
            assert e["eligibility"] == "WITHDRAWN_INACTIVE"
            assert e["status_override"] == "UNKNOWN_INACTIVE"
            assert e["event"] == src_text[e["beat_id"]]
    assert found == set(WITHDRAWN_BEATS)


def test_lesson_count_and_source_fields(out):
    assert len(out["lessons"]) == len(SRC_LESSONS)
    for src, dst in zip(SRC_LESSONS, out["lessons"]):
        assert dst["lesson_id"] == src["lesson_id"]
        assert len(dst["observed_events"]) == len(src["observed_events"])
        for key in src:
            if key in OVERRIDDEN:
                continue
            assert dst[key] == src[key], (src["lesson_id"], key)
        for sev, dev in zip(src["observed_events"], dst["observed_events"]):
            for key in sev:
                assert dev[key] == sev[key], (src["lesson_id"], key)


def test_lesson_f4_status(out):
    for src, dst in zip(SRC_LESSONS, out["lessons"]):
        if "technique_tags" not in src:
            expected = "SOURCE GAP (technique_tags missing)"
        elif src["technique_tags"] == []:
            expected = "UNMAPPED (technique_tags is empty)"
        else:
            expected = "MAPPING_NOT_ASSESSED (technique_tags present)"
        assert dst["f4_status"] == expected, src["lesson_id"]


def test_missing_technique_tags_is_source_gap():
    src = json.loads(json.dumps(SRC_LESSONS[0]))
    del src["technique_tags"]
    assert m.lesson_entry(src)["f4_status"] == "SOURCE GAP (technique_tags missing)"


def test_event_key_sets(out):
    for src_lesson, dst_lesson in zip(SRC_LESSONS, out["lessons"]):
        for sev, dev in zip(src_lesson["observed_events"], dst_lesson["observed_events"]):
            expected = set(sev) | {"distinct_video_count", "independent_creator_count"}
            if _withdrawn(src_lesson["lesson_id"], sev):
                # withdrawn events also carry the two count keys, since every event does
                expected |= {"eligibility", "status_override"}
            else:
                assert "eligibility" not in dev
                assert "status_override" not in dev
            assert set(dev) == expected


def test_every_source_event_present_with_beat_id(out):
    source_pairs = [
        (l["lesson_id"], e.get("beat_id")) for l in SRC_LESSONS for e in l["observed_events"]
    ]
    for lid, bid in source_pairs:
        assert bid is not None, lid
    out_pairs = [
        (l["lesson_id"], e.get("beat_id")) for l in out["lessons"] for e in l["observed_events"]
    ]
    assert sorted(source_pairs) == sorted(out_pairs)


def test_withdrawn_count(out):
    recomputed = sum(
        1 for l in SRC_LESSONS for e in l["observed_events"] if _withdrawn(l["lesson_id"], e)
    )
    in_output = sum(
        1
        for l in out["lessons"]
        for e in l["observed_events"]
        if e.get("eligibility") == "WITHDRAWN_INACTIVE"
    )
    assert recomputed == in_output == 2 == out["summary"]["withdrawn_event_count"]


def test_lesson_count_summary(out):
    n = len(out["lessons"])
    assert out["summary"]["lesson_count"] == n == len(SRC_LESSONS)


def test_summary_recount(out):
    cands = out["candidates"]
    s = out["summary"]
    assert s["total_candidates"] == len(cands) == len(EXPECTED)
    per_dept = {str(d): 0 for d in range(1, 17)}
    per_vid = {v: 0 for v in DEV_IDS}
    for c in cands:
        per_dept[str(c["department_id"])] += 1
        per_vid[c["video_id"]] += 1
    assert s["candidates_per_department"] == per_dept
    assert s["candidates_per_video"] == per_vid


def test_f4_reference_recomputed(out):
    diagnoses = F4["diagnoses"]
    counts = {}
    for d in diagnoses:
        counts[d["classification"]] = counts.get(d["classification"], 0) + 1
    ref = out["f4_reference"]
    assert ref["diagnosis_count"] == len(diagnoses)
    assert ref["by_classification"] == counts


def test_build_output_deterministic():
    first = json.dumps(m.build_output(ROOT), sort_keys=True)
    second = json.dumps(m.build_output(ROOT), sort_keys=True)
    assert first == second


def test_write_output_writes_only_target(tmp_path):
    count = m.write_output(ROOT, str(tmp_path / "c.json"))
    written = []
    for dirpath, _dirs, files in os.walk(str(tmp_path)):
        for name in files:
            written.append(os.path.relpath(os.path.join(dirpath, name), str(tmp_path)))
    assert written == ["c.json"]
    with open(str(tmp_path / "c.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    assert count == len(data["candidates"]) == len(EXPECTED)


def test_main_writes_file_and_prints_count(tmp_path, monkeypatch, capsys):
    target = str(tmp_path / "CROSS_VIDEO_TEACHER_CANDIDATES.json")
    monkeypatch.setattr(m, "OUT_PATH", target)
    m.main()
    assert os.path.isfile(target)
    with open(target, encoding="utf-8") as fh:
        assert len(json.load(fh)["candidates"]) == len(EXPECTED)
    assert capsys.readouterr().out.strip() == str(len(EXPECTED))
