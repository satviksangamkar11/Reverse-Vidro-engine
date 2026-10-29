"""Result recording, coverage accounting, and pattern analysis for cinematic review workflow."""
from __future__ import annotations

from typing import Any
import numbers

VALID_VERDICTS = {
    "POSE_SWAP",
    "CAMERA_MOVE",
    "ARTICULATION",
    "LAYER_MOVE",
    "EFFECT",
    "NOT_MOTION",
    "UNKNOWN",
}

KNOWN_DISPOSITIONS = {
    "REVIEWED",
    "INFERRED_FROM_CLUSTER",
    "PENDING_REVIEW",
}


def record_result(state: dict[str, dict[str, Any]], event_id: str, report: dict[str, Any]) -> dict[str, Any]:
    """Validate and record a review report into state.

    Args:
        state: Mutable mapping of event_id -> event record.
        event_id: Identifier of the event being reviewed.
        report: Review report with keys verdict, evidence_frames, counterexample, artwork_needed.

    Returns:
        {"status": "ok", "event_id": str} on success; {"status": "error", "event_id": str, "reason": str} on failure.
    """
    # Validate report is a dict
    if not isinstance(report, dict):
        reason = "report must be a dict"
        _set_pending_with_error(state, event_id, reason)
        return {"status": "error", "event_id": event_id, "reason": reason}

    # Validate required keys
    required_keys = {"verdict", "evidence_frames", "counterexample", "artwork_needed"}
    missing = required_keys - set(report.keys())
    if missing:
        reason = f"missing keys: {', '.join(sorted(missing))}"
        _set_pending_with_error(state, event_id, reason)
        return {"status": "error", "event_id": event_id, "reason": reason}

    verdict = report["verdict"]
    evidence_frames = report["evidence_frames"]
    counterexample = report["counterexample"]
    artwork_needed = report["artwork_needed"]

    # Validate verdict is a string and in VALID_VERDICTS
    if not isinstance(verdict, str) or verdict not in VALID_VERDICTS:
        reason = "invalid verdict"
        _set_pending_with_error(state, event_id, reason)
        return {"status": "error", "event_id": event_id, "reason": reason}

    # Validate evidence_frames is list of ints (reject bools, accept numpy ints)
    if not isinstance(evidence_frames, list) or not all(isinstance(f, numbers.Integral) and not isinstance(f, bool) for f in evidence_frames):
        reason = "evidence_frames must be a list of ints"
        _set_pending_with_error(state, event_id, reason)
        return {"status": "error", "event_id": event_id, "reason": reason}

    # Validate counterexample and artwork_needed are strings
    if not isinstance(counterexample, str) or not isinstance(artwork_needed, str):
        reason = "counterexample and artwork_needed must be strings"
        _set_pending_with_error(state, event_id, reason)
        return {"status": "error", "event_id": event_id, "reason": reason}

    # All valid: update state
    state[event_id] = {
        "disposition": "REVIEWED",
        "verdict": verdict,
        "evidence_frames": evidence_frames,
        "counterexample": counterexample,
        "artwork_needed": artwork_needed,
        "basis_event_ids": None,
    }
    return {"status": "ok", "event_id": event_id}


def _set_pending_with_error(state: dict[str, dict[str, Any]], event_id: str, reason: str) -> None:
    """Set event disposition to PENDING_REVIEW and record error reason, clearing review-specific fields."""
    state[event_id] = {
        "disposition": "PENDING_REVIEW",
        "error": reason,
    }


def coverage(state: dict[str, dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute coverage counts and unaccounted events.

    Args:
        state: Mapping of event_id -> event record with disposition.
        events: List of event dicts each containing "event_id".

    Returns:
        Dict with status, counts per known disposition (only for events in `events`), and unaccounted count.
    """
    # Collect event IDs from the events list
    event_ids = set()
    for ev in events:
        if isinstance(ev, dict):
            eid = ev.get("event_id")
            if isinstance(eid, str):
                event_ids.add(eid)

    # Count dispositions only for event IDs present in events
    counts: dict[str, int] = {}
    for eid in event_ids:
        record = state.get(eid)
        if not isinstance(record, dict):
            continue
        disp = record.get("disposition")
        if disp is not None:
            counts[disp] = counts.get(disp, 0) + 1

    # Ensure known dispositions appear with zero counts if absent
    for disp in KNOWN_DISPOSITIONS:
        counts.setdefault(disp, 0)

    unaccounted = 0
    for ev in events:
        if not isinstance(ev, dict) or "event_id" not in ev:
            unaccounted += 1
            continue
        eid = ev["event_id"]
        if not isinstance(eid, str):
            unaccounted += 1
            continue
        record = state.get(eid)
        if record is None:
            unaccounted += 1
        else:
            if not isinstance(record, dict):
                unaccounted += 1
            else:
                disp = record.get("disposition")
                if disp not in KNOWN_DISPOSITIONS:
                    unaccounted += 1

    return {"status": "ok", "counts": counts, "unaccounted": unaccounted}


def assert_complete(state: dict[str, dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    """Assert that all events are accounted for and none are pending.

    Args:
        state: Mapping of event_id -> event record.
        events: List of event dicts each containing "event_id".

    Returns:
        {"status": "ok"} if complete.

    Raises:
        AssertionError: If unaccounted > 0 or any event in the events list has disposition PENDING_REVIEW.
    """
    cov = coverage(state, events)
    unaccounted = cov["unaccounted"]
    # Count PENDING_REVIEW only for events in the events list
    event_ids = set()
    for ev in events:
        if isinstance(ev, dict):
            eid = ev.get("event_id")
            if isinstance(eid, str):
                event_ids.add(eid)
    pending = 0
    for eid in event_ids:
        record = state.get(eid)
        if record and isinstance(record, dict) and record.get("disposition") == "PENDING_REVIEW":
            pending += 1
    if unaccounted > 0 or pending > 0:
        raise AssertionError(f"Incomplete: {pending} PENDING_REVIEW, {unaccounted} unaccounted")
    return {"status": "ok"}


def patterns_and_exceptions(state: dict[str, dict[str, Any]], clusters: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize verdict distributions and counterexamples per cluster.

    Args:
        state: Mapping of event_id -> event record.
        clusters: List of cluster dicts with "cluster_id" and "members" (list of event_ids).

    Returns:
        Dict with status and patterns list.
    """
    patterns = []
    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        cluster_id = cluster.get("cluster_id", "")
        members = cluster.get("members", [])
        verdict_dist: dict[str, int] = {}
        when_it_fails: list[str] = []
        for eid in members:
            record = state.get(eid)
            if not record or not isinstance(record, dict):
                continue
            if record.get("disposition") != "REVIEWED":
                continue
            verdict = record.get("verdict")
            if verdict:
                verdict_dist[verdict] = verdict_dist.get(verdict, 0) + 1
            counterexample = record.get("counterexample", "")
            # Include all counterexamples from REVIEWED members regardless of verdict
            when_it_fails.append(counterexample)
        patterns.append({
            "cluster_id": cluster_id,
            "verdict_distribution": verdict_dist,
            "when_it_fails": when_it_fails,
        })
    return {"status": "ok", "patterns": patterns}
