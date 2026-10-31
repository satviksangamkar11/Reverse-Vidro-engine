"""Tests for pieces/fc13_lessons.py (Fast-Close V1.3 final five lessons)."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fc13_lessons", HERE / "fc13_lessons.py")
fc13 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fc13)

GAINS = {
    "01_establishing_shot": 0.28,
    "02_environmental_parallax": 0.13,
    "03_slow_cinematic_push": 0.20,
    "04_character_entrance": 0.14,
    "05_bowing_prayer": 0.14,
    "06_blessing_gesture": 0.30,
    "07_character_reaction": 0.14,
    "08_emotional_closeup": 0.25,
    "09_dialogue_composition": 0.13,
    "10_object_hand_insert": 0.14,
    "11_scene_transition": 0.00,
}

STRONG = {"01_establishing_shot", "03_slow_cinematic_push", "06_blessing_gesture", "08_emotional_closeup"}

TEXTS = [
    "EXPERIMENTAL DIRECTOR LESSON 1, opening (technique only; the owner's notes above always win): "
    "open on the scene's most relevant source-supported subject, action, object or setting, cited to its ovi. "
    "Establish the place when the viewer needs it to follow the action; 01_establishing_shot is one option, not a rule. "
    "Show nothing the ovis or the PACKET do not name.",
    "EXPERIMENTAL DIRECTOR LESSON 2, camera variation (technique only; the owner's notes above always win): "
    "choose each registered preset for the shot's action, attention and emotion. "
    "Avoid strong push-ins back to back (01_establishing_shot, 03_slow_cinematic_push, 06_blessing_gesture, "
    "08_emotional_closeup: fixed zoom gain 0.20 or more) unless the beat gives a specific dramatic reason; "
    "repeating a preset is fine when continuity benefits.",
    "EXPERIMENTAL DIRECTOR LESSON 3, visible reactions (technique only; the owner's notes above always win): "
    "when an ovi describes an important character response, give it visible emphasis with a supported framing "
    "and a held pose that matches the ovi; the narrator may tell it too, but must not replace it entirely. "
    "Do not invent gestures, feelings or events the ovi does not state.",
    "EXPERIMENTAL DIRECTOR LESSON 4, shot progression (technique only; the owner's notes above always win): "
    "choose framing and transitions so that events, reactions, reveals and who-is-where stay clear; "
    "use only the registered presets and the transitions cut, slide and pan_bridge. "
    "Wide-to-close is not required, and slide or pan_bridge do not need a change of place.",
    "EXPERIMENTAL DIRECTOR LESSON 5, emotional restraint (technique only; the owner's notes above always win): "
    "in quiet or emotional moments prefer the least distracting movement whose image roles fit "
    "(09_dialogue_composition 0.13; 05_bowing_prayer, 07_character_reaction, 10_object_hand_insert 0.14), "
    "avoid unnecessary consecutive pushes, and never let a camera move suggest a story event the ovis do not state.",
]

REAL = fc13.load_registry(fc13.INPUTS)


def _tree_hashes(folder):
    return {
        str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }


def test_load_registry_real_gains():
    assert {pid: row["gain"] for pid, row in REAL.items()} == GAINS


def test_strong_presets_are_exactly_four():
    strong = {pid for pid, row in REAL.items() if row["gain"] >= 0.20}
    assert strong == STRONG


@pytest.mark.parametrize("position", range(5))
def test_lesson_text_matches_spec(position):
    assert fc13.LESSONS[position]["text"] == TEXTS[position]


def test_real_lessons_pass_check():
    assert fc13.check(fc13.LESSONS, REAL) == []


def test_flags_unknown_preset_in_l1():
    lessons = copy.deepcopy(fc13.LESSONS)
    lessons[0]["text"] += " 12_made_up_preset"
    assert fc13.check(lessons, REAL)


def test_flags_forbidden_word_in_l3():
    lessons = copy.deepcopy(fc13.LESSONS)
    lessons[2]["text"] += " Devayani"
    assert fc13.check(lessons, REAL)


def test_flags_missing_owner_phrase_in_l4():
    lessons = copy.deepcopy(fc13.LESSONS)
    lessons[3]["text"] = lessons[3]["text"].replace(fc13.OWNER_PHRASE, "")
    assert fc13.check(lessons, REAL)


def test_flags_excluded_preset_in_l5():
    lessons = copy.deepcopy(fc13.LESSONS)
    lessons[4]["text"] += " 02_environmental_parallax"
    assert fc13.check(lessons, REAL)


def test_flags_four_lessons():
    lessons = copy.deepcopy(fc13.LESSONS)[:4]
    assert fc13.check(lessons, REAL)


def test_main_writes_valid_output(tmp_path, monkeypatch):
    out = tmp_path / "LESSONS_FINAL.json"
    monkeypatch.setattr(fc13, "OUT", out)
    assert fc13.main([]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["prompt_lines"] == TEXTS
    assert data["problems"] == []


def test_main_leaves_inputs_untouched(tmp_path, monkeypatch):
    monkeypatch.setattr(fc13, "OUT", tmp_path / "LESSONS_FINAL.json")
    before = _tree_hashes(fc13.INPUTS)
    assert before
    fc13.main([])
    assert _tree_hashes(fc13.INPUTS) == before
