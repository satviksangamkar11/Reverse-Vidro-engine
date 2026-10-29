"""Local overview and action evidence selection; no network access."""
from __future__ import annotations

import json
import math
import re
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


def _ssim(a, b):
    a, b = a.astype(np.float32), b.astype(np.float32)
    ma, mb = cv2.GaussianBlur(a, (7, 7), 1.5), cv2.GaussianBlur(b, (7, 7), 1.5)
    va = cv2.GaussianBlur(a * a, (7, 7), 1.5) - ma * ma
    vb = cv2.GaussianBlur(b * b, (7, 7), 1.5) - mb * mb
    cov = cv2.GaussianBlur(a * b, (7, 7), 1.5) - ma * mb
    score = ((2 * ma * mb + 58.5) * (2 * cov + 58.5)) / ((ma * ma + mb * mb + 58.5) * (va + vb + 58.5))
    return float(np.clip(score.mean(), -1, 1))


def _time_map(path):
    raw = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=best_effort_timestamp_time", "-of", "csv=p=0", str(path)], text=True, timeout=120)
    result = []
    for line in raw.splitlines():
        try:
            result.append(float(line.split(",")[0]))
        except ValueError:
            result.append(None)
    return result


def analyze_local_frames(folder: Path, manifest: dict, *, cut_hist=0.30, cut_ssim=0.68, action_residual=0.035, min_event_samples=2):
    files = sorted((folder / "selected_frames").glob("frame_*.jpg"))
    frames = [{"frame": int(re.search(r"(\d+)$", p.stem).group(1)), "path": p} for p in files]
    pts = _time_map(Path(manifest["source"])) if manifest["kind"] == "video" else []
    lookup = {x["frame"]: x["time"] for x in manifest["frames"]}
    for f in frames:
        idx = f["frame"]
        f["time"] = pts[idx] if idx < len(pts) else lookup.get(idx)
        with Image.open(f["path"]) as im:
            rgb = np.asarray(im.convert("RGB").resize((192, 108)))
        f["gray"] = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        f["hist"] = cv2.calcHist([f["gray"]], [0], None, [32], [0, 256])
        f.update({"shot": 1, "motion_score": 0.0, "global_motion": 0.0, "confidence": 1.0, "uncertain": False})
    cuts = [0] if frames else []
    for i in range(1, len(frames)):
        a, b = frames[i - 1], frames[i]
        hist = float(cv2.compareHist(a["hist"], b["hist"], cv2.HISTCMP_BHATTACHARYYA))
        ssim = _ssim(a["gray"], b["gray"])
        if hist > cut_hist and ssim < cut_ssim:
            cuts.append(i)
            frames[i]["shot"] = len(cuts)
            continue
        try:
            shift, response = cv2.phaseCorrelate(a["gray"].astype(np.float32), b["gray"].astype(np.float32))
            dx, dy = shift
            if not np.isfinite(dx + dy) or response < 0.05 or abs(dx) > 48 or abs(dy) > 27:
                raise ValueError("Unreliable camera compensation")
            warped = cv2.warpAffine(a["gray"], np.float32([[1, 0, dx], [0, 1, dy]]), (192, 108))
            residual = cv2.absdiff(warped, b["gray"])
            central = residual[12:100, 25:167]
            blocks = cv2.resize(central, (8, 5), interpolation=cv2.INTER_AREA)
            score = max(float(np.mean(central)), float(np.max(blocks)) * 0.5) / 255
            frames[i]["motion_score"] = score
            frames[i]["global_motion"] = math.hypot(dx, dy)
            frames[i]["confidence"] = float(np.clip(response, 0, 1))
        except (cv2.error, ValueError):
            frames[i]["motion_score"] = max(0.0, 1 - ssim)
            frames[i]["confidence"] = 0.0
            frames[i]["uncertain"] = True
        frames[i]["shot"] = len(cuts)
    return frames, cuts


def _sheet(frames, path, columns=4):
    if not frames:
        return
    with Image.open(frames[0]["path"]) as sample:
        portrait = sample.height > sample.width
    if portrait:
        w, h = 220, 400
        if len(frames) > 6:
            columns = 6
    else:
        w, h = 320, 205
    canvas = Image.new("RGB", (columns * w, math.ceil(len(frames) / columns) * h), "white")
    draw = ImageDraw.Draw(canvas)
    for j, f in enumerate(frames):
        with Image.open(f["path"]) as source:
            im = source.convert("RGB"); im.thumbnail((w - 8, h - 28))
        x, y = j % columns * w, j // columns * h
        canvas.paste(im, (x + 4, y + 2))
        draw.text((x + 4, y + h - 23), f"F{f['frame']}  {f['time'] if f['time'] is not None else 'UNKNOWN'}s  S{f['shot']}", fill="black")
    canvas.save(path, quality=88)


def build_selection(folder: Path, manifest: dict, *, overview_count=10, action_residual=0.035):
    frames, cuts = analyze_local_frames(folder, manifest, action_residual=action_residual)
    by_shot = {}
    for i, f in enumerate(frames):
        by_shot.setdefault(f["shot"], []).append(i)
    overview = set()
    reasons = {}
    for shot, ids in by_shot.items():
        picks = [ids[0], ids[len(ids) // 2], ids[-1]]
        for i, reason in zip(picks, ("SHOT_START", "SCENE_REPRESENTATIVE", "SHOT_END")):
            overview.add(i); reasons.setdefault(i, set()).add(reason)
    # A long shot gets proportional coverage; keep the overview readable.
    if len(overview) < overview_count:
        for x in np.linspace(0, len(frames) - 1, min(overview_count, len(frames))):
            i = round(x); overview.add(i); reasons.setdefault(i, set()).add("TEMPORAL_COVERAGE")
    overview = sorted(overview)
    api_overview = sorted({overview[round(x)] for x in np.linspace(0, len(overview) - 1, min(12, len(overview)))}) if overview else []
    _sheet([frames[i] for i in api_overview], folder / "storyboard_api.jpg")
    overview_sheets = []
    for page, start in enumerate(range(0, len(overview), 12), 1):
        path = folder / f"storyboard_{page:02d}.jpg"
        _sheet([frames[i] for i in overview[start:start + 12]], path)
        overview_sheets.append(path)
    # Group neighboring local residual changes; preserve onset, middle, end and context.
    candidates = [i for i in range(1, len(frames)) if frames[i]["motion_score"] >= action_residual and i not in cuts]
    events = []
    for i in candidates:
        if not events or i - events[-1][-1] > 2 or frames[i]["shot"] != frames[events[-1][-1]]["shot"]:
            events.append([i])
        else:
            events[-1].append(i)
    short_events = [run[start:start + 4] for run in events for start in range(0, len(run), 4)]
    event_records = []
    for event_number, ids in enumerate(short_events, 1):
        start, end = ids[0], ids[-1]
        same_shot = by_shot[frames[start]["shot"]]
        peak = max(ids, key=lambda i: frames[i]["motion_score"])
        burst_start = max(same_shot[0], min(peak - 1, same_shot[-1] - 3))
        burst = list(range(burst_start, min(same_shot[-1] + 1, burst_start + 4)))
        score = max(frames[i]["motion_score"] for i in ids)
        event_records.append({"event_id": f"event_{event_number:03d}", "shot_id": frames[start]["shot"], "start_frame": frames[start]["frame"], "end_frame": frames[end]["frame"], "score": score, "uncertain": any(frames[i]["uncertain"] for i in ids), "burst_indices": burst, "burst_frames": [frames[i]["frame"] for i in burst], "status": "PENDING"})
    event_records.sort(key=lambda e: e["score"], reverse=True)
    primary = event_records[0] if event_records else None
    if primary is None and frames:
        center = len(frames) // 2
        burst = sorted(set(max(0, min(len(frames) - 1, center + offset)) for offset in (-1, 0, 1, 2)))
        primary = {"event_id": "event_uncertain", "shot_id": frames[center]["shot"], "start_frame": frames[burst[0]]["frame"], "end_frame": frames[burst[-1]]["frame"], "score": 0.0, "uncertain": True, "burst_indices": burst, "burst_frames": [frames[i]["frame"] for i in burst], "status": "PENDING"}
        event_records.append(primary)
    if primary:
        _sheet([frames[i] for i in primary["burst_indices"]], folder / "action_burst_01.jpg")
    selected = set(api_overview) | (set(primary["burst_indices"]) if primary else set())
    records = []
    for i in sorted(selected):
        f = frames[i]
        tracks = []
        if i in api_overview:
            tracks.append("OVERVIEW")
        if primary and i in primary["burst_indices"]:
            tracks.append("ACTION")
        records.append({"video_id": manifest["video_id"], "original_frame_number": f["frame"], "timestamp": f["time"], "shot_id": f["shot"], "event_id": primary["event_id"] if "ACTION" in tracks else None, "selection_reason": sorted(reasons.get(i, set()) | ({"UNCERTAIN_MOTION"} if "ACTION" in tracks or f["uncertain"] else set())), "selection_track": tracks, "neighboring_frame_ids": [frames[j]["frame"] for j in (i - 1, i + 1) if 0 <= j < len(frames)], "motion_score": round(f["motion_score"], 5), "confidence": round(f["confidence"], 3)})
    selection = {"selection_version": 3, "video_id": manifest["video_id"], "local_frames_analyzed": len(frames), "local_frame_index": [{"frame": f["frame"], "time": f["time"], "shot": f["shot"], "file": f["path"].name} for f in frames], "overview_frames": len(api_overview), "manual_overview_frames": len(overview), "action_burst_frames": len(primary["burst_indices"]) if primary else 0, "unique_frames_selected_for_api": len(selected), "storyboard_calls": 1 if overview_sheets else 0, "action_calls": 1 if primary else 0, "storyboard_sheets": [p.name for p in overview_sheets], "api_storyboard_sheet": "storyboard_api.jpg", "events": [{k: v for k, v in e.items() if k != "burst_indices"} for e in event_records], "selected_frames": records, "primary_action_frames": [frames[i]["frame"] for i in primary["burst_indices"]] if primary else []}
    (folder / "frame_selection_manifest.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
    return selection
