import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import finding_lifecycle as fl  # noqa: E402

SAMPLE = (
    "HIGH - pieces/alpha.py:12 - missing guard on empty input\n"
    "Some prose that is not a finding\n"
    "MEDIUM - pieces/beta.py:7 - unclear naming\n"
    "LOW - no location in this one\n"
)


def _write(path, data):
    os.makedirs(os.path.dirname(str(path)), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


def _line_count(path):
    with open(path, encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def _files_under(base):
    found = set()
    for dirpath, _dirs, names in os.walk(base):
        for name in names:
            found.add(os.path.join(dirpath, name))
    return found


def _id_of(job, summary):
    return next(fid for fid, r in fl.load_ledger(job).items() if r["summary"] == summary)


def _blocking_summaries(job):
    return sorted(r["summary"] for r in fl.blocking_findings(job))


def test_parse_reads_severities_locations_and_summaries():
    found = fl.parse_findings(SAMPLE, "rev", 1, job="j")
    assert len(found) == 3
    high, med, low = found
    assert high["severity"] == "HIGH"
    assert (high["file"], high["line"], high["summary"]) == (
        "pieces/alpha.py", 12, "missing guard on empty input")
    assert med["severity"] == "MED"
    assert (med["file"], med["line"], med["summary"]) == (
        "pieces/beta.py", 7, "unclear naming")
    assert low["severity"] == "LOW"
    assert (low["file"], low["line"], low["summary"]) == (
        "", 0, "no location in this one")


def test_stable_id_survives_rounds_and_splits_reviewers():
    r1 = fl.parse_findings(SAMPLE, "ultra", 1, job="j")[0]["id"]
    r2 = fl.parse_findings(SAMPLE, "ultra", 2, job="j")[0]["id"]
    other = fl.parse_findings(SAMPLE, "codex", 1, job="j")[0]["id"]
    assert r1 == r2
    assert r1 != other
    assert r1.startswith("F-") and len(r1) == 14
    assert r1 == fl.stable_id("j", "ultra", "pieces/alpha.py", 12, "missing guard on empty input")
    assert r1 == fl.stable_id("j", "ultra", "pieces/alpha.py", 12, "Missing   GUARD on empty input")


def test_open_findings_appends_each_finding_once(tmp_path):
    job = tmp_path / "job"
    first = fl.open_findings(job, "rev", 1, SAMPLE)
    assert len(first) == 3
    assert fl.open_findings(job, "rev", 2, SAMPLE) == []
    assert len(fl.load_ledger(job)) == 3
    assert _line_count(os.path.join(job, fl.LEDGER_FILE)) == 3


def test_resolved_needs_passing_evidence(tmp_path):
    job = tmp_path / "job"
    fid = fl.open_findings(job, "rev", 1, "MED - pieces/a.py:3 - off by one\n")[0]
    ledger = os.path.join(job, fl.LEDGER_FILE)
    before = _line_count(ledger)
    with pytest.raises(ValueError):
        fl.resolve(job, fid, None)
    with pytest.raises(ValueError):
        fl.resolve(job, fid, {})
    with pytest.raises(ValueError):
        fl.resolve(job, fid, {"test": "t", "passed": False})
    assert _line_count(ledger) == before
    assert fl.load_ledger(job)[fid]["status"] == fl.OPEN
    fl.resolve(job, fid, {"test": "t", "passed": True})
    assert fl.load_ledger(job)[fid]["status"] == fl.RESOLVED
    assert _line_count(ledger) == before + 1


def test_dismissed_medium_needs_evidence_text(tmp_path):
    job = tmp_path / "job"
    fid = fl.open_findings(job, "rev", 1, "MED - pieces/a.py:3 - off by one\n")[0]
    with pytest.raises(ValueError):
        fl.dismiss(job, fid, {"text": "looks fine to me", "evidence_ref": "pieces/a.py:3"})
    with pytest.raises(ValueError):
        fl.dismiss(job, fid, {"text": "EVIDENCE: test_off_by_one passes", "evidence_ref": ""})
    assert fl.load_ledger(job)[fid]["status"] == fl.OPEN
    fl.dismiss(job, fid, {"text": "EVIDENCE: test_off_by_one passes",
                          "evidence_ref": "pieces/test_a.py:9"})
    assert fl.load_ledger(job)[fid]["status"] == fl.DISMISSED


def test_ledger_keeps_full_history(tmp_path):
    job = tmp_path / "job"
    fid = fl.open_findings(job, "rev", 1, "MED - pieces/a.py:3 - off by one\n")[0]
    fl.resolve(job, fid, {"test": "t", "passed": True})
    with open(os.path.join(job, fl.LEDGER_FILE), encoding="utf-8") as fh:
        events = [json.loads(line) for line in fh if line.strip()]
    assert [e["event"] for e in events] == ["OPENED", "RESOLVED"]
    assert all(e["id"] == fid for e in events)
    assert events[1]["evidence"] == {"test": "t", "passed": True}


def test_blocking_is_open_high_and_med_only(tmp_path):
    job = tmp_path / "job"
    report = (
        "HIGH - pieces/a.py:1 - high problem\n"
        "MED - pieces/a.py:2 - med problem\n"
        "LOW - low problem\n"
    )
    fl.open_findings(job, "rev", 1, report)
    assert _blocking_summaries(job) == ["high problem", "med problem"]
    fl.resolve(job, _id_of(job, "high problem"), {"test": "t", "passed": True})
    assert _blocking_summaries(job) == ["med problem"]


def test_can_accept_blocked_by_open_med(tmp_path):
    job = tmp_path / "job"
    fl.open_findings(job, "rev", 1, "MED - pieces/a.py:2 - med problem\nLOW - nit\n")
    assert fl.can_accept(job, "READY") is False
    fl.resolve(job, _id_of(job, "med problem"), {"test": "t", "passed": True})
    assert fl.can_accept(job, "READY") is True


def test_attempts_are_bounded_and_persisted(tmp_path):
    job = tmp_path / "job"
    assert fl.attempts_allowed(job, 2) is True
    assert fl.record_attempt(job) == 1
    assert fl.attempts_allowed(job, 2) is True
    assert fl.record_attempt(job) == 2
    assert fl.attempts_allowed(job, 2) is False
    with open(os.path.join(job, fl.ATTEMPTS_FILE), encoding="utf-8") as fh:
        assert json.load(fh)["count"] == 2


def test_freeze_then_verify_detects_change(tmp_path):
    root = tmp_path / "repo"
    job = tmp_path / "job"
    _write(root / "test_a.py", b"A = 1\n")
    _write(root / "test_b.py", b"B = 2\n")
    frozen = fl.freeze_tests(root, job, ["test_a.py", "test_b.py"])
    assert set(frozen) == {"test_a.py", "test_b.py"}
    assert fl.verify_frozen(root, job) == []
    _write(root / "test_a.py", b"A = 99\n")
    assert fl.verify_frozen(root, job) == ["test_a.py"]


def test_verify_without_freeze_raises(tmp_path):
    with pytest.raises(ValueError):
        fl.verify_frozen(tmp_path / "repo", tmp_path / "job")


def test_freeze_digest_is_raw_bytes_not_normalised(tmp_path):
    root = tmp_path / "repo"
    job = tmp_path / "job"
    _write(root / "test_crlf.py", b"X = 1\nY = 2\n")
    fl.freeze_tests(root, job, ["test_crlf.py"])
    _write(root / "test_crlf.py", b"X = 1\r\nY = 2\r\n")
    assert fl.verify_frozen(root, job) == ["test_crlf.py"]


def test_dismissed_high_needs_concrete_reference(tmp_path):
    job = tmp_path / "job"
    fl.open_findings(job, "rev", 1, "HIGH - pieces/a.py:5 - real defect\n")
    fid = _id_of(job, "real defect")
    with pytest.raises(ValueError):
        fl.dismiss(job, fid, {"text": "EVIDENCE: fake.py x", "evidence_ref": "pieces/a.py:5"})
    assert fl.load_ledger(job)[fid]["status"] == fl.OPEN
    fl.dismiss(job, fid, {"text": "EVIDENCE: test_real_check",
                          "evidence_ref": "pieces/test_a.py:5"})
    assert fl.load_ledger(job)[fid]["status"] == fl.DISMISSED


def test_nothing_written_outside_job_dir(tmp_path):
    root = tmp_path / "repo"
    job = tmp_path / "job"
    _write(root / "test_a.py", b"A = 1\n")
    before = _files_under(tmp_path)
    fl.freeze_tests(root, job, ["test_a.py"])
    ids = fl.open_findings(
        job, "rev", 1,
        "HIGH - pieces/a.py:1 - defect one\nMED - pieces/a.py:2 - defect two\n")
    fl.resolve(job, ids[0], {"test": "t", "passed": True})
    fl.dismiss(job, ids[1], {"text": "EVIDENCE: test_defect_two",
                             "evidence_ref": "pieces/a.py:2"})
    fl.record_attempt(job)
    fl.verify_frozen(root, job)
    fl.blocking_findings(job)
    fl.can_accept(job, "READY")
    new = _files_under(tmp_path) - before
    assert new
    job_prefix = os.path.abspath(job) + os.sep
    for path in new:
        assert os.path.abspath(path).startswith(job_prefix)
