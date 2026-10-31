import json
import os
import sys
from pathlib import Path

import pytest

ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, os.path.join(ROOT, "pieces"))
import d16_media as m  # noqa: E402

VID = "7434a0f7"


def _mutated_copy(tmp_path, rel, mutate):
    data = json.loads(Path(ROOT, rel).read_text(encoding="utf-8"))
    mutate(data)
    dst = tmp_path / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(data), encoding="utf-8")


def test_audio_key_gap_blocks_colour(tmp_path):
    rel = "work/phase1/v4/audit_%s/audio_%s.json" % (VID, VID)
    _mutated_copy(tmp_path, rel, lambda d: d.pop("wav_seconds"))
    _copy_valid(tmp_path, "work/phase1/v4/audit_%s/beats_%s.json" % (VID, VID))
    row = next(r for r in m.colour_rows(str(tmp_path)) if r["video_id"] == VID)
    assert row["status"] == "BLOCKED_BY_SOURCE"
    assert "missing key wav_seconds" in row["reason"]


def test_beat_key_gap_gives_no_hard_cut_count(tmp_path):
    rel = "work/phase1/v4/audit_%s/beats_%s.json" % (VID, VID)
    _mutated_copy(tmp_path, rel, lambda d: d["beats"][0].pop("end_time"))
    row = m._pacing_row(str(tmp_path), VID)
    assert row["pacing_status"] == "source gap"
    assert row["hard_cut_count"] == ""


def _beats_rel():
    return "work/phase1/v4/audit_%s/beats_%s.json" % (VID, VID)


def _audio_rel():
    return "work/phase1/v4/audit_%s/audio_%s.json" % (VID, VID)


def _copy_valid(tmp_path, rel):
    dst = tmp_path / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(Path(ROOT, rel).read_text(encoding="utf-8"), encoding="utf-8")


def test_beats_gap_with_valid_audio_blocks_every_combined_output(tmp_path):
    _mutated_copy(tmp_path, _beats_rel(), lambda d: d["beats"][0].pop("end_time"))
    _copy_valid(tmp_path, _audio_rel())
    colour = next(r for r in m.colour_rows(str(tmp_path)) if r["video_id"] == VID)
    pacing = m._pacing_row(str(tmp_path), VID)
    audio = next(r for r in m.audio_rows(str(tmp_path)) if r["video_id"] == VID)
    captions = [r for r in m.caption_rows(str(tmp_path)) if r["video_id"] == VID]
    assert colour["status"] == "BLOCKED_BY_SOURCE"
    assert pacing["pacing_status"] == "source gap"
    assert captions == []
    assert audio["analysed"] == "Y"


def test_audio_gap_with_valid_beats_blocks_every_combined_output(tmp_path):
    _mutated_copy(tmp_path, _audio_rel(), lambda d: d.pop("wav_seconds"))
    _copy_valid(tmp_path, _beats_rel())
    colour = next(r for r in m.colour_rows(str(tmp_path)) if r["video_id"] == VID)
    pacing = m._pacing_row(str(tmp_path), VID)
    audio = next(r for r in m.audio_rows(str(tmp_path)) if r["video_id"] == VID)
    captions = [r for r in m.caption_rows(str(tmp_path)) if r["video_id"] == VID]
    assert colour["status"] == "BLOCKED_BY_SOURCE"
    assert pacing["pacing_status"] == "source gap"
    assert captions == []
    assert audio["analysed"] == "N"


def test_both_sources_valid_are_not_blocked(tmp_path):
    _copy_valid(tmp_path, _beats_rel())
    _copy_valid(tmp_path, _audio_rel())
    pacing = m._pacing_row(str(tmp_path), VID)
    audio = next(r for r in m.audio_rows(str(tmp_path)) if r["video_id"] == VID)
    captions = [r for r in m.caption_rows(str(tmp_path)) if r["video_id"] == VID]
    colour = next(r for r in m.colour_rows(str(tmp_path)) if r["video_id"] == VID)
    assert pacing["pacing_status"] == "PACING_OK"
    assert audio["analysed"] == "Y"
    assert len(captions) > 0
    assert "source gap" not in colour["reason"] and "missing key" not in colour["reason"]


def test_protected_held_out_source_stays_protected_and_unread():
    for held in ("354a38a0", "37745d70", "baf59433"):
        with pytest.raises(ValueError):
            m._load_beats(ROOT, held)
        with pytest.raises(ValueError):
            m._audio_stats(ROOT, held)
    protected = [r for r in m.gap_rows(ROOT) if r["video_id"].endswith("_PROTECTED")]
    assert len(protected) == 3
    assert all(r["colour_status"] == "PROTECTED_HELDOUT" for r in protected)
