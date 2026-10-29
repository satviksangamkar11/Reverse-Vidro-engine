from typing import List, Dict, Any, Tuple, Set, Optional
import re

# Type aliases for clarity
BeatDict = Dict[str, Any]
RecipeDict = Dict[str, Any]
CompileResult = Dict[str, Any]


def _make_recipe_key(beat: BeatDict) -> Tuple[str, str, str]:
    """
    Internal helper: returns (purpose, camera_movement, method) tuple.
    """
    purpose = beat.get("purpose", "")
    camera_movement = beat.get("how_filmed", {}).get("camera_movement", "")
    method = beat.get("how_animated", {}).get("method", "")
    return (purpose, camera_movement, method)


def _merge_sound_lessons(beats: List[BeatDict]) -> str:
    """
    Internal helper: merges sound lessons from beats with real audio;
    returns "UNAVAILABLE \u2013 do not assume" if none.
    """
    lessons = []
    has_music = False
    for beat in beats:
        sound = beat.get("sound", {})
        music = sound.get("music", "UNAVAILABLE")
        narration = sound.get("narration", "UNAVAILABLE")
        ambience = sound.get("ambience", "UNAVAILABLE")
        sfx = sound.get("sfx", "UNAVAILABLE")

        beat_lessons = []
        if music and music != "UNAVAILABLE" and music != "UNKNOWN":
            beat_lessons.append(f"{music} works")
            has_music = True
        if narration and narration != "UNAVAILABLE" and narration != "UNKNOWN":
            beat_lessons.append(f"Narration: {narration}")
        if ambience and ambience != "UNAVAILABLE" and ambience != "UNKNOWN":
            beat_lessons.append(f"Ambience: {ambience}")
        if sfx and sfx != "UNAVAILABLE" and sfx != "UNKNOWN":
            beat_lessons.append(f"SFX: {sfx}")

        if beat_lessons:
            lessons.append("; ".join(beat_lessons))

    if not lessons:
        return "UNAVAILABLE \u2013 do not assume"

    combined = "; ".join(lessons)
    if has_music:
        return f"{combined}; if no music, do not assume \u2014 mark UNAVAILABLE."
    return combined


def _build_stage1(beats: List[BeatDict]) -> str:
    """
    Build stage1 directing lesson from beats.
    """
    if not beats:
        return ""

    # Use first beat as representative for purpose/camera/method
    beat = beats[0]
    purpose = beat.get("purpose", "")
    camera_movement = beat.get("how_filmed", {}).get("camera_movement", "")
    shot_scale = beat.get("how_filmed", {}).get("shot_scale", "")
    method = beat.get("how_animated", {}).get("method", "")
    notes = beat.get("how_animated", {}).get("notes", "")

    # Generic lesson based on purpose, incorporating camera_movement
    purpose_lessons = {
        "ESTABLISH": f"Use a {camera_movement.lower()} {shot_scale.lower()} shot to establish setting; let the environment speak.",
        "REVEAL": "Reveal the subject gradually; control information flow.",
        "EMPHASIZE": "Focus attention on key detail; use composition to guide eye.",
        "TRANSITION": "Bridge scenes with motivated movement; maintain spatial coherence.",
        "REACT": "Hold on reaction; let emotion land before cutting.",
        "PACE": "Control rhythm through shot duration; breathe with the moment.",
        "WITHHOLD": "Withhold visual information to build anticipation.",
        "PUSH_IN": "Push in to intensify focus on subject.",
        "PAUSE": "Hold the frame to let meaning settle.",
        "HARD_CUT": "Cut abruptly to shift attention or time.",
        "REACTION": "Show character response to preceding action.",
        "HOLD": "Sustain the shot beyond expected duration.",
    }

    base_lesson = purpose_lessons.get(purpose, f"Execute {purpose} with {camera_movement} camera and {method} method.")

    if notes:
        base_lesson += f" {notes}."

    return base_lesson


def _build_stage2(beats: List[BeatDict], registered_presets: Set[str]) -> str:
    """
    Build stage2 execution hint using only status/artwork_needed, never invented preset names.
    Filters out preset references not in registered_presets.
    """
    if not beats:
        return ""

    statuses = []
    all_artwork = set()
    methods = []

    for beat in beats:
        repro = beat.get("reproduction", {})
        status = repro.get("status", "UNKNOWN")
        artwork = repro.get("artwork_needed", [])
        simplest = repro.get("simplest_method", "")

        statuses.append(status)
        all_artwork.update(artwork)
        if simplest:
            # Filter out unregistered preset references
            filtered = _filter_unregistered_presets(simplest, registered_presets)
            if filtered:
                methods.append(filtered)

    unique_statuses = list(dict.fromkeys(statuses))  # preserve order, dedupe
    artwork_str = ", ".join(sorted(all_artwork)) if all_artwork else ""
    methods_str = " | ".join(methods) if methods else ""

    stage2 = f"Status: {' or '.join(unique_statuses)}."
    stage2 += f" Artwork needed: {artwork_str}."
    if methods_str:
        stage2 += f" Simplest: {methods_str}."

    return stage2


def _filter_unregistered_presets(text: str, registered_presets: Set[str]) -> str:
    """
    Remove references to preset IDs not in registered_presets.
    Handles:
    - preset 'name' / preset "name"
    - 'name' preset / "name" preset (quoted id before the word preset)
    - preset name (unquoted)
    - name preset (unquoted)
    Only strips bare quoted strings when they are adjacent to "preset" keyword.
    """
    if not registered_presets:
        # No registry provided - remove all preset-like references
        # preset 'name' / preset "name"
        result = re.sub(r"preset\s+['\"][^'\"]+['\"]", "", text)
        # 'name' preset / "name" preset
        result = re.sub(r"['\"][a-zA-Z0-9_.-]+['\"]\s+preset", "", result)
        # preset name (unquoted)
        result = re.sub(r"preset\s+[a-zA-Z0-9_.-]+", "", result)
        # name preset (unquoted)
        result = re.sub(r"[a-zA-Z0-9_.-]+\s+preset", "", result)
        return result.strip()
    
    # Allow hyphens and dots in preset IDs
    valid_presets = {p for p in registered_presets if re.match(r'^[a-zA-Z0-9_.-]+$', p)}
    
    def replace_quoted_after(match):
        preset_name = match.group(1)
        if preset_name in valid_presets:
            return match.group(0)
        return ""
    
    def replace_quoted_before(match):
        preset_name = match.group(1)
        if preset_name in valid_presets:
            return match.group(0)
        return ""
    
    def replace_unquoted_after(match):
        preset_name = match.group(1)
        if preset_name in valid_presets:
            return match.group(0)
        return ""
    
    def replace_unquoted_before(match):
        preset_name = match.group(1)
        if preset_name in valid_presets:
            return match.group(0)
        return ""
    
    # Match preset 'name' or preset "name"
    result = re.sub(r"preset\s+['\"]([^'\"]+)['\"]", replace_quoted_after, text)
    # Match 'name' preset or "name" preset
    result = re.sub(r"['\"]([a-zA-Z0-9_.-]+)['\"]\s+preset", replace_quoted_before, result)
    # Match preset name (unquoted)
    result = re.sub(r"preset\s+([a-zA-Z0-9_.-]+)", replace_unquoted_after, result)
    # Match name preset (unquoted)
    result = re.sub(r"([a-zA-Z0-9_.-]+)\s+preset", replace_unquoted_before, result)
    return result.strip()


def _build_applicability() -> str:
    """
    Standard applicability note.
    """
    return "Adapt 9:16 reel pacing to 16:9 devotional film; no copying reel dramatic cues."


def _build_counterexamples(beats: List[BeatDict]) -> List[str]:
    """
    Union of counterexamples from source beats and department_findings contraindications.
    """
    counterexamples = []
    seen = set()
    for beat in beats:
        ce = beat.get("counterexample", "")
        if ce and ce not in seen:
            counterexamples.append(ce)
            seen.add(ce)
        # Also include contraindications from department_findings
        dept_findings = beat.get("department_findings", {})
        for dept, findings in dept_findings.items():
            if isinstance(findings, list):
                for finding in findings:
                    if isinstance(finding, dict):
                        contra = finding.get("contraindication", "")
                        if contra and contra not in seen:
                            counterexamples.append(contra)
                            seen.add(contra)
            elif isinstance(findings, dict):
                contra = findings.get("contraindication", "")
                if contra and contra not in seen:
                    counterexamples.append(contra)
                    seen.add(contra)
    return counterexamples


def _extract_preset_id(simplest_method: str, registered_presets: Set[str]) -> Optional[str]:
    """
    Extract preset ID from simplest_method string if it matches a registered preset.
    Returns None if no registered preset found.
    Allows hyphens and dots in preset IDs.
    """
    if not simplest_method or not registered_presets:
        return None
    
    # Allow hyphens and dots in preset IDs
    valid_presets = {p for p in registered_presets if re.match(r'^[a-zA-Z0-9_.-]+$', p)}
    if not valid_presets:
        return None
    
    # Check each preset in deterministic order (sorted)
    for preset in sorted(valid_presets):
        # Match preset ID with word boundaries or quotes
        pattern = re.compile(r'(^|[^a-zA-Z0-9_.-])' + re.escape(preset) + r'($|[^a-zA-Z0-9_.-])')
        if pattern.search(simplest_method):
            return preset
    return None


def _build_stage1_lessons(beats: List[BeatDict]) -> List[str]:
    """
    Build structured stage1 lessons list covering:
    narrative presentation, shot sequencing, performance, camera/composition,
    editing/continuity, artwork requirements, sound.
    """
    if not beats:
        return []

    # Aggregate unique values across all beats in group
    purposes = set()
    camera_movements = set()
    shot_scales = set()
    angles = set()
    framings = set()
    compositions = set()
    cut_types = set()
    methods = set()
    all_observed = []
    all_inferred_claims = []
    all_artwork = set()
    all_sound_info = []

    for beat in beats:
        purposes.add(beat.get("purpose", ""))
        hf = beat.get("how_filmed", {})
        camera_movements.add(hf.get("camera_movement", ""))
        shot_scales.add(hf.get("shot_scale", ""))
        angles.add(hf.get("angle", ""))
        framings.add(hf.get("framing", ""))
        compositions.add(hf.get("composition", ""))
        cut_types.add(hf.get("cut_type", ""))
        methods.add(beat.get("how_animated", {}).get("method", ""))
        all_observed.extend(beat.get("observed", []))
        # Handle inferred as list of dicts with "claim" field
        for inf in beat.get("inferred", []):
            if isinstance(inf, dict):
                claim = inf.get("claim", "")
                if claim:
                    all_inferred_claims.append(claim)
            elif isinstance(inf, str):
                all_inferred_claims.append(inf)
        all_artwork.update(beat.get("reproduction", {}).get("artwork_needed", []))
        # Collect sound info
        sound = beat.get("sound", {})
        music = sound.get("music", "UNAVAILABLE")
        narration = sound.get("narration", "UNAVAILABLE")
        ambience = sound.get("ambience", "UNAVAILABLE")
        sfx = sound.get("sfx", "UNAVAILABLE")
        if music != "UNAVAILABLE" and music != "UNKNOWN":
            all_sound_info.append(f"music: {music}")
        if narration != "UNAVAILABLE" and narration != "UNKNOWN":
            all_sound_info.append(f"narration: {narration}")
        if ambience != "UNAVAILABLE" and ambience != "UNKNOWN":
            all_sound_info.append(f"ambience: {ambience}")
        if sfx != "UNAVAILABLE" and sfx != "UNKNOWN":
            all_sound_info.append(f"sfx: {sfx}")

    # Use first beat's purpose as primary for narrative lesson
    primary_purpose = beats[0].get("purpose", "")

    lessons = []

    # Narrative presentation
    purpose_narrative = {
        "ESTABLISH": "Narrative presentation: Establish setting and context; let environment convey mood.",
        "REVEAL": "Narrative presentation: Reveal information gradually to build understanding.",
        "EMPHASIZE": "Narrative presentation: Emphasize key detail to focus viewer attention.",
        "TRANSITION": "Narrative presentation: Transition between scenes maintaining spatial coherence.",
        "REACT": "Narrative presentation: Show reaction to convey emotional impact.",
        "PACE": "Narrative presentation: Control pacing to serve devotional rhythm.",
        "WITHHOLD": "Narrative presentation: Withhold visual information to create anticipation.",
        "PUSH_IN": "Narrative presentation: Push in to intensify focus on subject.",
        "PAUSE": "Narrative presentation: Pause to let meaning settle.",
        "HARD_CUT": "Narrative presentation: Hard cut to shift attention or time abruptly.",
        "REACTION": "Narrative presentation: Show character reaction to preceding action.",
        "HOLD": "Narrative presentation: Hold shot beyond expected duration for emphasis.",
    }
    lessons.append(purpose_narrative.get(primary_purpose, f"Narrative presentation: Execute {primary_purpose}."))

    # Shot sequencing
    shot_scale_str = ", ".join(sorted(s for s in shot_scales if s))
    camera_movement_str = ", ".join(sorted(c for c in camera_movements if c))
    lessons.append(f"Shot sequencing: {primary_purpose} beat uses {shot_scale_str} scale with {camera_movement_str.lower()} movement.")

    # Performance
    if all_inferred_claims:
        lessons.append(f"Performance: Inferred cues include {', '.join(sorted(set(all_inferred_claims)))}.")
    elif all_observed:
        # Only include observed if they describe performance (not general scene elements)
        perf_observed = [o for o in all_observed if any(kw in o.lower() for kw in ["performance", "actor", "expression", "gesture", "movement", "delivery", "emotion"])]
        if perf_observed:
            lessons.append(f"Performance: Observed elements include {', '.join(sorted(set(perf_observed)))}.")
        else:
            lessons.append("Performance: No specific performance cues noted.")
    else:
        lessons.append("Performance: No specific performance cues noted.")

    # Camera/composition
    angle_str = ", ".join(sorted(a for a in angles if a))
    framing_str = ", ".join(sorted(f for f in framings if f))
    composition_str = ", ".join(sorted(c for c in compositions if c))
    cam_comp = f"Camera/composition: {camera_movement_str} camera, {shot_scale_str} scale, {angle_str} angle, {framing_str} framing, {composition_str} composition."
    lessons.append(cam_comp)

    # Editing/continuity
    cut_type_str = ", ".join(sorted(c for c in cut_types if c))
    method_str = ", ".join(sorted(m for m in methods if m))
    lessons.append(f"Editing/continuity: {cut_type_str} cut type; maintain continuity with {method_str} method.")

    # Artwork requirements
    if all_artwork:
        lessons.append(f"Artwork requirements: Need {', '.join(sorted(all_artwork))}.")
    else:
        lessons.append("Artwork requirements: No additional artwork needed.")

    # Sound
    if all_sound_info:
        lessons.append(f"Sound: {', '.join(sorted(set(all_sound_info)))}.")
    else:
        lessons.append("Sound: No specific audio cues documented.")

    return lessons


def _build_stage2_lessons(beats: List[BeatDict], registered_presets: Set[str], preset_id: Optional[str]) -> List[str]:
    """
    Build structured stage2 lessons list covering:
    approved preset, compatible assets, feasible alternatives, exact NEED_NEW gap.
    Filters each preset reference against registry before including.
    """
    if not beats:
        return []

    lessons = []

    # Approved preset - use the recipe's preset_id (passed in)
    if preset_id:
        lessons.append(f"Approved preset: {preset_id}.")
    else:
        lessons.append("Approved preset: None.")

    # Compatible assets
    all_artwork = set()
    statuses = set()
    for beat in beats:
        repro = beat.get("reproduction", {})
        all_artwork.update(repro.get("artwork_needed", []))
        statuses.add(repro.get("status", "UNKNOWN"))
    if all_artwork:
        lessons.append(f"Compatible assets: {', '.join(sorted(all_artwork))}.")
    else:
        lessons.append("Compatible assets: None required.")

    # Feasible alternatives - keep documented non-preset alternatives; validate only preset references
    methods = []
    for beat in beats:
        simplest = beat.get("reproduction", {}).get("simplest_method", "")
        if simplest:
            # Filter the method through preset registry
            filtered = _filter_unregistered_presets(simplest, registered_presets)
            if filtered:
                methods.append(filtered)
    if methods:
        lessons.append(f"Feasible alternatives: {' | '.join(methods)}.")
    else:
        lessons.append("Feasible alternatives: None documented.")

    # Exact NEED_NEW gap
    need_new_beats = [b for b in beats if b.get("reproduction", {}).get("status") == "NEED_NEW"]
    if need_new_beats:
        gap_parts = []
        for b in need_new_beats:
            purpose = b.get("purpose", "")
            method = b.get("how_animated", {}).get("method", "")
            artwork = b.get("reproduction", {}).get("artwork_needed", [])
            gap_parts.append(f"{purpose} with {method} needs {', '.join(artwork) if artwork else 'new assets'}")
        lessons.append(f"Exact NEED_NEW gap: {'; '.join(gap_parts)}.")
    else:
        lessons.append("Exact NEED_NEW gap: None.")

    return lessons


def _build_when_not_to_use(beats: List[BeatDict]) -> str:
    """
    Build when_not_to_use string from union of counterexamples and contraindications.
    """
    counterexamples = _build_counterexamples(beats)
    if not counterexamples:
        return "No specific contraindications documented."
    return "Avoid: " + "; ".join(counterexamples)


def _build_sequence_pattern(beats: List[BeatDict]) -> List[str]:
    """
    Build sequence_pattern: ordered list of terms from department_findings or purposes,
    sorted by start_time within each video, then by video_id for cross-video ordering.
    Preserves repeats; only deduplicates consecutive identical terms.
    """
    # Sort beats by video_id then start_time to get temporal order
    sorted_beats = sorted(beats, key=lambda b: (b.get("video_id", ""), b.get("start_time", 0.0)))
    
    pattern = []
    for beat in sorted_beats:
        # Try to get term from department_findings first
        dept_findings = beat.get("department_findings", {})
        term_added = False
        for dept, findings in dept_findings.items():
            if isinstance(findings, list):
                for finding in findings:
                    if isinstance(finding, dict):
                        term = finding.get("term", "")
                        if term:
                            # Only dedup consecutive identical terms
                            if not pattern or pattern[-1] != term:
                                pattern.append(term)
                            term_added = True
            elif isinstance(findings, dict):
                term = findings.get("term", "")
                if term:
                    if not pattern or pattern[-1] != term:
                        pattern.append(term)
                    term_added = True
        # Fallback to purpose if no term found
        if not term_added:
            purpose = beat.get("purpose", "")
            if purpose:
                if not pattern or pattern[-1] != purpose:
                    pattern.append(purpose)
    
    return pattern


def compile_recipes(beats: List[BeatDict], registered_presets: Optional[Set[str]] = None) -> CompileResult:
    """
    Consolidates beats across videos by (purpose, camera_movement, method) key.
    Keeps ALL source references. Each recipe gets stage1, stage2, sound_lesson,
    applicability, counterexamples (union), verification, source_beats,
    sequence_pattern, when_not_to_use, preset_id, stage1_lessons, stage2_lessons.
    """
    if registered_presets is None:
        registered_presets = set()

    # Group beats by key
    groups: Dict[Tuple[str, str, str], List[BeatDict]] = {}
    for beat in beats:
        key = _make_recipe_key(beat)
        if key not in groups:
            groups[key] = []
        groups[key].append(beat)

    recipes = []
    for key, group_beats in groups.items():
        purpose, camera_movement, method = key

        # Preserve input order within each key group (don't sort)
        group_beats_sorted = group_beats

        source_beats = [
            {"video_id": b.get("video_id", ""), "beat_id": b.get("beat_id", "")}
            for b in group_beats_sorted
        ]

        verification = "MULTI_SOURCE" if len(group_beats) > 1 else "SINGLE_SOURCE"

        # Extract preset_id from group beats - collect ALL registered presets in group
        preset_ids = set()
        for beat in group_beats_sorted:
            simplest = beat.get("reproduction", {}).get("simplest_method", "")
            extracted = _extract_preset_id(simplest, registered_presets)
            if extracted:
                preset_ids.add(extracted)
        
        # Use first preset_id for the recipe's preset_id field (single ID per spec)
        # But keep all for stage2_lessons
        preset_id = sorted(preset_ids)[0] if preset_ids else None

        recipe: RecipeDict = {
            "key": {
                "purpose": purpose,
                "camera_movement": camera_movement,
                "method": method
            },
            "stage1": _build_stage1(group_beats_sorted),
            "stage2": _build_stage2(group_beats_sorted, registered_presets),
            "sound_lesson": _merge_sound_lessons(group_beats_sorted),
            "applicability": _build_applicability(),
            "counterexamples": _build_counterexamples(group_beats_sorted),
            "verification": verification,
            "source_beats": source_beats,
            "sequence_pattern": _build_sequence_pattern(group_beats_sorted),
            "when_not_to_use": _build_when_not_to_use(group_beats_sorted),
            "preset_id": preset_id,
            "stage1_lessons": _build_stage1_lessons(group_beats_sorted),
            "stage2_lessons": _build_stage2_lessons(group_beats_sorted, registered_presets, preset_id),
        }
        recipes.append(recipe)

    return {"status": "OK", "recipes": recipes}
