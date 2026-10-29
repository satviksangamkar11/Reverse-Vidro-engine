import json
import os
import re
from typing import Any, Callable, Dict, List, Union

BeatDict = Dict[str, Any]
RecipeDict = Dict[str, Any]
WriteResult = Dict[str, Union[str, List[str]]]
GuardResult = Dict[str, Union[str, List[str]]]

INTENT_PATTERNS = [
    r"the creator wanted",
    r"the creator intended",
    r"the author wanted",
    r"the author intended",
    r"the director wanted",
    r"the director intended",
    r"the writer wanted",
    r"the writer intended",
    r"the producer wanted",
    r"the producer intended",
]

# Tightened patterns: require instruction verb + value assignment for timing/duration
# Allow any words between verb and timing/duration, support decimal, plural seconds/frames
# Also match possessive forms like "shot's duration" and "beat's duration"
PLAYBOOK_FORBIDDEN_PATTERNS = [
    (r"rewrite.*EASY|paraphrase.*EASY", "Playbook instructs to rewrite or paraphrase EASY wording"),
    (r"invent.*(story|dialogue|event)", "Playbook instructs to invent story events or dialogue"),
    (r"(assign|set|specify)\b[^.\n]*?\b(timing|duration)\b[^.\n]*?\b\d+(?:\.\d+)?\s*(?:seconds?|frames?)\b", "Playbook instructs to assign timings in seconds/frames"),
    (r"name.*unregistered.*preset|unregistered.*preset.*id", "Playbook instructs to name an unregistered preset id"),
    (r"emit.*animation.*code", "Playbook instructs to emit animation code"),
    (r"add.*(music|background score).*production", "Playbook instructs to add music/background score to production"),
]

def _safe_path(output_dir: str, filename: str) -> str:
    """Resolve path and ensure it stays within output_dir."""
    base = os.path.realpath(output_dir)
    target = os.path.realpath(os.path.join(output_dir, filename))
    if not target.startswith(base + os.sep) and target != base:
        raise ValueError(f"Path traversal attempt: {filename}")
    return target

def write_deliverables(
    output_dir: str,
    beats: List[BeatDict],
    recipes: List[RecipeDict],
    read_file: Callable[[str], str],
    write_file: Callable[[str, str], None],
    list_dir: Callable[[str], List[str]],
) -> WriteResult:
    # Validate and prepare all data BEFORE any writes
    files_written = []

    # Extract allowed presets from recipes (use preset_id from D2 output)
    allowed_presets = []
    for recipe in recipes:
        preset_id = recipe.get("preset_id")
        if isinstance(preset_id, str) and preset_id.strip():
            allowed_presets.append(preset_id)

    # Validate recipes are JSON-serializable BEFORE generating playbook content
    json.dumps(recipes)  # will raise if not serializable

    # Generate playbook content first for guard check
    playbook_content = _generate_playbook_content(recipes)

    # Guard the playbook content
    guard_result = playbook_guard(playbook_content, allowed_presets)
    if guard_result["status"] == "VIOLATIONS":
        raise ValueError(f"Playbook guard violations: {guard_result['violations']}")

    # Read and validate MASTER_TECHNIQUES.json before any writes
    techniques_path = _safe_path(output_dir, "MASTER_TECHNIQUES.json")
    try:
        techniques_content = read_file(techniques_path)
        techniques_data = json.loads(techniques_content) if techniques_content else {}
    except FileNotFoundError:
        techniques_data = {}

    # Validate techniques_data is a dict
    if not isinstance(techniques_data, dict):
        raise TypeError("MASTER_TECHNIQUES.json must contain a JSON object")

    # Update MASTER_REPORT.md
    report_path = _safe_path(output_dir, "MASTER_REPORT.md")
    try:
        report_content = read_file(report_path)
    except FileNotFoundError:
        report_content = ""

    beats_section = _generate_beats_section(beats)
    new_report_content = _replace_section(report_content, "<!-- BEATS_START -->", "<!-- BEATS_END -->", beats_section)
    write_file(report_path, new_report_content)
    files_written.append("MASTER_REPORT.md")

    # Update MASTER_TECHNIQUES.json
    techniques_data["_beat_recipes"] = recipes
    write_file(techniques_path, json.dumps(techniques_data, indent=2))
    files_written.append("MASTER_TECHNIQUES.json")

    # Write KIMI_ANIMATION_PLAYBOOK.md
    playbook_path = _safe_path(output_dir, "KIMI_ANIMATION_PLAYBOOK.md")
    write_file(playbook_path, playbook_content)
    files_written.append("KIMI_ANIMATION_PLAYBOOK.md")

    return {"status": "OK", "files_written": files_written}


def playbook_guard(text: str, allowed_presets: List[str]) -> GuardResult:
    violations = []

    # Check for invented preset-like IDs (quoted or backtick-quoted only)
    preset_matches = re.findall(r"preset\s*[`'\"]([^`'\"]+)[`'\"]", text, re.IGNORECASE)
    for preset in preset_matches:
        if preset not in allowed_presets:
            violations.append(f"Invented preset-like ID: '{preset}' not in allowed list")

    # Check for creator intent phrases (case-insensitive)
    text_lower = text.lower()
    for pattern in INTENT_PATTERNS:
        if pattern in text_lower:
            # Report the lowercase pattern as per spec worked example
            violations.append(f"Phrase implies creator intent as fact: '{pattern}'")

    # Check for playbook forbidden patterns
    for pattern, message in PLAYBOOK_FORBIDDEN_PATTERNS:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for match in matches:
            # For music/production violation, check if THIS specific instruction is explicitly research-only
            if "add.*(music|background score).*production" in pattern:
                # Check if "reference only" appears immediately after the match (same clause)
                after_match = text[match.end():]
                if re.match(r"\s*\(\s*reference\s+only\s*\)", after_match, re.IGNORECASE):
                    continue
            violations.append(message)

    if violations:
        return {"status": "VIOLATIONS", "violations": violations}
    return {"status": "OK", "violations": []}


def _generate_playbook_content(recipes: List[RecipeDict]) -> str:
    lines = ["# KIMI Animation Playbook", ""]

    # Stage 1: Directing Lessons
    lines.append("## Stage 1: Directing Lessons")
    stage1_lessons = []
    for recipe in recipes:
        lesson = recipe.get("stage1", "").strip()
        if lesson:
            stage1_lessons.append(f"- {lesson}")
    if stage1_lessons:
        lines.extend(stage1_lessons)
    else:
        lines.append("- (no lessons)")
    lines.append("")

    # Stage 2: Execution Hints
    lines.append("## Stage 2: Execution Hints")
    stage2_hints = []
    for recipe in recipes:
        hint = recipe.get("stage2", "").strip()
        if hint:
            stage2_hints.append(f"- {hint}")
    if stage2_hints:
        lines.extend(stage2_hints)
    else:
        lines.append("- (no hints)")
    lines.append("")

    # Sound & Silence Rules
    lines.append("## Sound & Silence Rules")
    sound_rules = []
    for recipe in recipes:
        sound_lesson = recipe.get("sound_lesson", "").strip()
        if sound_lesson:
            sound_rules.append(f"- {sound_lesson}")
    if sound_rules:
        lines.extend(sound_rules)
    else:
        lines.append("- (no sound rules)")
    lines.append("")

    # Applicability
    lines.append("## Applicability")
    applicability_items = []
    for recipe in recipes:
        applicability = recipe.get("applicability", "").strip()
        if applicability:
            applicability_items.append(f"- {applicability}")
    if applicability_items:
        lines.extend(applicability_items)
    else:
        lines.append("- (no applicability notes)")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append("*read-only hints: canon and schema win*")
    lines.append("*reference music is research-only and prohibited in production*")
    lines.append("*reference dialogue never alters EASY wording*")

    return "\n".join(lines)


def _generate_beats_section(beats: List[BeatDict]) -> str:
    lines = ["## Beats"]
    for beat in beats:
        video_id = beat["video_id"]
        beat_id = beat["beat_id"]
        purpose = beat["purpose"]
        # Support both start_time/end_time (D1 spec) and start_sec/end_sec (legacy)
        start = beat.get("start_time", beat.get("start_sec", 0.0))
        end = beat.get("end_time", beat.get("end_sec", 0.0))
        lines.append(f"- {video_id}/{beat_id}: {purpose} ({start}-{end}s)")
    return "\n".join(lines)


def _replace_section(content: str, start_marker: str, end_marker: str, new_section: str) -> str:
    cleaned = content

    # Find the first START marker position for insertion point
    first_start_pos = cleaned.find(start_marker)

    # Remove all well-formed sections (start before end)
    while True:
        s = cleaned.find(start_marker)
        if s == -1:
            break
        e = cleaned.find(end_marker, s + len(start_marker))  # Find END after START
        if e != -1:
            cleaned = cleaned[:s] + cleaned[e + len(end_marker):]
        else:
            break

    # Remove reversed sections (end before start) - remove from end_marker through start_marker and the following line
    while True:
        e = cleaned.find(end_marker)
        if e == -1:
            break
        s = cleaned.find(start_marker, e + len(end_marker))  # Find START after END
        if s != -1:
            # Remove from end_marker through start_marker and the next line
            after_start = s + len(start_marker)
            # Find the end of the line containing start_marker
            line_end = cleaned.find("\n", after_start)
            if line_end != -1:
                # Also remove the next line
                next_line_end = cleaned.find("\n", line_end + 1)
                if next_line_end != -1:
                    cleaned = cleaned[:e] + cleaned[next_line_end + 1:]
                else:
                    cleaned = cleaned[:e] + cleaned[line_end + 1:]
            else:
                cleaned = cleaned[:e]
        else:
            break

    # Remove any remaining standalone markers
    cleaned = cleaned.replace(start_marker, "").replace(end_marker, "")

    # Trim trailing whitespace
    cleaned = cleaned.rstrip()

    # Insert fresh section at the first START marker's original position, or append if no marker existed
    if first_start_pos != -1:
        # Clamp insertion position to cleaned length (in case removal shortened it)
        insert_pos = min(first_start_pos, len(cleaned))
        # Ensure we insert at a line boundary
        if insert_pos > 0 and cleaned[insert_pos - 1] != "\n":
            # Find previous newline
            prev_nl = cleaned.rfind("\n", 0, insert_pos)
            if prev_nl != -1:
                insert_pos = prev_nl + 1
        new_content = cleaned[:insert_pos] + start_marker + "\n" + new_section + "\n" + end_marker + "\n" + cleaned[insert_pos:]
    else:
        # No markers existed, append at end
        if cleaned and not cleaned.endswith("\n"):
            cleaned += "\n"
        new_content = cleaned + start_marker + "\n" + new_section + "\n" + end_marker + "\n"

    # Ensure no double blank lines before trailing content
    # Normalize: replace 3+ newlines with 2 newlines
    new_content = re.sub(r"\n{3,}", "\n\n", new_content)

    return new_content
