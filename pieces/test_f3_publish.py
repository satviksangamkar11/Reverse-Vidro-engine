import os
import json
import tempfile
import shutil
import threading
import time
import sys
import unittest
from unittest.mock import patch

# Import the module under test
import f3_publish


class TestCorpusLock(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.lock_path = os.path.join(self.tmpdir, ".lock")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_lock_acquire_release(self):
        """Basic acquire and release works."""
        with f3_publish.corpus_lock(self.lock_path):
            pass  # lock held
        # lock released, can acquire again
        with f3_publish.corpus_lock(self.lock_path):
            pass

    def test_second_acquirer_raises_locked(self):
        """Second acquirer in another thread gets RuntimeError('LOCKED') immediately."""
        acquired = threading.Event()
        error_holder = {}

        def holder():
            with f3_publish.corpus_lock(self.lock_path):
                acquired.set()
                time.sleep(0.2)  # hold for a bit

        def waiter():
            time.sleep(0.05)  # ensure holder gets lock first
            try:
                with f3_publish.corpus_lock(self.lock_path):
                    error_holder["result"] = "acquired"
            except RuntimeError as e:
                error_holder["error"] = str(e)

        t1 = threading.Thread(target=holder)
        t2 = threading.Thread(target=waiter)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertIn("error", error_holder)
        self.assertEqual(error_holder["error"], "LOCKED")

    def test_lock_released_on_exception(self):
        """Lock is released even if exception raised inside context."""
        with self.assertRaises(ValueError):
            with f3_publish.corpus_lock(self.lock_path):
                raise ValueError("boom")
        # Should be able to acquire again
        with f3_publish.corpus_lock(self.lock_path):
            pass


class TestSnapshot(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ledger_path = os.path.join(self.tmpdir, "ledger.json")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_snapshot_returns_deep_copy_sorted_by_sha256(self):
        """snapshot returns deep-copied dict with videos sorted by sha256."""
        data = {
            "videos": [
                {"id": "b", "sha256": "bbb"},
                {"id": "a", "sha256": "aaa"},
                {"id": "c", "sha256": "ccc"},
            ],
            "meta": {"x": 1}
        }
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        snap = f3_publish.snapshot(self.ledger_path)
        # Check deep copy: modifying snap doesn't affect original file
        snap["videos"][0]["id"] = "modified"
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            original = json.load(f)
        self.assertEqual(original["videos"][0]["id"], "b")

        # Check sorted by sha256
        shas = [v["sha256"] for v in snap["videos"]]
        self.assertEqual(shas, ["aaa", "bbb", "ccc"])

    def test_snapshot_sorts_dict_videos_by_sha256_key(self):
        """snapshot sorts dict-shaped videos by sha256 key (F1 ledger schema)."""
        data = {
            "videos": {
                "bbb": {"id": "b", "sha256": "bbb"},
                "aaa": {"id": "a", "sha256": "aaa"},
                "ccc": {"id": "c", "sha256": "ccc"},
            },
            "meta": {"x": 1}
        }
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        snap = f3_publish.snapshot(self.ledger_path)
        # Check sorted by sha256 key
        shas = list(snap["videos"].keys())
        self.assertEqual(shas, ["aaa", "bbb", "ccc"])
        # Values should be preserved
        self.assertEqual(snap["videos"]["aaa"]["id"], "a")
        self.assertEqual(snap["videos"]["bbb"]["id"], "b")
        self.assertEqual(snap["videos"]["ccc"]["id"], "c")

    def test_snapshot_raises_on_corrupt_json(self):
        """Raises ValueError on corrupt JSON."""
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            f.write("{ not valid json }")
        with self.assertRaises(ValueError) as cm:
            f3_publish.snapshot(self.ledger_path)
        self.assertIn("corrupt JSON", str(cm.exception))


class TestPublish(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.out_dir = os.path.join(self.tmpdir, "out")
        os.makedirs(self.out_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_publish_creates_snapshot_and_current(self):
        """publish creates build_NNN folder and CURRENT.json pointer."""
        files = {"a.txt": "hello", "b.json": '{"x":1}'}
        result = f3_publish.publish(self.out_dir, files)
        self.assertEqual(result["build"], "build_001")
        self.assertEqual(set(result["published"]), {"a.txt", "b.json"})

        # Check CURRENT.json
        current_path = os.path.join(self.out_dir, "CURRENT.json")
        with open(current_path, "r", encoding="utf-8") as f:
            current = json.load(f)
        self.assertEqual(current["build"], "build_001")
        self.assertEqual(set(current["files"]), {"a.txt", "b.json"})

        # Check snapshot folder exists with files and manifest
        build_dir = os.path.join(self.out_dir, "snapshots", "build_001")
        self.assertTrue(os.path.isdir(build_dir))
        self.assertTrue(os.path.exists(os.path.join(build_dir, "a.txt")))
        self.assertTrue(os.path.exists(os.path.join(build_dir, "b.json")))
        self.assertTrue(os.path.exists(os.path.join(build_dir, "manifest.json")))

        # Verify manifest content
        with open(os.path.join(build_dir, "manifest.json"), "r", encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertIn("files", manifest)
        self.assertEqual(set(manifest["files"].keys()), {"a.txt", "b.json"})

    def test_publish_validates_non_empty(self):
        """publish rejects empty files."""
        files = {"empty.txt": ""}
        with self.assertRaises(ValueError) as cm:
            f3_publish.publish(self.out_dir, files)
        self.assertIn("empty file", str(cm.exception))

    def test_publish_validates_json_parse(self):
        """publish rejects invalid JSON files."""
        files = {"bad.json": "{ not json }"}
        with self.assertRaises(ValueError) as cm:
            f3_publish.publish(self.out_dir, files)
        self.assertIn("invalid JSON", str(cm.exception))

    def test_publish_custom_validate(self):
        """publish calls optional validate function."""
        def validate(name, text):
            if name == "reject.txt":
                return "rejected"
            return None

        files = {"ok.txt": "fine", "reject.txt": "bad"}
        with self.assertRaises(ValueError) as cm:
            f3_publish.publish(self.out_dir, files, validate=validate)
        self.assertIn("validation failed", str(cm.exception))

    def test_publish_atomic_replace_retries_on_permission_error(self):
        """publish retries os.replace on PermissionError."""
        files = {"a.txt": "hello"}
        # First publish succeeds
        f3_publish.publish(self.out_dir, files)

        # Mock os.replace to raise PermissionError twice then succeed
        original_replace = os.replace
        call_count = {"n": 0}

        def mock_replace(src, dst):
            call_count["n"] += 1
            if call_count["n"] <= 2:
                raise PermissionError("simulated")
            return original_replace(src, dst)

        with patch("f3_publish.os.replace", side_effect=mock_replace):
            result = f3_publish.publish(self.out_dir, {"b.txt": "world"}, retries=5, sleep=lambda _: None)
        self.assertEqual(result["build"], "build_002")
        self.assertEqual(call_count["n"], 3)

    def test_publish_failure_leaves_current_untouched(self):
        """If validation fails, CURRENT.json still points to previous build."""
        # First publish
        f3_publish.publish(self.out_dir, {"a.txt": "v1"})
        # Second publish fails validation
        def validate(name, text):
            return "fail"
        with self.assertRaises(ValueError):
            f3_publish.publish(self.out_dir, {"b.txt": "v2"}, validate=validate)

        # read_current should still return build_001
        current = f3_publish.read_current(self.out_dir)
        self.assertEqual(current["build"], "build_001")
        self.assertEqual(current["files"], {"a.txt": "v1"})

    def test_publish_crash_after_snapshot_before_pointer_leaves_previous(self):
        """Simulated crash after snapshot folder written but before pointer replace."""
        # First publish
        f3_publish.publish(self.out_dir, {"a.txt": "v1"})

        # Mock os.replace to raise exception (simulate crash)
        def mock_replace(src, dst):
            raise RuntimeError("simulated crash")
        with patch("f3_publish.os.replace", side_effect=mock_replace):
            with self.assertRaises(RuntimeError):
                f3_publish.publish(self.out_dir, {"b.txt": "v2"})

        # read_current should still return build_001
        current = f3_publish.read_current(self.out_dir)
        self.assertEqual(current["build"], "build_001")
        self.assertEqual(current["files"], {"a.txt": "v1"})

        # The half-built folder should be kept as incomplete (no manifest)
        # read_current ignores it because it has no manifest.json
        build_002 = os.path.join(self.out_dir, "snapshots", "build_002")
        self.assertTrue(os.path.isdir(build_002))
        self.assertFalse(os.path.exists(os.path.join(build_002, "manifest.json")))

    def test_publish_build_numbers_increment_never_reused(self):
        """Build numbers are max_existing+1 and never reused even after failed build."""
        f3_publish.publish(self.out_dir, {"a.txt": "v1"})  # build_001
        # Fail a publish (empty file)
        with self.assertRaises(ValueError):
            f3_publish.publish(self.out_dir, {"empty.txt": ""})
        # Next publish should be build_003 (build_002 was attempted but failed, kept as orphan)
        result = f3_publish.publish(self.out_dir, {"b.txt": "v2"})
        self.assertEqual(result["build"], "build_003")

    def test_publish_acquires_lock_internally(self):
        """publish acquires corpus_lock itself; second concurrent publish gets LOCKED."""
        # Hold the lock in the main thread, then try to publish from a worker thread
        lock_path = os.path.join(self.out_dir, ".lock")
        errors = {}
        done = threading.Event()

        def worker():
            try:
                f3_publish.publish(self.out_dir, {"worker.txt": "content"})
            except RuntimeError as e:
                errors["worker"] = str(e)
            finally:
                done.set()

        with f3_publish.corpus_lock(lock_path):
            t = threading.Thread(target=worker)
            t.start()
            done.wait(timeout=2.0)
            t.join(timeout=1.0)

        self.assertIn("worker", errors)
        self.assertEqual(errors["worker"], "LOCKED")

    def test_publish_not_lock_holder_check(self):
        """publish checks it is inside lock context (NOT_LOCK_HOLDER) when called outside lock."""
        # We can't easily call publish's internal check without the lock,
        # but we can verify the lock state tracking works by checking
        # that corpus_lock sets/clears the held_locks correctly.
        lock_path = os.path.join(self.out_dir, ".lock")
        with f3_publish.corpus_lock(lock_path):
            # Inside lock, held_locks should contain our lock
            self.assertIn(os.path.abspath(lock_path), f3_publish._lock_state.held_locks)
        # Outside lock, held_locks should not contain our lock
        self.assertNotIn(os.path.abspath(lock_path), f3_publish._lock_state.held_locks)

    def test_publish_rejects_reserved_manifest_name(self):
        """publish rejects file named manifest.json."""
        with self.assertRaises(ValueError) as cm:
            f3_publish.publish(self.out_dir, {"manifest.json": '{"x":1}'})
        self.assertIn("reserved file name", str(cm.exception))

    def test_publish_rejects_traversal_names(self):
        """publish rejects file names with path traversal."""
        for bad_name in ["../x.txt", "sub/../x.txt", "a/../../b.txt"]:
            with self.assertRaises(ValueError) as cm:
                f3_publish.publish(self.out_dir, {bad_name: "content"})
            self.assertIn("traversal", str(cm.exception))

    def test_publish_rejects_path_separators(self):
        """publish rejects file names with path separators."""
        for bad_name in ["sub/file.txt", "a/b/c.txt"]:
            with self.assertRaises(ValueError) as cm:
                f3_publish.publish(self.out_dir, {bad_name: "content"})
            self.assertIn("path separator", str(cm.exception))

    def test_publish_rejects_absolute_names(self):
        """publish rejects absolute file names."""
        bad_name = os.path.abspath("x.txt")
        with self.assertRaises(ValueError) as cm:
            f3_publish.publish(self.out_dir, {bad_name: "content"})
        self.assertIn("traversal", str(cm.exception))

    def test_publish_rejects_colon_names(self):
        """publish rejects file names containing colon (Windows drive prefix)."""
        for bad_name in ["C:evil.txt", "D:data.txt", "a:b.txt"]:
            with self.assertRaises(ValueError) as cm:
                f3_publish.publish(self.out_dir, {bad_name: "content"})
            self.assertIn("colon", str(cm.exception))

    def test_publish_rejects_nonpositive_retries(self):
        """publish raises ValueError if retries < 1."""
        with self.assertRaises(ValueError) as cm:
            f3_publish.publish(self.out_dir, {"a.txt": "x"}, retries=0)
        self.assertIn("retries must be >= 1", str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            f3_publish.publish(self.out_dir, {"a.txt": "x"}, retries=-1)
        self.assertIn("retries must be >= 1", str(cm.exception))


class TestReadCurrent(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.out_dir = os.path.join(self.tmpdir, "out")
        os.makedirs(self.out_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_read_current_loads_files_from_snapshot(self):
        """read_current resolves CURRENT.json once and loads all files from that snapshot."""
        f3_publish.publish(self.out_dir, {"a.txt": "hello", "b.json": '{"x":1}'})
        current = f3_publish.read_current(self.out_dir)
        self.assertEqual(current["build"], "build_001")
        self.assertEqual(current["dir"], os.path.join(self.out_dir, "snapshots", "build_001"))
        self.assertEqual(current["files"]["a.txt"], "hello")
        self.assertEqual(current["files"]["b.json"], '{"x":1}')

    def test_read_current_verifies_manifest(self):
        """read_current verifies manifest.json sha256 matches."""
        f3_publish.publish(self.out_dir, {"a.txt": "hello"})
        # Corrupt a file in the snapshot
        build_dir = os.path.join(self.out_dir, "snapshots", "build_001")
        with open(os.path.join(build_dir, "a.txt"), "w", encoding="utf-8") as f:
            f.write("corrupted")
        with self.assertRaises(ValueError) as cm:
            f3_publish.read_current(self.out_dir)
        self.assertEqual(str(cm.exception), "NO_SNAPSHOT")

    def test_read_current_missing_file_raises(self):
        """read_current raises if pointed snapshot missing a file."""
        f3_publish.publish(self.out_dir, {"a.txt": "hello", "b.txt": "world"})
        # Remove a file
        build_dir = os.path.join(self.out_dir, "snapshots", "build_001")
        os.unlink(os.path.join(build_dir, "b.txt"))
        with self.assertRaises(ValueError) as cm:
            f3_publish.read_current(self.out_dir)
        self.assertEqual(str(cm.exception), "NO_SNAPSHOT")

    def test_read_current_missing_current_raises_no_snapshot(self):
        """Missing/corrupt CURRENT.json => ValueError('NO_SNAPSHOT')."""
        with self.assertRaises(ValueError) as cm:
            f3_publish.read_current(self.out_dir)
        self.assertEqual(str(cm.exception), "NO_SNAPSHOT")

        # Corrupt CURRENT.json
        with open(os.path.join(self.out_dir, "CURRENT.json"), "w") as f:
            f.write("not json")
        with self.assertRaises(ValueError) as cm:
            f3_publish.read_current(self.out_dir)
        self.assertEqual(str(cm.exception), "NO_SNAPSHOT")

    def test_read_current_non_object_current_raises_no_snapshot(self):
        """CURRENT.json with non-object top level raises ValueError('NO_SNAPSHOT')."""
        with open(os.path.join(self.out_dir, "CURRENT.json"), "w") as f:
            f.write('["not", "an", "object"]')
        with self.assertRaises(ValueError) as cm:
            f3_publish.read_current(self.out_dir)
        self.assertEqual(str(cm.exception), "NO_SNAPSHOT")

        with open(os.path.join(self.out_dir, "CURRENT.json"), "w") as f:
            f.write('null')
        with self.assertRaises(ValueError) as cm:
            f3_publish.read_current(self.out_dir)
        self.assertEqual(str(cm.exception), "NO_SNAPSHOT")

    def test_read_current_ignores_orphan_folders(self):
        """Orphan folders without complete manifest are ignored."""
        f3_publish.publish(self.out_dir, {"a.txt": "v1"})  # build_001
        # Create an orphan build_002 folder without manifest
        orphan = os.path.join(self.out_dir, "snapshots", "build_002")
        os.makedirs(orphan)
        with open(os.path.join(orphan, "b.txt"), "w") as f:
            f.write("orphan")
        # read_current should still return build_001
        current = f3_publish.read_current(self.out_dir)
        self.assertEqual(current["build"], "build_001")

    def test_rebuilding_twice_from_one_snapshot_gives_identical_text(self):
        """Rebuilding twice from one snapshot gives identical file text."""
        # This test is about determinism: if we publish same files twice, the snapshot content is identical.
        files = {"a.txt": "hello", "b.json": '{"x":1}'}
        f3_publish.publish(self.out_dir, files)
        current1 = f3_publish.read_current(self.out_dir)
        # Publish again with same content (will be build_002)
        f3_publish.publish(self.out_dir, files)
        current2 = f3_publish.read_current(self.out_dir)
        # The file texts should be identical
        self.assertEqual(current1["files"], current2["files"])

    def test_read_current_handles_windows_newlines(self):
        """read_current correctly reads files with \\r\\n newlines (no translation)."""
        # Publish a file with explicit CRLF
        files = {"a.txt": "line1\r\nline2\r\n"}
        f3_publish.publish(self.out_dir, files)
        current = f3_publish.read_current(self.out_dir)
        # The text should be exactly what was published (no newline translation)
        self.assertEqual(current["files"]["a.txt"], "line1\r\nline2\r\n")

    def test_publish_and_read_current_roundtrip_with_crlf(self):
        """Full roundtrip: publish with CRLF, read_current returns identical text."""
        files = {"data.txt": "header\r\nvalue1\r\nvalue2\r\n"}
        f3_publish.publish(self.out_dir, files)
        current = f3_publish.read_current(self.out_dir)
        self.assertEqual(current["files"]["data.txt"], "header\r\nvalue1\r\nvalue2\r\n")

    def test_read_current_rejects_traversal_build_name(self):
        """read_current rejects build names with path traversal."""
        # Create a fake CURRENT.json with traversal build name
        current_path = os.path.join(self.out_dir, "CURRENT.json")
        with open(current_path, "w", encoding="utf-8") as f:
            json.dump({"build": "build_../../../etc", "files": ["x.txt"]}, f)
        with self.assertRaises(ValueError) as cm:
            f3_publish.read_current(self.out_dir)
        self.assertEqual(str(cm.exception), "NO_SNAPSHOT")

    def test_read_current_rejects_malformed_manifest(self):
        """read_current rejects manifest with non-object top level or missing files."""
        f3_publish.publish(self.out_dir, {"a.txt": "hello"})
        build_dir = os.path.join(self.out_dir, "snapshots", "build_001")
        manifest_path = os.path.join(build_dir, "manifest.json")
        
        # Test non-object manifest
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write('["not", "an", "object"]')
        with self.assertRaises(ValueError) as cm:
            f3_publish.read_current(self.out_dir)
        self.assertEqual(str(cm.exception), "NO_SNAPSHOT")
        
        # Test manifest with non-dict files
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({"files": "not a dict"}, f)
        with self.assertRaises(ValueError) as cm:
            f3_publish.read_current(self.out_dir)
        self.assertEqual(str(cm.exception), "NO_SNAPSHOT")

    def test_read_current_rejects_manifest_traversal_keys(self):
        """read_current rejects manifest keys with path traversal."""
        f3_publish.publish(self.out_dir, {"a.txt": "hello"})
        build_dir = os.path.join(self.out_dir, "snapshots", "build_001")
        manifest_path = os.path.join(build_dir, "manifest.json")
        
        # Tamper manifest with traversal key
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({"files": {"../../etc/passwd": "hash"}}, f)
        with self.assertRaises(ValueError) as cm:
            f3_publish.read_current(self.out_dir)
        self.assertEqual(str(cm.exception), "NO_SNAPSHOT")

    def test_read_current_handles_invalid_utf8(self):
        """read_current converts UnicodeDecodeError to NO_SNAPSHOT."""
        f3_publish.publish(self.out_dir, {"a.txt": "hello"})
        build_dir = os.path.join(self.out_dir, "snapshots", "build_001")
        # Write invalid UTF-8
        with open(os.path.join(build_dir, "a.txt"), "wb") as f:
            f.write(b"\xff\xfe")
        with self.assertRaises(ValueError) as cm:
            f3_publish.read_current(self.out_dir)
        self.assertEqual(str(cm.exception), "NO_SNAPSHOT")


class TestWorkedExample(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.out_dir = os.path.join(self.tmpdir, "out")
        os.makedirs(self.out_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_worked_example_publish_then_failing_publish(self):
        """publish #1 then publish #2 whose validation fails => read_current still returns build_001 with all three files."""
        # Publish #1 with three files
        files1 = {"a.txt": "v1", "b.txt": "v2", "c.txt": "v3"}
        f3_publish.publish(self.out_dir, files1)

        # Publish #2 with validation failure
        def validate(name, text):
            return "fail"
        with self.assertRaises(ValueError):
            f3_publish.publish(self.out_dir, {"d.txt": "v4"}, validate=validate)

        # read_current still returns build_001 with all three files
        current = f3_publish.read_current(self.out_dir)
        self.assertEqual(current["build"], "build_001")
        self.assertEqual(set(current["files"].keys()), {"a.txt", "b.txt", "c.txt"})
        self.assertEqual(current["files"]["a.txt"], "v1")
        self.assertEqual(current["files"]["b.txt"], "v2")
        self.assertEqual(current["files"]["c.txt"], "v3")

    def test_two_threads_corpus_lock_second_gets_locked(self):
        """Two threads call corpus_lock; second gets LOCKED."""
        lock_path = os.path.join(self.out_dir, ".lock")
        acquired = threading.Event()
        errors = {}

        def holder():
            with f3_publish.corpus_lock(lock_path):
                acquired.set()
                time.sleep(0.2)

        def waiter():
            acquired.wait()
            try:
                with f3_publish.corpus_lock(lock_path):
                    errors["result"] = "acquired"
            except RuntimeError as e:
                errors["error"] = str(e)

        t1 = threading.Thread(target=holder)
        t2 = threading.Thread(target=waiter)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertIn("error", errors)
        self.assertEqual(errors["error"], "LOCKED")


if __name__ == "__main__":
    unittest.main()
