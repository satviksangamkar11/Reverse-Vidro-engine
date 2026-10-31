import csv
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "work" / "phase1" / "departments_16" / "fastclose_v13" / "inputs"
SCENES = ("S3", "S6", "S8")
QS = ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6")

_spec = importlib.util.spec_from_file_location("fc13_eval", ROOT / "pieces" / "fc13_eval.py")
fc13 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fc13)


def _read(name):
    return json.loads((INPUTS / name).read_text(encoding="utf-8"))


SAMPLE = _read("sample_scene_result_S4.json")
TIMING = _read("A1_timing_plan.json")


def _scores(value, q5=None):
    scores = {q: value for q in QS}
    if q5 is not None:
        scores["Q5"] = q5
    return scores


def _flat_facts():
    return {s: {"A": {"validator_errors": 0}, "B": {"validator_errors": 0}} for s in SCENES}


def test_load_gains_matches_real_presets():
    expected = {
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
    assert fc13.load_gains(INPUTS) == expected


def test_visual_only_real_timing_plan():
    assert fc13.visual_only(TIMING, "S3") == [6]
    assert fc13.visual_only(TIMING, "S6") == [5, 6]
    assert fc13.visual_only(TIMING, "S8") == [5]


def test_compliance_real_sample():
    gains = fc13.load_gains(INPUTS)
    c = fc13.compliance(SAMPLE, gains, [4])
    assert c["computable"] is True
    assert c["C1_opening"] == {"first_preset": "01_establishing_shot", "first_shot_source_cited": True}
    assert c["C2_camera"] == {
        "shots": 5,
        "distinct_presets": 4,
        "same_preset_consecutive_pairs": 0,
        "strong_consecutive_pairs": 2,
    }
    assert c["C3_reaction"] == {"turn_ovi": "A1:112", "turn_shot_has_ovi_pose": True, "narrator_mentions": 4}
    assert c["C4_progression"] == {
        "invalid_transitions": 0,
        "unknown_presets": 0,
        "need_new": 0,
        "closeup_on_turn": True,
    }
    assert c["C5_quiet"] == {"visual_only_gains": [0.25], "quiet_strong_pushes": 1}


def test_quality_facts_real_sample():
    assert fc13.quality_facts(SAMPLE) == {
        "validator_result": "VALID",
        "validator_errors": 0,
        "warnings": 3,
        "staging_warnings": 3,
        "need_new": 0,
        "flat_compatible_share": 0.4,
        "images_needed": 9,
    }


def test_no_plan_is_recorded_not_dropped():
    result = {
        "scene": 9,
        "result": "INVALID",
        "errors": ["e1", "e2", "e3", "e4"],
        "warnings": [],
        "plan": None,
    }
    gains = fc13.load_gains(INPUTS)
    assert fc13.compliance(result, gains, []) == {"computable": False, "reason": "no plan"}
    assert fc13.quality_facts(result)["validator_result"] == "INVALID"
    text, _ = fc13.blinded_view(result)
    assert text.startswith("NO VALID PLAN")


def test_two_shot_fixture_counts():
    result = {
        "scene": 1,
        "result": "VALID",
        "errors": [],
        "warnings": [],
        "plan": {
            "goal": "g",
            "turn": {"ovi": "A1:1", "text": "t"},
            "shots": [
                {
                    "preset": "03_slow_cinematic_push",
                    "ovi_ids": ["A1:1"],
                    "claims": [],
                    "performance": "",
                    "transition_out": "dissolve",
                },
                {
                    "preset": "03_slow_cinematic_push",
                    "ovi_ids": [],
                    "claims": [],
                    "performance": "",
                    "transition_out": "cut",
                },
            ],
            "images_needed": [],
        },
    }
    c = fc13.compliance(result, fc13.load_gains(INPUTS), [])
    assert c["C2_camera"]["same_preset_consecutive_pairs"] == 1
    assert c["C2_camera"]["strong_consecutive_pairs"] == 1
    assert c["C4_progression"]["invalid_transitions"] == 1


def test_make_key_labels_differ_and_match_hashlib():
    seed = "fixed-seed"
    key = fc13.make_key(seed)
    for scene in SCENES:
        assert {key[scene]["A"], key[scene]["B"]} == {"P1", "P2"}
        first_byte = hashlib.sha256(f"{seed}|{scene}".encode()).digest()[0]
        expected_a = "P1" if first_byte % 2 == 0 else "P2"
        assert key[scene]["A"] == expected_a


def test_symmetry_swapping_labels_flips_verdict():
    key = fc13.make_key("fixed-seed")
    ratings = {}
    for scene in SCENES[:2]:
        a, b = key[scene]["A"], key[scene]["B"]
        ratings[scene] = {a: _scores(3), b: _scores(4), "preference": b}
    ratings["S8"] = {"P1": _scores(3), "P2": _scores(3), "preference": "TIE"}

    decided = fc13.decide(ratings, key, _flat_facts())
    assert decided["verdict"] == "B_BETTER"
    assert decided["per_scene"]["S3"] == "B"

    swapped = {s: {"A": key[s]["B"], "B": key[s]["A"]} for s in SCENES}
    assert fc13.decide(ratings, swapped, _flat_facts())["verdict"] == "A_BETTER"


def test_equal_ratings_no_clear_difference():
    key = fc13.make_key("fixed-seed")
    ratings = {s: {"P1": _scores(3), "P2": _scores(3), "preference": "TIE"} for s in SCENES}
    assert fc13.decide(ratings, key, _flat_facts())["verdict"] == "NO_CLEAR_DIFFERENCE"


def test_canon_guard_q5_and_validator_errors():
    key = fc13.make_key("fixed-seed")
    a, b = key["S3"]["A"], key["S3"]["B"]
    ratings = {s: {"P1": _scores(3), "P2": _scores(3), "preference": "TIE"} for s in SCENES}

    ratings["S3"] = {a: _scores(3), b: _scores(4), "preference": b}
    assert fc13.decide(ratings, key, _flat_facts())["per_scene"]["S3"] == "B"

    ratings["S3"] = {a: _scores(3), b: {**_scores(4), "Q5": 2}, "preference": b}
    assert fc13.decide(ratings, key, _flat_facts())["per_scene"]["S3"] == "TIE"

    ratings["S3"] = {a: _scores(3), b: _scores(4), "preference": b}
    facts = _flat_facts()
    facts["S3"]["B"]["validator_errors"] = 1
    assert fc13.decide(ratings, key, facts)["per_scene"]["S3"] == "TIE"


def test_decide_has_no_compliance_input():
    assert list(inspect.signature(fc13.decide).parameters) == ["ratings", "key", "facts"]


def test_compliance_numbers_cannot_change_verdict():
    gains = fc13.load_gains(INPUTS)
    key = fc13.make_key("fixed-seed")
    ratings = {}
    for scene in SCENES[:2]:
        a, b = key[scene]["A"], key[scene]["B"]
        ratings[scene] = {a: _scores(3), b: _scores(4), "preference": b}
    ratings["S8"] = {"P1": _scores(3), "P2": _scores(3), "preference": "TIE"}
    facts = _flat_facts()

    before = fc13.decide(ratings, key, facts)["verdict"]
    c1 = fc13.compliance(SAMPLE, gains, [4])
    c2 = fc13.compliance(SAMPLE, gains, [1, 2, 3, 5])
    assert c1 != c2
    assert fc13.decide(ratings, key, facts)["verdict"] == before


def test_blinded_view_real_sample_is_clean():
    text, risks = fc13.blinded_view(SAMPLE)
    lowered = text.lower()
    for word in ("kimi", "cost_usd", "reservation", "nemotron"):
        assert word not in lowered
    assert isinstance(risks, list)


def test_main_writes_three_files_and_keeps_seed(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fc13, "OUT_DIR", tmp_path)
    assert fc13.main([]) == 0
    key_file = tmp_path / "BLINDING_KEY.json"
    protocol_file = tmp_path / "EVAL_PROTOCOL.json"
    sheet_file = tmp_path / "BLINDED_SHEET_TEMPLATE.csv"
    seed = json.loads(key_file.read_text(encoding="utf-8"))["seed"]

    assert fc13.main([]) == 0
    assert json.loads(key_file.read_text(encoding="utf-8"))["seed"] == seed
    assert key_file.exists() and protocol_file.exists() and sheet_file.exists()

    protocol = json.loads(protocol_file.read_text(encoding="utf-8"))
    stored = protocol.pop("protocol_sha256")
    recomputed = hashlib.sha256(
        json.dumps(protocol, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert stored == recomputed
    assert capsys.readouterr().out.strip().splitlines()[-1] == stored

    with sheet_file.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert len(rows) == 6
    assert "arm" not in reader.fieldnames
