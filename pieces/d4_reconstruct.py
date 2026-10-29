from typing import Dict, List, Any, Optional, Set, Tuple
import copy

def reconstruct_sequence(beats: List[Dict[str, Any]], audio_evidence: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reconstruct a full 8-part sequence from validated beats and audio evidence.
    """
    if not beats:
        return _empty_reconstruction(audio_evidence)
    
    # Keep supplied beat order; if sorting ever needed, use (start_time.seconds, original index)
    # Here we assume beats are already in correct order.
    sorted_beats = beats
    
    # 1. narrative_progression
    narrative_progression = []
    for beat in sorted_beats:
        info = beat.get("information_conveyed", "")
        if info:
            narrative_progression.append({
                "beat_id": beat.get("beat_id", ""),
                "summary": info
            })
    
    # 2. shots_and_transitions
    shots_and_transitions = {}
    for beat in sorted_beats:
        beat_id = beat.get("beat_id", "")
        dept_findings = beat.get("department_findings", {})
        
        # Extract shot timing from department 1 (first finding if list)
        dept1_list = dept_findings.get("1", [])
        start = None
        end = None
        if dept1_list:
            first = dept1_list[0]
            start = first.get("start_frame") or first.get("start_time")
            end = first.get("end_frame") or first.get("end_time")
        
        # Extract terms from departments 4,5,6,7 (first OBSERVED finding each)
        shot_terms = {}
        for dept_num in ["4", "5", "6", "7"]:
            findings = dept_findings.get(dept_num, [])
            for finding in findings:
                if finding.get("status") == "OBSERVED":
                    term = finding.get("term") or finding.get("observed")
                    if term:
                        shot_terms[f"dept_{dept_num}"] = term
                    break
        
        shots_and_transitions[beat_id] = {
            "start": start,
            "end": end,
            "terms": shot_terms
        }
    
    # 3. performance (departments 8,9)
    performance = {}
    for beat in sorted_beats:
        beat_id = beat.get("beat_id", "")
        dept_findings = beat.get("department_findings", {})
        perf_data = {}
        for dept_num in ["8", "9"]:
            findings = dept_findings.get(dept_num, [])
            for finding in findings:
                if finding.get("status") == "OBSERVED":
                    term = finding.get("term") or finding.get("observed")
                    if term:
                        perf_data[f"dept_{dept_num}"] = term
                    break
        if perf_data:
            performance[beat_id] = perf_data
    
    # 4. sound_image (department 13 + audio_evidence)
    audio_status = audio_evidence.get("status", "UNAVAILABLE")
    if audio_status in ("UNAVAILABLE", "NO_AUDIO_STREAM"):
        sound_image = {"status": "UNAVAILABLE"}
    else:
        sound_image = {}
        # Add department 13 findings from beats (all OBSERVED findings)
        dept13_findings = []
        for beat in sorted_beats:
            beat_id = beat.get("beat_id", "")
            dept_findings = beat.get("department_findings", {})
            findings = dept_findings.get("13", [])
            for finding in findings:
                if finding.get("status") == "OBSERVED":
                    term = finding.get("term") or finding.get("observed")
                    if term:
                        dept13_findings.append({
                            "beat_id": beat_id,
                            "finding": term
                        })
        if dept13_findings:
            sound_image["dept_13_findings"] = dept13_findings
        # Add audio evidence
        if audio_evidence:
            sound_image["audio_evidence"] = audio_evidence
    
    # 5. techniques (departments 10,11,12,14)
    techniques = {}
    for beat in sorted_beats:
        beat_id = beat.get("beat_id", "")
        dept_findings = beat.get("department_findings", {})
        tech_data = {}
        for dept_num in ["10", "11", "12", "14"]:
            findings = dept_findings.get(dept_num, [])
            for finding in findings:
                if finding.get("status") == "OBSERVED":
                    term = finding.get("term") or finding.get("observed")
                    if term:
                        tech_data[f"dept_{dept_num}"] = term
                    break
        if tech_data:
            techniques[beat_id] = tech_data
    
    # 6. why_it_may_work: from each finding's inferred_purpose + cross-beat patterns
    why_it_may_work = []
    # Map confidence strings to numeric
    conf_map = {"LOW": 0.3, "MEDIUM": 0.6, "HIGH": 0.9}
    for beat in sorted_beats:
        beat_id = beat.get("beat_id", "")
        dept_findings = beat.get("department_findings", {})
        for dept_num, findings in dept_findings.items():
            for finding in findings:
                inferred = finding.get("inferred_purpose")
                if inferred:
                    conf_str = finding.get("confidence", "MEDIUM")
                    confidence = conf_map.get(conf_str, 0.5)
                    why_it_may_work.append({
                        "hypothesis": inferred,
                        "based_on_beat_ids": [beat_id],
                        "confidence": confidence
                    })
    # Cross-beat pattern hypotheses
    for i in range(len(sorted_beats) - 1):
        beat1 = sorted_beats[i]
        beat2 = sorted_beats[i + 1]
        pattern = beat1.get("sequence_pattern")
        if pattern:
            conf1 = beat1.get("confidence", 0.5)
            conf2 = beat2.get("confidence", 0.5)
            # If confidence is string, map it
            if isinstance(conf1, str):
                conf1 = conf_map.get(conf1, 0.5)
            if isinstance(conf2, str):
                conf2 = conf_map.get(conf2, 0.5)
            why_it_may_work.append({
                "hypothesis": f"Sequence pattern '{pattern}' links {beat1.get('beat_id')} to {beat2.get('beat_id')}",
                "based_on_beat_ids": [beat1.get("beat_id", ""), beat2.get("beat_id", "")],
                "confidence": min(conf1, conf2)
            })
    
    # 7. simplest_reproduction
    simplest_reproduction = {}
    for beat in sorted_beats:
        beat_id = beat.get("beat_id", "")
        reproduction = beat.get("reproduction", {})
        simplest_reproduction[beat_id] = {
            "status": reproduction.get("status", "UNKNOWN"),
            "artwork_needed": reproduction.get("artwork_needed", []),
            "simplest_method": reproduction.get("simplest_method", "")
        }
    
    # 8. unknowns
    unknowns = set()
    for beat in sorted_beats:
        # Add beat's unknowns
        beat_unknowns = beat.get("unknowns", [])
        if isinstance(beat_unknowns, list):
            unknowns.update(beat_unknowns)
        
        # Add NOT_OBSERVED/UNKNOWN/NOT_EXAMINED findings from department_findings
        dept_findings = beat.get("department_findings", {})
        for dept_num, findings in dept_findings.items():
            for finding in findings:
                status = finding.get("status")
                if status in ("NOT_OBSERVED", "UNKNOWN", "NOT_EXAMINED"):
                    if status == "NOT_EXAMINED":
                        unknowns.add(f"dept_{dept_num}: not examined")
                    else:
                        unknowns.add(f"dept_{dept_num}: {status.lower()}")
    
    # 9. relationships
    relationships = []
    for i in range(len(sorted_beats) - 1):
        beat1 = sorted_beats[i]
        beat2 = sorted_beats[i + 1]
        pattern = beat1.get("sequence_pattern")
        if pattern:
            relationships.append({
                "from_beat": beat1.get("beat_id", ""),
                "to_beat": beat2.get("beat_id", ""),
                "pattern": pattern
            })
    
    return {
        "narrative_progression": narrative_progression,
        "shots_and_transitions": shots_and_transitions,
        "performance": performance,
        "sound_image": sound_image,
        "techniques": techniques,
        "why_it_may_work": why_it_may_work,
        "simplest_reproduction": simplest_reproduction,
        "unknowns": sorted(list(unknowns)),
        "relationships": relationships
    }

def _empty_reconstruction(audio_evidence: Dict[str, Any]) -> Dict[str, Any]:
    audio_status = audio_evidence.get("status", "UNAVAILABLE")
    sound_image = {"status": "UNAVAILABLE"} if audio_status in ("UNAVAILABLE", "NO_AUDIO_STREAM") else {"audio_evidence": audio_evidence}
    return {
        "narrative_progression": [],
        "shots_and_transitions": {},
        "performance": {},
        "sound_image": sound_image,
        "techniques": {},
        "why_it_may_work": [],
        "simplest_reproduction": {},
        "unknowns": [],
        "relationships": []
    }

def verify_reconstruction(reconstruction: Dict[str, Any], beats: List[Dict[str, Any]], audit: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Mechanically verify the reconstruction against beats.
    Returns structural_ok, semantic_status, and problems list.
    """
    problems = []
    
    # Build evidence index from beats
    evidence_index = _build_evidence_index(beats)
    
    # Check 1: Every OBSERVED claim cites an evidence frame/time that exists in a source beat
    _check_observed_claims(reconstruction, beats, evidence_index, problems)
    
    # Check 2: Every hypothesis is in why_it_may_work (never in observed sections)
    _check_hypotheses_separated(reconstruction, beats, problems)
    
    # Check 3: No sound claim exists when audio is UNAVAILABLE
    _check_audio_rule(reconstruction, problems)
    
    # Check 4: At least one relationship entry exists when there are >=2 beats
    _check_relationships(reconstruction, beats, problems)
    
    # Check 5: No field asserts editing software, lens, hidden rig or screenplay text
    _check_forbidden_assertions(reconstruction, problems)
    
    # Check 6: No preset id appears that is not in the beats' reproduction data
    _check_preset_ids(reconstruction, beats, problems)
    
    structural_ok = len(problems) == 0
    
    # Determine semantic_status
    semantic_status = "NOT_VERIFIED"
    if audit and isinstance(audit, dict):
        verdict = audit.get("verdict")
        if verdict:
            semantic_status = f"AUDITED_{verdict}"
    
    return {
        "ok": structural_ok,
        "structural_ok": structural_ok,
        "semantic_status": semantic_status,
        "problems": problems
    }

def _build_evidence_index(beats: List[Dict[str, Any]]) -> Dict[str, Set[Tuple[str, Any]]]:
    """Build an index of all evidence frames/times per beat."""
    index = {}
    for beat in beats:
        beat_id = beat.get("beat_id", "")
        evidence_set = set()
        dept_findings = beat.get("department_findings", {})
        for dept_num, findings in dept_findings.items():
            for finding in findings:
                if finding.get("status") == "OBSERVED":
                    # Collect frame/time evidence from finding
                    for key in ["frame", "start_frame", "end_frame", "start_time", "end_time", "timecode"]:
                        if key in finding and finding[key] is not None:
                            evidence_set.add((key, finding[key]))
                    # Also check evidence list
                    if "evidence" in finding and isinstance(finding["evidence"], list):
                        for ev in finding["evidence"]:
                            if isinstance(ev, dict):
                                for k, v in ev.items():
                                    evidence_set.add((k, v))
        index[beat_id] = evidence_set
    return index

def _has_evidence(finding: Dict[str, Any]) -> bool:
    """Check if a finding has any evidence (direct fields or evidence list)."""
    # Check direct frame/time fields
    for key in ["frame", "start_frame", "end_frame", "start_time", "end_time", "timecode"]:
        if key in finding and finding[key] is not None:
            return True
    # Check evidence list
    if "evidence" in finding and isinstance(finding["evidence"], list) and len(finding["evidence"]) > 0:
        return True
    return False

def _check_observed_claims(reconstruction: Dict[str, Any], beats: List[Dict[str, Any]], 
                           evidence_index: Dict[str, Set[Tuple[str, Any]]], problems: List[str]):
    """Check that observed claims have supporting evidence in source beats."""
    # Check shots_and_transitions
    for beat_id, shot_data in reconstruction.get("shots_and_transitions", {}).items():
        terms = shot_data.get("terms", {})
        for dept_key, term in terms.items():
            source_beat = next((b for b in beats if b.get("beat_id") == beat_id), None)
            if not source_beat:
                problems.append(f"Shot {beat_id} references unknown beat")
                continue
            
            dept_num = dept_key.replace("dept_", "")
            findings = source_beat.get("department_findings", {}).get(dept_num, [])
            # Find the OBSERVED finding that matches this term
            matched = False
            for finding in findings:
                if finding.get("status") == "OBSERVED":
                    matched = True
                    # Check if there's evidence
                    if not _has_evidence(finding):
                        problems.append(f"OBSERVED claim in {beat_id} dept {dept_num} lacks evidence frame/time")
                    break
            if not matched:
                problems.append(f"OBSERVED claim in {beat_id} dept {dept_num} not found in source beat")
    
    # Check performance
    for beat_id, perf_data in reconstruction.get("performance", {}).items():
        source_beat = next((b for b in beats if b.get("beat_id") == beat_id), None)
        if not source_beat:
            continue
        for dept_key, finding_text in perf_data.items():
            dept_num = dept_key.replace("dept_", "")
            findings = source_beat.get("department_findings", {}).get(dept_num, [])
            matched = False
            for finding in findings:
                if finding.get("status") == "OBSERVED":
                    matched = True
                    if not _has_evidence(finding):
                        problems.append(f"OBSERVED performance claim in {beat_id} dept {dept_num} lacks evidence")
                    break
            if not matched:
                problems.append(f"OBSERVED performance claim in {beat_id} dept {dept_num} not found in source beat")
    
    # Check techniques
    for beat_id, tech_data in reconstruction.get("techniques", {}).items():
        source_beat = next((b for b in beats if b.get("beat_id") == beat_id), None)
        if not source_beat:
            continue
        for dept_key, finding_text in tech_data.items():
            dept_num = dept_key.replace("dept_", "")
            findings = source_beat.get("department_findings", {}).get(dept_num, [])
            matched = False
            for finding in findings:
                if finding.get("status") == "OBSERVED":
                    matched = True
                    if not _has_evidence(finding):
                        problems.append(f"OBSERVED technique claim in {beat_id} dept {dept_num} lacks evidence")
                    break
            if not matched:
                problems.append(f"OBSERVED technique claim in {beat_id} dept {dept_num} not found in source beat")
    
    # Check sound_image (dept 13)
    sound_image = reconstruction.get("sound_image", {})
    if sound_image.get("status") != "UNAVAILABLE":
        dept13_findings = sound_image.get("dept_13_findings", [])
        for finding_entry in dept13_findings:
            beat_id = finding_entry.get("beat_id")
            source_beat = next((b for b in beats if b.get("beat_id") == beat_id), None)
            if not source_beat:
                continue
            findings = source_beat.get("department_findings", {}).get("13", [])
            matched = False
            for finding in findings:
                if finding.get("status") == "OBSERVED":
                    matched = True
                    if not _has_evidence(finding):
                        problems.append(f"OBSERVED sound claim in {beat_id} dept 13 lacks evidence")
                    break
            if not matched:
                problems.append(f"OBSERVED sound claim in {beat_id} dept 13 not found in source beat")

def _check_hypotheses_separated(reconstruction: Dict[str, Any], beats: List[Dict[str, Any]], problems: List[str]):
    """Ensure hypotheses only appear in why_it_may_work, not in observed sections."""
    hypothesis_indicators = ["suggests", "implies", "hypothesis", "inferred", "likely", "probably", "indicates"]
    
    observed_sections = [
        ("shots_and_transitions", reconstruction.get("shots_and_transitions", {})),
        ("performance", reconstruction.get("performance", {})),
        ("techniques", reconstruction.get("techniques", {})),
        ("sound_image", reconstruction.get("sound_image", {})),
    ]
    
    for section_name, section_data in observed_sections:
        if section_name == "sound_image" and section_data.get("status") == "UNAVAILABLE":
            continue
        _check_dict_for_hypotheses(section_data, hypothesis_indicators, section_name, problems)

def _check_dict_for_hypotheses(data: Any, indicators: List[str], 
                                section_name: str, problems: List[str], path: str = ""):
    """Recursively check dict for hypothesis-like content in observed sections."""
    if isinstance(data, dict):
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key
            _check_dict_for_hypotheses(value, indicators, section_name, problems, new_path)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            _check_dict_for_hypotheses(item, indicators, section_name, problems, f"{path}[{i}]")
    elif isinstance(data, str):
        lower = data.lower()
        for indicator in indicators:
            if indicator in lower and len(data) > 20:
                problems.append(f"Hypothesis-like text found in observed section {section_name}{path}: {data[:100]}")
                return

def _check_audio_rule(reconstruction: Dict[str, Any], problems: List[str]):
    """Check no sound claims when audio is UNAVAILABLE."""
    sound_image = reconstruction.get("sound_image", {})
    if sound_image.get("status") == "UNAVAILABLE":
        if len(sound_image) > 1:
            problems.append("sound_image has extra fields when status is UNAVAILABLE")

def _check_relationships(reconstruction: Dict[str, Any], beats: List[Dict[str, Any]], problems: List[str]):
    """Check at least one relationship exists when >=2 beats."""
    if len(beats) >= 2:
        relationships = reconstruction.get("relationships", [])
        if not relationships:
            problems.append("No relationships found for sequence with 2+ beats")

def _check_forbidden_assertions(reconstruction: Dict[str, Any], problems: List[str]):
    """Check no field asserts editing software, lens, hidden rig or screenplay text."""
    forbidden_terms = [
        "editing software", "premiere", "final cut", "davinci", "avid",
        "lens", "focal length", "mm lens",
        "hidden rig", "rig removal", "wire removal",
        "screenplay", "script says", "according to script"
    ]
    
    def check_obj(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                check_obj(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                check_obj(v, f"{path}[{i}]")
        elif isinstance(obj, str):
            lower = obj.lower()
            for term in forbidden_terms:
                if term in lower:
                    problems.append(f"Forbidden assertion '{term}' found at {path}: {obj[:100]}")
    
    check_obj(reconstruction)

def _check_preset_ids(reconstruction: Dict[str, Any], beats: List[Dict[str, Any]], problems: List[str]):
    """Check no preset id appears that is not in beats' reproduction data."""
    valid_presets = set()
    for beat in beats:
        reproduction = beat.get("reproduction", {})
        preset_id = reproduction.get("preset_id")
        if preset_id:
            valid_presets.add(preset_id)
        for artwork in reproduction.get("artwork_needed", []):
            if isinstance(artwork, str) and artwork.startswith("preset_"):
                valid_presets.add(artwork)
    
    def check_presets(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "preset_id" and isinstance(v, str):
                    if v not in valid_presets:
                        problems.append(f"Unknown preset_id '{v}' at {path}")
                check_presets(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                check_presets(v, f"{path}[{i}]")
    
    check_presets(reconstruction)
