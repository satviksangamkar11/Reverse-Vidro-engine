"""Link Queue Management for Instagram Reel Imports."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Callable


def queue_links(
    urls: list[str],
    queue_file: str,
    normalize_reel_url: Callable[[str], str | None],
    clock_now: Callable[[], str],
) -> dict:
    """
    Add normalized reel URLs to a queue file, deduplicating against existing entries.

    Args:
        urls: Raw URL strings to add.
        queue_file: Path to the queue text file (one URL per line, comments start with '#').
        normalize_reel_url: Callable that returns a normalized URL or None if invalid.
        clock_now: Callable returning an ISO timestamp string (injected for future use).

    Returns:
        Dict with keys: added, already_queued, rejected, status.
    """
    # Read existing queue file atomically
    existing_urls = set()
    lines = []
    queue_path = Path(queue_file)
    try:
        content = queue_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                existing_urls.add(stripped)
    except FileNotFoundError:
        lines = []

    added = []
    already_queued = []
    rejected = []
    seen_in_batch = set()

    for raw_url in urls:
        normalized = normalize_reel_url(raw_url)
        if normalized is None:
            # Only add to rejected if this raw_url hasn't been seen before
            if raw_url not in seen_in_batch:
                rejected.append({"url": raw_url, "error": "Invalid Instagram Reel URL"})
                seen_in_batch.add(raw_url)
            continue

        # Track by normalized URL to deduplicate within batch
        if normalized in seen_in_batch:
            continue
        seen_in_batch.add(normalized)

        if normalized in existing_urls:
            already_queued.append(normalized)
        else:
            added.append(normalized)
            existing_urls.add(normalized)
            lines.append(normalized)

    # Write back queue file atomically (write to temp then replace)
    queue_dir = queue_path.parent
    queue_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=queue_dir,
        delete=False,
        prefix=queue_path.name + ".",
        suffix=".tmp",
    ) as tmp:
        tmp.write(("\n".join(lines) + "\n") if lines else "")
        tmp_path = tmp.name
    os.replace(tmp_path, queue_path)

    return {
        "added": added,
        "already_queued": already_queued,
        "rejected": rejected,
        "status": "ok",
    }


def queue_status(
    queue_file: str,
    ledger_path: str,
    read_text_file: Callable[[str], str],
    parse_json_lines: Callable[[str], list[dict]],
) -> dict:
    """
    Get the status of each URL in the queue file by cross-referencing the ledger.

    Args:
        queue_file: Path to the queue text file.
        ledger_path: Path to the JSON Lines ledger file.
        read_text_file: Callable to read a text file.
        parse_json_lines: Callable to parse JSON Lines into a list of dicts.

    Returns:
        Dict with keys: items (list of {url, state, error}), status.
    """
    # Read queue URLs in order
    queue_content = read_text_file(queue_file)
    queue_urls = []
    for line in queue_content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            queue_urls.append(stripped)

    # Read ledger entries (let read_text_file handle missing files)
    try:
        ledger_content = read_text_file(ledger_path)
    except FileNotFoundError:
        ledger_content = ""
    ledger_entries = parse_json_lines(ledger_content) if ledger_content else []

    # Build lookup: url -> (status, error)
    ledger_map = {}
    for entry in ledger_entries:
        url = entry.get("url")
        if url:
            ledger_map[url] = (entry.get("status"), entry.get("error"))

    items = []
    for url in queue_urls:
        if url in ledger_map:
            status, error = ledger_map[url]
            if status == "DOWNLOADED":
                state = "DOWNLOADED"
            elif status == "FAILED_INACCESSIBLE":
                state = "FAILED_INACCESSIBLE"
            else:
                state = "QUEUED"
            items.append({"url": url, "state": state, "error": error})
        else:
            items.append({"url": url, "state": "QUEUED", "error": None})

    return {"items": items, "status": "ok"}


def read_queue_file(
    queue_file: str,
    read_text_file: Callable[[str], str],
) -> dict:
    """
    Read a queue file and return URLs and comments separately, preserving order.

    Args:
        queue_file: Path to the queue text file.
        read_text_file: Callable to read a text file.

    Returns:
        Dict with keys: urls, comments, status.
    """
    content = read_text_file(queue_file)
    urls = []
    comments = []
    for line in content.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            comments.append(line.rstrip("\n\r"))
        elif line.strip():
            urls.append(line.strip())
    return {"urls": urls, "comments": comments, "status": "ok"}
