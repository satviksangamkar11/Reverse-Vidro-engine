"""Event clustering and representative selection for cinematic analysis.

Pure functions for grouping motion windows into similarity clusters and picking
representative events for review.
"""
from __future__ import annotations

import math
from typing import Any


def _score_band(score: float) -> float:
    """Compute score band using round to nearest 0.1 per worked example."""
    return round(score * 10) / 10.0


def _duration_band(duration_sec: float) -> float:
    """Compute duration band using floor to nearest 0.5."""
    return math.floor(duration_sec * 2) / 2.0


def _residual_band(residual: float) -> float:
    """Compute residual band using floor to nearest 0.1."""
    return math.floor(residual * 10) / 10.0


def _get_feature(features: list[dict] | None, event_id: str, key: str, default: Any) -> Any:
    """Safely retrieve a feature value for an event."""
    if not features:
        return default
    for feat in features:
        if feat.get("event_id") == event_id:
            return feat.get(key, default)
    return default


def cluster_windows(events: list[dict], features: list[dict] | None = None) -> dict:
    """Group events into similarity clusters by score, duration, residual, direction, region.

    Args:
        events: List of event dicts from cinematic_analysis.analyze_source.
        features: Optional list of feature dicts per event.

    Returns:
        Dict with status "ok" and list of clusters. Each cluster has cluster_id,
        members (list of event_ids), and signature dict.
    """
    clusters_map: dict[tuple, dict] = {}

    for event in events:
        event_id = event.get("event_id")
        if not event_id:
            continue

        score = event.get("score", 0.0) or 0.0
        start_frame = event.get("start_frame", 0)
        end_frame = event.get("end_frame", 0)
        duration_sec = (end_frame - start_frame) / 30.0

        mean_residual = _get_feature(features, event_id, "mean_residual", 0.0) or 0.0
        direction_hint = _get_feature(features, event_id, "direction_hint", "none") or "none"
        region = _get_feature(features, event_id, "region", "none") or "none"

        score_band = _score_band(score)
        duration_band = _duration_band(duration_sec)
        residual_band = _residual_band(mean_residual)

        key = (score_band, duration_band, residual_band, direction_hint, region)

        if key not in clusters_map:
            clusters_map[key] = {
                "cluster_id": "C_" + "_".join(str(k) for k in key),
                "members": [],
                "signature": {
                    "score_band": score_band,
                    "duration_band": duration_band,
                    "residual_band": residual_band,
                    "direction_hint": direction_hint,
                    "region": region,
                },
            }
        clusters_map[key]["members"].append(event_id)

    clusters = list(clusters_map.values())
    return {"status": "ok", "clusters": clusters}


def pick_representatives(cluster: dict, events: list[dict]) -> dict:
    """Select up to 3 distinct event_ids from a cluster's members.

    Criteria (priority order, distinct ids NOT required per worked example):
        best: highest score
        ambiguous: uncertain=True, else score nearest 0.5 (tie-break: lower event_id)
        failure: lowest score

    Args:
        cluster: Cluster dict with "members" list of event_ids.
        events: Full list of event dicts for metadata lookup.

    Returns:
        Dict with status "ok" and representatives dict with keys best, ambiguous, failure.
    """
    members = cluster.get("members", [])
    if not members:
        return {"status": "ok", "representatives": {"best": None, "ambiguous": None, "failure": None}}

    # Build lookup for event metadata
    event_lookup = {e.get("event_id"): e for e in events if e.get("event_id")}
    member_events = [event_lookup.get(mid) for mid in members if event_lookup.get(mid)]
    if not member_events:
        return {"status": "ok", "representatives": {"best": None, "ambiguous": None, "failure": None}}

    # Sort by score descending for best
    sorted_by_score_desc = sorted(member_events, key=lambda e: (e.get("score", 0.0) or 0.0), reverse=True)
    best_event = sorted_by_score_desc[0]
    best_id = best_event.get("event_id")

    # Sort by score ascending for failure
    sorted_by_score_asc = sorted(member_events, key=lambda e: (e.get("score", 0.0) or 0.0))
    failure_event = sorted_by_score_asc[0]
    failure_id = failure_event.get("event_id")

    # Ambiguous: uncertain=True preferred, else nearest to 0.5
    uncertain_events = [e for e in member_events if e.get("uncertain")]
    if uncertain_events:
        # Among uncertain, pick highest score (or any deterministic rule)
        ambiguous_event = max(uncertain_events, key=lambda e: (e.get("score", 0.0) or 0.0))
    else:
        # Nearest to 0.5, tie-break by lower event_id
        def dist_to_half(e):
            score = e.get("score", 0.0) or 0.0
            return (abs(score - 0.5), e.get("event_id", ""))
        ambiguous_event = min(member_events, key=dist_to_half)
    ambiguous_id = ambiguous_event.get("event_id")

    # Allow duplicates (per worked example)
    representatives = {"best": best_id, "ambiguous": ambiguous_id, "failure": failure_id}

    return {"status": "ok", "representatives": representatives}


def fps_for(event: dict) -> dict:
    """Determine re-extraction frame rate for an event.

    Rules: 8 fps if uncertain OR duration<0.5s OR score>=0.8 else 4 fps.

    Args:
        event: Event dict with start_frame, end_frame, score, uncertain.

    Returns:
        Dict with status "ok" and fps (int).
    """
    uncertain = event.get("uncertain", False)
    score = event.get("score", 0.0) or 0.0
    start_frame = event.get("start_frame", 0)
    # Default end_frame to start_frame + 15 (0.5s) if missing, so duration >= 0.5
    end_frame = event.get("end_frame", start_frame + 15)
    duration_sec = (end_frame - start_frame) / 30.0

    if uncertain or duration_sec < 0.5 or score >= 0.8:
        fps = 8
    else:
        fps = 4

    return {"status": "ok", "fps": fps}
