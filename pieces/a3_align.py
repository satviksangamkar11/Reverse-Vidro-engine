from typing import Callable
import os


def align_to_cuts(
    cut_times: list[float],
    silences: list[dict],
    onsets: list[dict],
    speech: list[dict],
    tol: float = 0.25
) -> dict:
    """
    Align cut timestamps to audio events.

    Args:
        cut_times: List of cut timestamps in seconds.
        silences: List of {"start": float, "end": float}.
        onsets: List of {"time": float, "rise_db": float, "label": "SOUND_ONSET"}.
        speech: List of {"start": float, "end": float, ...} from transcribe.
        tol: Tolerance in seconds for onset matching.

    Returns:
        Dict with status and alignment list.
    """
    alignment = []

    # Pre-sort for efficiency
    silences_sorted = sorted(silences, key=lambda s: s["start"])
    onsets_sorted = sorted(onsets, key=lambda o: o["time"])
    speech_sorted = sorted(speech, key=lambda s: s["start"])

    for ct in cut_times:
        # near_onset: nearest onset within tol
        near_onset = None
        min_diff = float("inf")
        for onset in onsets_sorted:
            diff = abs(onset["time"] - ct)
            if diff <= tol and diff < min_diff:
                min_diff = diff
                near_onset = onset
            if onset["time"] > ct + tol:
                break

        # in_silence: any silence with start <= ct <= end
        in_silence = any(s["start"] <= ct <= s["end"] for s in silences_sorted)

        # speech_active: any speech segment with start <= ct <= end
        speech_active = any(seg["start"] <= ct <= seg["end"] for seg in speech_sorted)

        # speech_pause_within_tol: cut falls in a silence that is between two speech segments
        # with gaps <= 2s on both sides (no centre-distance check)
        speech_pause_within_tol = False
        for sil in silences_sorted:
            if sil["start"] <= ct <= sil["end"]:
                before = None
                after = None
                for seg in speech_sorted:
                    if seg["end"] <= sil["start"]:
                        before = seg
                    elif seg["start"] >= sil["end"]:
                        after = seg
                        break
                if before is not None and after is not None:
                    gap_before = sil["start"] - before["end"]
                    gap_after = after["start"] - sil["end"]
                    if gap_before <= 2.0 and gap_after <= 2.0:
                        speech_pause_within_tol = True
                        break

        alignment.append({
            "cut": ct,
            "near_onset": near_onset,
            "in_silence": in_silence,
            "speech_active": speech_active,
            "speech_pause_within_tol": speech_pause_within_tol,
            "relationship": "CO_OCCURS"
        })

    return {"status": "OK", "alignment": alignment}


def analyze_audio(
    source: str,
    kind: str,
    cut_times: list[float],
    folder: str,
    transcribe_fn: Callable,
    extract_audio_fn: Callable,
    energy_profile_fn: Callable,
    find_silences_fn: Callable,
    find_onsets_fn: Callable,
    classify_gaps_fn: Callable,
    align_to_cuts_fn: Callable,
    write_json_atomic: Callable,
    read_json: Callable,
    path_exists: Callable,
    get_size_mtime: Callable,
    cache_get: Callable,
    cache_set: Callable,
    now: Callable
) -> dict:
    """
    Orchestrate audio analysis pipeline with caching and resumability.
    """
    evidence_path = f"{folder}/audio_evidence.json"
    wav_path = f"{folder}/audio.wav"
    model_size = "small"
    generated_at = now()

    # 1. Check for existing evidence
    if path_exists(evidence_path):
        cached = read_json(evidence_path)
        if cached is not None and isinstance(cached, dict):
            required_keys = {"status", "audio_status", "transcript", "silences", "gaps", "onsets", "cut_alignment", "uncertainty_notes"}
            if required_keys.issubset(cached.keys()):
                # Verify cut_times match (simple list equality)
                if cached.get("cut_times") == cut_times:
                    # Only return early if the cached evidence represents a successful or permanently unavailable extraction
                    cached_audio_status = cached.get("audio_status")
                    if cached.get("status") == "OK" or cached_audio_status in ("UNAVAILABLE", "NO_AUDIO_STREAM"):
                        cached["from_cache"] = True
                        return cached

    # 2. Check wav cache before extracting
    wav_cache_key = f"wav:{source}"
    cached_wav = cache_get(wav_cache_key)
    extract_result = None

    if cached_wav is not None:
        # Validate cached WAV: check it has required fields and the file still exists with same size/mtime
        if (isinstance(cached_wav, dict) and cached_wav.get("status") == "OK" and
                "wav_path" in cached_wav and path_exists(cached_wav["wav_path"])):
            # Verify source hasn't changed by checking size/mtime if available in cache
            source_meta = get_size_mtime(source)
            if (source_meta.get("status") == "OK" and
                    cached_wav.get("source_size") == source_meta.get("size") and
                    cached_wav.get("source_mtime") == source_meta.get("mtime")):
                extract_result = cached_wav

    if extract_result is None:
        # Extract audio - call with only supported arguments per spec
        extract_result = extract_audio_fn(source, wav_path)
        # Cache the wav result if successful, including source metadata
        if extract_result.get("status") == "OK":
            source_meta = get_size_mtime(source)
            if source_meta.get("status") == "OK":
                extract_result["source_size"] = source_meta["size"]
                extract_result["source_mtime"] = source_meta["mtime"]
            cache_set(wav_cache_key, extract_result)

    # Handle extract failures - any non-OK status
    if extract_result.get("status") != "OK":
        audio_status = extract_result.get("status", "ERROR")
        uncertainty_notes = []
        if audio_status == "UNAVAILABLE":
            uncertainty_notes.append("no audio source")
        elif audio_status == "NO_AUDIO_STREAM":
            uncertainty_notes.append("silent source")
        else:
            uncertainty_notes.append(f"audio extraction failed: {audio_status}")

        evidence = {
            "status": audio_status,
            "audio_status": audio_status,
            "transcript": {"status": audio_status, "segments": [], "language": None},
            "silences": [],
            "gaps": [],
            "onsets": [],
            "cut_alignment": [],
            "uncertainty_notes": uncertainty_notes,
            "cut_times": cut_times,
            "generated_at": generated_at,
            "from_cache": False
        }
        # Add note before writing so it's in the persisted evidence if write succeeds
        write_result = write_json_atomic(evidence_path, evidence)
        if write_result.get("status") != "OK":
            # Note: if write fails, the file on disk won't have this note; returned dict does
            evidence["uncertainty_notes"].append("failed to write evidence")
        return evidence

    # Use the wav_path from extract_result
    actual_wav_path = extract_result.get("wav_path", wav_path)

    # 3. Energy profile, silences, onsets
    profile_result = energy_profile_fn(actual_wav_path)
    if profile_result.get("status") != "OK":
        profile = []
        uncertainty_notes = ["energy profile failed"]
    else:
        profile = profile_result.get("profile", [])
        uncertainty_notes = []

    silences_result = find_silences_fn(profile)
    onsets_result = find_onsets_fn(profile)

    silences = silences_result.get("silences", []) if silences_result.get("status") == "OK" else []
    onsets = onsets_result.get("onsets", []) if onsets_result.get("status") == "OK" else []

    if silences_result.get("status") != "OK":
        uncertainty_notes.append("silence detection failed")
    if onsets_result.get("status") != "OK":
        uncertainty_notes.append("onset detection failed")

    # 4. Transcribe (with cache)
    transcript_cache_key = f"transcript:{source}:{model_size}"
    cached_transcript = cache_get(transcript_cache_key)
    transcript_result = None

    if cached_transcript is not None:
        # Validate cached transcript: check status OK and source hasn't changed
        if (isinstance(cached_transcript, dict) and cached_transcript.get("status") == "OK"):
            source_meta = get_size_mtime(source)
            if (source_meta.get("status") == "OK" and
                    cached_transcript.get("source_size") == source_meta.get("size") and
                    cached_transcript.get("source_mtime") == source_meta.get("mtime")):
                transcript_result = cached_transcript

    if transcript_result is None:
        transcript_result = transcribe_fn(actual_wav_path, runner=None)
        # Cache the transcript result ONLY on success
        if transcript_result.get("status") == "OK":
            source_meta = get_size_mtime(source)
            if source_meta.get("status") == "OK":
                transcript_result["source_size"] = source_meta["size"]
                transcript_result["source_mtime"] = source_meta["mtime"]
            cache_set(transcript_cache_key, transcript_result)

    # 5. Classify gaps
    speech_segments = transcript_result.get("segments", []) if transcript_result.get("status") == "OK" else []
    gaps_result = classify_gaps_fn(silences, speech_segments)
    gaps = gaps_result.get("gaps", []) if gaps_result.get("status") == "OK" else []

    if gaps_result.get("status") != "OK":
        uncertainty_notes.append("gap classification failed")

    # 6. Align cuts
    align_result = align_to_cuts_fn(cut_times, silences, onsets, speech_segments, tol=0.25)
    cut_alignment = align_result.get("alignment", []) if align_result.get("status") == "OK" else []

    if align_result.get("status") != "OK":
        uncertainty_notes.append("cut alignment failed")

    # 7. Add transcript unavailable note if needed
    if transcript_result.get("status") != "OK":
        uncertainty_notes.append("transcript unavailable")

    # 8. Build evidence
    if transcript_result.get("status") == "TRANSCRIBER_UNAVAILABLE":
        transcript_section = {"status": "TRANSCRIBER_UNAVAILABLE"}
    else:
        transcript_section = {
            "status": transcript_result.get("status", "UNKNOWN"),
            "segments": transcript_result.get("segments", []),
            "language": transcript_result.get("language")
        }

    evidence = {
        "status": "OK",
        "audio_status": "OK",
        "transcript": transcript_section,
        "silences": silences,
        "gaps": gaps,
        "onsets": onsets,
        "cut_alignment": cut_alignment,
        "uncertainty_notes": uncertainty_notes,
        "cut_times": cut_times,
        "generated_at": generated_at,
        "from_cache": False
    }

    # 9. Write atomically and check result
    write_result = write_json_atomic(evidence_path, evidence)
    if write_result.get("status") != "OK":
        evidence["uncertainty_notes"].append("failed to write evidence")

    return evidence
