"""Read-only compatibility check of Reverse-Video techniques and lessons against GranthStudio.

GranthStudio is never written, imported or executed. Only text search and JSON reads
are performed, and the single output file lives in the Reverse-Video repository.
"""

import json
import os
import re
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# GRANTH_ROOT overrides the default sibling-folder location.
GS_ROOT = os.environ.get("GRANTH_ROOT") or os.path.join(os.path.dirname(ROOT), "granthstudio")
DEFAULT_OUT = os.path.join(ROOT, "work", "phase1", "departments_16", "PRODUCTION_EXECUTION_COMPATIBILITY.json")

BOUNDARY_NOTE = "GranthStudio read-only; no file modified; no model call"
ASSET_DIRS = ("assets/v5_presets", "assets/pilot_refs")
CONSUMER_DIRS = ("scripts", "src")
# Plain substring match on purpose: word boundaries would miss names such as preset_id.
CONSUMER_PATTERN = re.compile(r"v5_presets|index\.json|preset")
GUIDANCE_SUFFIX = " candidate; not verified"
LESSON_FILE = "lesson_candidates_7434a0f7.json"


def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _asset_files(gs_root):
    names = []
    for sub in ASSET_DIRS:
        folder = os.path.join(gs_root, *sub.split("/"))
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            if os.path.isfile(os.path.join(folder, name)):
                names.append(name)
    return names


def _asset_status(asset, names):
    for name in names:
        if name == asset or name.startswith(asset + ".") or name.startswith(asset + "_"):
            return "found"
    return "not found"


def load_presets(gs_root):
    """Return the 11 preset dicts from index.json with asset_status and assets_available added."""
    entries = _read_json(os.path.join(gs_root, "assets", "v5_presets", "index.json"))
    names = _asset_files(gs_root)
    presets = []
    for entry in entries:
        preset = dict(entry)
        status = {asset: _asset_status(asset, names) for asset in entry["assets"]}
        preset["asset_status"] = status
        preset["assets_available"] = bool(entry["assets"]) and all(v == "found" for v in status.values())
        presets.append(preset)
    return presets


def load_techniques(root):
    """Return the 13 F4 techniques with only the raw keys needed for classification."""
    diagnoses = _read_json(os.path.join(root, "work", "phase1", "f4_diagnosis_v2.json"))["diagnoses"]
    techniques = []
    for diag in diagnoses:
        tech = diag["technique"]
        # assets_available is copied from the F4 file as-is; all 13 entries are false there.
        techniques.append({
            "id": diag["id"],
            "classification": diag["classification"],
            "executability": diag["executability"],
            "bucket": diag["bucket"],
            "reasons": list(diag["reasons"]),
            "preset_id": tech["preset_id"],
            "assets_available": tech["assets_available"],
        })
    return techniques


def load_lessons(root, lesson_file=LESSON_FILE):
    # Fixed file name by default, because a glob could pick a different candidate set.
    data = _read_json(os.path.join(root, "work", "phase1", "overlays", lesson_file))
    return list(data["lessons"])


def preset_match(technique):
    if technique["preset_id"] is None:
        return "NO_REGISTERED_PRESET"
    return technique["preset_id"]


def classify_need(technique):
    if technique["executability"] == "NEED_NEW":
        return "NEEDS_NEW_CAPABILITY"
    if technique["preset_id"] is not None:
        return "NEEDS_EXISTING_PRESET"
    return "UNKNOWN"


def lesson_compatibility(lesson):
    return {
        "lesson_id": lesson["lesson_id"],
        "title": lesson["title"],
        "status": lesson["status"],
        "technique_tags": list(lesson["technique_tags"]),
        "preset_match": "NO_REGISTERED_PRESET",
        "story_directing_guidance": lesson["title"] + GUIDANCE_SUFFIX,
        "renderer_executability": "NOT_EXECUTABLE_WITHOUT_PRESET",
        "need": "UNKNOWN",
    }


def consumer_search(gs_root):
    """Text-search GranthStudio scripts and src for preset references."""
    results = []
    for sub in CONSUMER_DIRS:
        base = os.path.join(gs_root, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for name in sorted(filenames):
                if name.endswith(".pyc"):
                    continue
                path = os.path.join(dirpath, name)
                rel = os.path.relpath(path, gs_root).replace(os.sep, "/")
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()
                except (OSError, UnicodeDecodeError) as exc:
                    sys.stderr.write("warning: skipped unreadable file " + rel + ": " + str(exc) + "\n")
                    continue
                for lineno, line in enumerate(text.split("\n"), start=1):
                    found = sorted(set(hit.group(0) for hit in CONSUMER_PATTERN.finditer(line)))
                    if found:
                        results.append({
                            "file": rel,
                            "line": lineno,
                            "excerpt": line.strip()[:120],
                            "mentions": found,
                        })
    results.sort(key=lambda r: (r["file"], r["line"]))
    return results


def build_output(root, gs_root):
    presets = load_presets(gs_root)
    techniques = [dict(t, need=classify_need(t), preset_match=preset_match(t)) for t in load_techniques(root)]
    lessons = [lesson_compatibility(lesson) for lesson in load_lessons(root)]
    consumers = consumer_search(gs_root)
    return {
        "boundary_note": BOUNDARY_NOTE,
        "presets": presets,
        "techniques": techniques,
        "lessons": lessons,
        "consumers": consumers,
        "counts": {
            "presets": len(presets),
            "techniques": len(techniques),
            "lessons": len(lessons),
            "consumers": len(consumers),
        },
    }


def write_output(root, gs_root, out_path):
    """The only function that opens a file for writing."""
    if os.path.islink(out_path):
        raise ValueError("output path is a symbolic link: " + out_path)
    out_real = os.path.realpath(out_path)
    allowed = os.path.realpath(os.path.join(root, "work", "phase1", "departments_16"))
    if not os.path.normcase(out_real).startswith(os.path.normcase(allowed + os.sep)):
        raise ValueError("output path is outside " + allowed)
    os.makedirs(os.path.dirname(out_real), exist_ok=True)
    output = build_output(root, gs_root)
    with open(out_real, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, sort_keys=True)
    return output


def main(argv):
    out_path = argv[0] if argv else DEFAULT_OUT
    output = write_output(ROOT, GS_ROOT, out_path)
    for key in sorted(output["counts"]):
        print(key, output["counts"][key])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
