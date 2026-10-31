import csv
import functools
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pytest
import d16_matrix as m

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROWS = m.build_rows(ROOT)
HELD = [r for r in ROWS if r["video_id"] in m.HELD]
DATA = [r for r in ROWS if r["video_id"] not in m.HELD]


def _src(name):
    with open(os.path.join(ROOT, "pieces", name), encoding="utf-8") as f:
        return f.read()


@functools.lru_cache(None)
def _beats(vid):
    with open(os.path.join(ROOT, "work", "phase1", "v4", "audit_" + vid, "beats_" + vid + ".json"), encoding="utf-8") as f:
        return json.load(f)["beats"]


def _raw_ledger():
    with open(os.path.join(ROOT, *m.LEDGER.split("/")), newline="", encoding="utf-8-sig") as f:
        return {(int(r["dept"]), r["video_id"]): r for r in csv.DictReader(f)}


def test_size():
    assert len(_src("d16_matrix.py")) <= 9000
    assert len(_src("test_d16_matrix.py")) <= 5000


def test_shape():
    keys = [(r["dept"], r["video_id"]) for r in ROWS]
    assert len(ROWS) == 208 and len(set(keys)) == 208
    assert {k[0] for k in keys} == set(range(1, 17))
    assert len({k[1] for k in keys}) == 13
    assert keys == sorted(keys)


def test_held_rows():
    assert len(HELD) == 48
    for r in HELD:
        assert r["research_status"] == "BLOCKED_BY_SOURCE"
        assert r["evidence_type"] == "NONE_NOT_READ"
        assert r["measured"] == "N"
        assert r["observed_beat_count"] == 0 and r["observed_beat_ids"] == ""
        assert r["unknown_beat_count"] == 0 and r["not_examined_beat_count"] == 0 and r["missing_beat_count"] == 0
        assert r["extraction_performed"] == "none (protected; not read)"
        assert r["sources_read"] == m.LEDGER
        assert r["further_offline_analysis"] == "NOT_ALLOWED: protected"


@pytest.mark.parametrize("vid", sorted(m.HELD))
def test_load_beats_held(vid):
    with pytest.raises(ValueError):
        m.load_beats(ROOT, vid)


def test_never_examined():
    for r in ROWS:
        if r["ledger_category"] == "NEVER_EXAMINED":
            assert r["research_status"] == "NOT_EXAMINED" and r["observed_beat_count"] == 0


def test_observed_count():
    for r in DATA:
        n = sum(any(i["status"] == "OBSERVED" for i in b["department_findings"].get(str(r["dept"]), [])) for b in _beats(r["video_id"]))
        assert r["observed_beat_count"] == n


def test_measured():
    got = {(r["dept"], r["video_id"]) for r in ROWS if r["measured"] == "Y"}
    with open(os.path.join(ROOT, *m.MEASUREMENTS.split("/")), encoding="utf-8") as f:
        keys = set(json.load(f))
    assert {"7434a0f7", "7a1e2b26"} <= keys
    assert got == {(d, v) for d in (5, 7) for v in ("7434a0f7", "7a1e2b26")}
    assert {r["measured"] for r in ROWS} == {"Y", "N"}


def test_status_and_evidence():
    assert all(r["research_status"] != "RESEARCH_COMPLETE_FROM_AVAILABLE_EVIDENCE" for r in ROWS)
    assert {r["evidence_type"] for r in ROWS} <= {"NONE_NOT_READ", "MEASUREMENT", "AI_OBSERVATION", "TRANSCRIPT_UNVERIFIED", "NONE"}


def test_human_verified_count():
    led = _raw_ledger()
    for r in ROWS:
        cell = led[(r["dept"], r["video_id"])]["human_verified_items"].strip()
        assert r["human_verified_items_count"] == (1 if cell and cell != "0" else 0)


def test_sources_exist():
    for r in ROWS:
        for p in r["sources_read"].split(";"):
            assert os.path.exists(os.path.join(ROOT, *p.split("/")))


def test_write(tmp_path):
    assert m.write_matrix(ROOT, tmp_path / "m.csv") == 208
    with open(tmp_path / "m.csv", newline="", encoding="utf-8") as f:
        lines = list(csv.reader(f))
    assert lines[0] == m.COLUMNS and len(lines) == 209
    assert os.listdir(tmp_path) == ["m.csv"]


def test_dept13_5c93ec37():
    with open(os.path.join(ROOT, "work", "phase1", "v4", "audit_5c93ec37", "audio_5c93ec37.json"), encoding="utf-8") as f:
        assert len(json.load(f)["speech_segments"]) == 0
    r = next(x for x in ROWS if x["video_id"] == "5c93ec37" and x["dept"] == 13)
    assert r["research_status"] == "BLOCKED_BY_SOURCE"
    assert all(x["research_status"] != "BLOCKED_BY_SOURCE" for x in DATA if x["dept"] == 13 and x["video_id"] != "5c93ec37")


def test_dept57_text():
    t = "NOT_JUSTIFIED: frozen detector output exists only for 7434a0f7 and 7a1e2b26 (existing read-only measurement); no measurement exists for this video; Step 5 deferred; no re-run"
    assert sum(r["further_offline_analysis"] == t for r in DATA if r["dept"] in (5, 7)) == 20


def test_main(tmp_path, monkeypatch, capsys):
    out = tmp_path / "DEPARTMENT_VIDEO_MATRIX.csv"
    monkeypatch.setattr(m, "OUT_PATH", str(out))
    m.main()
    with open(out, newline="", encoding="utf-8") as f:
        assert len(list(csv.reader(f))) == 209
    assert capsys.readouterr().out.strip() == "208"
