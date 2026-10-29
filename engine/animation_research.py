"""Standalone, checkpointed research of animation references."""
from __future__ import annotations

import argparse
import base64
import bisect
import csv
import hashlib
import io
import json
import math
import re
import subprocess
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from frame_selection import build_selection
from nvidia_scheduler import NvidiaScheduler, load_env_keys
from instagram_import import import_reels, read_urls
from cinematic_analysis import analyze_source, write_knowledge

MODEL = "nvidia/nemotron-3.5-super-vl-120b-a12b"
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm"}
IMAGE_EXT = {".png", ".jpg", ".jpeg"}
FIELDS = ("video_id scene_id start_frame end_frame start_time end_time characters observed_animation inferred_technique camera_motion character_motion visual_effects required_assets potential_blender_implementation granthstudio_capability evidence_frames confidence uncertainties").split()
INSTRUCTION = """You are a Senior Animation Technical Director studying sequential frames from an animated video.

Analyze the visible animation, not just the depicted story.

Identify:
- Character body and limb movements
- Changes in facial expression
- Walking, bowing, hand gestures and reactions
- Camera movement and zoom
- Layered artwork and parallax
- Object movement
- Environmental effects
- Lighting and particle animation
- Pose switching
- Apparent cutout or puppet movement
- Cinematic cuts and composition
- Text and subtitle animation
- Timing and movement continuity

For every significant observation, report its exact provided frame numbers and timestamps.

Separate:
OBSERVED: what visibly changes between frames.
INFERRED: what technique might explain it.
PROPOSED: how GranthStudio could reproduce it.

Do not invent animation software, skeletons, Blender rigs, joint coordinates, hidden layers or source project structures.
When evidence is insufficient, use UNKNOWN.
Distinguish genuine character articulation from moving or replacing a whole illustration.
Identify the assets and controls that would be needed to recreate each observed effect.

Return one JSON object with these keys: """ + ", ".join(FIELDS) + """.
Classify granthstudio_capability as V2_REUSE, V2_EXTENSION, V3_ACTION, NEW_ARTWORK, or UNKNOWN. V2_REUSE is a possibility, never a claim of implementation or testing."""


def save_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def natural_key(s):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", str(s))]


def digest_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


@dataclass
class Source:
    path: Path
    kind: str
    entries: list[str]
    identity: str


def discover(root: Path):
    videos, zips, groups = [], [], defaultdict(list)
    for p in ([root] if root.is_file() else sorted(root.rglob("*"))):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in VIDEO_EXT:
            videos.append(p)
        elif ext == ".zip":
            zips.append(p)
        elif ext in IMAGE_EXT:
            m = re.match(r"^(.*?)(\d+)$", p.stem)
            if m:
                groups[(p.parent, m.group(1))].append(p)
    sources, seen = [], set()
    for p in videos:
        h = digest_file(p)
        if h not in seen:
            sources.append(Source(p, "video", [], h))
            seen.add(h)
    for (parent, prefix), files in groups.items():
        if len(files) < 2:
            continue
        files.sort(key=natural_key)
        h = hashlib.sha256("".join(digest_file(p) for p in files).encode()).hexdigest()
        if h not in seen:
            sources.append(Source(parent / prefix, "sequence", [str(p) for p in files], h))
            seen.add(h)
    for p in zips:
        try:
            with zipfile.ZipFile(p) as z:
                entries = sorted((i.filename for i in z.infolist() if not i.is_dir() and Path(i.filename).suffix.lower() in IMAGE_EXT and not i.flag_bits & 1 and i.file_size <= 100_000_000 and i.file_size <= max(1_000_000, i.compress_size * 100)), key=natural_key)
                if not entries or len(entries) > 20000 or sum(z.getinfo(e).file_size for e in entries) > 4_000_000_000:
                    continue
                # Hash decompressed supported frames to deduplicate extracted sequences.
                h = hashlib.sha256()
                for name in entries:
                    with z.open(name) as f:
                        h.update(hashlib.sha256(f.read()).digest())
                if h.hexdigest() not in seen:
                    sources.append(Source(p, "zip", entries, h.hexdigest()))
                    seen.add(h.hexdigest())
        except (OSError, zipfile.BadZipFile, RuntimeError):
            continue
    return sorted(sources, key=lambda s: str(s.path).lower())


def probe(path: Path):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,avg_frame_rate,nb_frames:format=duration", "-of", "json", str(path)]
    data = json.loads(subprocess.check_output(cmd, text=True, timeout=30))
    stream = data["streams"][0]
    a, b = stream.get("avg_frame_rate", "0/1").split("/")
    fps = float(a) / float(b) if float(b) else 0
    if fps <= 0:
        raise ValueError("Unknown video FPS")
    return {"fps": fps, "duration": float(data["format"]["duration"]), "width": stream["width"], "height": stream["height"], "frame_count": int(stream.get("nb_frames") or 0) or None}


def load_candidates(source: Source):
    if source.kind == "video":
        meta = probe(source.path)
        pts_raw = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=best_effort_timestamp_time", "-of", "csv=p=0", str(source.path)], text=True, timeout=120)
        pts = []
        for line in pts_raw.splitlines():
            try:
                pts.append(float(line.split(",")[0]))
            except ValueError:
                pts.append(None)
        meta["timing"] = "EXACT_FFPROBE_PTS" if pts else "UNKNOWN"
        cap = cv2.VideoCapture(str(source.path))
        if not cap.isOpened():
            raise ValueError("OpenCV cannot decode video")
        count = len(pts) or meta["frame_count"] or int(round(meta["duration"] * meta["fps"]))
        valid_pts = pts and all(t is not None for t in pts)
        indexes = sorted(set([0, max(0, count - 1)] + [min(count - 1, bisect.bisect_left(pts, t) if valid_pts else round(t * meta["fps"])) for t in np.arange(0, meta["duration"], 0.5)]))
        items = []
        for idx in indexes:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, bgr = cap.read()
            if ok:
                items.append({"frame": idx, "time": round(pts[idx], 6) if idx < len(pts) and pts[idx] is not None else None, "image": Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))})
        cap.release()
    else:
        meta = {"fps": None, "duration": None, "width": None, "height": None, "frame_count": len(source.entries), "timing": "UNKNOWN"}
        items = []
        z = zipfile.ZipFile(source.path) if source.kind == "zip" else None
        try:
            for idx, name in enumerate(source.entries):
                try:
                    raw = z.read(name) if z else Path(name).read_bytes()
                    if len(raw) > 100_000_000:
                        continue
                    im = Image.open(io.BytesIO(raw)); im.load()
                    items.append({"frame": idx, "time": None, "image": im.convert("RGB"), "source_name": name})
                except (OSError, ValueError):
                    continue
        finally:
            if z:
                z.close()
        if items:
            meta["width"], meta["height"] = items[0]["image"].size
    if not items:
        raise ValueError("No readable frames")
    return items, meta


def features(im):
    a = np.asarray(ImageOps.fit(im.convert("RGB"), (160, 90)))
    gray = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    return gray, cv2.calcHist([gray], [0], None, [32], [0, 256])


def select_frames(items, meta, target_per_30=18):
    n = len(items)
    if n == 1:
        return [0], [0]
    scores, cuts, motions = [0.0] * n, [0], []
    last_gray, last_hist = features(items[0]["image"])
    for i in range(1, n):
        gray, hist = features(items[i]["image"])
        diff = float(np.mean(cv2.absdiff(gray, last_gray))) / 255
        hdiff = float(cv2.compareHist(last_hist, hist, cv2.HISTCMP_BHATTACHARYYA))
        scores[i] = diff + hdiff * 0.25
        if diff > 0.28 and hdiff > 0.2:
            cuts.append(i)
        elif diff > 0.025:
            motions.append(i)
        last_gray, last_hist = gray, hist
    mandatory = {0, n - 1}
    for c in cuts[1:]:
        mandatory.update((c - 1, c))
    # Merge nearby movement samples into events, then keep a short pose progression.
    runs = []
    for i in motions:
        if not runs or i - runs[-1][-1] > 2:
            runs.append([i])
        else:
            runs[-1].append(i)
    duration = meta.get("duration")
    target = max(2, math.ceil((duration or n / 2) / 30 * target_per_30))
    for i in np.linspace(0, n - 1, min(target, n)):
        mandatory.add(round(i))
    ranked = sorted(runs, key=lambda run: max(scores[i] for i in run), reverse=True)
    for run in ranked[:max(1, target // 5)]:
        peak = max(run, key=lambda i: scores[i])
        mandatory.update((max(0, peak - 1), peak, min(n - 1, peak + 1)))
        if len(run) >= 8:
            mandatory.update(round(x) for x in np.linspace(run[0], run[-1], min(4, len(run))))
    selected = sorted(mandatory)
    # Only exact visual duplicates can be removed; retain first/last shot evidence.
    protected = {0, n - 1} | {j for c in cuts[1:] for j in (c - 1, c)}
    reduced = []
    previous = None
    for i in selected:
        gray, _ = features(items[i]["image"])
        if i in protected or previous is None or np.mean(cv2.absdiff(gray, previous)) > 0.7:
            reduced.append(i)
            previous = gray
    return reduced, cuts


def prepare(source: Source, root: Path, output: Path, target_per_30=18, refresh=False):
    relative = source.path.relative_to(root).with_suffix("")
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(relative)).strip("_")[:90] or "video"
    folder = output / f"{slug}_{source.identity[:8]}"
    manifest_path = folder / "frame_manifest.json"
    if manifest_path.exists() and not refresh:
        return folder, read_json(manifest_path, {})
    items, meta = load_candidates(source)
    _, cuts = select_frames(items, meta, target_per_30)
    frames_dir = folder / "selected_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for i in range(len(items)):
        item = items[i]
        name = f"frame_{item['frame']:08d}.jpg"
        im = item["image"].copy(); im.thumbnail((1280, 1280))
        im.save(frames_dir / name, "JPEG", quality=83)
        records.append({"frame": item["frame"], "time": item["time"], "file": name, "shot": 1 + sum(i >= c for c in cuts[1:])})
    width, height = 240, 165
    sheet_records = [records[round(i)] for i in np.linspace(0, len(records) - 1, min(24, len(records)))]
    sheet = Image.new("RGB", (width * 4, height * math.ceil(len(sheet_records) / 4)), "white")
    draw = ImageDraw.Draw(sheet)
    for j, rec in enumerate(sheet_records):
        im = Image.open(frames_dir / rec["file"]); im.thumbnail((width, height - 25))
        x, y = j % 4 * width, j // 4 * height
        sheet.paste(im, (x, y))
        draw.text((x + 3, y + height - 22), f"#{rec['frame']}  t={rec['time'] if rec['time'] is not None else 'UNKNOWN'}", fill="black")
    sheet.save(folder / "contact_sheet.jpg", quality=85)
    manifest = {"video_id": folder.name, "source": str(source.path), "kind": source.kind, "identity": source.identity, "metadata": meta, "sampled_count": len(items), "shot_starts": [items[i]["frame"] for i in cuts], "frames": records}
    save_json(manifest_path, manifest)
    return folder, manifest


def image_url(path: Path):
    with Image.open(path) as source:
        im = source.convert("RGB"); im.thumbnail((1024, 1024))
        b = io.BytesIO(); im.save(b, "JPEG", quality=78)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode("ascii")


def validate_report(raw, video_id, group):
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
        data = json.loads(cleaned)
        if not isinstance(data, dict) or any(k not in data for k in FIELDS):
            return None
        if data["granthstudio_capability"] not in {"V2_REUSE", "V2_EXTENSION", "V3_ACTION", "NEW_ARTWORK", "UNKNOWN"}:
            return None
        if str(data["video_id"]) != video_id:
            return None
        if str(data["scene_id"]) != group["id"]:
            return None
        allowed = {f["frame"] for f in group["frames"]}
        if not isinstance(data["evidence_frames"], list) or any((not isinstance(f, int)) or f not in allowed for f in data["evidence_frames"]):
            return None
        return data
    except (ValueError, TypeError):
        return None


def mark_reviewed(folder, group_id):
    path = folder / "frame_selection_manifest.json"
    selection = read_json(path, {})
    if group_id == "pilot_storyboard":
        selection["storyboard_status"] = "PILOT_REVIEWED"
    elif group_id == "pilot_action" and selection.get("events"):
        selection["events"][0]["status"] = "PILOT_REVIEWED"
    else:
        for event in selection.get("events", []):
            if event["event_id"] == group_id:
                event["status"] = "REVIEWED"
    save_json(path, selection)


def repair_saved_invalid(pending, scheduler):
    """Use one text-only repair for saved malformed JSON before resending images."""
    image_jobs = []
    for folder, manifest, state, group in pending:
        gid = group["id"]
        entry = state.get(gid, {})
        if entry.get("reason") != "INVALID_JSON":
            if entry.get("status") != "COMPLETE" and entry.get("reason") != "REPAIR_FAILED":
                image_jobs.append((folder, manifest, state, group))
            continue
        raw_path = folder / "raw_responses" / f"{gid}.txt"
        repair_path = folder / "raw_responses" / f"{gid}_repair.txt"
        current_frames = [f["frame"] for f in group["frames"]]
        if entry.get("frames") != current_frames or not raw_path.exists():
            entry.update({"status": "PENDING", "reason": "STALE_SELECTION", "frames": current_frames})
            save_json(folder / "api_log.json", state)
            image_jobs.append((folder, manifest, state, group))
            continue
        if repair_path.exists():
            report = validate_report(repair_path.read_text(encoding="utf-8"), manifest["video_id"], group)
            entry.update({"status": "COMPLETE" if report else "PENDING", "reason": None if report else "REPAIR_FAILED"})
            if report:
                entry["report"] = report
                mark_reviewed(folder, gid)
            save_json(folder / "api_log.json", state)
            continue
        if scheduler.calls >= scheduler.max_calls:
            continue
        raw = raw_path.read_text(encoding="utf-8")
        prompt = f"Repair this malformed JSON. Preserve only stated observations; use UNKNOWN for missing fields. Return valid JSON only with all required fields. video_id={manifest['video_id']}; scene_id={gid}; allowed evidence frames={current_frames}. Original:\n{raw}"
        repair = scheduler.call([{"type": "text", "text": prompt}], max_tokens=4000)
        text = repair.get("text") or ""
        if repair.get("status") == "OK" and text.strip():
            repair_path.write_text(text, encoding="utf-8")
            report = validate_report(text, manifest["video_id"], group)
            entry.update({"status": "COMPLETE" if report else "PENDING", "reason": None if report else "REPAIR_FAILED", "repair_usage": repair.get("usage")})
            if report:
                entry["report"] = report
                mark_reviewed(folder, gid)
        else:
            entry["repair_error"] = repair.get("status")
        save_json(folder / "api_log.json", state)
    return image_jobs


def content_for(folder, manifest, group):
    labels = ", ".join(f"frame {f['frame']} at {f['time'] if f['time'] is not None else 'UNKNOWN'} sec" for f in group["frames"])
    content = [{"type": "text", "text": INSTRUCTION + f"\nvideo_id={manifest['video_id']}; scene_id={group['id']}; provided frames: {labels}. Frame numbers refer to the original video or ordered image sequence. If time is UNKNOWN, keep it null. Only cite these frame numbers. Return only valid JSON without Markdown. evidence_frames must be a list of the provided integer frame numbers; do not add unprovided frames. In this pilot, report at most two significant observations. Keep each field concise, usually one sentence."}]
    if group.get("sheet"):
        content[0]["text"] += " This is a labeled chronological storyboard. Report only changes supported by its thumbnails; precise limb timing is UNKNOWN."
        content.append({"type": "image_url", "image_url": {"url": image_url(folder / group["sheet"])}})
        return content
    for f in group["frames"]:
        content.append({"type": "text", "text": f"Frame {f['frame']}; timestamp {f['time'] if f['time'] is not None else 'UNKNOWN'} sec"})
        content.append({"type": "image_url", "image_url": {"url": image_url(folder / "selected_frames" / f["file"])}})
    return content


def write_reports(output, entries, failures=None, skipped=None):
    techniques = defaultdict(list)
    failures, skipped = failures or [], skipped or []
    master = ["# Animation research master report", "", f"Unique sources discovered: {len(entries)}", "", "## Videos processed", ""]
    characters, cinematography, gaps, actions, artwork, uncertainty = [], [], [], [], [], []
    for folder, manifest, state in entries:
        reports = [v["report"] for v in state.values() if v.get("status") == "COMPLETE"]
        pending = [k for k, v in state.items() if v.get("status") != "COMPLETE"]
        save_json(folder / "scene_analysis.json", {"video_id": manifest["video_id"], "scenes": reports, "pending": pending})
        with (folder / "animation_events.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["scene_id", "start_frame", "end_frame", "start_time", "end_time", "observed_animation", "inferred_technique", "granthstudio_capability", "evidence_frames"])
            writer.writeheader()
            for r in reports:
                writer.writerow({k: json.dumps(r[k], ensure_ascii=False) if isinstance(r[k], (list, dict)) else r[k] for k in writer.fieldnames})
        lines = [f"# {manifest['video_id']}", "", f"Source: {manifest['source']}", f"Selected frames: {len(manifest['frames'])}; status: {len(reports)} complete, {len(pending)} pending", ""]
        for r in reports:
            lines += [f"## {r['scene_id']} ({r['granthstudio_capability']})", "", f"Observed: {r['observed_animation']}", "", f"Inferred: {r['inferred_technique']}", "", f"Proposed Blender implementation: {r['potential_blender_implementation']}", "", f"Evidence frames: {r['evidence_frames']}", "", f"Uncertainties: {r['uncertainties']}", ""]
            technique = str(r["inferred_technique"])
            techniques[technique].append({"video_id": manifest["video_id"], "scene_id": r["scene_id"], "frames": r["evidence_frames"], "capability": r["granthstudio_capability"]})
            ref = f"{manifest['video_id']} {r['scene_id']} frames {r['evidence_frames']}"
            if r["character_motion"] not in (None, "UNKNOWN", [], ""):
                characters.append(f"- {ref}: {r['character_motion']}")
            if r["camera_motion"] not in (None, "UNKNOWN", [], "") or r["visual_effects"] not in (None, "UNKNOWN", [], ""):
                cinematography.append(f"- {ref}: camera {r['camera_motion']}; effects {r['visual_effects']}")
            if r["granthstudio_capability"] in ("V2_EXTENSION", "V3_ACTION", "NEW_ARTWORK"):
                gaps.append(f"- {ref}: {r['granthstudio_capability']} (proposed; engine capability unverified)")
            if r["potential_blender_implementation"] not in (None, "UNKNOWN", [], ""):
                actions.append(f"- {ref}: {r['potential_blender_implementation']}")
            if r["required_assets"] not in (None, "UNKNOWN", [], ""):
                artwork.append(f"- {ref}: {r['required_assets']}")
            if r["uncertainties"] not in (None, "UNKNOWN", [], ""):
                uncertainty.append(f"- {ref}: {r['uncertainties']}")
        (folder / "animation_review.md").write_text("\n".join(lines), encoding="utf-8")
        master += [f"## {manifest['video_id']}", "", f"Source: {manifest['source']}", f"Selected frames: {len(manifest['frames'])}; reviewed: {len(reports)}; pending: {len(pending)}", ""]
    master += ["## Techniques and evidence", ""]
    for technique, examples in techniques.items():
        master += [f"### {technique}", ""] + [f"- {e['video_id']} {e['scene_id']} frames {e['frames']} ({e['capability']})" for e in examples] + [""]
    for heading, lines in [("Character animation methods", characters), ("Cinematography and visual effects", cinematography), ("GranthStudio capability gaps", gaps), ("Candidate reusable Blender actions", actions), ("Artwork and rig requirements", artwork), ("Uncertainty and missing evidence", uncertainty)]:
        master += [f"## {heading}", ""] + (lines or ["PENDING or UNKNOWN until reviewed."]) + [""]
    master += ["## Failed or skipped sources", ""] + [f"- {x['source']}: {x['error']}" for x in failures + skipped] + (["None."] if not failures and not skipped else []) + [""]
    master += ["PENDING segments require review. V2 classifications are hypotheses, not implementation claims.", ""]
    (output / "MASTER_REPORT.md").write_text("\n".join(master), encoding="utf-8")
    save_json(output / "MASTER_TECHNIQUES.json", dict(techniques))


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--url", action="append", default=[], help="Public Instagram Reel URL; queued unless --download-links is set")
    p.add_argument("--urls-file", type=Path, help="File of public Instagram Reel URLs")
    p.add_argument("--download-links", action="store_true", help="Download supplied public links before research")
    p.add_argument("--output", type=Path, required=True)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--extract-only", action="store_true")
    mode.add_argument("--review", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--max-api-calls", type=int, default=20)
    p.add_argument("--target-per-30", type=int, default=18)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--mode", choices=("pilot", "full"), default="pilot")
    p.add_argument("--per-key-limit", type=int, default=10)
    p.add_argument("--global-limit", type=int, default=10)
    p.add_argument("--window-seconds", type=int, default=60)
    p.add_argument("--smoke-only", action="store_true")
    args = p.parse_args(argv)
    if not args.input.exists() or args.max_api_calls < 0 or args.target_per_30 < 1:
        p.error("Input path must exist and numeric limits must be nonnegative")
    urls = read_urls(args.url, args.urls_file)
    if urls:
        if not args.input.is_dir():
            p.error("Instagram imports require an input directory")
        imported = import_reels(urls, args.input, run=args.download_links and not args.dry_run)
        print(json.dumps({"instagram_import": imported}, indent=2))
        if not args.download_links or args.dry_run:
            return
    args.output.mkdir(parents=True, exist_ok=True)
    sources = discover(args.input)
    entries, failures, selections = [], [], []
    seen_video_hashes = {}
    skipped = []
    for pth in sorted(p for p in args.input.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXT):
        h = digest_file(pth)
        if h in seen_video_hashes:
            skipped.append({"source": str(pth), "error": f"Byte-identical duplicate of {seen_video_hashes[h]}"})
        else:
            seen_video_hashes[h] = str(pth)
    for source in sources:
        try:
            folder, manifest = prepare(source, args.input if args.input.is_dir() else args.input.parent, args.output, args.target_per_30, refresh=args.extract_only and not args.resume)
            cached_selection = read_json(folder / "frame_selection_manifest.json", {}) if args.resume else {}
            local_count = sum(1 for _ in (folder / "selected_frames").glob("frame_*.jpg"))
            selection = cached_selection if cached_selection.get("selection_version") == 3 and cached_selection.get("local_frames_analyzed") == local_count and (folder / "storyboard_api.jpg").exists() else build_selection(folder, manifest)
            selections.append(selection)
            frame_lookup = {f["frame"]: f for f in selection["local_frame_index"]}
            overview_numbers = [f["original_frame_number"] for f in selection["selected_frames"] if "OVERVIEW" in f["selection_track"]]
            action_numbers = selection["primary_action_frames"]
            def make_group(group_id, numbers, sheet=None):
                return {"id": group_id, "shot": 0, "frames": [frame_lookup[n] for n in numbers], "sheet": sheet}
            groups = [make_group("pilot_storyboard", overview_numbers, selection["api_storyboard_sheet"]), make_group("pilot_action", action_numbers)]
            if args.mode == "full":
                groups = []
                by_shot = defaultdict(list)
                for f in selection["local_frame_index"]:
                    by_shot[f["shot"]].append(f["frame"])
                for shot, nums in by_shot.items():
                    picks = sorted({nums[0], nums[len(nums) // 2], nums[-1]})
                    groups.append(make_group(f"shot_{shot:03d}", picks))
                for event in selection["events"]:
                    groups.append(make_group(event["event_id"], event["burst_frames"]))
            current_ids = {g["id"] for g in groups}
            old_state = read_json(folder / "api_log.json", {}) if args.resume else {}
            state = {k: v for k, v in old_state.items() if k in current_ids or (args.mode == "full" and k.startswith("pilot_"))}
            for g in groups:
                state.setdefault(g["id"], {"status": "PENDING", "frames": [f["frame"] for f in g["frames"]]})
            save_json(folder / "api_log.json", state)
            entries.append((folder, manifest, state, groups))
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            failures.append({"source": str(source.path), "error": f"{type(e).__name__}: {e}"})
    pending = [(folder, manifest, state, g) for folder, manifest, state, groups in entries for g in groups if state[g["id"]]["status"] != "COMPLETE"]
    cached_smoke = read_json(args.output / "VISION_SMOKE.json", {}) if args.resume else {}
    cached_multi = read_json(args.output / "MULTI_IMAGE_PROBE.json", {}) if args.resume else {}
    probes_needed = (0 if cached_smoke.get("status") == "OK" and cached_smoke.get("response") else 1) + (0 if "multi_image_supported" in cached_multi else 1)
    plan = {"before": {"selected_frames": 1365, "groups": 481}, "files_seen": len(sources) + len(skipped), "unique_sources_discovered": len(sources), "sources_prepared": len(entries), "failed": failures, "skipped": skipped, "local_frames_retained": sum(s["local_frames_analyzed"] for s in selections), "overview_frames_selected": sum(s["overview_frames"] for s in selections), "action_burst_frames_selected": sum(s["action_burst_frames"] for s in selections), "unique_frames_selected_for_api": sum(s["unique_frames_selected_for_api"] for s in selections), "storyboard_calls": sum(s["storyboard_calls"] for s in selections), "detailed_review_calls": sum(s["action_calls"] for s in selections), "pending_groups": len(pending), "estimated_total_calls_with_two_probes": len(pending) + (2 if pending else 0), "planned_requests_this_run": min(args.max_api_calls, len(pending) + (probes_needed if pending else 0)), "unreviewed_events": sum(max(0, len(s["events"]) - 1) for s in selections), "coverage_by_video": [{"video_id": s["video_id"], "local_frames": s["local_frames_analyzed"], "overview_frames": s["overview_frames"], "action_frames": s["action_burst_frames"], "events_pending_after_pilot": max(0, len(s["events"]) - 1)} for s in selections], "model": MODEL}
    save_json(args.output / "RUN_PLAN.json", plan)
    print(json.dumps(plan, indent=2))
    if args.mode == "full" and args.review and not args.dry_run:
        if any(not all(state.get(k, {}).get("status") == "COMPLETE" for k in ("pilot_storyboard", "pilot_action")) for _, _, state, _ in entries):
            raise SystemExit("Full review requires validated, completed pilot reviews for every video.")
    if args.review and not args.dry_run and pending and args.max_api_calls:
        keys = load_env_keys(Path(__file__).with_name(".env"))
        scheduler = NvidiaScheduler(keys, reasoning_effort="low", per_key_limit=args.per_key_limit, global_limit=args.global_limit, window_seconds=args.window_seconds, workers=args.workers, max_calls=args.max_api_calls)
        smoke = {"status": "OK", "text": cached_smoke["response"]} if cached_smoke.get("status") == "OK" and cached_smoke.get("response") else None
        if smoke is None:
            first_action = next((item for item in pending if item[3]["id"] == "pilot_action"), pending[0])
            probe_frame = first_action[3]["frames"][0]
            probe_content = [{"type": "text", "text": f"This is frame {probe_frame['frame']} of an animation. Name one visible object in one sentence."}, {"type": "image_url", "image_url": {"url": image_url(first_action[0] / "selected_frames" / probe_frame["file"])}}]
            smoke = scheduler.call(probe_content, max_tokens=1000)
            save_json(args.output / "VISION_SMOKE.json", {k: v for k, v in smoke.items() if k != "text"} | {"response": smoke["text"]})
        if smoke["status"] != "OK" or not smoke["text"].strip():
            raise SystemExit("Real image-input smoke test failed. No batch started.")
        multi_group = next((item for item in pending if len(item[3]["frames"]) >= 2 and not item[3].get("sheet")), None)
        multi_ok = bool(cached_multi.get("multi_image_supported"))
        if "multi_image_supported" not in cached_multi and scheduler.calls < scheduler.max_calls and multi_group:
            probe_frames = multi_group[3]["frames"][:3]
            multi_content = [{"type": "text", "text": "These are three ordered animation frames. Briefly describe one visible change between them, or say UNKNOWN."}]
            for f in probe_frames:
                multi_content += [{"type": "text", "text": f"Frame {f['frame']} at {f['time']} seconds"}, {"type": "image_url", "image_url": {"url": image_url(multi_group[0] / "selected_frames" / f["file"])}}]
            multi = scheduler.call(multi_content, max_tokens=1000)
            multi_ok = multi["status"] == "OK" and bool(multi["text"].strip())
            save_json(args.output / "MULTI_IMAGE_PROBE.json", {k: v for k, v in multi.items() if k != "text"} | {"response": multi["text"], "multi_image_supported": multi_ok})
        if args.smoke_only:
            print(json.dumps({"smoke": smoke["status"], "multi_image_supported": multi_ok, **scheduler.snapshot()}, indent=2))
            write_reports(args.output, [(f, m, s) for f, m, s, _ in entries], failures, skipped)
            return
        pending = repair_saved_invalid(pending, scheduler)
        if not multi_ok:
            singles = []
            for folder, manifest, state, group in pending:
                if group.get("sheet"):
                    singles.append((folder, manifest, state, group)); continue
                state.pop(group["id"], None)
                for frame in group["frames"]:
                    one = {"id": f"{group['id']}_frame{frame['frame']}", "shot": group["shot"], "frames": [frame]}
                    state.setdefault(one["id"], {"status": "PENDING", "frames": [frame["frame"]], "temporal_interpretation": "LIMITED_SINGLE_IMAGE"})
                    if state[one["id"]]["status"] != "COMPLETE":
                        singles.append((folder, manifest, state, one))
                save_json(folder / "api_log.json", state)
            pending = singles
        jobs = [{"item": item, "content": content_for(item[0], item[1], item[3]), "max_tokens": 4000 if args.mode == "pilot" else 5000} for item in pending]
        checkpoint_lock = Lock()
        def on_result(job, result, snapshot):
            folder, manifest, state, group = job["item"]
            with checkpoint_lock:
                raw_dir = folder / "raw_responses"; raw_dir.mkdir(exist_ok=True)
                (raw_dir / f"{group['id']}.txt").write_text(result["text"], encoding="utf-8")
                report = validate_report(result["text"], manifest["video_id"], group)
                state[group["id"]] = {"status": "COMPLETE" if report else "PENDING", "reason": None if report else "INVALID_JSON" if result["status"] == "OK" and result["text"] else "EMPTY_RESPONSE" if result["status"] == "OK" else result["status"], "key_index": result.get("key_index"), "latency_sec": result.get("latency_sec"), "usage": result.get("usage"), "error": result.get("error"), "frames": [f["frame"] for f in group["frames"]]}
                if report:
                    state[group["id"]]["report"] = report
                save_json(folder / "api_log.json", state)
                if report:
                    mark_reviewed(folder, group["id"])
                completed_videos = sum(all(v.get("status") == "COMPLETE" for k, v in s.items() if k.startswith("pilot_")) for _, _, s, _ in entries)
                print(json.dumps({"total_videos": len(entries), "completed_videos": completed_videos, "frames_analyzed_locally": plan["local_frames_retained"], "completed_api_requests": snapshot["completed_api_requests"], "pending_requests": sum(v.get("status") != "COMPLETE" for _, _, s, _ in entries for v in s.values()), "available_keys": snapshot["available_keys"], "cooling_keys": snapshot["cooling_keys"], "next_eligible_seconds": snapshot["next_eligible_seconds"], "retries": snapshot["retries"], "errors": snapshot["errors"], "token_usage": result.get("usage")}, ensure_ascii=False))
        scheduler.run_jobs(jobs, on_result)
    write_reports(args.output, [(f, m, s) for f, m, s, _ in entries], failures, skipped)
    if not args.dry_run:
        analyses = [analyze_source(Path(m["source"]), m["kind"], m, selection, folder) for (folder, m, _, _), selection in zip(entries, selections)]
        write_knowledge(args.output, analyses)
    if failures:
        save_json(args.output / "FAILED_SOURCES.json", failures)


if __name__ == "__main__":
    main()
