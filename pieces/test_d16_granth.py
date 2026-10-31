import ast
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import d16_granth as m

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GS_ROOT = os.environ.get("GRANTH_ROOT") or os.path.join(os.path.dirname(ROOT), "granthstudio")

MODULE_PATH = os.path.join(HERE, "d16_granth.py")
F4_REL = ("work", "phase1", "f4_diagnosis_v2.json")
LESSON_REL = ("work", "phase1", "overlays", "lesson_candidates_7434a0f7.json")
ASSET_SUBDIRS = ("assets/v5_presets", "assets/pilot_refs")
CONSUMER_TERMS = ("v5_presets", "index.json", "preset")
FORBIDDEN_IMPORTS = {"shutil", "subprocess", "urllib", "requests", "http", "socket", "openai", "anthropic"}


def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _index():
    return _read_json(os.path.join(GS_ROOT, "assets", "v5_presets", "index.json"))


def _f4():
    return _read_json(os.path.join(ROOT, *F4_REL))


def _lessons():
    return _read_json(os.path.join(ROOT, *LESSON_REL))


def _real_asset_names():
    names = []
    for sub in ASSET_SUBDIRS:
        folder = os.path.join(GS_ROOT, *sub.split("/"))
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            if os.path.isfile(os.path.join(folder, name)):
                names.append(name)
    return names


def _expected_found(asset, names):
    return any(n == asset or n.startswith(asset + ".") or n.startswith(asset + "_") for n in names)


def _expected_consumer_pairs():
    pairs = set()
    for sub in ("scripts", "src"):
        for dirpath, dirnames, filenames in os.walk(os.path.join(GS_ROOT, sub)):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for name in filenames:
                if name.endswith(".pyc"):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()
                except (OSError, UnicodeDecodeError):
                    continue
                rel = os.path.relpath(path, GS_ROOT).replace(os.sep, "/")
                for lineno, line in enumerate(text.split("\n"), start=1):
                    if any(term in line for term in CONSUMER_TERMS):
                        pairs.add((rel, lineno))
    return pairs


def _module_tree():
    with open(MODULE_PATH, "r", encoding="utf-8") as f:
        return ast.parse(f.read(), filename=MODULE_PATH)


def _is_write_open(node):
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Name) or node.func.id != "open":
        return False
    mode = node.args[1] if len(node.args) >= 2 else None
    for kw in node.keywords:
        if kw.arg == "mode":
            mode = kw.value
    if mode is None:
        return False
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return any(ch in mode.value for ch in "wax+")
    return True


def _seed_repo(repo):
    for rel in (F4_REL, LESSON_REL):
        dst = os.path.join(str(repo), *rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(os.path.join(ROOT, *rel), "rb") as src:
            data = src.read()
        with open(dst, "wb") as out:
            out.write(data)


def test_preset_count_and_order():
    index = _index()
    assert len(index) == 11
    out = m.build_output(ROOT, GS_ROOT)
    assert len(out["presets"]) == 11
    assert [p["preset"] for p in out["presets"]] == [e["preset"] for e in index]


def test_asset_status_and_availability_match_real_files():
    names = _real_asset_names()
    out = m.build_output(ROOT, GS_ROOT)
    for entry, preset in zip(_index(), out["presets"]):
        assert preset["assets"] == entry["assets"]
        expected = {a: ("found" if _expected_found(a, names) else "not found") for a in entry["assets"]}
        assert set(preset["asset_status"]) == set(expected)
        for asset in entry["assets"]:
            assert preset["asset_status"][asset] in ("found", "not found")
            assert preset["asset_status"][asset] == expected[asset]
        expected_available = bool(entry["assets"]) and all(v == "found" for v in expected.values())
        assert preset["assets_available"] == expected_available


def test_techniques_from_build_output_are_not_executable():
    out = m.build_output(ROOT, GS_ROOT)
    techniques = out["techniques"]
    assert len(techniques) == 13
    for tech in techniques:
        assert tech["preset_id"] is None
        assert tech["assets_available"] is False
        expected_need = "NEEDS_NEW_CAPABILITY" if tech["executability"] == "NEED_NEW" else "UNKNOWN"
        assert tech["need"] == expected_need
        assert tech["preset_match"] == "NO_REGISTERED_PRESET"


def test_lessons_separate_guidance_from_executability():
    lessons = _lessons()["lessons"]
    out = m.build_output(ROOT, GS_ROOT)
    assert len(lessons) == 7
    assert len(out["lessons"]) == 7
    for src, got in zip(lessons, out["lessons"]):
        assert got["renderer_executability"] == "NOT_EXECUTABLE_WITHOUT_PRESET"
        assert got["preset_match"] == "NO_REGISTERED_PRESET"
        assert got["story_directing_guidance"] == src["title"] + " candidate; not verified"
        assert got["need"] == "UNKNOWN"


def test_consumer_entries_are_valid():
    consumers = m.build_output(ROOT, GS_ROOT)["consumers"]
    assert consumers
    for entry in consumers:
        assert os.path.isfile(os.path.join(GS_ROOT, *entry["file"].split("/")))
        assert entry["line"] >= 1
        assert entry["mentions"]


def test_consumer_set_matches_independent_scan():
    expected = _expected_consumer_pairs()
    assert expected
    got = {(c["file"], c["line"]) for c in m.build_output(ROOT, GS_ROOT)["consumers"]}
    assert got == expected


def test_single_write_open_is_inside_write_output():
    tree = _module_tree()
    total = sum(1 for node in ast.walk(tree) if _is_write_open(node))
    assert total == 1
    owners = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(node):
                if _is_write_open(sub):
                    owners.append(node.name)
    assert owners == ["write_output"]


def test_forbidden_imports_absent():
    names = []
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
            names.extend(alias.name for alias in node.names)
    for name in names:
        assert name.split(".")[0] not in FORBIDDEN_IMPORTS
        assert "kimi" not in name.lower()


def test_write_output_refuses_path_outside_departments_16(tmp_path):
    with pytest.raises(ValueError):
        m.write_output(ROOT, GS_ROOT, str(tmp_path / "x.json"))


def test_write_output_success_path(tmp_path):
    _seed_repo(tmp_path)
    out_path = str(tmp_path / "work" / "phase1" / "departments_16" / "out.json")
    m.write_output(str(tmp_path), GS_ROOT, out_path)
    assert os.path.isfile(out_path)
    data = _read_json(out_path)
    for key in ("presets", "techniques", "lessons", "consumers", "counts"):
        assert key in data
    assert len(data["presets"]) == 11
    assert len(data["techniques"]) == 13


def test_granthstudio_tree_not_modified():
    targets = [
        os.path.join(GS_ROOT, "assets", "v5_presets", "index.json"),
        os.path.join(GS_ROOT, "assets", "v5_presets", "README.md"),
    ]
    before = {p: os.path.getmtime(p) for p in targets}
    m.build_output(ROOT, GS_ROOT)
    after = {p: os.path.getmtime(p) for p in targets}
    assert before == after


def test_build_output_is_deterministic():
    first = m.build_output(ROOT, GS_ROOT)
    second = m.build_output(ROOT, GS_ROOT)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_write_output_refuses_symlink(tmp_path):
    out_dir = tmp_path / "work" / "phase1" / "departments_16"
    out_dir.mkdir(parents=True)
    target = tmp_path / "outside.json"
    target.write_text("{}", encoding="utf-8")
    link = out_dir / "link.json"
    try:
        os.symlink(str(target), str(link))
    except OSError:
        pytest.skip("symlinks unavailable on this system")
    with pytest.raises(ValueError):
        m.write_output(str(tmp_path), GS_ROOT, str(link))
