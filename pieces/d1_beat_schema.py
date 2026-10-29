"""Beat schema, validation, prompt building, and parsing for cinematic analysis.

BeatDict schema:
{
    "video_id": str,
    "beat_id": str,
    "start_time": float,
    "end_time": float,
    "purpose": "ESTABLISH" | "REVEAL" | "EMPHASIZE" | "REACT" | "RESOLVE" | "TRANSITION" | "UNKNOWN",
    "how_filmed": {
        "shot_scale": str,
        "angle": str,
        "framing": str,
        "camera_movement": str,
        "cut_type": str,
        "composition": str
    },
    "how_animated": {
        "method": "POSE_SWAP" | "LAYER_MOTION" | "RIG_ARTICULATION" | "CAMERA_ONLY" | "EFFECT" | "UNKNOWN",
        "notes": str
    },
    "sound": {
        "narration": str,
        "silence": str,
        "ambience": str,
        "sfx": str,
        "music": str,
        "sync_with_cut": str
    },
    "observed": [str],
    "inferred": [{"claim": str, "confidence": "LOW" | "MEDIUM" | "HIGH", "based_on": [str]}],
    "reproduction": {
        "status": "EXISTING_PRESET" | "POSE_OR_LAYER_CHANGE" | "NEED_NEW" | "RESEARCH_ONLY",
        "artwork_needed": [str],
        "simplest_method": str
    },
    "counterexample": str,
    "evidence": [{"frame": int, "time": float}],
    "source_url": str | None,
    "level_links": {"video_id": str, "sequence_id": str, "shot_ids": [str]},
    "verification_status": "UNVERIFIED" | "FRAME_CHECKED" | "AUDIO_CHECKED" | "BOTH_CHECKED",
    "unknowns": [str],
    "information_conveyed": str,
    "department_findings": {
        "1".."16": [{
            "term": str,
            "status": "OBSERVED" | "NOT_OBSERVED" | "UNKNOWN" | "NOT_EXAMINED",
            "observed": str,
            "evidence": [{"frame": int, "time": float}],
            "inferred_purpose": str | None,
            "alternatives": [str],
            "contraindication": str | None,
            "confidence": "LOW" | "MEDIUM" | "HIGH",
            "examined_basis": str | None
        }]
    }
}
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Callable

VALID_PURPOSES = {
    "ESTABLISH", "REVEAL", "EMPHASIZE", "REACT", "RESOLVE", "TRANSITION", "UNKNOWN"
}

VALID_ANIMATION_METHODS = {
    "POSE_SWAP", "LAYER_MOTION", "RIG_ARTICULATION", "CAMERA_ONLY", "EFFECT", "UNKNOWN"
}

VALID_CONFIDENCES = {"LOW", "MEDIUM", "HIGH"}

VALID_REPRODUCTION_STATUSES = {
    "EXISTING_PRESET", "POSE_OR_LAYER_CHANGE", "NEED_NEW", "RESEARCH_ONLY"
}

VALID_FINDING_STATUSES = {"OBSERVED", "NOT_OBSERVED", "UNKNOWN", "NOT_EXAMINED"}

VALID_VERIFICATION_STATUSES = {"UNVERIFIED", "FRAME_CHECKED", "AUDIO_CHECKED", "BOTH_CHECKED"}

VALID_DEPARTMENTS = {
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16"
}

# Match software names and assertion phrasing, not bare technique words
FORBIDDEN_FACT_PATTERNS = [
    r"\b(premiere pro|adobe premiere|final cut pro|davinci resolve|after effects|capcut)\b.*\b(used|using|edited with|created with|edited in|edit in|was used)\b",
    r"\b(used|using|edited with|created with|edited in|edit in|was used)\b.*\b(premiere pro|adobe premiere|final cut pro|davinci resolve|after effects|capcut)\b",
    r"\bcamera lens\b",
    r"\bfocal length\b",
    r"\b\d+\s*mm\s+lens\b",
    r"\bhidden rig\b",
    r"\boriginal screenplay\b",
]


def _check_forbidden_facts(text: str) -> str | None:
    """Check if text asserts forbidden facts as statements of fact."""
    text_lower = text.lower()
    for pattern in FORBIDDEN_FACT_PATTERNS:
        if re.search(pattern, text_lower):
            return f"forbidden fact assertion: {pattern}"
    return None


def _walk_strings(obj: Any, path: str = "") -> list[tuple[str, str]]:
    """Walk an object and yield (path, string_value) for all string values."""
    results = []
    if isinstance(obj, str):
        results.append((path, obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            results.extend(_walk_strings(v, new_path))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_path = f"{path}[{i}]"
            results.extend(_walk_strings(v, new_path))
    return results


def _is_finite_number(val: Any) -> bool:
    """Check if value is a finite int/float (not bool, not NaN, not inf)."""
    if isinstance(val, bool):
        return False
    if not isinstance(val, (int, float)):
        return False
    return math.isfinite(val)


def validate_beat(beat: dict) -> dict:
    """Validate a beat dict against the schema."""
    # Non-dict guard
    if not isinstance(beat, dict):
        return {"status": "ERROR", "reason": "Input must be a dict"}

    # Required top-level fields
    required_fields = [
        "video_id", "beat_id", "start_time", "end_time", "purpose",
        "how_filmed", "how_animated", "sound", "observed", "inferred",
        "reproduction", "counterexample", "evidence"
    ]
    for field in required_fields:
        if field not in beat:
            return {"status": "ERROR", "reason": f"Missing required field: {field}"}

    # Type checks
    if not isinstance(beat["video_id"], str):
        return {"status": "ERROR", "reason": "video_id must be string"}
    if not isinstance(beat["beat_id"], str):
        return {"status": "ERROR", "reason": "beat_id must be string"}
    if not _is_finite_number(beat["start_time"]):
        return {"status": "ERROR", "reason": "start_time must be finite number"}
    if not _is_finite_number(beat["end_time"]):
        return {"status": "ERROR", "reason": "end_time must be finite number"}
    if beat["end_time"] < beat["start_time"]:
        return {"status": "ERROR", "reason": "end_time must be >= start_time"}

    # Purpose validation
    purpose = beat["purpose"]
    if not isinstance(purpose, str) or purpose not in VALID_PURPOSES:
        return {"status": "ERROR", "reason": f"Invalid purpose: {purpose}"}

    # how_filmed validation
    hf = beat["how_filmed"]
    if not isinstance(hf, dict):
        return {"status": "ERROR", "reason": "how_filmed must be dict"}
    required_hf = ["shot_scale", "angle", "framing", "camera_movement", "cut_type", "composition"]
    for key in required_hf:
        if key not in hf:
            return {"status": "ERROR", "reason": f"how_filmed missing key: {key}"}
        if not isinstance(hf[key], str):
            return {"status": "ERROR", "reason": f"how_filmed.{key} must be string"}

    # how_animated validation
    ha = beat["how_animated"]
    if not isinstance(ha, dict):
        return {"status": "ERROR", "reason": "how_animated must be dict"}
    if "method" not in ha or "notes" not in ha:
        return {"status": "ERROR", "reason": "how_animated missing method or notes"}
    method = ha["method"]
    if not isinstance(method, str) or method not in VALID_ANIMATION_METHODS:
        return {"status": "ERROR", "reason": f"Invalid animation method: {method}"}
    if not isinstance(ha["notes"], str):
        return {"status": "ERROR", "reason": "how_animated.notes must be string"}

    # sound validation
    sound = beat["sound"]
    if not isinstance(sound, dict):
        return {"status": "ERROR", "reason": "sound must be dict"}
    required_sound = ["narration", "silence", "ambience", "sfx", "music", "sync_with_cut"]
    for key in required_sound:
        if key not in sound:
            return {"status": "ERROR", "reason": f"sound missing key: {key}"}
        if not isinstance(sound[key], str):
            return {"status": "ERROR", "reason": f"sound.{key} must be string"}

    # observed validation
    observed = beat["observed"]
    if not isinstance(observed, list):
        return {"status": "ERROR", "reason": "observed must be list"}
    for i, item in enumerate(observed):
        if not isinstance(item, str):
            return {"status": "ERROR", "reason": f"observed[{i}] must be string"}

    # inferred validation
    inferred = beat["inferred"]
    if not isinstance(inferred, list):
        return {"status": "ERROR", "reason": "inferred must be list"}
    for i, item in enumerate(inferred):
        if not isinstance(item, dict):
            return {"status": "ERROR", "reason": f"inferred[{i}] must be dict"}
        if "claim" not in item:
            return {"status": "ERROR", "reason": f"Inferred item missing required keys: claim"}
        if "confidence" not in item:
            return {"status": "ERROR", "reason": f"Inferred item missing required keys: confidence"}
        if "based_on" not in item:
            return {"status": "ERROR", "reason": f"Inferred item missing required keys: based_on"}
        if not isinstance(item["claim"], str):
            return {"status": "ERROR", "reason": f"inferred[{i}].claim must be string"}
        confidence = item["confidence"]
        if not isinstance(confidence, str) or confidence not in VALID_CONFIDENCES:
            return {"status": "ERROR", "reason": f"inferred[{i}].confidence must be LOW/MEDIUM/HIGH"}
        if not isinstance(item["based_on"], list):
            return {"status": "ERROR", "reason": f"inferred[{i}].based_on must be list"}
        for j, ref in enumerate(item["based_on"]):
            if not isinstance(ref, str):
                return {"status": "ERROR", "reason": f"inferred[{i}].based_on[{j}] must be string"}

    # reproduction validation
    repro = beat["reproduction"]
    if not isinstance(repro, dict):
        return {"status": "ERROR", "reason": "reproduction must be dict"}
    required_repro = ["status", "artwork_needed", "simplest_method"]
    for key in required_repro:
        if key not in repro:
            return {"status": "ERROR", "reason": f"reproduction missing key: {key}"}
    status = repro["status"]
    if not isinstance(status, str) or status not in VALID_REPRODUCTION_STATUSES:
        return {"status": "ERROR", "reason": f"Invalid reproduction status: {status}"}
    if not isinstance(repro["artwork_needed"], list):
        return {"status": "ERROR", "reason": "reproduction.artwork_needed must be list"}
    for i, item in enumerate(repro["artwork_needed"]):
        if not isinstance(item, str):
            return {"status": "ERROR", "reason": f"reproduction.artwork_needed[{i}] must be string"}
    if not isinstance(repro["simplest_method"], str):
        return {"status": "ERROR", "reason": "reproduction.simplest_method must be string"}

    # counterexample
    if not isinstance(beat["counterexample"], str):
        return {"status": "ERROR", "reason": "counterexample must be string"}

    # evidence validation
    evidence = beat["evidence"]
    if not isinstance(evidence, list):
        return {"status": "ERROR", "reason": "evidence must be list"}
    for i, item in enumerate(evidence):
        if not isinstance(item, dict):
            return {"status": "ERROR", "reason": f"evidence[{i}] must be dict"}
        if "frame" not in item or "time" not in item:
            return {"status": "ERROR", "reason": f"evidence[{i}] missing frame or time"}
        if not isinstance(item["frame"], int) or isinstance(item["frame"], bool):
            return {"status": "ERROR", "reason": f"evidence[{i}].frame must be int"}
        if not _is_finite_number(item["time"]):
            return {"status": "ERROR", "reason": f"evidence[{i}].time must be finite number"}

    # Optional fields validation
    # source_url
    if "source_url" in beat and beat["source_url"] is not None:
        if not isinstance(beat["source_url"], str):
            return {"status": "ERROR", "reason": "source_url must be string or null"}

    # level_links
    if "level_links" in beat:
        ll = beat["level_links"]
        if not isinstance(ll, dict):
            return {"status": "ERROR", "reason": "level_links must be dict"}
        if "video_id" not in ll or "sequence_id" not in ll or "shot_ids" not in ll:
            return {"status": "ERROR", "reason": "level_links missing required keys"}
        if not isinstance(ll["video_id"], str) or not isinstance(ll["sequence_id"], str):
            return {"status": "ERROR", "reason": "level_links video_id/sequence_id must be string"}
        if not isinstance(ll["shot_ids"], list):
            return {"status": "ERROR", "reason": "level_links.shot_ids must be list"}
        for i, sid in enumerate(ll["shot_ids"]):
            if not isinstance(sid, str):
                return {"status": "ERROR", "reason": f"level_links.shot_ids[{i}] must be string"}

    # verification_status
    if "verification_status" in beat:
        vs = beat["verification_status"]
        if not isinstance(vs, str) or vs not in VALID_VERIFICATION_STATUSES:
            return {"status": "ERROR", "reason": f"Invalid verification_status: {vs}"}

    # unknowns
    if "unknowns" in beat:
        unk = beat["unknowns"]
        if not isinstance(unk, list):
            return {"status": "ERROR", "reason": "unknowns must be list"}
        for i, item in enumerate(unk):
            if not isinstance(item, str):
                return {"status": "ERROR", "reason": f"unknowns[{i}] must be string"}

    # information_conveyed
    if "information_conveyed" in beat:
        if not isinstance(beat["information_conveyed"], str):
            return {"status": "ERROR", "reason": "information_conveyed must be string"}

    # department_findings
    if "department_findings" in beat:
        df = beat["department_findings"]
        if not isinstance(df, dict):
            return {"status": "ERROR", "reason": "department_findings must be dict"}
        for dept_id, findings in df.items():
            if dept_id not in VALID_DEPARTMENTS:
                return {"status": "ERROR", "reason": f"Invalid department id: {dept_id}"}
            if not isinstance(findings, list):
                return {"status": "ERROR", "reason": f"department_findings[{dept_id}] must be list"}
            for fi, finding in enumerate(findings):
                if not isinstance(finding, dict):
                    return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}] must be dict"}
                required_finding = ["term", "status", "observed", "evidence", "inferred_purpose", "alternatives", "contraindication", "confidence"]
                for key in required_finding:
                    if key not in finding:
                        return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}] missing key: {key}"}
                if not isinstance(finding["term"], str):
                    return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}].term must be string"}
                finding_status = finding["status"]
                if not isinstance(finding_status, str) or finding_status not in VALID_FINDING_STATUSES:
                    return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}].status invalid: {finding_status}"}
                if not isinstance(finding["observed"], str):
                    return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}].observed must be string"}
                if not isinstance(finding["evidence"], list):
                    return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}].evidence must be list"}
                for ei, ev in enumerate(finding["evidence"]):
                    if not isinstance(ev, dict) or "frame" not in ev or "time" not in ev:
                        return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}].evidence[{ei}] missing frame/time"}
                    if not isinstance(ev["frame"], int) or isinstance(ev["frame"], bool):
                        return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}].evidence[{ei}] frame must be int"}
                    if not _is_finite_number(ev["time"]):
                        return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}].evidence[{ei}] time must be finite number"}
                if finding["inferred_purpose"] is not None and not isinstance(finding["inferred_purpose"], str):
                    return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}].inferred_purpose must be string or null"}
                if not isinstance(finding["alternatives"], list):
                    return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}].alternatives must be list"}
                for ai, alt in enumerate(finding["alternatives"]):
                    if not isinstance(alt, str):
                        return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}].alternatives[{ai}] must be string"}
                if finding["contraindication"] is not None and not isinstance(finding["contraindication"], str):
                    return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}].contraindication must be string or null"}
                finding_confidence = finding["confidence"]
                if not isinstance(finding_confidence, str) or finding_confidence not in VALID_CONFIDENCES:
                    return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}].confidence invalid"}

                # OBSERVED findings need >=1 evidence entry
                if finding["status"] == "OBSERVED" and len(finding["evidence"]) == 0:
                    return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}]: OBSERVED finding requires >=1 evidence entry"}

                # NOT_OBSERVED needs examined_basis
                if finding["status"] == "NOT_OBSERVED":
                    if "examined_basis" not in finding or not isinstance(finding["examined_basis"], str) or not finding["examined_basis"].strip():
                        return {"status": "ERROR", "reason": f"department_findings[{dept_id}][{fi}]: NOT_OBSERVED requires non-empty examined_basis"}

    # Check for forbidden facts in ALL free-text string fields
    # Skip only structural/enum fields (identifiers and controlled vocabularies)
    skip_paths = {
        "video_id", "beat_id", "purpose",
        "how_animated.method",
        "reproduction.status",
        "source_url", "level_links.video_id", "level_links.sequence_id", "verification_status"
    }
    for path, text in _walk_strings(beat):
        if path in skip_paths:
            continue
        forbidden = _check_forbidden_facts(text)
        if forbidden:
            return {"status": "ERROR", "reason": f"{path}: {forbidden}"}

    return {"status": "OK", "beat": beat}


def beat_prompt(shot_context: dict, audio_evidence: dict) -> dict:
    """Build the six-question prompt demanding JSON in the beat schema."""
    video_id = shot_context.get("video_id", "UNKNOWN")
    beat_id = shot_context.get("beat_id", "UNKNOWN")
    start_time = shot_context.get("start_time", 0.0)
    end_time = shot_context.get("end_time", 0.0)
    shot_description = shot_context.get("shot_description", "No description")

    narration = audio_evidence.get("narration", "UNAVAILABLE")
    music = audio_evidence.get("music", "UNAVAILABLE")
    sfx = audio_evidence.get("sfx", "UNAVAILABLE")
    sync_with_cut = audio_evidence.get("sync_with_cut", "UNKNOWN")

    prompt = f"""Analyze this cinematic beat and return ONLY valid JSON matching the schema below.

Context:
- Video ID: {video_id}
- Beat ID: {beat_id}
- Time: {start_time}s - {end_time}s
- Shot: {shot_description}
- Audio: narration={narration}, music={music}, sfx={sfx}, sync_with_cut={sync_with_cut}

Answer these six questions in the JSON:
1. What is the storytelling beat (purpose)? Choose from: ESTABLISH, REVEAL, EMPHASIZE, REACT, RESOLVE, TRANSITION, UNKNOWN.
2. How was it filmed? (shot_scale, angle, framing, camera_movement, cut_type, composition)
3. How was it animated? (method: POSE_SWAP, LAYER_MOTION, RIG_ARTICULATION, CAMERA_ONLY, EFFECT, UNKNOWN + notes)
4. What sound is present? (narration, silence, ambience, sfx, music, sync_with_cut — each a string or UNAVAILABLE/UNKNOWN)
5. Why might this beat work? (hypothesis)
6. How reproducible in GranthStudio? (reproduction status, artwork_needed, simplest_method)

Also include: observed (list of strings), inferred (list of {{claim, confidence: LOW/MEDIUM/HIGH, based_on: [str]}}), counterexample (string), evidence (list of {{frame: int, time: float}}).

Return ONLY the JSON object."""

    schema_hint = """BeatDict schema:
{
    "video_id": str,
    "beat_id": str,
    "start_time": float,
    "end_time": float,
    "purpose": "ESTABLISH" | "REVEAL" | "EMPHASIZE" | "REACT" | "RESOLVE" | "TRANSITION" | "UNKNOWN",
    "how_filmed": {"shot_scale": str, "angle": str, "framing": str, "camera_movement": str, "cut_type": str, "composition": str},
    "how_animated": {"method": "POSE_SWAP" | "LAYER_MOTION" | "RIG_ARTICULATION" | "CAMERA_ONLY" | "EFFECT" | "UNKNOWN", "notes": str},
    "sound": {"narration": str, "silence": str, "ambience": str, "sfx": str, "music": str, "sync_with_cut": str},
    "observed": [str],
    "inferred": [{"claim": str, "confidence": "LOW" | "MEDIUM" | "HIGH", "based_on": [str]}],
    "reproduction": {"status": "EXISTING_PRESET" | "POSE_OR_LAYER_CHANGE" | "NEED_NEW" | "RESEARCH_ONLY", "artwork_needed": [str], "simplest_method": str},
    "counterexample": str,
    "evidence": [{"frame": int, "time": float}],
    "source_url": str | None,
    "level_links": {"video_id": str, "sequence_id": str, "shot_ids": [str]},
    "verification_status": "UNVERIFIED" | "FRAME_CHECKED" | "AUDIO_CHECKED" | "BOTH_CHECKED",
    "unknowns": [str],
    "information_conveyed": str,
    "department_findings": {"1".."16": [{"term": str, "status": "OBSERVED" | "NOT_OBSERVED" | "UNKNOWN" | "NOT_EXAMINED", "observed": str, "evidence": [{"frame": int, "time": float}], "inferred_purpose": str | None, "alternatives": [str], "contraindication": str | None, "confidence": "LOW" | "MEDIUM" | "HIGH", "examined_basis": str | None}]}
}"""

    return {"prompt": prompt, "schema_hint": schema_hint}


# Sentinel to distinguish "not provided" from "explicitly None"
_AUDIO_STATUS_UNSET = object()


def parse_beat(text: str, validate_fn: Callable[[dict], dict], audio_status: str | None = _AUDIO_STATUS_UNSET) -> dict:
    """Extract JSON from text, validate using validate_fn, reject if observed/inferred mixed or purpose invalid.
    
    Args:
        text: Raw text potentially containing JSON
        validate_fn: Validation function (typically validate_beat)
        audio_status: Optional audio status from source (e.g., "UNAVAILABLE" for frame-only ZIP).
                      When "UNAVAILABLE", all sound.* fields must be UNKNOWN/UNAVAILABLE and
                      sound department findings must be UNKNOWN with no observed text.
                      When None (explicitly passed), no audio cross-check is performed.
                      When not provided (default), falls back to checking model's sound.narration for backward compatibility.
    """
    # Guard non-string input
    if not isinstance(text, str):
        return {"status": "ERROR", "reason": "Input text must be a string"}
    
    # Extract JSON from text
    text = text.strip()
    
    # Try to parse the whole text as JSON first
    try:
        beat = json.loads(text)
        if not isinstance(beat, dict):
            return {"status": "ERROR", "reason": "Parsed JSON is not an object"}
    except json.JSONDecodeError:
        # Try to extract JSON object from text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {"status": "ERROR", "reason": "Failed to parse JSON: No JSON object found in text"}
        json_text = match.group(0)
        try:
            beat = json.loads(json_text)
        except json.JSONDecodeError as e:
            return {"status": "ERROR", "reason": f"Failed to parse JSON: {e}"}
        if not isinstance(beat, dict):
            return {"status": "ERROR", "reason": "Parsed JSON is not an object"}

    # Check observed/inferred mixing: observed must be all strings, inferred must be all dicts with claim
    observed = beat.get("observed", [])
    if isinstance(observed, list):
        for i, item in enumerate(observed):
            if not isinstance(item, str):
                return {"status": "ERROR", "reason": "Observed contains non-string items (inferred mixed in)"}

    inferred = beat.get("inferred", [])
    if isinstance(inferred, list):
        for i, item in enumerate(inferred):
            if not isinstance(item, dict) or "claim" not in item:
                return {"status": "ERROR", "reason": "Inferred item missing required keys: claim"}

    # Validate using injected function
    result = validate_fn(beat)
    if result["status"] == "ERROR":
        return {"status": "ERROR", "reason": result["reason"]}

    # Audio status cross-check
    # Determine if we should run the audio check
    run_audio_check = False
    if audio_status is _AUDIO_STATUS_UNSET:
        # Backward compatibility: check model's sound.narration
        run_audio_check = beat.get("sound", {}).get("narration") == "UNAVAILABLE"
    elif audio_status == "UNAVAILABLE":
        run_audio_check = True
    # If audio_status is None (explicitly passed), run_audio_check stays False

    if run_audio_check:
        sound = beat.get("sound", {})
        for key in ["narration", "silence", "ambience", "sfx", "music", "sync_with_cut"]:
            val = sound.get(key, "")
            if val and val.strip() and val not in ("UNAVAILABLE", "UNKNOWN"):
                return {"status": "ERROR", "reason": f"Audio UNAVAILABLE but sound.{key} has real text: {val}"}
        
        df = beat.get("department_findings", {})
        # Check sound-related findings across ALL departments, not just "13"
        for dept_id, findings in df.items():
            for finding in findings:
                # Check if this finding is sound-related by term or department
                term = finding.get("term", "").lower()
                is_sound_finding = (
                    dept_id == "13" or 
                    any(kw in term for kw in ["sound", "audio", "narration", "music", "sfx", "ambience", "silence", "sync"])
                )
                if is_sound_finding:
                    if finding.get("status") != "UNKNOWN":
                        return {"status": "ERROR", "reason": "Audio UNAVAILABLE but sound finding status is not UNKNOWN"}
                    if finding.get("observed", "").strip():
                        return {"status": "ERROR", "reason": "Audio UNAVAILABLE but sound finding has observed text"}

    return {"status": "OK", "beat": result["beat"]}
