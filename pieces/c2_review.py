"""Review planning and frame re-extraction commands for cinematic analysis."""
from __future__ import annotations

import math
from typing import Any


def pick_representatives(cluster: dict, events: list[dict]) -> dict:
    """Pick best, ambiguous, failure representatives from a cluster."""
    members = cluster["members"]
    event_map = {e["event_id"]: e for e in events}
    cluster_events = [event_map[m] for m in members if m in event_map]
    if not cluster_events:
        return {"representatives": {}}

    # Sort by score descending
    sorted_events = sorted(cluster_events, key=lambda e: e.get("score", 0), reverse=True)
    best = sorted_events[0]["event_id"]
    failure = sorted_events[-1]["event_id"]

    # Ambiguous: closest to 0.5 score
    ambiguous = min(sorted_events, key=lambda e: abs(e.get("score", 0) - 0.5))["event_id"]

    return {"representatives": {"best": best, "ambiguous": ambiguous, "failure": failure}}


def fps_for(event: dict) -> int:
    """Determine target fps for re-extraction based on event properties."""
    if event.get("uncertain", False):
        return 8
    score = event.get("score", 0)
    duration_frames = event.get("end_frame", 0) - event.get("start_frame", 0)
    duration_sec = duration_frames / 30.0
    if score >= 0.8 and duration_sec <= 1.0:
        return 8
    return 4


def plan_review(clusters: list[dict], events: list[dict], reviewed_ids: set[str], budget: int) -> dict:
    """Build ordered review job list respecting budget."""
    event_map = {e["event_id"]: e for e in events}
    reviewed_verdicts = {}

    for eid in reviewed_ids:
        if eid in event_map:
            reviewed_verdicts[eid] = event_map[eid].get("disposition", "REVIEWED")

    all_jobs = []
    all_inferred = []

    # Process each cluster, sorted by cluster_id for deterministic ordering
    sorted_clusters = sorted(clusters, key=lambda c: c["cluster_id"])

    for cluster_idx, cluster in enumerate(sorted_clusters):
        cluster_id = cluster["cluster_id"]
        reps_result = pick_representatives(cluster, events)
        reps = reps_result["representatives"]
        rep_ids = list(reps.values())

        # Find reviewed representatives
        reviewed_reps = [r for r in rep_ids if r in reviewed_ids]

        # Check for disagreement among reviewed reps
        disagreement = False
        uncertain_reviewed = False
        if len(reviewed_reps) >= 2:
            verdicts = [reviewed_verdicts.get(r) for r in reviewed_reps]
            if len(set(v for v in verdicts if v)) > 1:
                disagreement = True
        for r in reviewed_reps:
            if event_map.get(r, {}).get("uncertain", False):
                uncertain_reviewed = True

        members = cluster["members"]
        unreviewed_members = [m for m in members if m not in reviewed_ids]

        if disagreement or uncertain_reviewed:
            # All unreviewed members become jobs
            reason = "DISAGREEMENT" if disagreement else "UNCERTAIN"
            for m in unreviewed_members:
                ev = event_map.get(m)
                if ev:
                    all_jobs.append({
                        "event_id": m,
                        "priority": 0,
                        "reason": reason,
                        "fps": fps_for(ev),
                        "_cluster_id": cluster_id,
                        "_cluster_idx": cluster_idx,
                        "_group": 1,  # expansion group
                        "_type_order": 0,
                    })
        else:
            # Agreeing or no reviewed reps
            # Representatives first (unreviewed ones) - deduplicate by event_id
            added_rep_ids = set()
            rep_priority = {"best": 0, "ambiguous": 1, "failure": 2}
            for rep_type in ["best", "ambiguous", "failure"]:
                rep_id = reps.get(rep_type)
                if rep_id and rep_id not in reviewed_ids and rep_id not in added_rep_ids:
                    ev = event_map.get(rep_id)
                    if ev:
                        reason_map = {"best": "REPRESENTATIVE_BEST", "ambiguous": "REPRESENTATIVE_AMBIGUOUS", "failure": "REPRESENTATIVE_FAILURE"}
                        all_jobs.append({
                            "event_id": rep_id,
                            "priority": 0,
                            "reason": reason_map[rep_type],
                            "fps": fps_for(ev),
                            "_cluster_id": cluster_id,
                            "_cluster_idx": cluster_idx,
                            "_group": 0,  # representative group
                            "_type_order": rep_priority[rep_type],
                        })
                        added_rep_ids.add(rep_id)

            # Verification: sample every 4th member (sorted by event_id), min 1
            sorted_members = sorted(members)
            verification_indices = list(range(0, len(sorted_members), 4))
            if not verification_indices:
                verification_indices = [0]
            verification_members = [sorted_members[i] for i in verification_indices if i < len(sorted_members)]
            # Only unreviewed verification members that are not already jobs become jobs
            for m in verification_members:
                if m not in reviewed_ids and m not in [j["event_id"] for j in all_jobs]:
                    ev = event_map.get(m)
                    if ev:
                        all_jobs.append({
                            "event_id": m,
                            "priority": 0,
                            "reason": "VERIFICATION",
                            "fps": fps_for(ev),
                            "_cluster_id": cluster_id,
                            "_cluster_idx": cluster_idx,
                            "_group": 2,  # verification group
                            "_type_order": 0,
                        })

            # Inferred: remaining unreviewed members
            basis_ids = reviewed_reps if reviewed_reps else rep_ids
            for m in unreviewed_members:
                if m not in [j["event_id"] for j in all_jobs]:
                    all_inferred.append({
                        "event_id": m,
                        "disposition": "INFERRED_FROM_CLUSTER",
                        "basis_event_ids": list(basis_ids)  # copy per record
                    })

    # Sort jobs: group 0=representatives, 1=expansion, 2=verification; then cluster_idx, type_order, event_id
    def job_sort_key(job):
        return (job["_group"], job["_cluster_idx"], job["_type_order"], job["event_id"])

    all_jobs.sort(key=job_sort_key)

    # Assign priorities
    for idx, job in enumerate(all_jobs):
        job["priority"] = idx + 1
        # Remove internal fields
        job.pop("_cluster_id", None)
        job.pop("_cluster_idx", None)
        job.pop("_group", None)
        job.pop("_type_order", None)

    # Apply budget (clamp to >= 0)
    budget = max(0, budget)
    jobs_within_budget = all_jobs[:budget]
    overflow_jobs = all_jobs[budget:]
    pending = [j["event_id"] for j in overflow_jobs]

    return {
        "status": "ok",
        "jobs": jobs_within_budget,
        "inferred": all_inferred,
        "pending": pending
    }


def reextract_cmd(source: str, event: dict, fps: int, out_dir: str) -> dict:
    """Generate ffmpeg command for frame re-extraction."""
    start_frame = event.get("start_frame", 0)
    end_frame = event.get("end_frame", 0)

    # Validate inputs
    if end_frame < start_frame:
        return {"status": "ERROR", "error": "end_frame < start_frame"}
    if fps not in (4, 8):
        return {"status": "ERROR", "error": "fps must be 4 or 8"}

    start_sec = start_frame / 30.0
    duration_sec = (end_frame - start_frame) / 30.0
    num_frames = math.ceil(duration_sec * fps) + 1

    argv = [
        "ffmpeg", "-y",
        "-ss", str(start_sec),
        "-i", source,
        "-vf", f"fps={fps}",
        "-frames:v", str(num_frames),
        f"{out_dir}/frame_%04d.png"
    ]
    return {"status": "ok", "argv": argv}
