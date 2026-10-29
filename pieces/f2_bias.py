import hashlib
import math
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Type aliases for clarity
VideoMeta = Dict[str, Any]
VideoTags = Dict[str, Any]
Ref = Dict[str, str]
TagsByVideo = Dict[str, VideoTags]
BalanceReport = Dict[str, Any]
EvidenceCounts = Dict[str, Any]


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _is_hashable(val: Any) -> bool:
    try:
        hash(val)
        return True
    except TypeError:
        return False


def tag_video(meta: VideoMeta) -> VideoTags:
    """
    Extract standardized tags from a video metadata dictionary.
    Never filters a video out; returns defaults for missing/unknown fields.

    Returns dict with keys:
    - aspect: "9:16" | "16:9" | "1:1" | "other"
    - duration_band: "<15s" | "15-45s" | "45-120s" | ">120s" | "UNKNOWN" (missing/nonnumeric duration)
    - has_audio: True | False | "UNAVAILABLE"
    - origin: str (or "UNKNOWN")
    - art_style: str (or "UNKNOWN")
    - pacing_band: "slow" | "medium" | "fast" | "UNKNOWN" | None (missing cut/duration data)
    - creator_id: str (or "UNKNOWN")
    """
    # Aspect ratio
    w = meta.get("width")
    h = meta.get("height")
    aspect = "other"
    if isinstance(w, (int, float)) and isinstance(h, (int, float)) and h > 0:
        ratio = w / h
        if abs(ratio - 9/16) < 0.02:
            aspect = "9:16"
        elif abs(ratio - 16/9) < 0.02:
            aspect = "16:9"
        elif abs(ratio - 1.0) < 0.02:
            aspect = "1:1"

    # Duration band - "UNKNOWN" for missing/nonnumeric (missing sentinel)
    dur = meta.get("duration_sec")
    duration_band = "UNKNOWN"
    if isinstance(dur, (int, float)) and math.isfinite(dur):
        if dur < 15:
            duration_band = "<15s"
        elif dur <= 45:
            duration_band = "15-45s"
        elif dur <= 120:
            duration_band = "45-120s"
        else:
            duration_band = ">120s"

    # Audio - strict boolean check; "UNAVAILABLE" is explicit in spec
    has_audio = meta.get("has_audio", "UNAVAILABLE")
    if not (type(has_audio) is bool or has_audio == "UNAVAILABLE"):
        has_audio = "UNAVAILABLE"

    # Origin
    origin = meta.get("origin", "UNKNOWN")
    if not isinstance(origin, str) or not origin:
        origin = "UNKNOWN"

    # Art style
    art_style = meta.get("art_style", "UNKNOWN")
    if not isinstance(art_style, str) or not art_style:
        art_style = "UNKNOWN"

    # Pacing band (cuts per minute)
    cuts = meta.get("cuts")
    duration = meta.get("duration_sec")
    pacing_band = "UNKNOWN"
    if (isinstance(cuts, (int, float)) and math.isfinite(cuts) and cuts >= 0 and
        isinstance(duration, (int, float)) and math.isfinite(duration) and duration > 0):
        cpm = (cuts / duration) * 60.0
        if cpm < 12:
            pacing_band = "slow"
        elif cpm <= 30:
            pacing_band = "medium"
        else:
            pacing_band = "fast"
    elif cuts is None or duration is None:
        pacing_band = None  # Missing data signal
    elif isinstance(cuts, (int, float)) and (not math.isfinite(cuts) or cuts < 0):
        pacing_band = None  # Negative or non-finite cuts treated as missing

    # Creator ID
    creator_id = meta.get("creator_id", "UNKNOWN")
    if not isinstance(creator_id, str) or not creator_id:
        creator_id = "UNKNOWN"

    return {
        "aspect": aspect,
        "duration_band": duration_band,
        "has_audio": has_audio,
        "origin": origin,
        "art_style": art_style,
        "pacing_band": pacing_band,
        "creator_id": creator_id,
    }


def evidence_counts(refs: List[Ref], tags_by_video: TagsByVideo) -> EvidenceCounts:
    """
    Count evidence from refs against the tagged corpus.
    Raises ValueError if any ref video_key is not in tags_by_video.
    """
    # Validate ref structure
    for i, r in enumerate(refs):
        if not isinstance(r, dict):
            raise ValueError(f"Ref at index {i} is not a dict")
        if "video_key" not in r:
            raise ValueError(f"Ref at index {i} missing 'video_key'")
        if "technique" not in r:
            raise ValueError(f"Ref at index {i} missing 'technique'")
        if not isinstance(r["video_key"], str):
            raise ValueError(f"Ref at index {i} 'video_key' must be a string")
        if not isinstance(r["technique"], str):
            raise ValueError(f"Ref at index {i} 'technique' must be a string")

    # Validate all ref video_keys exist in tags_by_video
    known_keys = set(tags_by_video.keys())
    ref_keys = {r["video_key"] for r in refs}
    missing = ref_keys - known_keys
    if missing:
        raise ValueError(f"Unknown video_key(s) in refs: {sorted(missing)}")

    # Distinct videos referenced
    video_keys = {r["video_key"] for r in refs}
    videos = len(video_keys)

    # Independent creators (KNOWN only)
    known_creators: Set[str] = set()
    unknown_creator_videos = 0
    for vk in video_keys:
        cid = tags_by_video[vk].get("creator_id")
        if cid is None:
            cid = "UNKNOWN"
        elif cid == "":
            cid = "UNKNOWN"
        if cid != "UNKNOWN":
            known_creators.add(cid)
        else:
            unknown_creator_videos += 1

    # By art_style (distinct videos per style)
    by_type: Dict[str, int] = defaultdict(int)
    for vk in video_keys:
        style = tags_by_video[vk].get("art_style", "UNKNOWN")
        if style is None:
            style = "UNKNOWN"
        by_type[style] += 1

    total_corpus = len(tags_by_video)
    prevalence = round(videos / total_corpus, 3) if total_corpus > 0 else 0.0

    return {
        "videos": videos,
        "independent_creators": len(known_creators),
        "unknown_creator_videos": unknown_creator_videos,
        "by_type": dict(by_type),
        "total_corpus": total_corpus,
        "prevalence": prevalence,
    }


def _is_missing_value(dim: str, val: Any) -> bool:
    """Check if a value is a missing sentinel for the given dimension."""
    # For all dimensions, None and "UNKNOWN" are missing sentinels
    if val is None or val == "UNKNOWN":
        return True
    # has_audio additionally has "UNAVAILABLE"
    if dim == "has_audio" and val == "UNAVAILABLE":
        return True
    # pacing_band can also be None (already caught above) or "UNKNOWN"
    return False


def balance_report(tags_list: List[VideoTags], expected: Optional[Dict[str, List[str]]] = None) -> BalanceReport:
    """
    Produce a balance report over a list of video tags.
    - counts: per-dimension value frequencies (excluding missing)
    - dominant: dimensions where a single value has share > 0.5 and count >= 3
                share is calculated over known (non-missing) values for that dimension
    - gaps: expected values with zero observed videos (excluding missing sentinels)
    - missing_<dimension>_count: for dimensions where None/"UNKNOWN"/"UNAVAILABLE" appear
    """
    # Dimensions we track (creator_id is not a balance dimension per spec)
    dimensions = [
        "aspect",
        "duration_band",
        "has_audio",
        "origin",
        "art_style",
        "pacing_band",
    ]

    counts: Dict[str, Counter] = {dim: Counter() for dim in dimensions}
    missing_counts: Dict[str, int] = {dim: 0 for dim in dimensions}

    for tags in tags_list:
        for dim in dimensions:
            # Use .get(dim) which returns None if key absent
            val = tags.get(dim)
            # Skip unhashable values (treat as missing)
            if not _is_hashable(val):
                missing_counts[dim] += 1
                continue
            
            if _is_missing_value(dim, val):
                missing_counts[dim] += 1
            else:
                counts[dim][val] += 1

    # Build output counts dict (only non-missing values)
    out_counts: Dict[str, Dict[str, int]] = {}
    for dim in dimensions:
        if counts[dim]:
            out_counts[dim] = dict(counts[dim])
        else:
            out_counts[dim] = {}

    # Dominant buckets: share > 0.5 and n >= 3, excluding missing
    # Denominator is count of known (non-missing) values for that dimension
    dominant = []
    for dim in dimensions:
        known_total = sum(counts[dim].values())
        if known_total >= 3:
            for val, cnt in counts[dim].items():
                share = cnt / known_total
                if share > 0.5 and cnt >= 3:
                    dominant.append({"dimension": dim, "value": val, "share": round(share, 3)})

    # Gaps: expected values with zero observed videos (excluding missing sentinels)
    gaps = []
    if expected:
        for dim, exp_values in expected.items():
            if not isinstance(exp_values, list):
                continue
            # Ensure counter exists for any expected dimension
            if dim not in counts:
                counts[dim] = Counter()
            for val in exp_values:
                # Skip missing sentinels in expected values
                if _is_missing_value(dim, val):
                    continue
                if counts[dim].get(val, 0) == 0:
                    gaps.append(val)

    # Assemble report
    report: BalanceReport = {
        "counts": out_counts,
        "dominant": dominant,
        "gaps": gaps,
    }
    # Add missing counts
    for dim, mc in missing_counts.items():
        if mc > 0:
            report[f"missing_{dim}_count"] = mc

    return report
