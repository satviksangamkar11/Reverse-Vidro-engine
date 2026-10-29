from typing import Dict, List, Any

VALID_EXECUTABILITY = {"EXISTING_PRESET", "POSE_OR_LAYER_CHANGE", "NEED_NEW", "RESEARCH_ONLY"}
VALID_CLASSIFICATION = {"GENERAL", "STYLE_SPECIFIC", "EXPERIMENTAL"}

def _compute_styles_from_videos(videos: List[Dict[str, Any]]) -> int:
    """Count distinct art_style values across videos."""
    if not videos:
        return 0
    styles = set()
    for v in videos:
        art_style = v.get("art_style")
        if art_style:
            styles.add(art_style)
    return len(styles)

def _get_styles(evidence: Dict[str, Any]) -> int:
    """Get styles count: derive from videos list if present, else use precomputed, else 0."""
    if isinstance(evidence.get("videos"), list):
        return _compute_styles_from_videos(evidence["videos"])
    return evidence.get("styles", 0)

def _get_videos_count(evidence: Dict[str, Any]) -> int:
    """Get videos count: if videos is a list, return its length; else return integer value or 0."""
    videos = evidence.get("videos", 0)
    if isinstance(videos, list):
        return len(videos)
    return videos if isinstance(videos, int) else 0

def classify_technique(evidence: Dict[str, Any]) -> str:
    """Classify technique based on evidence.
    
    Styles is always derived from the videos list (distinct art_style values)
    when evidence contains a videos list. Precomputed "styles" is only used
    when no videos list is present.
    """
    evidence = evidence or {}
    videos = _get_videos_count(evidence)
    independent_creators = evidence.get("independent_creators", 0)
    styles = _get_styles(evidence)
    
    if independent_creators >= 2 and styles >= 2:
        return "GENERAL"
    elif (videos >= 2 or independent_creators >= 2) and styles == 1:
        return "STYLE_SPECIFIC"
    else:
        return "EXPERIMENTAL"

def research_confidence(evidence: Dict[str, Any]) -> str:
    """Determine research confidence based on evidence."""
    evidence = evidence or {}
    videos = _get_videos_count(evidence)
    independent_creators = evidence.get("independent_creators", 0)
    method_verified = evidence.get("method_verified") is True
    
    if videos < 2 or not method_verified:
        return "LOW"
    elif independent_creators >= 3 and method_verified:
        return "HIGH"
    else:
        return "MEDIUM"

def usage_bucket(technique: Dict[str, Any]) -> str:
    """Determine usage bucket for a technique. Returns bucket string only."""
    classification = technique.get("classification", "")
    if classification not in VALID_CLASSIFICATION:
        raise ValueError(f"Invalid classification: {classification}")
    
    executability_raw = technique.get("executability")
    if not isinstance(executability_raw, str):
        raise ValueError(f"Invalid executability: {executability_raw}")
    executability = executability_raw.strip()
    
    # assets_available must be exactly True (not truthy)
    assets_available = technique.get("assets_available") is True
    
    if executability not in VALID_EXECUTABILITY:
        raise ValueError(f"Invalid executability: {executability}")
    
    # Truth table per spec
    if classification == "EXPERIMENTAL" or executability == "RESEARCH_ONLY":
        return "RESEARCH_ONLY"
    elif executability in ("EXISTING_PRESET", "POSE_OR_LAYER_CHANGE"):
        if assets_available:
            return "USABLE_NOW"
        else:
            return "USEFUL_BUT_BLOCKED"
    elif executability == "NEED_NEW":
        return "USEFUL_BUT_BLOCKED"
    
    # Should never reach here due to validation above
    raise ValueError(f"Unhandled executability: {executability}")

def _blocked_reason(technique: Dict[str, Any], bucket: str) -> str:
    """Return blocked_reason for USEFUL_BUT_BLOCKED items, else None."""
    if bucket != "USEFUL_BUT_BLOCKED":
        return None
    executability_raw = technique.get("executability", "")
    executability = executability_raw.strip() if isinstance(executability_raw, str) else ""
    if executability == "NEED_NEW":
        return "NEED_NEW"
    # EXISTING_PRESET or POSE_OR_LAYER_CHANGE with assets_available False
    return "MISSING_ASSET"

def _make_evidence_summary(technique: Dict[str, Any]) -> Dict[str, int]:
    """Build evidence_summary from technique, computing styles from videos if needed."""
    evidence = technique.get("evidence") or {}
    videos = _get_videos_count(evidence)
    independent_creators = evidence.get("independent_creators", 0)
    styles = _get_styles(evidence)
    
    return {
        "videos": videos,
        "independent_creators": independent_creators,
        "styles": styles
    }

def kimi_views(techniques: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Generate Kimi views from techniques."""
    # Sort by technique id for stable ordering, handle None/mixed types
    sorted_techniques = sorted(techniques, key=lambda t: str(t.get("id") or ""))
    
    stage1 = []
    stage2 = []
    research_only = []
    
    for tech in sorted_techniques:
        bucket = usage_bucket(tech)
        tech_id = tech.get("id", "")
        classification = tech.get("classification", "")
        preset_id = tech.get("preset_id")
        
        evidence_summary = _make_evidence_summary(tech)
        confidence = research_confidence(tech.get("evidence") or {})
        
        base_item = {
            "id": tech_id,
            "classification": classification,
            "evidence_summary": evidence_summary,
            "research_confidence": confidence
        }
        
        if bucket == "USABLE_NOW":
            # Add to stage1
            stage1_item = base_item.copy()
            stage1_item["blocked_reason"] = None
            stage1.append(stage1_item)
            
            # Add to stage2 only if preset_id exists and is non-empty string
            if isinstance(preset_id, str) and preset_id.strip():
                stage2_item = {"id": tech_id, "preset_id": preset_id}
                stage2.append(stage2_item)
                
        elif bucket == "USEFUL_BUT_BLOCKED":
            stage1_item = base_item.copy()
            stage1_item["blocked_reason"] = _blocked_reason(tech, bucket)
            # Add the required note for all blocked items
            stage1_item["blocked_note"] = "report via existing NEED_NEW if no approved asset"
            stage1.append(stage1_item)
            
        elif bucket == "RESEARCH_ONLY":
            research_only.append(base_item)
    
    return {
        "stage1": stage1,
        "stage2": stage2,
        "research_only": research_only
    }
