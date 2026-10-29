"""Evidence accounting and audio timing for cinematic reference research.

Frame selection stays in frame_selection.py; this module only interprets saved
manifests and reviews. No model calls occur here.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

def _json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default

def _save(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)

def _brief(values):
    return "; ".join(str(value) for value in values) if values else "UNKNOWN"

def _audio(source, manifest, folder):
    if manifest.get("kind") != "video":
        return {"status": "UNAVAILABLE", "reason": "image sequence has no supplied audio", "transcript": "UNVERIFIED", "sound_classes": "UNKNOWN", "low_volume_intervals": []}
    try:
        probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "json", str(source)], capture_output=True, text=True, timeout=30)
        if probe.returncode:
            raise ValueError("ffprobe audio inspection failed")
        streams = json.loads(probe.stdout).get("streams", [])
        if not streams:
            return {"status": "NO_AUDIO_STREAM", "transcript": "UNAVAILABLE", "sound_classes": "UNAVAILABLE", "low_volume_intervals": []}
        wav = folder / "audio_analysis.wav"
        signature = {"identity": manifest.get("identity"), "source_size": source.stat().st_size, "source_mtime_ns": source.stat().st_mtime_ns}
        stamp = folder / "audio_analysis_source.json"
        if not wav.is_file() or _json(stamp, {}) != signature:
            tmp = folder / "audio_analysis.tmp.wav"
            duration = float(manifest.get("metadata", {}).get("duration") or 0)
            run = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(source), "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(tmp)], capture_output=True, timeout=min(1800, max(120, int(duration * 3))))
            if run.returncode or not tmp.is_file() or tmp.stat().st_size < 44:
                tmp.unlink(missing_ok=True)
                raise ValueError("audio extraction failed")
            tmp.replace(wav)
            _save(stamp, signature)
        duration = float(manifest.get("metadata", {}).get("duration") or 0)
        run = subprocess.run(["ffmpeg", "-v", "info", "-i", str(wav), "-af", "silencedetect=noise=-35dB:d=0.35", "-f", "null", "-"], capture_output=True, text=True, timeout=min(1800, max(120, int(duration * 3))))
        if run.returncode:
            raise ValueError("silence detection failed")
        intervals, start = [], None
        for line in run.stderr.splitlines():
            match = re.search(r"silence_start:\s*([0-9.]+)", line)
            if match:
                start = float(match.group(1))
            match = re.search(r"silence_end:\s*([0-9.]+)", line)
            if match and start is not None:
                end = float(match.group(1))
                intervals.append({"start": start, "end": end, "duration": round(end - start, 3), "meaning": "LOW_VOLUME_ONLY"})
                start = None
        if start is not None and duration > start:
            intervals.append({"start": start, "end": duration, "duration": round(duration - start, 3), "meaning": "LOW_VOLUME_ONLY"})
        return {"status": "EXTRACTED", "analysis_audio": str(wav), "source_audio_preserved_in": str(source), "transcript": "UNVERIFIED", "sound_classes": "UNKNOWN", "low_volume_intervals": intervals}
    except (OSError, ValueError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        return {"status": "ERROR", "reason": f"{type(exc).__name__}: {exc}", "transcript": "UNVERIFIED", "sound_classes": "UNKNOWN", "low_volume_intervals": []}

def _time(frame, frame_times, fps):
    if frame in frame_times and frame_times[frame] is not None:
        return {"seconds": frame_times[frame], "basis": "SAMPLED_PTS"}
    if fps:
        return {"seconds": round(frame / fps, 3), "basis": "FPS_ESTIMATE"}
    return {"seconds": None, "basis": "UNKNOWN"}

def analyze_source(source_path: Path, kind: str, manifest: dict, selection: dict, folder: Path) -> dict:
    """Build shot beats and an exact disposition for every motion candidate."""
    state = _json(folder / "api_log.json", {})
    index = selection.get("local_frame_index", [])
    frame_times = {f["frame"]: f.get("time") for f in index}
    fps = manifest.get("metadata", {}).get("fps")
    max_frame = max((f["frame"] for f in index), default=0)
    starts = sorted(set(manifest.get("shot_starts", []) or [0]))
    beats = []
    video_id = manifest.get("video_id")
    for pos, start in enumerate(starts):
        end = starts[pos + 1] - 1 if pos + 1 < len(starts) else max_frame
        shot = pos + 1
        group = f"shot_{shot:03d}"
        entry = state.get(group, {})
        report = entry.get("report", {}) if entry.get("status") == "COMPLETE" else {}
        evidence = [f for f in report.get("evidence_frames", []) if isinstance(f, int) and start <= f <= end]
        beats.append({
            "video_id": video_id, "beat_id": f"{video_id}:shot_{shot:03d}", "shot": shot,
            "start_frame": start, "end_frame": end,
            "start_time": _time(start, frame_times, fps), "end_time": _time(end, frame_times, fps),
            "review_status": "REVIEWED" if report else "PENDING_REVIEW",
            "purpose": "UNKNOWN", "shot_scale": "UNKNOWN", "angle": "UNKNOWN",
            "composition": "UNKNOWN", "lighting": "UNKNOWN", "transition": "UNKNOWN",
            "observed": report.get("observed_animation", "UNKNOWN"),
            "camera_motion": report.get("camera_motion", "UNKNOWN"),
            "character_motion": report.get("character_motion", "UNKNOWN"),
            "inferred_method": report.get("inferred_technique", "UNKNOWN"),
            "artwork_needed": report.get("required_assets", "UNKNOWN"),
            "sound_relationship": "UNKNOWN", "evidence_frames": evidence,
            "uncertainty": report.get("uncertainties", "Shot has not received a dedicated review"),
        })
    events = []
    for candidate in selection.get("events", []):
        event_id = candidate["event_id"]
        entry = state.get(event_id, {})
        reviewed = entry.get("status") == "COMPLETE" and bool(entry.get("report"))
        start, end = candidate["start_frame"], candidate["end_frame"]
        events.append({
            "video_id": video_id, "event_id": event_id, "shot": candidate.get("shot_id"),
            "start_frame": start, "end_frame": end,
            "start_time": _time(start, frame_times, fps), "end_time": _time(end, frame_times, fps),
            "score": candidate.get("score"), "uncertain": candidate.get("uncertain"),
            "burst_frames": candidate.get("burst_frames", []),
            "disposition": "REVIEWED" if reviewed else "PENDING_REVIEW",
            "report_id": event_id if reviewed else None,
        })
    # Metadata clusters are prioritization hints; every member retains its own disposition.
    clusters = defaultdict(list)
    for event in events:
        score = event["score"] or 0
        key = (event["shot"], "high" if score >= .7 else "medium" if score >= .4 else "low", bool(event["uncertain"]))
        clusters[key].append(event["event_id"])
    result = {
        "video_id": video_id, "source": str(source_path), "audio": _audio(source_path, manifest, folder),
        "beats": beats, "events": events,
        "candidate_clusters": [{"basis": {"shot": key[0], "score_band": key[1], "uncertain": key[2]}, "representative": ids[0], "members": ids} for key, ids in clusters.items()],
        "pilot_context": [state[k]["report"] for k in ("pilot_storyboard", "pilot_action") if state.get(k, {}).get("status") == "COMPLETE" and state[k].get("report")],
    }
    _save(folder / "cinematic_analysis.json", result)
    return result

def write_knowledge(output: Path, analyses: list[dict]) -> None:
    """Append a replaceable evidence section and preserve the prior technique map."""
    report_path = output / "MASTER_REPORT.md"
    tech_path = output / "MASTER_TECHNIQUES.json"
    playbook_path = output / "KIMI_ANIMATION_PLAYBOOK.md"
    existing = _json(tech_path, {})
    if not isinstance(existing, dict):
        existing = {}
    patterns = defaultdict(lambda: {"evidence": [], "observed": [], "inferred": [], "required_artwork": [], "capability_hypotheses": []})
    for analysis in analyses:
        for item in analysis.get("pilot_context", []):
            method = str(item.get("inferred_technique") or "UNKNOWN").strip()
            if method == "UNKNOWN":
                continue
            key = re.sub(r"\s+", " ", method.lower())[:160]
            pattern = patterns[key]
            pattern["evidence"].append({"video_id": analysis["video_id"], "scene_id": item.get("scene_id"), "frames": item.get("evidence_frames", []), "start_time": item.get("start_time"), "end_time": item.get("end_time"), "review_scope": "PILOT_CONTEXT"})
            for dest, source in (("observed", "observed_animation"), ("inferred", "inferred_technique"), ("required_artwork", "required_assets"), ("capability_hypotheses", "granthstudio_capability")):
                value = item.get(source)
                if value and value != "UNKNOWN" and value not in pattern[dest]:
                    pattern[dest].append(value)
    recipes = []
    for key, values in patterns.items():
        recipes.append({
            "pattern": key, **values, "verification": "PILOT_HYPOTHESIS",
            "purpose": "UNKNOWN", "sound_relation": "UNKNOWN",
            "applicability": "Check against approved 16:9 story beat, artwork and sound palette.",
            "counterexample": "Avoid when it adds motion without clarifying an approved beat or breaks visual continuity.",
            "stage1": "Choose shot purpose and framing from the approved scene; use observed method only if it helps that beat.",
            "stage2": "Check the actual preset roles and approved images. Use NEED_NEW for missing image, JSON arrangement or renderer capability; never invent a preset.",
        })
    existing["_cinematic_recipes"] = recipes
    _save(tech_path, existing)
    beginning = "<!-- CINEMATIC_RESEARCH_START -->"
    ending = "<!-- CINEMATIC_RESEARCH_END -->"
    old = report_path.read_text(encoding="utf-8") if report_path.is_file() else "# Animation research master report\n"
    if beginning in old and ending in old:
        old = old.split(beginning)[0].rstrip() + "\n" + old.split(ending, 1)[1].lstrip()
    lines = [beginning, "## Cinematic beats and sound evidence", ""]
    for analysis in analyses:
        audio = analysis["audio"]
        reviewed = sum(e["disposition"] == "REVIEWED" for e in analysis["events"])
        lines += [f"### {analysis['video_id']}", "", f"Source: {analysis['source']}", f"Audio: {audio['status']}; speech/music/SFX: {audio['sound_classes']}; transcript: {audio['transcript']}", f"Low-volume intervals: {len(audio['low_volume_intervals'])} (not proof of intentional silence or speech pause)", f"Shots: {len(analysis['beats'])}; motion candidates: {len(analysis['events'])}; directly reviewed: {reviewed}", ""]
        for beat in analysis["beats"]:
            lines.append(f"- {beat['beat_id']} frames {beat['start_frame']}–{beat['end_frame']}, {beat['start_time']['seconds']}–{beat['end_time']['seconds']}s: {beat['review_status']}; observed {beat['observed']}; inferred {beat['inferred_method']}")
    lines += ["", "Unreviewed shots and events are pending evidence. Pilot context does not complete their review.", ending, ""]
    report_path.write_text(old.rstrip() + "\n\n" + "\n".join(lines), encoding="utf-8")
    pb = ["# Kimi animation research playbook", "", "Read-only research hints. Approved source and canon control story facts; code controls timing and audio. Keep the existing Stage 1 and Stage 2 JSON schemas.", "", "## Stage 1 direction", "", "- Choose an establishing, reveal, emphasis, reaction or resolution shot only when the approved beat warrants it. Record pose, gaze, screen geography and framing in the existing shot and image brief fields.", "- Adapt vertical reel compositions to the 16:9 film and its longer pacing. Do not copy a reel's speed or dramatic cue by default.", "- Treat detected low volume as an audio measurement. Narration, music, SFX and intentional silence require separate listening or transcription evidence.", "", "## Stage 2 execution", "", "- Use only real preset IDs and their required image roles. Match approved catalog images to roles and use a held pose where sufficient.", "- Use NEED_NEW with the actual missing_image, json_arrangement or renderer_gap reason when existing assets or presets cannot execute the shot.", "- A saved Stage 2 result remains cached; research does not silently invalidate it.", "", "## Candidate recipes", ""]
    if not recipes:
        pb.append("No verified recipe yet. Pilot reviews have not established shot-level execution.")
    for recipe in recipes:
        refs = ", ".join(f"{e['video_id']} {e['scene_id']} frames {e['frames']}" for e in recipe["evidence"])
        pb += [f"### {recipe['pattern']}", "", f"Status: {recipe['verification']}", f"Observed: {_brief(recipe['observed'])}", f"Inferred method: {_brief(recipe['inferred'])}", f"Artwork: {_brief(recipe['required_artwork'])}", f"Stage 1: {recipe['stage1']}", f"Stage 2: {recipe['stage2']}", f"Use when: {recipe['applicability']}", f"Avoid when: {recipe['counterexample']}", f"Evidence: {refs}", ""]
    playbook_path.write_text("\n".join(pb), encoding="utf-8")
