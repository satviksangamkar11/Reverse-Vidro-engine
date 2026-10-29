"""Autonomous review/fix cycle for GranthStudio pieces.

Pure logic with injected callables; no network, no model calls.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple, Union


StateDict = Dict[str, Any]
Action = str
ReviewerText = Dict[str, str]
LogEntry = Tuple[int, str, str]
CycleResult = Dict[str, Union[List[str], int, List[LogEntry]]]

REQUIRED_DEPS = ("get_state", "relaunch", "run_reviewers", "apply_findings", "escalate", "sleep")


def decide(state: StateDict) -> Action:
    """Decide the next action for a piece based on its state.

    Priority order: WAIT, RELAUNCH, ESCALATE, FIX_TESTS, REVIEW, APPLY, DONE.
    """
    job_raw = state.get("job")
    if job_raw is None:
        job = "missing"
    else:
        job = job_raw.strip().lower()

    known_jobs = {"running", "missing", "failed", "escalate", "passed", "passed-no-review"}
    if job not in known_jobs:
        raise ValueError(f"Unknown job state: {job_raw!r}")

    tests_green = state.get("tests_green", False)
    changed = state.get("changed_since_review", False)
    last_review = state.get("last_review")

    # 1. WAIT
    if job == "running":
        return "WAIT"

    # 2. RELAUNCH
    if job in ("missing", "failed"):
        return "RELAUNCH"

    # 3. ESCALATE
    if job == "escalate":
        return "ESCALATE"

    # 4. FIX_TESTS
    if job in ("passed", "passed-no-review") and not tests_green:
        return "FIX_TESTS"

    # 5. REVIEW
    if tests_green and (last_review is None or changed):
        return "REVIEW"

    # 6. APPLY / 7. DONE (only reached if tests_green and review is current)
    if tests_green and not changed and last_review is not None:
        # Check for FINDINGS
        has_findings = any(v == "FINDINGS" for v in last_review.values())
        if has_findings:
            return "APPLY"

        # No FINDINGS - check for PASS and all-NO_REVIEW special case
        has_pass = any(v == "PASS" for v in last_review.values())
        main_reviewers = ("luna", "glm", "minimax")
        all_no_review = all(last_review.get(r) == "NO_REVIEW" for r in main_reviewers)

        if all_no_review:
            return "REVIEW"
        elif has_pass:
            return "DONE"
        else:
            # No PASS, no FINDINGS, not all NO_REVIEW -> treat as needing review
            return "REVIEW"

    # Fallback (should not happen with valid states)
    return "REVIEW"


def merge_findings(reviews: ReviewerText, minimum_len: int = 20) -> str:
    """Merge reviewer findings into a single string.

    Includes a reviewer if their text:
      - is not "NO_REVIEW"
      - does not start with "PASS" (unless it contains a HIGH/MED line)
      - has at least minimum_len characters (unless it contains a HIGH/MED line or is exactly "FINDINGS")

    Reviewers ordered: luna, glm, minimax, then others alphabetically.
    Returns empty string if nothing qualifies.
    """
    priority = ("luna", "glm", "minimax")
    ordered = [r for r in priority if r in reviews]
    others = sorted([r for r in reviews if r not in priority])
    ordered.extend(others)

    parts = []
    for reviewer in ordered:
        text = reviews[reviewer]
        if text == "NO_REVIEW":
            continue

        lines = text.splitlines()
        has_high_med = any("HIGH" in line or "MED" in line for line in lines)
        is_findings_verdict = text == "FINDINGS"

        if text.startswith("PASS") and not has_high_med:
            continue
        if len(text) < minimum_len and not has_high_med and not is_findings_verdict:
            continue

        parts.append(f"{reviewer}:\n{text}")

    return "\n\n".join(parts) if parts else ""


def run_cycles(
    ids: List[str],
    deps: Dict[str, Callable],
    max_cycles: int = 50,
    sleep_s: int = 60,
) -> CycleResult:
    """Run autonomous cycles over the given piece IDs.

    Args:
        ids: List of piece IDs to process.
        deps: Dictionary of injected callables:
            - get_state(id) -> state dict
            - relaunch(id)
            - run_reviewers(id) -> dict reviewer->text
            - apply_findings(id, text)
            - escalate(id)
            - sleep(seconds)
        max_cycles: Maximum number of cycles to run.
        sleep_s: Seconds to sleep between cycles.

    Returns:
        Dict with keys: "done" (list of IDs), "stuck" (list of IDs),
        "cycles" (int), "log" (list of (cycle, id, action) tuples).
    """
    missing = [k for k in REQUIRED_DEPS if k not in deps]
    if missing:
        raise ValueError(f"missing deps: {', '.join(sorted(missing))}")

    done: set[str] = set()
    stuck: set[str] = set()
    log: List[LogEntry] = []
    cycles_run = 0

    for cycle in range(1, max_cycles + 1):
        visited_any = False
        for pid in ids:
            if pid in done or pid in stuck:
                continue
            visited_any = True
            try:
                state = deps["get_state"](pid)
                # Check if already escalated more than 2 times
                if state.get("escalations", 0) > 2:
                    stuck.add(pid)
                    log.append((cycle, pid, "STUCK"))
                    continue

                action = decide(state)
                log.append((cycle, pid, action))

                if action == "RELAUNCH":
                    deps["relaunch"](pid)
                elif action == "ESCALATE":
                    deps["escalate"](pid)
                elif action == "REVIEW":
                    reviews = deps["run_reviewers"](pid)
                    # Reviews are stored by the injected callable; next get_state will reflect them.
                elif action == "APPLY":
                    findings_text = merge_findings(state.get("last_review", {}))
                    deps["apply_findings"](pid, findings_text)
                elif action == "FIX_TESTS":
                    deps["relaunch"](pid)
                elif action == "DONE":
                    done.add(pid)
                # WAIT does nothing
            except Exception as e:
                log.append((cycle, pid, f"ERROR:{type(e).__name__}"))

        if not visited_any:
            break
        cycles_run += 1
        deps["sleep"](sleep_s)

    return {
        "done": sorted(done),
        "stuck": sorted(stuck),
        "cycles": cycles_run,
        "log": log,
    }
