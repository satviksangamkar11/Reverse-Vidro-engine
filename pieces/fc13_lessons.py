"""Fast-Close V1.3 final five director lessons: data, checks, and LESSONS_FINAL.json writer.

Lessons stay EXPERIMENTAL and F4 stays UNCHANGED. Reads the snapshot folder only.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDER = Path("work") / "phase1" / "departments_16" / "fastclose_v13"
INPUTS = ROOT / FOLDER / "inputs"
OUT = ROOT / FOLDER / "LESSONS_FINAL.json"

TRANSITIONS = ("cut", "slide", "pan_bridge")
OWNER_PHRASE = "the owner's notes above always win"
FORBIDDEN = ("drill", "clay", "devayani", "kacha", "vow", "marry", "7434a0f7", "7a1e2b26")
EVIDENCE_KEYS = ("video", "interval_s", "observation", "provenance")
PRESET_ID = re.compile(r"[0-9][0-9]_[a-z_]+")

LESSONS = [
    {
        "id": "L1",
        "topic": "opening",
        "text": (
            "EXPERIMENTAL DIRECTOR LESSON 1, opening (technique only; the owner's notes above always win): "
            "open on the scene's most relevant source-supported subject, action, object or setting, cited to its ovi. "
            "Establish the place when the viewer needs it to follow the action; 01_establishing_shot is one option, not a rule. "
            "Show nothing the ovis or the PACKET do not name."
        ),
        "presets": [
            {"preset": "01_establishing_shot", "use": "the place itself matters first"},
            {"preset": "10_object_hand_insert", "use": "a named object or action leads"},
            {"preset": "03_slow_cinematic_push", "use": "one complete image of the subject"},
            {"preset": "02_environmental_parallax", "use": "a setting whose depth matters"},
        ],
        "when_applies": "the first shot of every scene.",
        "evidence": [
            {
                "video": "7a1e2b26",
                "interval_s": "0.0-1.88 and 3.5-4.0",
                "observation": "opens on the drill bit before the first wide view",
                "provenance": "owner Review 2 S01 and S03 (recorded by statement)",
            },
        ],
        "status": "EXPERIMENTAL",
        "f4": "UNCHANGED",
    },
    {
        "id": "L2",
        "topic": "camera variation",
        "text": (
            "EXPERIMENTAL DIRECTOR LESSON 2, camera variation (technique only; the owner's notes above always win): "
            "choose each registered preset for the shot's action, attention and emotion. "
            "Avoid strong push-ins back to back (01_establishing_shot, 03_slow_cinematic_push, 06_blessing_gesture, "
            "08_emotional_closeup: fixed zoom gain 0.20 or more) unless the beat gives a specific dramatic reason; "
            "repeating a preset is fine when continuity benefits."
        ),
        "presets": [
            {"preset": "01_establishing_shot", "use": "strong push (gain 0.20 or more)"},
            {"preset": "03_slow_cinematic_push", "use": "strong push (gain 0.20 or more)"},
            {"preset": "06_blessing_gesture", "use": "strong push (gain 0.20 or more)"},
            {"preset": "08_emotional_closeup", "use": "strong push (gain 0.20 or more)"},
        ],
        "when_applies": "every pair of consecutive shots.",
        "evidence": [
            {
                "video": "7434a0f7",
                "interval_s": "0.5-11.0 and 11.7-12.8",
                "observation": "slow zooms through the setup; the one strong zoom lands on the proposal line",
                "provenance": "owner Review 1 B03, B04, B06 and B10 (owner-confirmed)",
            },
        ],
        "status": "EXPERIMENTAL",
        "f4": "UNCHANGED",
    },
    {
        "id": "L3",
        "topic": "visible reactions",
        "text": (
            "EXPERIMENTAL DIRECTOR LESSON 3, visible reactions (technique only; the owner's notes above always win): "
            "when an ovi describes an important character response, give it visible emphasis with a supported framing "
            "and a held pose that matches the ovi; the narrator may tell it too, but must not replace it entirely. "
            "Do not invent gestures, feelings or events the ovi does not state."
        ),
        "presets": [
            {"preset": "07_character_reaction", "use": "one face"},
            {"preset": "08_emotional_closeup", "use": "a quiet face beat"},
            {"preset": "03_slow_cinematic_push", "use": "a complete close image"},
            {"preset": "09_dialogue_composition", "use": "two people facing each other"},
            {"preset": "05_bowing_prayer", "use": "a bow the ovi states"},
        ],
        "when_applies": "a shot whose ovi states a person's response.",
        "evidence": [
            {
                "video": "7434a0f7",
                "interval_s": "3.0-4.5 and 5.0-6.5",
                "observation": "one character acts, then the other responds, in order",
                "provenance": "owner Review 1 B04 and B05 (owner's words)",
            },
            {
                "video": "7434a0f7",
                "interval_s": "9.5-11.0",
                "observation": "an entrance read as a reveal",
                "provenance": "owner Review 1 B09 (owner-confirmed)",
            },
        ],
        "status": "EXPERIMENTAL",
        "f4": "UNCHANGED",
    },
    {
        "id": "L4",
        "topic": "shot progression",
        "text": (
            "EXPERIMENTAL DIRECTOR LESSON 4, shot progression (technique only; the owner's notes above always win): "
            "choose framing and transitions so that events, reactions, reveals and who-is-where stay clear; "
            "use only the registered presets and the transitions cut, slide and pan_bridge. "
            "Wide-to-close is not required, and slide or pan_bridge do not need a change of place."
        ),
        "presets": [
            {"preset": "01_establishing_shot", "use": "registered"},
            {"preset": "02_environmental_parallax", "use": "registered"},
            {"preset": "03_slow_cinematic_push", "use": "registered"},
            {"preset": "04_character_entrance", "use": "registered"},
            {"preset": "05_bowing_prayer", "use": "registered"},
            {"preset": "06_blessing_gesture", "use": "registered"},
            {"preset": "07_character_reaction", "use": "registered"},
            {"preset": "08_emotional_closeup", "use": "registered"},
            {"preset": "09_dialogue_composition", "use": "registered"},
            {"preset": "10_object_hand_insert", "use": "registered"},
            {"preset": "11_scene_transition", "use": "registered"},
        ],
        "when_applies": "the order of shots and every transition_out.",
        "evidence": [
            {
                "video": "7434a0f7",
                "interval_s": "8.97-46.9",
                "observation": "transitions through black between scenes; cuts within",
                "provenance": "frozen detector STEP4_MEASUREMENTS.json plus owner visual read round 2; 4.93 s and 12.9 s OPEN",
            },
        ],
        "status": "EXPERIMENTAL",
        "f4": "UNCHANGED",
    },
    {
        "id": "L5",
        "topic": "emotional restraint",
        "text": (
            "EXPERIMENTAL DIRECTOR LESSON 5, emotional restraint (technique only; the owner's notes above always win): "
            "in quiet or emotional moments prefer the least distracting movement whose image roles fit "
            "(09_dialogue_composition 0.13; 05_bowing_prayer, 07_character_reaction, 10_object_hand_insert 0.14), "
            "avoid unnecessary consecutive pushes, and never let a camera move suggest a story event the ovis do not state."
        ),
        "presets": [
            {"preset": "09_dialogue_composition", "use": "0.13"},
            {"preset": "05_bowing_prayer", "use": "0.14"},
            {"preset": "07_character_reaction", "use": "0.14"},
            {"preset": "10_object_hand_insert", "use": "0.14"},
        ],
        "when_applies": "visual-only shots of the timeline and ovis that state silence, stillness or devotion.",
        "evidence": [
            {
                "video": "7a1e2b26",
                "interval_s": "0.0-12.0",
                "observation": "the camera stays still between cuts",
                "provenance": "owner round 3 (owner-reported, not human-verified)",
            },
        ],
        "status": "EXPERIMENTAL",
        "f4": "UNCHANGED",
    },
]


def load_registry(inputs_dir):
    inputs_dir = Path(inputs_dir)
    index = json.loads((inputs_dir / "presets" / "index.json").read_text(encoding="utf-8"))
    if len(index) != 11:
        raise ValueError(f"index.json lists {len(index)} presets, expected 11")
    registry = {}
    for item in index:
        preset_id = item["preset"]
        path = inputs_dir / "presets" / f"{preset_id}.json"
        if not path.is_file():
            raise ValueError(f"preset file missing: {preset_id}")
        segments = json.loads(path.read_text(encoding="utf-8"))["segments"]
        start = segments[0]["camera"]["start"]["zoom"]
        end = segments[-1]["camera"]["end"]["zoom"]
        registry[preset_id] = {
            "gain": round(end - start, 2),
            "zoom": [start, end],
            "roles": list(item["assets"]),
        }
    return registry


def preset_ids(text):
    found = []
    for match in PRESET_ID.findall(text):
        if match not in found:
            found.append(match)
    return found


def check(lessons, registry):
    problems = []
    if len(lessons) != 5:
        problems.append(f"expected 5 lessons, got {len(lessons)}")
    for position, lesson in enumerate(lessons, start=1):
        lesson_id = lesson.get("id", f"#{position}")
        text = lesson.get("text", "")
        lowered = text.lower()
        in_text = preset_ids(text)
        listed = [p.get("preset", "") for p in lesson.get("presets", [])]

        if not text.startswith(f"EXPERIMENTAL DIRECTOR LESSON {position},"):
            problems.append(f"{lesson_id}: text does not start with 'EXPERIMENTAL DIRECTOR LESSON {position},'")
        if OWNER_PHRASE not in text:
            problems.append(f"{lesson_id}: owner phrase missing")
        for preset_id in in_text + listed:
            if preset_id not in registry:
                problems.append(f"{lesson_id}: unknown preset {preset_id}")
        for word in FORBIDDEN:
            if word in lowered:
                problems.append(f"{lesson_id}: forbidden word {word!r}")
        if len(text) > 700:
            problems.append(f"{lesson_id}: text longer than 700 characters")
        if lesson.get("status") != "EXPERIMENTAL":
            problems.append(f"{lesson_id}: status is not EXPERIMENTAL")
        if lesson.get("f4") != "UNCHANGED":
            problems.append(f"{lesson_id}: f4 is not UNCHANGED")

        evidence = lesson.get("evidence") or []
        if not evidence:
            problems.append(f"{lesson_id}: no evidence")
        for item in evidence:
            missing = [key for key in EVIDENCE_KEYS if key not in item]
            if missing:
                problems.append(f"{lesson_id}: evidence missing {missing}")

        if lesson_id == "L2":
            strong = {pid for pid, row in registry.items() if row["gain"] >= 0.20}
            if set(in_text) != strong:
                problems.append(f"{lesson_id}: preset set {sorted(in_text)} is not the gain >= 0.20 set")
        if lesson_id == "L4":
            for word in TRANSITIONS:
                if word not in lowered:
                    problems.append(f"{lesson_id}: transition {word!r} missing")
        if lesson_id == "L5":
            for preset_id in in_text:
                row = registry.get(preset_id)
                if row is None:
                    continue
                if row["gain"] > 0.14 or preset_id == "11_scene_transition":
                    problems.append(f"{lesson_id}: preset {preset_id} is not allowed for restraint")
                # Gain alone misses 02 (0.13) and 04 (0.14), which the spec excludes by name.
                if preset_id not in listed:
                    problems.append(f"{lesson_id}: text names {preset_id}, which is not in its presets list")
    return problems


def build(root):
    inputs = Path(root) / FOLDER / "inputs"
    manifest = (inputs / "SNAPSHOT_MANIFEST.json").read_bytes()
    registry = load_registry(inputs)
    return {
        "schema": 1,
        "name": "FASTCLOSE_V13_LESSONS_FINAL",
        "status": "EXPERIMENTAL",
        "f4": "UNCHANGED",
        "snapshot_manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "registry": {pid: row["gain"] for pid, row in registry.items()},
        "lessons": LESSONS,
        "prompt_lines": [lesson["text"] for lesson in LESSONS],
        "problems": check(LESSONS, registry),
    }


def main(argv=None):
    result = build(ROOT)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"problems: {len(result['problems'])}")
    return 0 if not result["problems"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
