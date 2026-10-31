"""Tests for pieces/d16_media.py: real reference files plus literal fixtures in tmp_path.

The held-out ids are taken from the module constant only. The literal ids appear in
PROTECTED_IDS in the module and nowhere else in the source.
"""

import ast
import builtins
import csv
import glob
import json
import os
import re
import statistics
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import d16_media as media  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE_DIR = os.path.join(os.path.dirname(ROOT), "reference_videos")
ANIM_DIR = os.path.join(os.path.dirname(ROOT), "animation_research_tool", "animation_research")
SIX_FILES = {
    "colour_brightness_summary.csv", "brightness_series.csv", "audio_timing_summary.csv",
    "pacing_rhythm_summary.csv", "caption_text_inventory.csv", "media_gaps.csv",
}
FOLDER_TS = r"(\d{1,2})_(\d{2})_(\d{2})_(AM|PM)"
REF_NAME = "WhatsApp Video 2026-10-28 at %s.%s.%s %s.mp4"
QUOTE = r"(?<!\w)(['\"])(.{2,}?)\1(?!\w)"


def _json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


def _audit(root, vid):
    path = os.path.join(root, "work", "phase1", "v4", "audit_" + vid)
    os.makedirs(path, exist_ok=True)
    return path


def _audio_path(vid):
    return os.path.join(ROOT, "work", "phase1", "v4", "audit_" + vid, "audio_" + vid + ".json")


def _beats_path(vid):
    return os.path.join(ROOT, "work", "phase1", "v4", "audit_" + vid, "beats_" + vid + ".json")


def _rows_by_id(rows):
    return {r["video_id"]: r for r in rows}


def _folder_basename(vid):
    folder = _json(_audio_path(vid))["folder"]
    return os.path.basename(folder.replace("\\", "/"))


def _ref_listing():
    return set(os.listdir(REFERENCE_DIR)) if os.path.isdir(REFERENCE_DIR) else set()


def _discovered_ids():
    ids = set()
    for path in glob.glob(os.path.join(ROOT, "work", "phase1", "v4", "audit_*", "audio_*.json")):
        ids.add(os.path.basename(path)[len("audio_"):-len(".json")])
    return ids - set(media.PROTECTED_IDS)


def _protected_stamps():
    if not os.path.isdir(ANIM_DIR):
        return []
    stamps = []
    for name in os.listdir(ANIM_DIR):
        for pid in media.PROTECTED_IDS:
            found = re.search(FOLDER_TS + "_" + re.escape(pid) + "$", name)
            if found:
                stamps.append(found.groups())
    return stamps


def _beat_ok(beat):
    if not isinstance(beat, dict):
        return False
    if not all(k in beat for k in ("beat_id", "start_time", "end_time", "department_findings")):
        return False
    findings = beat["department_findings"]
    if not isinstance(findings, dict):
        return False
    for items in findings.values():
        if not isinstance(items, list):
            return False
        for item in items:
            if not isinstance(item, dict) or "status" not in item:
                return False
            if item["status"] == "OBSERVED" and "observed" not in item:
                return False
    return True


def _recomputed_captions():
    out = []
    for vid in media.DEV:
        if not os.path.isfile(_beats_path(vid)):
            continue
        beats = _json(_beats_path(vid)).get("beats")
        if not isinstance(beats, list) or not all(_beat_ok(b) for b in beats):
            continue
        for beat in beats:
            for dept, items in beat["department_findings"].items():
                for item in items:
                    if item["status"] == "OBSERVED":
                        for match in re.findall(QUOTE, item["observed"]):
                            out.append((vid, beat["beat_id"], int(dept), match[1]))
    return out


@pytest.fixture(scope="module")
def real_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("media")
    counts = media.write_all(ROOT, str(out))
    return out, counts


def test_held_out_ids_only_in_protected_constant_and_outputs(real_run):
    source_path = media.__file__
    with open(source_path, encoding="utf-8") as fh:
        source = fh.read()
    for pid in media.PROTECTED_IDS:
        for line in source.splitlines():
            if pid in line:
                assert line.startswith("PROTECTED_IDS"), "held-out id outside the protected constant"
    out, _ = real_run
    for name in SIX_FILES:
        with open(os.path.join(str(out), name), encoding="utf-8") as fh:
            text = fh.read()
        for pid in media.PROTECTED_IDS:
            assert pid not in text


def test_module_imports_and_paths_are_allowed():
    with open(media.__file__, encoding="utf-8") as fh:
        source = fh.read()
    assert "measure_track" not in source
    assert not re.search(r"[A-Za-z]:[\\/]", source)
    names = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    banned = {"urllib", "requests", "http", "socket", "openai", "anthropic"}
    for name in names:
        assert name.split(".")[0] not in banned
        assert "kimi" not in name.lower()
        assert "measure_track" not in name


def test_resolve_mp4_matches_listing():
    listing = _ref_listing()
    for vid in media.DEV:
        found = re.search(FOLDER_TS + "_" + vid + "$", _folder_basename(vid))
        expected = None
        if found:
            name = REF_NAME % found.groups()
            if name in listing:
                expected = os.path.join(REFERENCE_DIR, name)
        assert media.resolve_mp4(ROOT, vid) == expected


def test_reel_ids_resolve_to_none():
    reels = [v for v in media.DEV if not re.search(r"_(AM|PM)_", _folder_basename(v))]
    assert reels
    for vid in reels:
        assert media.resolve_mp4(ROOT, vid) is None


def test_held_out_ids_raise_value_error():
    for pid in media.PROTECTED_IDS:
        with pytest.raises(ValueError):
            media.resolve_mp4(ROOT, pid)


def test_colour_rows_contract():
    rows = media.colour_rows(ROOT)
    assert len(rows) == len(media.DEV)
    for row in rows:
        if row["status"] == "MEASURED_MEDIA":
            assert 0 <= row["mean_luma"] <= 1
            assert abs(row["samples"] - round(row["duration_s"] * 2)) <= 2
        else:
            assert row["status"] == "BLOCKED_BY_SOURCE"
            assert row["reason"]
            assert row["mean_luma"] == ""


def test_audio_rows_match_real_files():
    rows = _rows_by_id(media.audio_rows(ROOT))
    for vid in media.DEV:
        data = _json(_audio_path(vid))
        row = rows[vid]
        assert row["speech_segment_count"] == len(data["speech_segments"])
        if not data["speech_segments"]:
            assert "transcript empty" in row["gap_note"]


def test_zero_length_beats_recomputed():
    beats = _json(_beats_path("7434a0f7"))["beats"]
    expected = [b["beat_id"] for b in beats if b["end_time"] == b["start_time"]]
    row = _rows_by_id(media.pacing_rows(ROOT))["7434a0f7"]
    assert row["zero_length_beat_ids"] == ";".join(expected)
    assert row["zero_length_beat_count"] == len(expected)


def test_hard_cut_counts_recomputed():
    step4 = _json(os.path.join(ROOT, "work", "phase1", "step4", "STEP4_MEASUREMENTS.json"))
    rows = _rows_by_id(media.pacing_rows(ROOT))
    for vid in media.DEV:
        if vid in step4:
            events = step4[vid]["transitions"]["events"]
            expected = sum(1 for ev in events if ev["kind"] == "hard_cut")
            assert rows[vid]["hard_cut_count"] == expected
        else:
            assert rows[vid]["hard_cut_count"] == "UNKNOWN_NOT_MEASURED"


def test_median_nonzero_beat_seconds_recomputed():
    rows = _rows_by_id(media.pacing_rows(ROOT))
    for vid in media.DEV:
        beats = _json(_beats_path(vid))["beats"]
        lengths = [b["end_time"] - b["start_time"] for b in beats if b["end_time"] != b["start_time"]]
        got = rows[vid]["median_nonzero_beat_seconds"]
        if lengths:
            assert got == pytest.approx(statistics.median(lengths))
        else:
            assert got == ""


def test_caption_rows_equal_recomputed_list():
    rows = media.caption_rows(ROOT)
    got = [(r["video_id"], r["beat_id"], r["department_id"], r["quoted_text"]) for r in rows]
    expected = _recomputed_captions()
    if expected:
        assert got
    assert got == expected
    for row in rows:
        beat = next(b for b in _json(_beats_path(row["video_id"]))["beats"]
                    if b["beat_id"] == row["beat_id"])
        observed = [f["observed"] for f in beat["department_findings"][str(row["department_id"])]
                    if f["status"] == "OBSERVED"]
        assert any(row["quoted_text"] in text for text in observed)
        assert row["verification"] == "AI_READING_UNVERIFIED"


def test_caption_fixture_literal(tmp_path):
    root = str(tmp_path)
    vid = media.DEV[0]
    beats = {"beats": [
        {"beat_id": "shot_001", "start_time": 0.0, "end_time": 1.0,
         "department_findings": {"1": [
             {"status": "OBSERVED", "observed": "'She proposed' and \"So she cursed\""},
             {"status": "UNKNOWN", "observed": "'ignored'"}]}},
        {"beat_id": "shot_002", "start_time": 1.0, "end_time": 2.0,
         "department_findings": {"2": [{"status": "OBSERVED", "observed": "no quotes here"}]}},
    ]}
    _write_json(os.path.join(_audit(root, vid), "beats_%s.json" % vid), beats)
    import shutil
    shutil.copyfile(os.path.join(media.ROOT, "work", "phase1", "v4", "audit_%s" % vid, "audio_%s.json" % vid),
                    os.path.join(_audit(root, vid), "audio_%s.json" % vid))
    rows = [r for r in media.caption_rows(root) if r["video_id"] == vid]
    assert [r["quoted_text"] for r in rows] == ["She proposed", "So she cursed"]
    assert all(r["verification"] == "AI_READING_UNVERIFIED" for r in rows)
    assert media._quoted_texts("'She proposed' and \"So she cursed\"") == ["She proposed", "So she cursed"]
    assert media._quoted_texts("no quotes here") == []


def test_invalid_utf8_gives_explicit_source_gap(tmp_path):
    root = str(tmp_path)
    vid = media.DEV[0]
    path = _audit(root, vid)
    with open(os.path.join(path, "audio_%s.json" % vid), "wb") as fh:
        fh.write(b"\xff\xfe\x80 not utf-8 \x81")
    with open(os.path.join(path, "beats_%s.json" % vid), "wb") as fh:
        fh.write(b"\xff\xfe\x80 not utf-8 \x81")
    audio = _rows_by_id(media.audio_rows(root))[vid]
    assert audio["analysed"] == "N"
    assert audio["gap_note"] == "source gap: audio_%s.json unreadable" % vid
    pacing = _rows_by_id(media.pacing_rows(root))[vid]
    assert pacing["pacing_status"] == "source gap"
    assert pacing["gap_note"] == "source gap: beats_%s.json unreadable" % vid


def test_missing_beats_is_source_gap_not_ok(tmp_path):
    root = str(tmp_path)
    vid = media.DEV[0]
    row = _rows_by_id(media.pacing_rows(root))[vid]
    assert row["pacing_status"] == "source gap"
    assert row["gap_note"] == "source gap: beats file missing"
    assert row["pacing_status"] not in ("NO_BEATS", "PACING_OK")
    assert vid not in {r["video_id"] for r in media.caption_rows(root)}


def test_empty_beats_never_pacing_ok(tmp_path):
    root = str(tmp_path)
    vid = media.DEV[0]
    _write_json(os.path.join(_audit(root, vid), "beats_%s.json" % vid), {"beats": []})
    import shutil
    shutil.copyfile(os.path.join(media.ROOT, "work", "phase1", "v4", "audit_%s" % vid, "audio_%s.json" % vid),
                    os.path.join(_audit(root, vid), "audio_%s.json" % vid))
    row = _rows_by_id(media.pacing_rows(root))[vid]
    assert row["pacing_status"] == "no beats recorded in file"


def test_colour_not_all_blocked():
    assert media._tool("FFMPEG_BIN", "ffmpeg"), "ffmpeg not found: colour regression"
    assert media._tool("FFPROBE_BIN", "ffprobe"), "ffprobe not found: colour regression"
    path = media.resolve_mp4(ROOT, "7434a0f7")
    assert path is not None and os.path.isfile(path), "mapped mp4 for 7434a0f7 missing"
    stamp = re.search(FOLDER_TS + "_7434a0f7$", _folder_basename("7434a0f7")).groups()
    assert os.path.basename(path) == REF_NAME % stamp
    assert os.path.basename(path) == "WhatsApp Video 2026-10-28 at 9.46.07 PM.mp4"
    rows = media.colour_rows(ROOT)
    by_id = _rows_by_id(rows)
    assert by_id["7434a0f7"]["status"] == "MEASURED_MEDIA", by_id["7434a0f7"]["reason"]
    measured = [r for r in rows if r["status"] == "MEASURED_MEDIA" and r["mapped_file"]
                and os.path.isfile(os.path.join(REFERENCE_DIR, r["mapped_file"]))]
    assert measured, "no MEASURED_MEDIA colour row with an existing mapped file"


def test_protected_detection_only_by_protected_ids(tmp_path):
    anim = tmp_path / "anim"
    (anim / "WhatsApp_Video_2026-10-28_at_9_46_15_PM_10151cce").mkdir(parents=True)
    assert media._protected_timestamps(str(anim)) == []
    pid = media.PROTECTED_IDS[0]
    (anim / ("WhatsApp_Video_2026-10-28_at_9_46_11_PM_" + pid)).mkdir()
    assert media._protected_timestamps(str(anim)) == [("9", "46", "11", "PM")]


def test_protected_files_never_opened_or_passed_to_tools(tmp_path, monkeypatch):
    opened = []
    commands = []
    real_open = builtins.open
    real_run = subprocess.run

    def open_spy(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    def run_spy(args, *rest, **kwargs):
        commands.append(" ".join(str(a) for a in args))
        return real_run(args, *rest, **kwargs)

    monkeypatch.setattr(builtins, "open", open_spy)
    monkeypatch.setattr(media.subprocess, "run", run_spy)
    media.write_all(ROOT, str(tmp_path))
    for pid in media.PROTECTED_IDS:
        assert not any(pid in path for path in opened + commands)


def test_missing_audio_key_gives_gap_row(tmp_path):
    root = str(tmp_path)
    vid = sorted(_discovered_ids())[0]
    data = _json(_audio_path(vid))
    del data["wav_seconds"]
    _write_json(os.path.join(_audit(root, vid), "audio_%s.json" % vid), data)
    gap = _rows_by_id(media.gap_rows(root))[vid]
    assert "missing key wav_seconds" in gap["gap_note"]
    audio = _rows_by_id(media.audio_rows(root))[vid]
    assert audio["analysed"] == "N"
    assert audio["speech_segment_count"] == ""


def test_missing_beat_key_is_source_gap_without_captions(tmp_path):
    root = str(tmp_path)
    vid = "7434a0f7"
    data = _json(_beats_path(vid))
    del data["beats"][0]["end_time"]
    _write_json(os.path.join(_audit(root, vid), "beats_%s.json" % vid), data)
    row = _rows_by_id(media.pacing_rows(root))[vid]
    assert row["pacing_status"] == "source gap"
    assert "missing key end_time" in row["gap_note"]
    assert vid not in {r["video_id"] for r in media.caption_rows(root)}


def test_write_all_writes_exactly_six_files(real_run):
    out, counts = real_run
    assert sorted(os.listdir(str(out))) == sorted(SIX_FILES)
    assert set(counts) == SIX_FILES


def test_gap_rows_dev_set_and_special_rows(real_run):
    rows = media.gap_rows(ROOT)
    ids = [r["video_id"] for r in rows]
    discovered = _discovered_ids()
    assert discovered == set(media.DEV)
    for vid in discovered:
        assert ids.count(vid) == 1
    assert "9.47.17_UNMAPPED" in ids
    by_id = _rows_by_id(rows)
    listing = _ref_listing()
    for stamp in _protected_stamps():
        if REF_NAME % tuple(stamp) in listing:
            label = "%s.%s.%s_PROTECTED" % tuple(stamp[:3])
            assert label in by_id
            assert by_id[label]["gap_note"] == "protected held-out; not read"
            assert not label.endswith("_UNMAPPED")


def test_real_files_have_expected_keys():
    audio = _json(_audio_path("7434a0f7"))
    for key in ("folder", "wav_seconds", "silences", "low_volume_intervals",
                "speech_segments", "transcript_status", "sound_classes"):
        assert key in audio
    beats = _json(_beats_path("7434a0f7"))["beats"]
    for key in ("beat_id", "start_time", "end_time", "department_findings"):
        assert key in beats[0]
