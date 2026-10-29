import random
import math
from typing import Any, Callable


def blind_pairs(results_a: list[dict], results_b: list[dict], seed: int) -> dict:
    """Create blind A/B pairs with randomized X/Y assignment per scene."""
    if not isinstance(results_a, list) or not isinstance(results_b, list):
        return {
            "status": "error",
            "pairs": None,
            "key": None,
            "error": "results_a and results_b must be lists"
        }

    if len(results_a) != len(results_b):
        return {
            "status": "error",
            "pairs": None,
            "key": None,
            "error": "results_a and results_b must have same length"
        }

    for i, (a, b) in enumerate(zip(results_a, results_b)):
        if not isinstance(a, dict) or not isinstance(b, dict):
            return {
                "status": "error",
                "pairs": None,
                "key": None,
                "error": f"results_a[{i}] and results_b[{i}] must be dicts"
            }
        scene_id_a = a.get("scene_id")
        scene_id_b = b.get("scene_id")
        if not isinstance(scene_id_a, str) or not isinstance(scene_id_b, str):
            return {
                "status": "error",
                "pairs": None,
                "key": None,
                "error": f"scene_id must be a string at index {i}"
            }
        if scene_id_a != scene_id_b:
            return {
                "status": "error",
                "pairs": None,
                "key": None,
                "error": f"scene_id mismatch at index {i}: {scene_id_a} vs {scene_id_b}"
            }

    # Check for duplicate scene_ids (handle unhashable gracefully)
    scene_ids = []
    for a in results_a:
        sid = a.get("scene_id")
        try:
            if sid in scene_ids:
                return {
                    "status": "error",
                    "pairs": None,
                    "key": None,
                    "error": "duplicate scene_ids in results_a"
                }
            scene_ids.append(sid)
        except TypeError:
            return {
                "status": "error",
                "pairs": None,
                "key": None,
                "error": "scene_id must be hashable"
            }

    rng = random.Random(seed)
    pairs = []
    key = {}

    for a, b in zip(results_a, results_b):
        scene_id = a["scene_id"]
        # Use >= 0.5 to match spec worked example for seed=42
        if rng.random() >= 0.5:
            x_val, y_val = a, b
            x_label, y_label = "A", "B"
        else:
            x_val, y_val = b, a
            x_label, y_label = "B", "A"

        pairs.append({
            "scene_id": scene_id,
            "X": x_val,
            "Y": y_val
        })
        key[scene_id] = {"X": x_label, "Y": y_label}

    return {
        "status": "ok",
        "pairs": pairs,
        "key": key,
        "error": None
    }


def score_plan(plan: dict, validator: Callable[[dict], dict], assets: dict) -> dict:
    """Score a plan across multiple quality metrics."""
    if not isinstance(plan, dict):
        return {
            "status": "error",
            "metrics": None,
            "error": "plan must be a dict"
        }
    if not isinstance(assets, dict):
        return {
            "status": "error",
            "metrics": None,
            "error": "assets must be a dict"
        }

    if "shots" not in plan:
        return {
            "status": "error",
            "metrics": None,
            "error": "plan must have 'shots' key"
        }
    
    shots = plan.get("shots", [])
    if not isinstance(shots, list):
        return {
            "status": "error",
            "metrics": None,
            "error": "plan must have 'shots' as a list"
        }

    # Wrap validator call to catch exceptions
    try:
        validation = validator(plan)
    except Exception as e:
        return {
            "status": "error",
            "metrics": None,
            "error": f"validator raised exception: {e}"
        }

    if not isinstance(validation, dict):
        return {
            "status": "error",
            "metrics": None,
            "error": "validator must return a dict"
        }

    unsupported_facts = validation.get("unsupported_facts")
    continuity_errors = validation.get("continuity_errors")

    if not isinstance(unsupported_facts, list) or not isinstance(continuity_errors, list):
        return {
            "status": "error",
            "metrics": None,
            "error": "validator must return 'unsupported_facts' and 'continuity_errors' as lists"
        }

    canon_fidelity = len(unsupported_facts)
    continuity_errors_count = len(continuity_errors)

    purposes = set()
    comp_mov_pairs = []
    executability_count = 0
    need_new_count = 0
    sound_judgment = 0
    justified_silence_count = 0

    available_presets = assets.get("presets", set())
    available_assets = assets.get("assets", set())

    dict_shot_count = 0
    for shot in shots:
        if not isinstance(shot, dict):
            continue

        dict_shot_count += 1
        purpose = shot.get("purpose")
        if purpose is not None:
            try:
                purposes.add(purpose)
            except TypeError:
                # Unhashable purpose, skip
                pass

        composition = shot.get("composition")
        movement = shot.get("movement")
        if composition is not None and movement is not None:
            comp_mov_pairs.append((composition, movement))

        preset = shot.get("preset")
        asset = shot.get("asset")
        
        # Handle unhashable preset/asset gracefully
        try:
            preset_ok = preset in available_presets
        except TypeError:
            preset_ok = False
        try:
            asset_ok = asset in available_assets
        except TypeError:
            asset_ok = False
        
        if not preset_ok or not asset_ok:
            need_new_count += 1
        if preset_ok and asset_ok:
            executability_count += 1

        sfx = shot.get("sfx")
        justification = shot.get("justification")
        has_sfx = sfx is not None and str(sfx).strip() != ""
        has_justification = justification is not None and str(justification).strip() != ""

        if has_sfx and not has_justification:
            sound_judgment += 1
        if not has_sfx and has_justification:
            justified_silence_count += 1

    coverage = len(purposes)

    pair_counts = {}
    for pair in comp_mov_pairs:
        try:
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
        except TypeError:
            # Unhashable pair, skip
            pass
    repetition = sum(count - 1 for count in pair_counts.values() if count > 1)

    executability = executability_count / dict_shot_count if dict_shot_count > 0 else 0.0

    return {
        "status": "ok",
        "metrics": {
            "canon_fidelity": canon_fidelity,
            "coverage": coverage,
            "continuity_errors": continuity_errors_count,
            "repetition": repetition,
            "executability": executability,
            "need_new_count": need_new_count,
            "sound_judgment": sound_judgment,
            "justified_silence_count": justified_silence_count
        },
        "error": None
    }


def summarize(scores_a: list[dict], scores_b: list[dict], cost: dict) -> dict:
    """Summarize scores across scenes and compute deltas."""
    if not isinstance(scores_a, list) or not isinstance(scores_b, list):
        return {
            "status": "error",
            "summary": None,
            "error": "scores_a and scores_b must be lists"
        }
    if not isinstance(cost, dict):
        return {
            "status": "error",
            "summary": None,
            "error": "cost must be a dict"
        }

    if len(scores_a) != len(scores_b):
        return {
            "status": "error",
            "summary": None,
            "error": "scores_a and scores_b must have same length"
        }

    metric_names = [
        "canon_fidelity", "coverage", "continuity_errors", "repetition",
        "executability", "need_new_count", "sound_judgment", "justified_silence_count"
    ]

    # Validate cost keys
    required_cost_keys = [
        "kimi_calls_a", "kimi_calls_b",
        "tokens_a", "tokens_b",
        "timeouts_a", "timeouts_b",
        "retries_a", "retries_b",
        "owner_corrections_a", "owner_corrections_b"
    ]
    for key in required_cost_keys:
        if key not in cost:
            return {
                "status": "error",
                "summary": None,
                "error": f"cost missing required key: {key}"
            }
        val = cost[key]
        if not isinstance(val, int) or isinstance(val, bool):
            return {
                "status": "error",
                "summary": None,
                "error": f"cost key '{key}' must be an integer"
            }

    def avg_metrics(scores: list[dict]) -> dict:
        if not scores:
            return {m: 0.0 for m in metric_names}
        sums = {m: 0.0 for m in metric_names}
        for s in scores:
            if not isinstance(s, dict):
                return {
                    "status": "error",
                    "summary": None,
                    "error": "each score entry must be a dict"
                }
            # Require every metric key in each score entry
            for m in metric_names:
                if m not in s:
                    return {
                        "status": "error",
                        "summary": None,
                        "error": f"score entry missing required metric: {m}"
                    }
                val = s[m]
                if not isinstance(val, (int, float)) or isinstance(val, bool):
                    return {
                        "status": "error",
                        "summary": None,
                        "error": f"metric '{m}' must be numeric"
                    }
                if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                    return {
                        "status": "error",
                        "summary": None,
                        "error": f"metric '{m}' must be finite"
                    }
                sums[m] += val
        n = len(scores)
        return {m: sums[m] / n for m in metric_names}

    metrics_a = avg_metrics(scores_a)
    if isinstance(metrics_a, dict) and "status" in metrics_a:
        return metrics_a  # error dict

    metrics_b = avg_metrics(scores_b)
    if isinstance(metrics_b, dict) and "status" in metrics_b:
        return metrics_b  # error dict

    deltas = {m: metrics_b[m] - metrics_a[m] for m in metric_names}

    return {
        "status": "ok",
        "summary": {
            "metrics_a": metrics_a,
            "metrics_b": metrics_b,
            "deltas": deltas,
            "cost": cost
        },
        "error": None
    }


def promotion_verdict(summary: dict, owner_approved: bool, animatic_compared: bool) -> dict:
    """Determine promotion verdict based on summary and flags."""
    if not isinstance(summary, dict):
        return {
            "status": "ok",
            "verdict": "HOLD",
            "reasons": ["summary must be a dict"]
        }
    if summary.get("status") != "ok" or "summary" not in summary:
        return {
            "status": "ok",
            "verdict": "HOLD",
            "reasons": ["Invalid summary"]
        }

    data = summary["summary"]
    if not isinstance(data, dict):
        return {
            "status": "ok",
            "verdict": "HOLD",
            "reasons": ["summary.summary must be a dict"]
        }

    deltas = data.get("deltas")
    cost = data.get("cost")

    # Validate deltas and cost are dictionaries
    if not isinstance(deltas, dict):
        return {
            "status": "ok",
            "verdict": "HOLD",
            "reasons": ["incomplete summary: deltas must be a dict"]
        }
    if not isinstance(cost, dict):
        return {
            "status": "ok",
            "verdict": "HOLD",
            "reasons": ["incomplete summary: cost must be a dict"]
        }

    # Validate all eight delta fields exist and are numeric (not bool)
    all_delta_fields = [
        "canon_fidelity", "coverage", "continuity_errors", "repetition",
        "executability", "need_new_count", "sound_judgment", "justified_silence_count"
    ]
    for field in all_delta_fields:
        if field not in deltas:
            return {
                "status": "ok",
                "verdict": "HOLD",
                "reasons": [f"incomplete summary: missing delta field '{field}'"]
            }
        val = deltas[field]
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            return {
                "status": "ok",
                "verdict": "HOLD",
                "reasons": [f"incomplete summary: delta field '{field}' must be numeric"]
            }
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return {
                "status": "ok",
                "verdict": "HOLD",
                "reasons": [f"incomplete summary: delta field '{field}' must be finite"]
            }

    # Validate cost tokens exist and are numeric (not bool)
    if "tokens_a" not in cost or "tokens_b" not in cost:
        return {
            "status": "ok",
            "verdict": "HOLD",
            "reasons": ["incomplete summary: cost missing tokens_a or tokens_b"]
        }
    tokens_a = cost["tokens_a"]
    tokens_b = cost["tokens_b"]
    if not isinstance(tokens_a, (int, float)) or isinstance(tokens_a, bool):
        return {
            "status": "ok",
            "verdict": "HOLD",
            "reasons": ["incomplete summary: cost tokens must be numeric"]
        }
    if not isinstance(tokens_b, (int, float)) or isinstance(tokens_b, bool):
        return {
            "status": "ok",
            "verdict": "HOLD",
            "reasons": ["incomplete summary: cost tokens must be numeric"]
        }
    if isinstance(tokens_a, float) and (math.isnan(tokens_a) or math.isinf(tokens_a)):
        return {
            "status": "ok",
            "verdict": "HOLD",
            "reasons": ["incomplete summary: cost tokens must be finite"]
        }
    if isinstance(tokens_b, float) and (math.isnan(tokens_b) or math.isinf(tokens_b)):
        return {
            "status": "ok",
            "verdict": "HOLD",
            "reasons": ["incomplete summary: cost tokens must be finite"]
        }

    reasons = []

    if not owner_approved:
        reasons.append("owner_approved flag is False")
    if not animatic_compared:
        reasons.append("animatic_compared flag is False")

    if deltas.get("canon_fidelity", 0) > 0:
        reasons.append("canon_fidelity worsened")
    if deltas.get("continuity_errors", 0) > 0:
        reasons.append("continuity_errors worsened")

    positive_metrics = ["coverage", "executability", "justified_silence_count"]
    negative_metrics = ["repetition", "need_new_count", "sound_judgment"]

    improved_count = 0
    for m in positive_metrics:
        if deltas.get(m, 0) > 0:
            improved_count += 1
    for m in negative_metrics:
        if deltas.get(m, 0) < 0:
            improved_count += 1

    if improved_count < 2:
        reasons.append(f"Only {improved_count} of 6 secondary metrics improved (need at least 2): coverage, repetition, executability, need_new_count, sound_judgment, justified_silence_count")

    if tokens_a > 0:
        cost_increase = (tokens_b - tokens_a) / tokens_a
        if cost_increase >= 0.25:
            reasons.append(f"Cost increase {cost_increase * 100:.1f}% exceeds 25% threshold")

    verdict = "PROMOTE" if not reasons else "HOLD"
    return {
        "status": "ok",
        "verdict": verdict,
        "reasons": reasons
    }


def render_review_note() -> dict:
    """Return static reminder note about animatic comparison requirement."""
    return {
        "status": "ok",
        "note": "REMINDER: Animatic/render comparison is required. JSON validity alone is insufficient. Verdict must include animatic_compared field and cannot be PROMOTE if False."
    }
