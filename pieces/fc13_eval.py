"""FC13E: frozen, blinded A/B evaluation protocol for Fast-Close V1.3.

Writes the protocol, a blinding key and an empty blinded rating sheet.
Makes no model call and reads only the snapshot folder.
"""
import csv
import hashlib
import json
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS_REL = Path("work/phase1/departments_16/fastclose_v13/inputs")
INPUTS = ROOT / INPUTS_REL
OUT_DIR = ROOT / "work/phase1/departments_16/fastclose_v13"
SCENES = ("S3", "S6", "S8")
ARMS = ("A", "B")
TRANSITIONS = ("cut", "slide", "pan_bridge")
CLOSEUPS = ("07_character_reaction", "08_emotional_closeup", "10_object_hand_insert")
FLAT_OK = ("03_slow_cinematic_push", "10_object_hand_insert", "11_scene_transition")
STRONG = 0.20
OVI_REF = re.compile(r"^A[0-9]+:[0-9]+$")
QS = ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6")
SHEET_FIELDS = ["scene", "label", "anon_id", *QS, "preference", "notes"]
RISK_WORDS = ("lesson", "experimental", "baseline", "assisted")

RUBRIC = [
    {
        "id": "Q1",
        "name": "narrative clarity",
        "question": "Can a viewer follow what happens and why?",
        "anchor_1": "The viewer cannot tell what happens or why.",
        "anchor_3": "The main events are clear, but one link or motive is missing.",
        "anchor_5": "Every event and its reason follow in order without confusion.",
    },
    {
        "id": "Q2",
        "name": "emotional communication",
        "question": "Is the stated feeling conveyed without invention?",
        "anchor_1": "The feeling is missing, or the pictures contradict it.",
        "anchor_3": "The feeling is visible but only partly shown, or a little is invented.",
        "anchor_5": "The feeling is shown plainly and nothing beyond the source is added.",
    },
    {
        "id": "Q3",
        "name": "visual storytelling",
        "question": "Do the pictures carry the scene, not only the narration?",
        "anchor_1": "The pictures only repeat the narration or leave out what the story needs.",
        "anchor_3": "Some beats are carried by the pictures and some only by the narration.",
        "anchor_5": "The pictures alone show the main action, the reaction and the place.",
    },
    {
        "id": "Q4",
        "name": "shot progression",
        "question": "Does the order of framings and transitions clarify events, reactions, reveals and space?",
        "anchor_1": "Framings and transitions confuse who is where or what changed.",
        "anchor_3": "The order is mostly clear, but one reaction or space change is unclear.",
        "anchor_5": "Each framing and transition makes the next event, reaction or space easy to read.",
    },
    {
        "id": "Q5",
        "name": "canon fidelity",
        "question": "Is there nothing beyond the ovis and PACKET, and is every claim sourced?",
        "anchor_1": "Several claims are unsourced or invented.",
        "anchor_3": "Claims are sourced, but one detail is loose or unsourced.",
        "anchor_5": "Every claim traces to an ovi or PACKET and nothing is added.",
    },
    {
        "id": "Q6",
        "name": "production feasibility",
        "question": "Can it be built with the registered presets and flat final images?",
        "anchor_1": "It needs new presets or images the registry does not have.",
        "anchor_3": "It is buildable with a few new images or a close substitute.",
        "anchor_5": "It is buildable now with registered presets and flat final images.",
    },
]

COMPLIANCE_DEFINITIONS = {
    "C1_opening": "First shot's preset, and whether its first person, event, prop or scenery claim cites an ovi.",
    "C2_camera": "Shot count, distinct presets, adjacent same-preset pairs, and adjacent pairs where both presets have gain >= 0.20.",
    "C3_reaction": "Whether a shot holding the turn ovi has a pose claim sourced to an ovi, and how many shots mention the narrator.",
    "C4_progression": "Transitions outside cut, slide and pan_bridge; unknown presets; NEED_NEW count; whether a close-up preset carries the turn ovi.",
    "C5_quiet": "Gains of the visual-only shots, and how many are at or above 0.20. Descriptive only.",
}

DECISION_RULE = (
    "For each scene, the arm the rater prefers wins the scene only if its Q1-Q6 total is at least "
    "the other arm's total, its Q5 (canon fidelity) is at least the other arm's, and its validator "
    "error count is no higher; otherwise the scene is a TIE, and a TIE preference is a TIE. The verdict "
    "is B_BETTER if B wins at least 2 scenes, A_BETTER if A wins at least 2 scenes, and "
    "NO_CLEAR_DIFFERENCE otherwise. Compliance counts never enter this rule. The decision is "
    "symmetric between the arms and never assumes that arm B is better."
)


def load_gains(inputs_dir):
    base = Path(inputs_dir) / "presets"
    index = json.loads((base / "index.json").read_text(encoding="utf-8"))
    gains = {}
    for item in index:
        preset = item["preset"]
        data = json.loads((base / f"{preset}.json").read_text(encoding="utf-8"))
        segments = data["segments"]
        start = segments[0]["camera"]["start"]["zoom"]
        end = segments[-1]["camera"]["end"]["zoom"]
        gains[preset] = round(end - start, 2)
    if len(gains) != 11:
        raise ValueError(f"expected 11 presets, found {len(gains)}")
    return gains


def visual_only(timing, scene):
    for entry in timing["scenes"]:
        if entry["scene"] == scene:
            return [shot["shot"] for shot in entry["shots"] if not shot["lines_starting"]]
    raise ValueError(f"unknown scene: {scene}")


def _shots(result):
    plan = result.get("plan")
    if not isinstance(plan, dict):
        return None
    shots = plan.get("shots")
    if not isinstance(shots, list) or not shots:
        return None
    return shots


def _sourced(claim):
    source = claim.get("source")
    return isinstance(source, str) and OVI_REF.match(source) is not None


def compliance(result, gains, visual_only_shots):
    shots = _shots(result)
    if shots is None:
        return {"computable": False, "reason": "no plan"}
    turn_ovi = (result["plan"].get("turn") or {}).get("ovi")
    presets = [shot["preset"] for shot in shots]
    n = len(shots)
    pairs = range(n - 1)

    def strong(preset):
        return preset in gains and gains[preset] >= STRONG

    first = shots[0]
    turn_pose = any(
        turn_ovi in shot.get("ovi_ids", [])
        and any(c.get("kind") == "pose" and _sourced(c) for c in shot.get("claims", []))
        for shot in shots
    )
    vo_gains = [gains.get(shots[k - 1]["preset"]) for k in visual_only_shots if 1 <= k <= n]
    return {
        "computable": True,
        "C1_opening": {
            "first_preset": first["preset"],
            "first_shot_source_cited": any(
                c.get("kind") in ("person", "event", "prop", "scenery") and _sourced(c)
                for c in first.get("claims", [])
            ),
        },
        "C2_camera": {
            "shots": n,
            "distinct_presets": len(set(presets)),
            "same_preset_consecutive_pairs": sum(presets[i] == presets[i + 1] for i in pairs),
            "strong_consecutive_pairs": sum(strong(presets[i]) and strong(presets[i + 1]) for i in pairs),
        },
        "C3_reaction": {
            "turn_ovi": turn_ovi,
            "turn_shot_has_ovi_pose": turn_pose,
            "narrator_mentions": sum("narrat" in shot.get("performance", "").lower() for shot in shots),
        },
        "C4_progression": {
            "invalid_transitions": sum(shot["transition_out"] not in TRANSITIONS for shot in shots),
            "unknown_presets": sum(p not in gains and p != "NEED_NEW" for p in presets),
            "need_new": sum(p == "NEED_NEW" for p in presets),
            "closeup_on_turn": any(
                shot["preset"] in CLOSEUPS and turn_ovi in shot.get("ovi_ids", []) for shot in shots
            ),
        },
        "C5_quiet": {
            "visual_only_gains": vo_gains,
            "quiet_strong_pushes": sum(g is not None and g >= STRONG for g in vo_gains),
        },
    }


def quality_facts(result):
    shots = _shots(result)
    errors = result.get("errors", [])
    warnings = result.get("warnings", [])
    plan = result.get("plan") if isinstance(result.get("plan"), dict) else {}
    images = plan.get("images_needed")
    facts = {
        "validator_result": result["result"],
        "validator_errors": len(errors),
        "warnings": len(warnings),
        "staging_warnings": sum("STAGING" in w for w in warnings),
        "need_new": 0,
        "flat_compatible_share": None,
        "images_needed": len(images) if isinstance(images, list) else 0,
    }
    if shots:
        facts["need_new"] = sum(shot["preset"] == "NEED_NEW" for shot in shots)
        facts["flat_compatible_share"] = round(
            sum(shot["preset"] in FLAT_OK for shot in shots) / len(shots), 3
        )
    return facts


def blinded_view(result):
    shots = _shots(result)
    if shots is None:
        first = "; ".join(result.get("errors", [])[:3])
        text = f"NO VALID PLAN (experimental failure). Validator: {result['result']}; first errors: {first}"
    else:
        plan = result["plan"]
        turn = plan.get("turn") or {}
        lines = [f"Goal: {plan.get('goal', '')}", f"Turn: {turn.get('text', '')}"]
        for number, shot in enumerate(shots, 1):
            lines.append("")
            lines.append(f"shot {number}")
            lines.append(f"preset: {shot['preset']}")
            lines.append(f"ovi_ids: {', '.join(shot.get('ovi_ids', []))}")
            for field in ("action", "held_pose", "performance", "camera"):
                lines.append(f"{field}: {shot.get(field, '')}")
            lines.append(f"staging: {' | '.join(shot.get('staging', []))}")
            lines.append(f"transition_out: {shot['transition_out']}")
            lines.extend(f"dialogue: {d['meaning_en']}" for d in shot.get("dialogue", []))
        text = "\n".join(lines)
    risks = sorted(w for w in RISK_WORDS if w in text.lower())
    return text, risks


def make_key(seed):
    key = {}
    for scene in SCENES:
        even = hashlib.sha256((seed + "|" + scene).encode()).digest()[0] % 2 == 0
        first, second = ("P1", "P2") if even else ("P2", "P1")
        key[scene] = {"A": first, "B": second}
    return key


def anon_id(seed, scene, arm):
    return "X" + hashlib.sha256((seed + "|" + scene + "|" + arm).encode()).hexdigest()[:7]


def sheet_rows(key, seed):
    rows = []
    for scene in SCENES:
        for label in ("P1", "P2"):
            arm = next(a for a in ARMS if key[scene][a] == label)
            row = {"scene": scene, "label": label, "anon_id": anon_id(seed, scene, arm)}
            row.update({q: "" for q in QS})
            row["preference"] = ""
            row["notes"] = ""
            rows.append(row)
    return rows


def decide(ratings, key, facts):
    per_scene = {}
    for scene in SCENES:
        arm_of = {label: arm for arm, label in key[scene].items()}
        r = ratings[scene]
        preference = r["preference"]
        if preference not in arm_of:  # "TIE"
            per_scene[scene] = "TIE"
            continue
        win = arm_of[preference]
        other = "B" if win == "A" else "A"
        mine = r[key[scene][win]]
        theirs = r[key[scene][other]]
        ok = (
            sum(mine[q] for q in QS) >= sum(theirs[q] for q in QS)
            and mine["Q5"] >= theirs["Q5"]
            and facts[scene][win]["validator_errors"] <= facts[scene][other]["validator_errors"]
        )
        per_scene[scene] = win if ok else "TIE"
    wins_a = sum(v == "A" for v in per_scene.values())
    wins_b = sum(v == "B" for v in per_scene.values())
    if wins_b >= 2:
        verdict = "B_BETTER"
    elif wins_a >= 2:
        verdict = "A_BETTER"
    else:
        verdict = "NO_CLEAR_DIFFERENCE"
    return {"per_scene": per_scene, "verdict": verdict}


def protocol(root):
    inputs = Path(root) / INPUTS_REL
    timing = json.loads((inputs / "A1_timing_plan.json").read_text(encoding="utf-8"))
    body = {
        "schema": 1,
        "name": "FASTCLOSE_V13_EVAL_PROTOCOL",
        "scenes": list(SCENES),
        "arms": {"A": "baseline", "B": "baseline plus the five experimental director lessons"},
        "compliance_definitions": COMPLIANCE_DEFINITIONS,
        "quality_deterministic": list(QUALITY_KEYS),
        "rubric": RUBRIC,
        "decision_rule": DECISION_RULE,
        "visual_only": {scene: visual_only(timing, scene) for scene in SCENES},
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "snapshot_manifest_sha256": hashlib.sha256(
            (inputs / "SNAPSHOT_MANIFEST.json").read_bytes()
        ).hexdigest(),
    }
    body["protocol_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return body


QUALITY_KEYS = (
    "validator_result",
    "validator_errors",
    "warnings",
    "staging_warnings",
    "need_new",
    "flat_compatible_share",
    "images_needed",
)


def main(argv=None):
    proto = protocol(ROOT)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    key_path = OUT_DIR / "BLINDING_KEY.json"
    if key_path.exists():
        blinding = json.loads(key_path.read_text(encoding="utf-8"))
    else:
        seed = secrets.token_hex(16)
        blinding = {
            "seed": seed,
            "key": make_key(seed),
            "anon_ids": {s: {a: anon_id(seed, s, a) for a in ARMS} for s in SCENES},
        }
        key_path.write_text(json.dumps(blinding, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "EVAL_PROTOCOL.json").write_text(
        json.dumps(proto, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (OUT_DIR / "BLINDED_SHEET_TEMPLATE.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_FIELDS)
        writer.writeheader()
        writer.writerows(sheet_rows(blinding["key"], blinding["seed"]))
    print(proto["protocol_sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
