"""Audio extraction and energy analysis utilities.

Pure stdlib + numpy. No ML dependencies.
"""
from __future__ import annotations

import os
import wave
from typing import Callable

import numpy as np


def extract_audio(
    source: str,
    wav_path: str,
    ffmpeg_runner: Callable[[list[str]], dict],
    get_source_size_mtime: Callable[[str], dict],
    cache_get: Callable[[str], dict | None],
    cache_set: Callable[[str, dict], None],
) -> dict:
    """Extract audio from a video source to a 16 kHz mono WAV file.

    Args:
        source: Path to video file, image sequence directory, or ZIP archive.
        wav_path: Output path for the WAV file.
        ffmpeg_runner: Callable that runs an ffmpeg command and returns a status dict.
        get_source_size_mtime: Callable returning size and mtime of the source.
        cache_get: Callable to retrieve a cached entry by key.
        cache_set: Callable to store a cache entry.

    Returns:
        A dict with keys: status, wav_path, from_cache (and optionally reason).
    """
    cache_key = f"extract_audio:{source}:{wav_path}"

    # Detect source kind: ZIP or image sequence directory BEFORE existence check
    # (so unavailable sources are caught even if they don't exist)
    if source.lower().endswith(".zip"):
        return {"status": "UNAVAILABLE"}

    # Check for directory (including trailing separator for nonexistent paths)
    # Check both forward slash and backslash as trailing separators
    is_dir = os.path.isdir(source) or source.endswith("/") or source.endswith("\\")
    if is_dir:
        image_exts = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".dpx", ".exr"}
        try:
            entries = os.listdir(source)
            # Empty directory or all image files -> UNAVAILABLE
            all_images = all(
                any(entry.lower().endswith(ext) for ext in image_exts)
                for entry in entries
            )
            if all_images:
                return {"status": "UNAVAILABLE"}
        except OSError:
            # Not a directory or unreadable; but if path ends with separator, treat as image sequence dir
            if source.endswith("/") or source.endswith("\\"):
                return {"status": "UNAVAILABLE"}
            pass  # proceed to ffmpeg

    # Check source exists and get size/mtime
    source_info = get_source_size_mtime(source)
    if source_info.get("status") == "NOT_FOUND":
        return {"status": "ERROR", "reason": "source not found"}

    # Check cache AFTER source-kind detection
    cached = cache_get(cache_key)
    if cached is not None:
        if cached.get("source_size") == source_info.get("size") and cached.get("source_mtime") == source_info.get("mtime"):
            return {"status": "OK", "wav_path": wav_path, "from_cache": True}

    # Run ffmpeg to extract audio
    cmd = [
        "ffmpeg",
        "-i", source,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        wav_path,
    ]
    result = ffmpeg_runner(cmd)
    if result.get("status") != "OK":
        stderr = (result.get("stderr") or "").lower()
        if "no audio stream" in stderr or "does not contain any stream" in stderr:
            return {"status": "NO_AUDIO_STREAM"}
        return {"status": "ERROR", "reason": result.get("stderr") or "ffmpeg failed"}

    # Verify output WAV has frames
    try:
        with wave.open(wav_path, "rb") as wf:
            nframes = wf.getnframes()
            if nframes == 0:
                return {"status": "NO_AUDIO_STREAM"}
    except wave.Error:
        return {"status": "ERROR", "reason": "invalid wav format"}
    except FileNotFoundError:
        return {"status": "ERROR", "reason": "output wav not found"}

    # Cache success
    cache_set(cache_key, {
        "wav_path": wav_path,
        "source_size": source_info.get("size"),
        "source_mtime": source_info.get("mtime"),
    })
    return {"status": "OK", "wav_path": wav_path, "from_cache": False}


def energy_profile(
    wav_path: str,
    win: float = 0.05,
    wave_open: Callable = wave.open,
    np_array: Callable = np.array,
    np_sqrt: Callable = np.sqrt,
    np_mean: Callable = np.mean,
    np_log10: Callable = np.log10,
) -> dict:
    """Compute RMS energy profile in dB for a 16 kHz mono WAV.

    Args:
        wav_path: Path to the WAV file.
        win: Window size in seconds.
        wave_open: Callable to open WAV file (default: wave.open).
        np_array: Callable to create numpy array (default: numpy.array).
        np_sqrt: Callable for sqrt (default: numpy.sqrt).
        np_mean: Callable for mean (default: numpy.mean).
        np_log10: Callable for log10 (default: numpy.log10).

    Returns:
        Dict with status, profile (list of {time, db}), sample_rate, window_sec.
    """
    with wave_open(wav_path, "rb") as wf:
        nframes = wf.getnframes()
        framerate = wf.getframerate()
        sampwidth = wf.getsampwidth()
        nchannels = wf.getnchannels()

        if sampwidth != 2 or nchannels != 1:
            return {"status": "ERROR", "reason": "expected 16-bit mono WAV"}

        frame_size = int(win * framerate)
        if frame_size <= 0:
            frame_size = 1

        raw = wf.readframes(nframes)
        samples = np_array(np.frombuffer(raw, dtype=np.int16), dtype=np.float64)

    profile = []
    num_windows = (len(samples) + frame_size - 1) // frame_size
    for i in range(num_windows):
        start = i * frame_size
        end = min(start + frame_size, len(samples))
        window_samples = samples[start:end]
        if len(window_samples) == 0:
            continue
        rms = np_sqrt(np_mean(window_samples ** 2))
        if rms == 0:
            db = -120.0
        else:
            db = 20.0 * np_log10(rms / 32768.0)
        centre_time = (start + end) / 2.0 / framerate
        profile.append({"time": centre_time, "db": db})

    return {
        "status": "OK",
        "profile": profile,
        "sample_rate": framerate,
        "window_sec": win,
    }


def find_silences(
    profile: list[dict],
    thresh_db: float = -35.0,
    min_dur: float = 0.35,
    win: float = 0.05,
) -> dict:
    """Find silence intervals from an energy profile.

    Args:
        profile: List of {time, db} dicts from energy_profile.
        thresh_db: Threshold in dB; windows with db <= thresh_db are silent.
        min_dur: Minimum duration in seconds for a silence region to be kept.
        win: Window size in seconds (default 0.05, same as energy_profile).

    Returns:
        Dict with status and list of silence intervals {start, end}.
    """
    if not profile:
        return {"status": "OK", "silences": []}

    # Step 1: Find all raw silent regions (contiguous windows with db <= thresh_db)
    raw_regions = []
    region_start_idx = None

    for i, point in enumerate(profile):
        if point["db"] <= thresh_db:
            if region_start_idx is None:
                region_start_idx = i
        else:
            if region_start_idx is not None:
                region_end_idx = i - 1
                start_time = profile[region_start_idx]["time"] - win / 2
                end_time = profile[region_end_idx]["time"] + win / 2
                raw_regions.append({"start": start_time, "end": end_time})
                region_start_idx = None

    if region_start_idx is not None:
        region_end_idx = len(profile) - 1
        start_time = profile[region_start_idx]["time"] - win / 2
        end_time = profile[region_end_idx]["time"] + win / 2
        raw_regions.append({"start": start_time, "end": end_time})

    # Step 2: Merge regions separated by < win (strictly less than one window)
    merged = []
    for s in raw_regions:
        if not merged:
            merged.append(s)
        else:
            last = merged[-1]
            if s["start"] - last["end"] < win - 1e-9:
                last["end"] = s["end"]
            else:
                merged.append(s)

    # Step 3: Filter by min_dur
    silences = []
    for s in merged:
        if s["end"] - s["start"] >= min_dur - 1e-9:
            # Clamp negative start times to 0.0
            if s["start"] < 0:
                s["start"] = 0.0
            silences.append(s)

    return {"status": "OK", "silences": silences}
