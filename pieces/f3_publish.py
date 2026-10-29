import os
import json
import hashlib
import time
import sys
import contextlib
import threading
import errno
from typing import Dict, List, Optional, Callable, Any

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

# Global state to track lock ownership for NOT_LOCK_HOLDER check
_lock_state = threading.local()


@contextlib.contextmanager
def corpus_lock(lock_path: str):
    """
    OS-backed exclusive non-blocking lock.
    Raises RuntimeError("LOCKED") if lock cannot be acquired.
    Lock is released on exit (even after exception) and when process exits.
    """
    f = None
    try:
        dir_name = os.path.dirname(lock_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        # Open in binary mode for locking APIs
        f = open(lock_path, "wb")
        try:
            if sys.platform == "win32":
                try:
                    # Lock first byte, non-blocking
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError:
                    raise RuntimeError("LOCKED")
            else:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    raise RuntimeError("LOCKED")
        except RuntimeError:
            # Lock acquisition failed, close file and re-raise
            f.close()
            f = None
            raise
        # Mark that we hold the lock for this specific path
        if not hasattr(_lock_state, 'held_locks'):
            _lock_state.held_locks = set()
        _lock_state.held_locks.add(os.path.abspath(lock_path))
        try:
            yield
        finally:
            _lock_state.held_locks.discard(os.path.abspath(lock_path))
    finally:
        # Only unlock/close if file wasn't already closed due to lock acquisition failure
        if f is not None and not f.closed:
            try:
                if sys.platform == "win32":
                    try:
                        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
                else:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except OSError:
                        pass
            finally:
                f.close()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate_name(name: str) -> None:
    """Validate a file name: no reserved names, no path separators, no traversal, no colons."""
    if name == "manifest.json":
        raise ValueError(f"reserved file name: {name}")
    if os.path.isabs(name):
        raise ValueError(f"invalid file name (traversal): {name}")
    if ".." in name.split(os.sep) or (os.altsep and ".." in name.split(os.altsep)):
        raise ValueError(f"invalid file name (traversal): {name}")
    if os.sep in name or (os.altsep and os.altsep in name):
        raise ValueError(f"invalid file name (path separator): {name}")
    if ":" in name:
        raise ValueError(f"invalid file name (colon): {name}")


def snapshot(ledger_path: str) -> Dict[str, Any]:
    """
    Read ledger once, return deep-copied dict with videos sorted by sha256.
    Raises ValueError on corrupt JSON.
    """
    with open(ledger_path, "r", encoding="utf-8", newline="") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError("corrupt JSON") from e
    # Deep copy via JSON round-trip
    data = json.loads(json.dumps(data))
    # Sort videos by sha256 if present (handles both list and dict shapes)
    if "videos" in data:
        vids = data["videos"]
        if isinstance(vids, list):
            data["videos"] = sorted(vids, key=lambda v: v.get("sha256", ""))
        elif isinstance(vids, dict):
            # F1 ledger schema: {"videos": {sha256: {...}}}
            # Sort by key (sha256) and rebuild dict preserving order (Python 3.7+)
            data["videos"] = dict(sorted(vids.items(), key=lambda kv: kv[0]))
    return data


def publish(
    out_dir: str,
    files: Dict[str, str],
    validate: Optional[Callable[[str, str], Optional[str]]] = None,
    retries: int = 5,
    sleep: Callable[[float], None] = time.sleep,
) -> Dict[str, Any]:
    """
    Build immutable snapshot folder out_dir/snapshots/build_NNN/,
    validate all files, then atomically replace out_dir/CURRENT.json.
    Acquires corpus_lock(out_dir/.lock) internally.
    Returns {"build": "...", "published": [...]}.
    """
    if retries < 1:
        raise ValueError("retries must be >= 1")

    # Validate all file names upfront
    for name in files.keys():
        _validate_name(name)

    lock_path = os.path.join(out_dir, ".lock")
    snapshots_dir = os.path.join(out_dir, "snapshots")
    os.makedirs(snapshots_dir, exist_ok=True)

    with corpus_lock(lock_path):
        # Verify we are the lock holder for this specific lock path
        held = getattr(_lock_state, 'held_locks', set())
        if os.path.abspath(lock_path) not in held:
            raise RuntimeError("NOT_LOCK_HOLDER")

        # Determine next build number: max existing + 1 (inside lock to avoid races)
        # Count ALL build_XXX folders (including incomplete orphans) so numbers are never reused
        existing = []
        for name in os.listdir(snapshots_dir):
            if name.startswith("build_") and name[6:].isdigit():
                existing.append(int(name[6:]))
        next_num = (max(existing) + 1) if existing else 1
        build_name = f"build_{next_num:03d}"
        build_dir = os.path.join(snapshots_dir, build_name)

        # Write all files to build_dir
        os.makedirs(build_dir, exist_ok=True)
        file_names = list(files.keys())
        tmp_path = None
        try:
            # Validate and write each file
            for name, text in files.items():
                if not text:
                    raise ValueError(f"empty file: {name}")
                if name.endswith(".json"):
                    try:
                        json.loads(text)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"invalid JSON in {name}: {e}") from e
                if validate is not None:
                    err = validate(name, text)
                    if err:
                        raise ValueError(f"validation failed for {name}: {err}")
                file_path = os.path.join(build_dir, name)
                with open(file_path, "w", encoding="utf-8", newline="") as f:
                    f.write(text)

            # Write manifest.json with sha256 of each file
            manifest = {"files": {name: _sha256(text) for name, text in files.items()}}
            manifest_path = os.path.join(build_dir, "manifest.json")
            with open(manifest_path, "w", encoding="utf-8", newline="") as f:
                json.dump(manifest, f, separators=(",", ":"))

            # Prepare CURRENT.json content
            current_data = {
                "build": build_name,
                "files": file_names,
                "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            current_path = os.path.join(out_dir, "CURRENT.json")
            tmp_path = current_path + ".tmp"

            # Write tmp and replace with retries on PermissionError/sharing violations
            last_err = None
            for attempt in range(retries):
                try:
                    with open(tmp_path, "w", encoding="utf-8", newline="") as f:
                        json.dump(current_data, f, separators=(",", ":"))
                    os.replace(tmp_path, current_path)
                    tmp_path = None  # successfully replaced
                    break
                except OSError as e:
                    last_err = e
                    # Retry on permission errors and sharing violations
                    is_sharing = False
                    if isinstance(e, PermissionError):
                        is_sharing = True
                    elif sys.platform == "win32" and getattr(e, 'winerror', None) == 32:  # ERROR_SHARING_VIOLATION
                        is_sharing = True
                    elif e.errno in (errno.EACCES, errno.EAGAIN, errno.ETXTBSY):
                        is_sharing = True
                    
                    if is_sharing and attempt < retries - 1:
                        sleep(0.01 * (attempt + 1))
                        continue
                    # Clean up tmp file on any OSError before re-raising
                    try:
                        if tmp_path and os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                    except OSError:
                        pass
                    tmp_path = None
                    raise
            else:
                # Should not reach here
                if last_err:
                    raise last_err

        except Exception:
            # On failure, keep the build folder but WITHOUT manifest.json (incomplete orphan)
            # read_current ignores folders without manifest.json
            try:
                manifest_path = os.path.join(build_dir, "manifest.json")
                if os.path.exists(manifest_path):
                    os.unlink(manifest_path)
            except Exception:
                pass
            # Clean up tmp file if still exists
            try:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except OSError:
                pass
            raise

    return {"build": build_name, "published": file_names}


def read_current(out_dir: str) -> Dict[str, Any]:
    """
    Resolve CURRENT.json once, load all files from that snapshot folder.
    Verifies manifest.json. Returns {"build", "dir", "files": {name: text}}.
    Raises ValueError if pointed snapshot missing a file or manifest mismatch.
    """
    current_path = os.path.join(out_dir, "CURRENT.json")
    if not os.path.exists(current_path):
        raise ValueError("NO_SNAPSHOT")
    try:
        with open(current_path, "r", encoding="utf-8", newline="") as f:
            current = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError("NO_SNAPSHOT") from e

    # Validate CURRENT.json is a dict with required fields
    if not isinstance(current, dict):
        raise ValueError("NO_SNAPSHOT")

    build_name = current.get("build")
    if not isinstance(build_name, str):
        raise ValueError("NO_SNAPSHOT")
    
    # Validate build name format to prevent path traversal
    if not (build_name.startswith("build_") and build_name[6:].isdigit()):
        raise ValueError("NO_SNAPSHOT")
    
    build_dir = os.path.join(out_dir, "snapshots", build_name)
    if not os.path.isdir(build_dir):
        raise ValueError("NO_SNAPSHOT")

    # Load manifest
    manifest_path = os.path.join(build_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        raise ValueError("NO_SNAPSHOT")
    try:
        with open(manifest_path, "r", encoding="utf-8", newline="") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError("NO_SNAPSHOT") from e

    # Validate manifest structure
    if not isinstance(manifest, dict):
        raise ValueError("NO_SNAPSHOT")
    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, dict):
        raise ValueError("NO_SNAPSHOT")

    expected_names = set()
    for k in manifest_files.keys():
        if not isinstance(k, str):
            raise ValueError("NO_SNAPSHOT")
        try:
            _validate_name(k)
        except ValueError:
            raise ValueError("NO_SNAPSHOT")
        expected_names.add(k)

    current_files = current.get("files")
    if not isinstance(current_files, list):
        raise ValueError("NO_SNAPSHOT")
    current_names = set()
    for k in current_files:
        if not isinstance(k, str):
            raise ValueError("NO_SNAPSHOT")
        current_names.add(k)

    if expected_names != current_names:
        raise ValueError("NO_SNAPSHOT")

    # Load each file and verify sha256
    files_dict = {}
    for name in expected_names:
        file_path = os.path.join(build_dir, name)
        if not os.path.exists(file_path):
            raise ValueError("NO_SNAPSHOT")
        try:
            with open(file_path, "r", encoding="utf-8", newline="") as f:
                text = f.read()
        except UnicodeDecodeError as e:
            raise ValueError("NO_SNAPSHOT") from e
        if _sha256(text) != manifest_files[name]:
            raise ValueError("NO_SNAPSHOT")
        files_dict[name] = text

    return {"build": build_name, "dir": build_dir, "files": files_dict}
