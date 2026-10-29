"""WP-A2: Input Collection (collect_inputs)"""
from __future__ import annotations

import os
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, List, Dict, Any, Tuple


# Video extensions: .mp4, .mov, .mkv, .webm (case-insensitive)
VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".webm")
# Image-sequence extensions: .jpg, .jpeg, .png (case-insensitive)
IMAGE_EXTS = (".jpg", ".jpeg", ".png")
MEDIA_EXTS = VIDEO_EXTS + IMAGE_EXTS

MAX_TOTAL_SIZE = 4 * 1024**3  # 4 GiB
MAX_MEMBERS = 20000


def _is_media_file(path: str) -> bool:
    """Check if file has a valid media extension (case-insensitive)."""
    ext = os.path.splitext(path)[1].lower()
    return ext in MEDIA_EXTS


def _is_unsafe_path(name: str) -> Tuple[bool, str]:
    """
    Check if a zip member path is unsafe.
    Returns (is_unsafe, error_message).
    Validation order: absolute, '..', ':' or backslash, symlink.
    """
    # Absolute path (POSIX or Windows drive letter)
    # Use PurePosixPath and PureWindowsPath to detect absolute paths cross-platform
    if PurePosixPath(name).is_absolute() or PureWindowsPath(name).is_absolute():
        return True, "Absolute path not allowed"
    # Path traversal - check both POSIX and Windows separators
    # Split on both / and \ to catch .. in any position
    parts = name.replace("\\", "/").split("/")
    if ".." in parts:
        return True, "Zip-slip attempt: path traversal"
    # Backslash or colon (Windows-specific unsafe)
    if "\\" in name or ":" in name:
        return True, "Unsafe path"
    return False, ""


def _walk_files(root: str, list_dir: Callable[[str], List[str]], is_file: Callable[[str], bool], is_dir: Callable[[str], bool]) -> List[str]:
    """Recursively walk a directory and return all file paths."""
    files = []
    def walk(current: str):
        for entry in list_dir(current):
            if is_file(entry):
                files.append(entry)
            elif is_dir(entry):
                walk(entry)
    walk(root)
    return files


def scan_for_media(
    root: str,
    video_exts: Tuple[str, ...],
    image_exts: Tuple[str, ...],
    list_dir: Callable[[str], List[str]],
    is_file: Callable[[str], bool],
    is_dir: Callable[[str], bool],
) -> Dict[str, Any]:
    """
    Recursively scan a directory for media files.
    Returns {"media_files": list[str], "status": "ok"}
    """
    media_files = []
    media_set = set(video_exts + image_exts)

    def walk(current: str):
        for entry in list_dir(current):
            if is_file(entry):
                ext = os.path.splitext(entry)[1].lower()
                if ext in media_set:
                    media_files.append(entry)
            elif is_dir(entry):
                walk(entry)

    walk(root)
    return {"media_files": media_files, "status": "ok"}


def extract_zip_safe(
    zip_path: str,
    dest_dir: str,
    max_total_size: int,
    max_members: int,
    open_zip: Callable[[str], Any],
    get_zip_info: Callable[[Any], List[Any]],
    extract_member: Callable[[Any, Any, str], None],
    make_dirs: Callable[[str], None],
) -> Dict[str, Any]:
    """
    Safely extract a zip file with validation.
    Returns {"extracted": list[str], "rejected": list[dict], "status": "ok"}
    All members validated before any extraction.
    Members placed in dest_dir/<member path>.
    """
    extracted = []
    rejected = []

    with open_zip(zip_path) as zf:
        members = get_zip_info(zf)

        # Check member count limit
        if len(members) > max_members:
            for info in members:
                rejected.append({"item": info.filename, "error": "Too many members in archive"})
            return {"extracted": [], "rejected": rejected, "status": "ok"}

        # Validate all members first
        total_size = 0
        valid_members = []
        for info in members:
            # Skip directories
            if info.is_dir():
                continue

            # Check symlink (Unix symlink flag in external_attr high bytes)
            # Shift right 16 bits to get Unix mode, then check file type bits
            mode = (info.external_attr >> 16) & 0xFFFF
            if mode & 0o170000 == 0o120000:  # S_IFLNK
                rejected.append({"item": info.filename, "error": "Symlink not allowed"})
                continue

            # Check unsafe path
            unsafe, error = _is_unsafe_path(info.filename)
            if unsafe:
                rejected.append({"item": info.filename, "error": error})
                continue

            # Check extension
            if not _is_media_file(info.filename):
                rejected.append({"item": info.filename, "error": "Not a video or image-sequence file"})
                continue

            # Check if destination file already exists (no-overwrite)
            dest_path = os.path.join(dest_dir, info.filename)
            if os.path.exists(dest_path):
                rejected.append({"item": info.filename, "error": "Destination file exists"})
                continue

            total_size += info.file_size
            valid_members.append(info)

        # Check total size limit
        if total_size > max_total_size:
            rejected.extend(
                {"item": info.filename, "error": "Total size exceeds limit"}
                for info in valid_members
            )
            valid_members = []

        # Extract valid members
        for info in valid_members:
            dest_path = os.path.join(dest_dir, info.filename)
            make_dirs(os.path.dirname(dest_path))
            extract_member(zf, info, dest_path)
            extracted.append(dest_path)

    return {"extracted": extracted, "rejected": rejected, "status": "ok"}


def collect_inputs(
    inputs: List[str],
    dest: str,
    sha256_file: Callable[[str], str],
    copy_file: Callable[[str, str], None],
    make_dirs: Callable[[str], None],
    list_dir: Callable[[str], List[str]],
    is_file: Callable[[str], bool],
    is_dir: Callable[[str], bool],
    get_size: Callable[[str], int],
    extract_zip_safe: Callable[
        [str, str, int, int], Dict[str, Any]
    ],
) -> Dict[str, Any]:
    """
    Collect media inputs from files, directories, and zip archives.
    Returns {"copied": list[str], "duplicates": list[dict], "rejected": list[dict], "status": "ok"}
    """
    copied = []
    duplicates = []
    rejected = []
    seen_hashes = {}  # hash -> dest_path

    make_dirs(dest)

    for input_path in inputs:
        # Check for zip file FIRST (before is_file, since zip files are files)
        if input_path.lower().endswith(".zip"):
            # Zip file
            zip_stem = Path(input_path).stem
            zip_dest = os.path.join(dest, zip_stem)
            make_dirs(zip_dest)

            zip_result = extract_zip_safe(input_path, zip_dest, MAX_TOTAL_SIZE, MAX_MEMBERS)

            for extracted_path in zip_result["extracted"]:
                file_hash = sha256_file(extracted_path)
                if file_hash in seen_hashes:
                    duplicates.append({"file": extracted_path, "duplicate_of": seen_hashes[file_hash]})
                    # Remove the extracted duplicate
                    try:
                        os.remove(extracted_path)
                    except OSError:
                        pass
                    continue
                copied.append(extracted_path)
                seen_hashes[file_hash] = extracted_path

            # Process rejected items - convert "Destination file exists" to duplicates
            for rej in zip_result["rejected"]:
                if rej["error"] == "Destination file exists":
                    # Reconstruct the destination path
                    dest_path = os.path.join(zip_dest, rej["item"])
                    duplicates.append({"file": rej["item"], "duplicate_of": dest_path})
                else:
                    rejected.append(rej)

        elif is_file(input_path):
            # Single file
            if not _is_media_file(input_path):
                rejected.append({"item": input_path, "error": "Not a video or image-sequence file"})
                continue

            file_hash = sha256_file(input_path)
            dest_path = os.path.join(dest, os.path.basename(input_path))

            if os.path.exists(dest_path):
                # Check if it's a duplicate (same hash)
                existing_hash = sha256_file(dest_path)
                if existing_hash == file_hash:
                    duplicates.append({"file": input_path, "duplicate_of": dest_path})
                    continue
                # Different file with same name - skip to avoid overwrite
                duplicates.append({"file": input_path, "duplicate_of": dest_path})
                continue

            if file_hash in seen_hashes:
                duplicates.append({"file": input_path, "duplicate_of": seen_hashes[file_hash]})
                continue

            copy_file(input_path, dest_path)
            copied.append(dest_path)
            seen_hashes[file_hash] = dest_path

        elif is_dir(input_path):
            # Directory - scan all files recursively, accept media, reject others
            all_files = _walk_files(input_path, list_dir, is_file, is_dir)
            for file_path in all_files:
                if _is_media_file(file_path):
                    file_hash = sha256_file(file_path)
                    dest_path = os.path.join(dest, os.path.basename(file_path))

                    if os.path.exists(dest_path):
                        existing_hash = sha256_file(dest_path)
                        if existing_hash == file_hash:
                            duplicates.append({"file": file_path, "duplicate_of": dest_path})
                            continue
                        duplicates.append({"file": file_path, "duplicate_of": dest_path})
                        continue

                    if file_hash in seen_hashes:
                        duplicates.append({"file": file_path, "duplicate_of": seen_hashes[file_hash]})
                        continue

                    copy_file(file_path, dest_path)
                    copied.append(dest_path)
                    seen_hashes[file_hash] = dest_path
                else:
                    rejected.append({"item": file_path, "error": "Not a video or image-sequence file"})

        else:
            rejected.append({"item": input_path, "error": "Not a file, directory, or zip archive"})

    return {
        "copied": copied,
        "duplicates": duplicates,
        "rejected": rejected,
        "status": "ok"
    }
