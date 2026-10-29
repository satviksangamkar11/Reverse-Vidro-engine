"""
WP-F1: Cumulative corpus ledger (no network, no model calls).

Immutable per-video results + one ledger. Ledger JSON schema:
{
  "schema": 1,
  "videos": {
    "<sha256>": {
      "sha256": "...",
      "kind": "video" | "image_sequence",
      "analysis_path": "...",
      "analyzed_at": "...",
      "versions": {"analysis": "...", "prompt": "...", "model": "..."},
      "sources": [
        {"source": "...", "origin": "local" | "instagram", "url": "...", "creator_id": "..."}
      ],
      "tags": {...},
      "history": [
        {"analyzed_at": "...", "analysis_path": "...", "versions": {...}}
      ]
    }
  }
}

Key is the CONTENT hash (sha256 of raw video bytes, or ordered frame manifest for image_sequence).
Source identity is separate: a second entry with the same sha256 but a different url/source
APPENDS to that video's "sources" list (status DUPLICATE) so attribution is kept.
Same sha256 + same versions + same sources => UPDATED no-op.

Atomic write (tmp+replace), utf-8; corrupt ledger raises ValueError, never silently resets.

Image sequence identity MUST preserve temporal order. Sort frames by numeric index
parsed from the filename (natural sort), then sha256 an ordered manifest of lines
"<position>:<frame_content_sha256>". Filenames do not matter beyond ordering.
Tests: A-B-C and C-B-A give DIFFERENT identities; identical ordered content under
different filenames gives the SAME identity. Raw-file sha256 stays for exact MP4 dedupe;
it is NOT perceptual duplicate detection (a re-encoded video is a different video here).
"""

import copy
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

__all__ = [
    "corpus_add",
    "corpus_status",
    "stale_entries",
    "compute_video_sha256",
    "compute_image_sequence_sha256",
    "normalize_url",
    "LedgerError",
]


class LedgerError(ValueError):
    """Raised when ledger is corrupt or cannot be parsed."""


def _natural_sort_key(s: str) -> List[Union[int, str]]:
    """Key for natural sorting (e.g., frame_2 before frame_10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def compute_video_sha256(video_path: Union[str, Path]) -> str:
    """Compute SHA256 of raw video file bytes."""
    h = hashlib.sha256()
    with open(video_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_image_sequence_sha256(frame_dir: Union[str, Path]) -> str:
    """
    Compute SHA256 of ordered frame manifest.
    Frames are sorted by numeric index parsed from filename (natural sort).
    Manifest lines: "<position>:<frame_content_sha256>"
    Only common image files are considered; hidden files are skipped.
    Tiebreaker: exact filename for deterministic ordering when keys tie.
    Raises ValueError if no frames are found.
    """
    frame_dir = Path(frame_dir)
    image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
    files = [
        f for f in frame_dir.iterdir()
        if f.is_file() and not f.name.startswith('.') and f.suffix.lower() in image_extensions
    ]
    if not files:
        raise ValueError("No image frames found in directory")
    # Sort by natural key, then by exact filename as tiebreaker for determinism
    files.sort(key=lambda p: (_natural_sort_key(p.name), p.name))

    h = hashlib.sha256()
    for idx, frame_path in enumerate(files):
        frame_hash = hashlib.sha256()
        with open(frame_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                frame_hash.update(chunk)
        manifest_line = f"{idx}:{frame_hash.hexdigest()}\n"
        h.update(manifest_line.encode("utf-8"))
    return h.hexdigest()


def normalize_url(url: Optional[str]) -> Optional[str]:
    """Normalize URL: lowercase host, strip query and trailing slash. Preserve scheme case."""
    if url is None:
        return None
    try:
        # Parse manually to preserve scheme case
        if "://" not in url:
            return url.lower().rstrip('/')
        scheme, rest = url.split("://", 1)
        # Split host from path/query
        if "/" in rest:
            host, path_query = rest.split("/", 1)
            path_part = path_query.split("?")[0].rstrip('/')
            path = "/" + path_part if path_part else ""
        else:
            host = rest.split("?")[0]
            path = ""
        normalized = f"{scheme}://{host.lower()}{path}"
        return normalized
    except Exception:
        # Fallback: best effort
        if "://" in url:
            scheme, rest = url.split("://", 1)
            if "/" in rest:
                host, path_query = rest.split("/", 1)
                path_part = path_query.split("?")[0].rstrip('/')
                path = "/" + path_part if path_part else ""
            else:
                host = rest.split("?")[0]
                path = ""
            return f"{scheme}://{host.lower()}{path}"
        return url.lower().rstrip('/')


def _source_key(source: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Key for deduplicating sources: normalized URL when present, otherwise source path."""
    url = normalize_url(source.get("url"))
    if url is not None:
        return (url, None)
    src = source.get("source", "")
    return (None, src)


def _validate_source(source: Dict[str, Any]) -> None:
    """Validate a source dict has required fields and allowed values."""
    if not isinstance(source, dict):
        raise LedgerError("Source must be a dictionary")
    required = {"source", "origin", "url", "creator_id"}
    missing = required - set(source.keys())
    if missing:
        raise LedgerError(f"Source missing required keys: {missing}")
    if not isinstance(source["source"], str):
        raise LedgerError("Source 'source' must be a string")
    if not isinstance(source["origin"], str):
        raise LedgerError("Source 'origin' must be a string")
    if source["origin"] not in ("local", "instagram"):
        raise LedgerError(f"Invalid origin: {source['origin']}")
    if source["url"] is not None and not isinstance(source["url"], str):
        raise LedgerError("Source url must be string or null")
    if source["creator_id"] is not None and not isinstance(source["creator_id"], str):
        raise LedgerError("Source creator_id must be string or null")


def _load_ledger(ledger_path: Union[str, Path]) -> Dict[str, Any]:
    """Load ledger from path, raise LedgerError if corrupt."""
    path = Path(ledger_path)
    if not path.exists():
        return {"schema": 1, "videos": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise LedgerError(f"Corrupt ledger JSON: {e}") from e
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise LedgerError("Invalid ledger schema")
    videos = data.get("videos")
    if not isinstance(videos, dict):
        raise LedgerError("Invalid ledger: 'videos' must be a dictionary")
    # Validate each video entry has required fields and types
    required_video_keys = {"sha256", "kind", "analysis_path", "analyzed_at", "versions", "sources", "tags", "history"}
    for key, video in videos.items():
        if not isinstance(video, dict):
            raise LedgerError(f"Invalid video entry for {key}: not a dict")
        missing = required_video_keys - set(video.keys())
        if missing:
            raise LedgerError(f"Invalid video entry for {key}: missing keys {missing}")
        if video.get("sha256") != key:
            raise LedgerError(f"Video key mismatch: {key} != {video.get('sha256')}")
        if video["kind"] not in ("video", "image_sequence"):
            raise LedgerError(f"Invalid kind for {key}: {video['kind']}")
        if not isinstance(video["versions"], dict):
            raise LedgerError(f"Invalid versions for {key}: not a dict")
        required_version_keys = {"analysis", "prompt", "model"}
        if not required_version_keys.issubset(video["versions"]):
            raise LedgerError(f"Invalid versions for {key}: missing keys")
        if not isinstance(video["sources"], list):
            raise LedgerError(f"Invalid sources for {key}: not a list")
        for src in video["sources"]:
            _validate_source(src)
        if not isinstance(video["tags"], dict):
            raise LedgerError(f"Invalid tags for {key}: not a dict")
        if not isinstance(video["history"], list):
            raise LedgerError(f"Invalid history for {key}: not a list")
        for hist in video["history"]:
            if not isinstance(hist, dict):
                raise LedgerError(f"Invalid history entry for {key}: not a dict")
            if not {"analyzed_at", "analysis_path", "versions"}.issubset(hist):
                raise LedgerError(f"Invalid history entry for {key}: missing keys")
    return data


def _save_ledger(ledger_path: Union[str, Path], data: Dict[str, Any]) -> None:
    """Atomically save ledger to path (tmp + replace) with fsync."""
    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
        ) as tmp:
            tmp_path = tmp.name
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


def corpus_add(
    ledger_path: Union[str, Path],
    entry: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Add or update an entry in the corpus ledger.

    Args:
        ledger_path: Path to ledger JSON file.
        entry: Dict with keys:
            - sha256 (str): Content hash (non-empty string).
            - kind (str): "video" or "image_sequence".
            - analysis_path (str): Path to analysis output.
            - analyzed_at (str): ISO timestamp.
            - versions (dict): {"analysis": str, "prompt": str, "model": str}.
            - sources (list): List of source dicts with keys:
                source (str), origin ("local"|"instagram"), url (str|None), creator_id (str|None).
            - tags (dict): Arbitrary tags.

    Returns:
        Dict with keys:
            - status: "ADDED" | "UPDATED" | "DUPLICATE"
            - video_key: sha256
            - sources_added: int (number of new sources appended)
    """
    required_keys = {"sha256", "kind", "analysis_path", "analyzed_at", "versions", "sources", "tags"}
    missing = required_keys - set(entry.keys())
    if missing:
        raise ValueError(f"Missing required entry keys: missing {missing}")

    sha256 = entry["sha256"]
    if not isinstance(sha256, str) or not sha256:
        raise ValueError("sha256 must be a non-empty string")

    kind = entry["kind"]
    if kind not in ("video", "image_sequence"):
        raise ValueError(f"Invalid kind: {kind}")

    # Validate versions dict has required keys and is a dict
    if not isinstance(entry["versions"], dict):
        raise ValueError("versions must be a dictionary")
    required_version_keys = {"analysis", "prompt", "model"}
    if not required_version_keys.issubset(entry["versions"]):
        raise ValueError(f"versions must contain keys: {required_version_keys}")

    # Validate tags is a dict
    if not isinstance(entry["tags"], dict):
        raise ValueError("tags must be a dictionary")

    # Validate sources
    if not isinstance(entry["sources"], list):
        raise ValueError("sources must be a list")
    for src in entry["sources"]:
        _validate_source(src)

    ledger = _load_ledger(ledger_path)
    videos = ledger["videos"]

    # Normalize and dedupe incoming sources
    incoming_sources = []
    seen_source_keys = set()
    for src in entry["sources"]:
        key = _source_key(src)
        if key not in seen_source_keys:
            seen_source_keys.add(key)
            incoming_sources.append(src)

    if sha256 not in videos:
        # New video
        video_entry = {
            "sha256": sha256,
            "kind": kind,
            "analysis_path": entry["analysis_path"],
            "analyzed_at": entry["analyzed_at"],
            "versions": copy.deepcopy(entry["versions"]),
            "sources": copy.deepcopy(incoming_sources),
            "tags": copy.deepcopy(entry["tags"]),
            "history": [],
        }
        videos[sha256] = video_entry
        _save_ledger(ledger_path, ledger)
        return {"status": "ADDED", "video_key": sha256, "sources_added": len(incoming_sources)}

    # Existing video
    existing = videos[sha256]

    # Validate kind matches
    if existing["kind"] != kind:
        raise ValueError(f"Kind mismatch for {sha256}: existing={existing['kind']} new={kind}")

    # Check if versions differ
    versions_changed = existing["versions"] != entry["versions"]

    # Determine new sources to add
    existing_source_keys = {_source_key(s) for s in existing["sources"]}
    new_sources = [s for s in incoming_sources if _source_key(s) not in existing_source_keys]
    sources_added = len(new_sources)

    # Analysis fields change ONLY when versions differ (per spec)
    analysis_fields_changed = versions_changed

    if not analysis_fields_changed and sources_added == 0:
        # No changes at all: same versions, no new sources -> UPDATED no-op
        return {"status": "UPDATED", "video_key": sha256, "sources_added": 0}

    # Push current state to history ONLY when versions change
    if analysis_fields_changed:
        history_entry = {
            "analyzed_at": existing["analyzed_at"],
            "analysis_path": existing["analysis_path"],
            "versions": copy.deepcopy(existing["versions"]),
        }
        existing["history"].append(history_entry)

        # Update analysis fields when versions change
        existing["analysis_path"] = entry["analysis_path"]
        existing["analyzed_at"] = entry["analyzed_at"]
        existing["versions"] = copy.deepcopy(entry["versions"])
        existing["tags"] = copy.deepcopy(entry["tags"])
    # When versions unchanged but new sources added: do NOT overwrite analysis fields, do NOT push history

    # Union sources (always)
    if new_sources:
        existing["sources"].extend(copy.deepcopy(new_sources))

    _save_ledger(ledger_path, ledger)

    if versions_changed:
        return {"status": "UPDATED", "video_key": sha256, "sources_added": sources_added}
    else:
        # versions unchanged but new sources were added
        return {"status": "DUPLICATE", "video_key": sha256, "sources_added": sources_added}


def corpus_status(
    ledger_path: Union[str, Path],
    queue_urls: List[str],
    failed_urls: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Get corpus status relative to a queue of URLs.

    Args:
        ledger_path: Path to ledger JSON file.
        queue_urls: List of URLs in the processing queue.
        failed_urls: Optional list of URLs that failed processing.

    Returns:
        Dict with keys:
            - analyzed: count of queue URLs that have a source in ledger.
            - queued_not_analyzed: list of queue URLs with no ledger source (original URLs).
            - failed: list of failed URLs (from failed_urls param, returned as-is).
            - total: total queue URLs.
    """
    if failed_urls is None:
        failed_urls = []

    ledger = _load_ledger(ledger_path)

    # Build set of normalized URLs present in ledger sources
    ledger_urls = set()
    for video in ledger["videos"].values():
        for src in video.get("sources", []):
            norm = normalize_url(src.get("url"))
            if norm:
                ledger_urls.add(norm)

    # Track original URLs alongside normalized
    analyzed = 0
    queued_not_analyzed = []
    for u in queue_urls:
        norm = normalize_url(u)
        if norm in ledger_urls:
            analyzed += 1
        else:
            queued_not_analyzed.append(u)

    return {
        "analyzed": analyzed,
        "queued_not_analyzed": queued_not_analyzed,
        "failed": failed_urls,
        "total": len(queue_urls),
    }


def stale_entries(
    ledger_path: Union[str, Path],
    current_versions: Dict[str, str],
    strict: bool = False,
) -> List[Dict[str, str]]:
    """
    Find entries whose analysis or prompt version differs from current_versions.

    Args:
        ledger_path: Path to ledger JSON file.
        current_versions: Dict with keys "analysis", "prompt", "model".
        strict: If True, also consider model version changes as stale.

    Returns:
        Sorted list of dicts: [{"sha256": "...", "reason": "..."}].
        Reasons: "analysis_version", "prompt_version", "model_version" (strict only).
    """
    required_version_keys = {"analysis", "prompt", "model"}
    if not required_version_keys.issubset(current_versions):
        raise ValueError(f"current_versions must contain keys: {required_version_keys}")

    ledger = _load_ledger(ledger_path)
    stale = []

    for sha256, video in ledger["videos"].items():
        v = video["versions"]
        reasons = []
        if v.get("analysis") != current_versions.get("analysis"):
            reasons.append("analysis_version")
        if v.get("prompt") != current_versions.get("prompt"):
            reasons.append("prompt_version")
        if strict and v.get("model") != current_versions.get("model"):
            reasons.append("model_version")
        if reasons:
            stale.append({"sha256": sha256, "reason": ", ".join(reasons)})

    # Sort by sha256 for deterministic output
    stale.sort(key=lambda x: x["sha256"])
    return stale
