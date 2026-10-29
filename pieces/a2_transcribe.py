import copy
import os
from typing import Callable, Optional, List, Dict, Any


def transcribe(
    wav_path: str,
    language: Optional[str] = None,
    model_size: str = "small",
    runner: Optional[Callable[[str, Optional[str], str], Dict[str, Any]]] = None,
    import_faster_whisper: Callable[[], Any] = lambda: __import__("faster_whisper")
) -> Dict[str, Any]:
    """
    Transcribe audio using faster_whisper or a provided runner.
    Returns a dict with status, segments (with confidence flags), and language.
    """
    if runner is not None:
        result = runner(wav_path, language, model_size)
        # Deep-copy to avoid mutating caller's data
        result_copy = copy.deepcopy(result)
        # Add confidence flags to segments if missing (runner may not include them)
        if result_copy.get("status") == "OK" and "segments" in result_copy:
            for seg in result_copy["segments"]:
                if "confidence" not in seg:
                    avg_logprob = seg.get("avg_logprob", 0.0)
                    seg["confidence"] = "LOW_CONFIDENCE" if avg_logprob < -1.0 else "OK"
        return result_copy

    # Validate wav_path only when using real transcriber
    # Note: This check returns TRANSCRIBER_UNAVAILABLE for missing/empty files.
    # This behavior is not in the spec but prevents cryptic errors from faster_whisper.
    if not isinstance(wav_path, str) or not wav_path:
        return {"status": "TRANSCRIBER_UNAVAILABLE"}
    try:
        abs_path = os.path.abspath(wav_path)
        if not os.path.isfile(abs_path) or os.path.getsize(abs_path) == 0:
            return {"status": "TRANSCRIBER_UNAVAILABLE"}
    except OSError:
        return {"status": "TRANSCRIBER_UNAVAILABLE"}

    try:
        fw = import_faster_whisper()
    except ImportError:
        return {"status": "TRANSCRIBER_UNAVAILABLE"}

    try:
        model = fw.WhisperModel(model_size, device="cpu", compute_type="int8")
    except Exception:
        return {"status": "TRANSCRIBER_UNAVAILABLE"}

    try:
        segments_gen, info = model.transcribe(
            wav_path,
            language=language,
            beam_size=5,
            vad_filter=True
        )
    except Exception:
        return {"status": "TRANSCRIBER_UNAVAILABLE"}

    segments = []
    try:
        for seg in segments_gen:
            # Use a large negative finite default to preserve LOW_CONFIDENCE behavior
            # while avoiding -inf which is not valid strict JSON
            avg_logprob = getattr(seg, 'avg_logprob', -100.0)
            seg_dict = {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
                "avg_logprob": avg_logprob
            }
            if avg_logprob < -1.0:
                seg_dict["confidence"] = "LOW_CONFIDENCE"
            else:
                seg_dict["confidence"] = "OK"
            segments.append(seg_dict)
    except Exception:
        return {"status": "TRANSCRIBER_UNAVAILABLE"}

    detected_lang = getattr(info, "language", "unknown")

    return {
        "status": "OK",
        "segments": segments,
        "language": detected_lang
    }


def classify_gaps(
    silences: List[Dict[str, float]],
    speech_segments: List[Dict[str, float]]
) -> Dict[str, Any]:
    """
    Classify silence gaps based on surrounding speech segments.
    SPEECH_PAUSE requires silence duration < 1.0s (per worked example;
    spec prose says <=2.0s gaps on both sides, but example shows 1.5s
    silence with both gaps <=2.0s labeled INTENTIONAL_SILENCE_CANDIDATE).
    """
    gaps = []
    for sil in silences:
        sil_start = sil["start"]
        sil_end = sil["end"]
        sil_dur = sil_end - sil_start

        # Find previous speech segment (max end <= silence start)
        prev_seg = None
        for seg in speech_segments:
            if seg["end"] <= sil_start:
                if prev_seg is None or seg["end"] > prev_seg["end"]:
                    prev_seg = seg

        # Find next speech segment (min start >= silence end)
        next_seg = None
        for seg in speech_segments:
            if seg["start"] >= sil_end:
                if next_seg is None or seg["start"] < next_seg["start"]:
                    next_seg = seg

        # Check for overlapping speech
        has_overlap = any(
            seg["start"] < sil_end and seg["end"] > sil_start
            for seg in speech_segments
        )

        # Check SPEECH_PAUSE condition first (spec priority)
        if prev_seg and next_seg:
            gap_before = sil_start - prev_seg["end"]
            gap_after = next_seg["start"] - sil_end
            if gap_before <= 2.0 and gap_after <= 2.0 and sil_dur < 1.0:
                label = "SPEECH_PAUSE"
            elif sil_dur >= 1.0 and not has_overlap:
                label = "INTENTIONAL_SILENCE_CANDIDATE"
            else:
                label = "LOW_VOLUME_ONLY"
        else:
            # No both neighbors, check INTENTIONAL_SILENCE_CANDIDATE
            if sil_dur >= 1.0 and not has_overlap:
                label = "INTENTIONAL_SILENCE_CANDIDATE"
            else:
                label = "LOW_VOLUME_ONLY"

        gaps.append({"start": sil_start, "end": sil_end, "label": label})

    return {"status": "OK", "gaps": gaps}


def find_onsets(
    profile: List[Dict[str, float]],
    rise_db: float = 9.0,
    min_gap: float = 0.15
) -> Dict[str, Any]:
    """
    Detect sound onsets from an energy profile.
    Uses epsilon to avoid float precision issues at exact boundary.
    """
    onsets = []
    last_onset_time = -float("inf")
    eps = 1e-12

    for i in range(1, len(profile)):
        prev = profile[i - 1]
        curr = profile[i]
        delta = curr["db"] - prev["db"]
        if delta >= rise_db:
            time_since_last = curr["time"] - last_onset_time
            if time_since_last >= min_gap - eps:
                onsets.append({
                    "time": curr["time"],
                    "rise_db": delta,
                    "label": "SOUND_ONSET"
                })
                last_onset_time = curr["time"]

    return {"status": "OK", "onsets": onsets}
