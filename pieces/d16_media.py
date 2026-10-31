"""Departments 12-15 and the timing parts of 5-7: colour, sound, text and pacing summaries.

Local tools only (ffmpeg, ffprobe, numpy) on the local reference videos, plus the cached
transcripts, beat timings and text observations. No model, no network, no detector.
Held-out videos are identified from folder basenames only and are never read.
"""

import csv
import json
import os
import re
import shutil
import statistics
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE_DIR = os.path.join(os.path.dirname(ROOT), "reference_videos")
ANIM_DIR = os.path.join(os.path.dirname(ROOT), "animation_research_tool", "animation_research")
OUT_PARTS = ("work", "phase1", "departments_16", "media")

DEV = ("10151cce", "264e48c4", "585b32de", "5c93ec37", "69a00a0f",
       "7434a0f7", "7a1e2b26", "85c38505", "a44aef0b", "caf6fb64")
PROTECTED_IDS = ("354a38a0", "37745d70", "baf59433")  # held-out: folder-name metadata only
MEASURED_CUT_IDS = ("7434a0f7", "7a1e2b26")
AUDIO_KEYS = ("video_id", "folder", "audio_status", "availability", "wav_seconds", "silences",
              "low_volume_intervals", "speech_segments", "transcript_status", "sound_classes",
              "gap_classes")

AI_VERIFY = "AI_READING_UNVERIFIED"
OBSERVED = "OBSERVED"
UNKNOWN_CUTS = "UNKNOWN_NOT_MEASURED"
UNMAPPED_ALWAYS = "9.47.17_UNMAPPED"
NO_FOLDER_NOTE = "reference file has no analysed folder; not analysed"
PROTECTED_NOTE = "protected held-out; not read"
FPS = 2
FRAME_SHAPE = (36, 64, 3)
SAMPLE_TIMEOUT_S = 300
REF_PATTERN = r"WhatsApp Video 2026-10-28 at (\d{1,2})\.(\d{2})\.(\d{2}) (AM|PM)\.mp4"
REF_TEMPLATE = "WhatsApp Video 2026-10-28 at %s.%s.%s %s.mp4"
FOLDER_TS = r"(\d{1,2})_(\d{2})_(\d{2})_(AM|PM)"
# quoted text of length 2 or more, between matching single or double quotes (spec)
QUOTE_RE = re.compile(r"(?<!\w)(['\"])(.{2,}?)\1(?!\w)")

COLOUR_FIELDS = ["video_id", "status", "reason", "mapped_file", "duration_s", "samples",
                 "mean_luma", "std_luma", "near_black_fraction", "mean_saturation"]
SERIES_FIELDS = ["video_id", "t_s", "mean_luma", "mean_saturation"]
AUDIO_FIELDS = ["video_id", "analysed", "transcript_status", "speech_segment_count",
                "speech_seconds_total", "wav_seconds", "speech_coverage_fraction",
                "silence_seconds", "low_volume_seconds", "sound_classes", "gap_note"]
PACING_FIELDS = ["video_id", "pacing_status", "gap_note", "beat_count", "zero_length_beat_count",
                 "zero_length_beat_ids", "nonzero_beat_count", "union_covered_seconds",
                 "median_nonzero_beat_seconds", "overlapping_pairs", "hard_cut_count",
                 "cuts_per_minute"]
CAPTION_FIELDS = ["video_id", "beat_id", "start_time", "end_time", "department_id",
                  "quoted_text", "verification"]
GAP_FIELDS = ["video_id", "colour_status", "audio_analysed", "transcript_status",
              "caption_inventory_count", "pacing_status", "gap_note"]


class SourceGap(Exception):
    """A required file or key is missing or malformed; the video gets a gap row."""

    def __init__(self, note):
        super().__init__(note)
        self.note = note


def _guard_id(vid):
    if vid in PROTECTED_IDS:
        raise ValueError("held-out video requested")


def _tool(env_name, exe):
    env = os.environ.get(env_name)
    if env and os.path.isfile(env):
        return env
    return shutil.which(exe)


def _stderr_text(proc):
    return proc.stderr.decode("utf-8", "replace").strip()


def _load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh), "ok"
    except FileNotFoundError:
        return None, "missing"
    except (OSError, ValueError):
        return None, "unreadable"


def _need(data, key):
    if not isinstance(data, dict) or key not in data:
        raise SourceGap("missing key " + key)
    return data[key]


def _num(value, key):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SourceGap("bad value " + key)
    return float(value)


def _intervals(data, key, fields):
    items = _need(data, key)
    if not isinstance(items, list):
        raise SourceGap("bad value " + key)
    return [{f: _num(_need(item, f), f) for f in fields} for item in items]


def _audit_path(root, vid, prefix):
    return os.path.join(root, "work", "phase1", "v4", "audit_" + vid, prefix + vid + ".json")


def _folder_ref_name(root, vid):
    data, status = _load_json(_audit_path(root, vid, "audio_"))
    if status != "ok" or not isinstance(data, dict):
        return None
    folder = data.get("folder")
    if not isinstance(folder, str):
        return None
    base = os.path.basename(folder.replace("\\", "/"))
    found = re.search(FOLDER_TS + "_" + re.escape(vid) + "$", base)
    return REF_TEMPLATE % found.groups() if found else None


def resolve_mp4(root, video_id):
    _guard_id(video_id)
    name = _folder_ref_name(root, video_id)
    if name is None:
        return None
    path = os.path.join(REFERENCE_DIR, name)
    return path if os.path.isfile(path) else None


def probe_duration(path):
    ffprobe = _tool("FFPROBE_BIN", "ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe not found")
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, timeout=120, check=False)
    if proc.returncode != 0:
        raise RuntimeError(_stderr_text(proc) or "ffprobe failed")
    return float(proc.stdout.decode("utf-8", "replace").strip())


def sample_brightness(path, fps=FPS):
    ffmpeg = _tool("FFMPEG_BIN", "ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")
    cmd = [ffmpeg, "-v", "error", "-i", path, "-vf", "fps=%d,scale=64:36" % fps,
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    proc = subprocess.run(cmd, capture_output=True, timeout=SAMPLE_TIMEOUT_S, check=False)
    if proc.returncode != 0:
        raise RuntimeError(_stderr_text(proc) or "ffmpeg failed")
    if not proc.stdout:
        raise RuntimeError("no frames decoded")
    frame = FRAME_SHAPE[0] * FRAME_SHAPE[1] * FRAME_SHAPE[2]
    raw = np.frombuffer(proc.stdout, dtype=np.uint8)
    count = raw.size // frame
    if count == 0:
        raise RuntimeError("no frames decoded")
    arr = raw[: count * frame].reshape((count,) + FRAME_SHAPE).astype(np.float64) / 255.0
    luma = (0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]).mean(axis=(1, 2))
    high = arr.max(axis=3)
    low = arr.min(axis=3)
    safe = np.where(high > 0, high, 1.0)
    sat = np.where(high > 0, (high - low) / safe, 0.0).mean(axis=(1, 2))
    return luma, sat


def _colour_blank(vid):
    return {"video_id": vid, "status": "", "reason": "", "mapped_file": "", "duration_s": "",
            "samples": "", "mean_luma": "", "std_luma": "", "near_black_fraction": "",
            "mean_saturation": "", "_luma": None, "_sat": None}


def _block(row, reason):
    row["status"] = "BLOCKED_BY_SOURCE"
    row["reason"] = reason


def _record_gap(root, vid):
    # Shared integrity check for one video's combined audio and beats record.
    # Returns the gap note when either source is incomplete, "" when both are complete.
    try:
        _load_beats(root, vid)
    except SourceGap as gap:
        return gap.note
    _, note = _audio_stats(root, vid)
    return note


def colour_rows(root):
    rows = []
    tools = bool(_tool("FFMPEG_BIN", "ffmpeg")) and bool(_tool("FFPROBE_BIN", "ffprobe"))
    for vid in DEV:
        row = _colour_blank(vid)
        rows.append(row)
        if not tools:
            _block(row, "ffmpeg not found")
            continue
        note = _record_gap(root, vid)
        if note:
            _block(row, note)
            continue
        path = resolve_mp4(root, vid)
        if path is None:
            _block(row, "no reference file mapped")
            continue
        row["mapped_file"] = os.path.basename(path)
        try:
            duration = probe_duration(path)
            luma, sat = sample_brightness(path)
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as err:
            _block(row, "ffmpeg failed: " + str(err))
            continue
        row.update(status="MEASURED_MEDIA", reason="", duration_s=duration,
                   samples=int(luma.size), mean_luma=float(luma.mean()),
                   std_luma=float(luma.std()), near_black_fraction=float((luma < 0.08).mean()),
                   mean_saturation=float(sat.mean()), _luma=luma, _sat=sat)
    return rows


def brightness_series(rows):
    out = []
    for row in rows:
        if row["status"] != "MEASURED_MEDIA":
            continue
        pairs = zip(row["_luma"].tolist(), row["_sat"].tolist())
        for index, (luma, sat) in enumerate(pairs):
            out.append({"video_id": row["video_id"], "t_s": index / FPS,
                        "mean_luma": luma, "mean_saturation": sat})
    return out


def _audio_stats(root, vid):
    _guard_id(vid)
    data, status = _load_json(_audit_path(root, vid, "audio_"))
    if status == "missing":
        return None, "source gap: audio_%s.json missing" % vid
    if status == "unreadable":
        return None, "source gap: audio_%s.json unreadable" % vid
    try:
        for key in AUDIO_KEYS:
            _need(data, key)
        wav = _num(_need(data, "wav_seconds"), "wav_seconds")
        speech = _intervals(data, "speech_segments", ("start", "end"))
        silences = _intervals(data, "silences", ("start", "end"))
        low = _intervals(data, "low_volume_intervals", ("start", "end", "duration"))
        transcript = _need(data, "transcript_status")
        sounds = _need(data, "sound_classes")
    except SourceGap as gap:
        return None, gap.note
    stats = {
        "wav_seconds": wav,
        "transcript_status": transcript,
        "sound_classes": sounds,
        "speech_count": len(speech),
        "speech_seconds": float(sum(s["end"] - s["start"] for s in speech)),
        "silence_seconds": float(sum(s["end"] - s["start"] for s in silences)),
        "low_volume_seconds": float(sum(s["duration"] for s in low)),
    }
    return stats, ""


def _audio_blank(vid, note):
    return {"video_id": vid, "analysed": "N", "transcript_status": "", "speech_segment_count": "",
            "speech_seconds_total": "", "wav_seconds": "", "speech_coverage_fraction": "",
            "silence_seconds": "", "low_volume_seconds": "", "sound_classes": "", "gap_note": note}


def audio_rows(root):
    rows = []
    for vid in DEV:
        stats, note = _audio_stats(root, vid)
        row = _audio_blank(vid, note)
        if stats is not None:
            wav = stats["wav_seconds"]
            notes = []
            if stats["sound_classes"] == "UNKNOWN":
                notes.append("sound classes never analysed")
            if stats["speech_count"] == 0:
                notes.append("transcript empty")
            row.update(analysed="Y", transcript_status=stats["transcript_status"],
                       speech_segment_count=stats["speech_count"],
                       speech_seconds_total=stats["speech_seconds"], wav_seconds=wav,
                       speech_coverage_fraction=stats["speech_seconds"] / wav if wav else "",
                       silence_seconds=stats["silence_seconds"],
                       low_volume_seconds=stats["low_volume_seconds"],
                       sound_classes=stats["sound_classes"], gap_note="; ".join(notes))
        rows.append(row)
    return rows


def _check_beat(beat):
    bid = _need(beat, "beat_id")
    start = _num(_need(beat, "start_time"), "start_time")
    end = _num(_need(beat, "end_time"), "end_time")
    dept_map = _need(beat, "department_findings")
    if not isinstance(dept_map, dict):
        raise SourceGap("bad value department_findings")
    findings = []
    for key, items in dept_map.items():
        try:
            dept = int(key)
        except (TypeError, ValueError):
            raise SourceGap("bad value department_findings")
        if not isinstance(items, list):
            raise SourceGap("bad value department_findings")
        for item in items:
            status = _need(item, "status")
            observed = None
            if status == OBSERVED:
                observed = _need(item, "observed")
                if not isinstance(observed, str):
                    raise SourceGap("bad value observed")
            findings.append((dept, status, observed))
    return (bid, start, end, findings)


def _load_beats(root, vid):
    _guard_id(vid)
    data, status = _load_json(_audit_path(root, vid, "beats_"))
    if status == "missing":
        # spec wording: the frozen test and the spec require this exact note
        raise SourceGap("source gap: beats file missing")
    if status == "unreadable":
        raise SourceGap("source gap: beats_%s.json unreadable" % vid)
    beats = _need(data, "beats")
    if not isinstance(beats, list):
        raise SourceGap("bad value beats")
    return [_check_beat(beat) for beat in beats]


def _hard_cut_count(root, vid):
    if vid not in MEASURED_CUT_IDS:
        return UNKNOWN_CUTS
    data, status = _load_json(os.path.join(root, "work", "phase1", "step4", "STEP4_MEASUREMENTS.json"))
    if status != "ok":
        return UNKNOWN_CUTS
    try:
        events = data[vid]["transitions"]["events"]
        return sum(1 for ev in events if isinstance(ev, dict) and ev.get("kind") == "hard_cut")
    except (KeyError, TypeError):
        return UNKNOWN_CUTS


def _union_seconds(spans):
    total = 0.0
    current = None
    for start, end, _ in sorted(spans):
        if current is None:
            current = [start, end]
        elif start <= current[1]:
            current[1] = max(current[1], end)
        else:
            total += current[1] - current[0]
            current = [start, end]
    if current is not None:
        total += current[1] - current[0]
    return total


def _overlap_pairs(spans):
    count = 0
    for i, (a0, a1, _) in enumerate(spans):
        for b0, b1, _ in spans[i + 1:]:
            if min(a1, b1) - max(a0, b0) > 0:
                count += 1
    return count


def _pacing_row(root, vid):
    row = {"video_id": vid, "pacing_status": "", "gap_note": "", "beat_count": "",
           "zero_length_beat_count": "", "zero_length_beat_ids": "", "nonzero_beat_count": "",
           "union_covered_seconds": "", "median_nonzero_beat_seconds": "",
           "overlapping_pairs": "", "hard_cut_count": "", "cuts_per_minute": ""}
    note = _record_gap(root, vid)
    if note:
        row.update(pacing_status="source gap", gap_note=note)
        return row
    beats = _load_beats(root, vid)
    hard = _hard_cut_count(root, vid)
    row["hard_cut_count"] = hard
    zero = [bid for bid, start, end, _ in beats if end == start]
    spans = [(min(start, end), max(start, end), end - start)
             for _, start, end, _ in beats if end != start]
    row.update(beat_count=len(beats), zero_length_beat_count=len(zero),
               zero_length_beat_ids=";".join(str(bid) for bid in zero),
               nonzero_beat_count=len(spans), union_covered_seconds=_union_seconds(spans),
               median_nonzero_beat_seconds=statistics.median([s[2] for s in spans]) if spans else "",
               overlapping_pairs=_overlap_pairs(spans))
    if beats and isinstance(hard, int):
        longest = max(end for _, _, end, _ in beats)
        if longest > 0:
            row["cuts_per_minute"] = hard / (longest / 60.0)
    if beats:
        row["pacing_status"] = "PACING_OK"
    else:
        row.update(pacing_status="no beats recorded in file", gap_note="no beats recorded in file")
    return row


def pacing_rows(root):
    return [_pacing_row(root, vid) for vid in DEV]


def _quoted_texts(text):
    return [match[1] for match in QUOTE_RE.findall(text)]


def caption_rows(root):
    rows = []
    for vid in DEV:
        if _record_gap(root, vid):
            continue
        beats = _load_beats(root, vid)
        for beat_id, start, end, findings in beats:
            for dept, status, observed in findings:
                if status != OBSERVED:
                    continue
                for text in _quoted_texts(observed):
                    rows.append({"video_id": vid, "beat_id": beat_id, "start_time": start,
                                 "end_time": end, "department_id": dept, "quoted_text": text,
                                 "verification": AI_VERIFY})
    return rows


def _reference_files():
    if not os.path.isdir(REFERENCE_DIR):
        return {}
    found = {}
    for name in os.listdir(REFERENCE_DIR):
        match = re.fullmatch(REF_PATTERN, name)
        if match:
            found[name] = match.groups()
    return found


def _protected_timestamps(anim_dir=ANIM_DIR):
    if not os.path.isdir(anim_dir):
        return []
    stamps = []
    for name in sorted(os.listdir(anim_dir)):
        for pid in PROTECTED_IDS:
            found = re.search(FOLDER_TS + "_" + re.escape(pid) + "$", name)
            if found:
                stamps.append(found.groups())
    return stamps


def _ref_name(stamp):
    return REF_TEMPLATE % tuple(stamp)


def _label(stamp):
    return "%s.%s.%s" % tuple(stamp[:3])


def _gap_row(video_id, colour_status, audio_analysed, transcript_status, caption_count,
             pacing_status, gap_note):
    return {"video_id": video_id, "colour_status": colour_status,
            "audio_analysed": audio_analysed, "transcript_status": transcript_status,
            "caption_inventory_count": caption_count, "pacing_status": pacing_status,
            "gap_note": gap_note}


def gap_rows(root, colour=None, audio=None, pacing=None, caption=None):
    colour = colour_rows(root) if colour is None else colour
    audio = audio_rows(root) if audio is None else audio
    pacing = pacing_rows(root) if pacing is None else pacing
    caption = caption_rows(root) if caption is None else caption
    colour_by = {r["video_id"]: r for r in colour}
    audio_by = {r["video_id"]: r for r in audio}
    pacing_by = {r["video_id"]: r for r in pacing}
    caption_counts = {}
    for row in caption:
        caption_counts[row["video_id"]] = caption_counts.get(row["video_id"], 0) + 1

    rows = []
    for vid in DEV:
        c, a, p = colour_by[vid], audio_by[vid], pacing_by[vid]
        notes = []
        if c["status"] != "MEASURED_MEDIA":
            notes.append("colour: " + c["reason"])
        notes.extend(note for note in (a["gap_note"], p["gap_note"]) if note)
        rows.append(_gap_row(vid, c["status"], a["analysed"], a["transcript_status"],
                             caption_counts.get(vid, 0), p["pacing_status"], "; ".join(notes)))

    refs = _reference_files()
    mapped = {_folder_ref_name(root, vid) for vid in DEV}
    protected = set()
    for stamp in _protected_timestamps():
        name = _ref_name(stamp)
        if name in refs:
            protected.add(name)
    for name in sorted(protected):
        rows.append(_gap_row(_label(refs[name]) + "_PROTECTED", "PROTECTED_HELDOUT",
                             "PROTECTED_HELDOUT", "", 0, "PROTECTED_HELDOUT", PROTECTED_NOTE))

    unmapped = []
    for name in sorted(refs):
        if name in mapped or name in protected:
            continue
        unmapped.append(_gap_row(_label(refs[name]) + "_UNMAPPED", "NOT_ANALYSED", "N", "",
                                 0, "NOT_ANALYSED", NO_FOLDER_NOTE))
    if not any(r["video_id"] == UNMAPPED_ALWAYS for r in unmapped):
        unmapped.append(_gap_row(UNMAPPED_ALWAYS, "NOT_ANALYSED", "N", "", 0,
                                 "NOT_ANALYSED", NO_FOLDER_NOTE))
    rows.extend(unmapped)
    return rows


def write_all(root, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    colour = colour_rows(root)
    audio = audio_rows(root)
    pacing = pacing_rows(root)
    caption = caption_rows(root)
    tables = {
        "colour_brightness_summary.csv": (COLOUR_FIELDS, colour),
        "brightness_series.csv": (SERIES_FIELDS, brightness_series(colour)),
        "audio_timing_summary.csv": (AUDIO_FIELDS, audio),
        "pacing_rhythm_summary.csv": (PACING_FIELDS, pacing),
        "caption_text_inventory.csv": (CAPTION_FIELDS, caption),
        "media_gaps.csv": (GAP_FIELDS, gap_rows(root, colour, audio, pacing, caption)),
    }
    counts = {}
    for name, (fields, rows) in tables.items():
        with open(os.path.join(out_dir, name), "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        counts[name] = len(rows)
    return counts


def main(argv=None):
    counts = write_all(ROOT, os.path.join(ROOT, *OUT_PARTS))
    for name, count in counts.items():
        print("%s %d" % (name, count))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
