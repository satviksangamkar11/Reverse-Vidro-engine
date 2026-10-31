import builtins
import functools
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pytest
import d16_matrix as m

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEAS = "STEP4_MEASUREMENTS.json"


def _run():
    log, real = [], builtins.open

    def spy(file, *a, **k):
        fr = sys._getframe(1)
        while fr is not None and fr.f_code.co_name != "build_rows":
            fr = fr.f_back
        loc = fr.f_locals if fr is not None else {}
        log.append((str(file), loc.get("vid"), loc.get("dept")))
        return real(file, *a, **k)

    builtins.open = spy
    try:
        rows = m.build_rows(ROOT)
    finally:
        builtins.open = real
    return log, rows


LOG, ROWS = _run()


@functools.lru_cache(None)
def _beats(vid):
    with open(os.path.join(ROOT, "work", "phase1", "v4", "audit_" + vid, "beats_" + vid + ".json"), encoding="utf-8") as f:
        return json.load(f)["beats"]


def _snap(rels):
    out = {}
    for rel in rels:
        p = os.path.join(ROOT, *rel.split("/"))
        if os.path.isdir(p):
            for dp, _, fs in os.walk(p):
                for f in fs:
                    q = os.path.join(dp, f)
                    out[q] = os.stat(q).st_mtime_ns
        elif os.path.isfile(p):
            out[p] = os.stat(p).st_mtime_ns
    return out


def _root_with(tmp_path, old, new):
    d = tmp_path / "work" / "phase1" / "coverage_16"
    d.mkdir(parents=True)
    with open(os.path.join(ROOT, *m.LEDGER.split("/")), encoding="utf-8-sig") as f:
        text = f.read()
    with open(d / os.path.basename(m.LEDGER), "w", encoding="utf-8", newline="") as f:
        f.write(text.replace(old, new, 1))
    return str(tmp_path)


def test_spy_no_held_open():
    assert not [e for e in LOG if e[1] in m.HELD or any(h in e[0] for h in m.HELD)]


def test_spy_measurement_open():
    ms = [e for e in LOG if e[0].endswith(MEAS)]
    assert ms
    assert all(e[1] in m.DEV and e[1] in m.MEASURED_VIDEOS and e[2] in m.MEASURED_DEPTS for e in ms)


def test_strict_measurement_open():
    ms = [e for e in LOG if e[0].endswith(MEAS)]
    assert len(ms) >= 1 and all(e[1] in m.DEV for e in ms)


def test_output_values():
    for r in ROWS:
        if r["video_id"] in m.HELD:
            continue
        d, beats = r["dept"], _beats(r["video_id"])
        obs, unk, nex, mis = [], 0, 0, 0
        for b in beats:
            sts = [i["status"] for i in b["department_findings"].get(str(d), [])]
            mis += 0 if sts else 1
            unk += "UNKNOWN" in sts
            nex += "NOT_EXAMINED" in sts
            if "OBSERVED" in sts:
                obs.append(b)
        assert r["observed_beat_ids"] == ";".join(str(b["beat_id"]) for b in obs)
        assert r["observed_time_min"] == (min(b["start_time"] for b in obs) if obs else "")
        assert r["observed_time_max"] == (max(b["end_time"] for b in obs) if obs else "")
        assert (r["unknown_beat_count"], r["not_examined_beat_count"], r["missing_beat_count"]) == (unk, nex, mis)


def test_bad_category_raises(tmp_path):
    with pytest.raises(ValueError):
        m.build_rows(_root_with(tmp_path, ",MODEL_ONLY,", ",BOGUS_CATEGORY,"))


def test_findings_not_list_raises():
    with pytest.raises(ValueError):
        m.findings_for({"department_findings": {"5": {"status": "OBSERVED"}}}, 5)


def test_write_location(tmp_path):
    rels = ["work/phase1"] + sorted({p for r in ROWS for p in r["sources_read"].split(";")})
    before = _snap(rels)
    m.write_matrix(ROOT, tmp_path / "m.csv")
    assert _snap(rels) == before
    assert os.listdir(tmp_path) == ["m.csv"]
