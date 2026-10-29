"""
Unit tests for f1_corpus.py (WP-F1).
All tests use temporary directories, no network, no absolute paths.
"""

import hashlib
import json
import os
import tempfile
import shutil
from pathlib import Path
import unittest

from f1_corpus import (
    corpus_add,
    corpus_status,
    stale_entries,
    compute_video_sha256,
    compute_image_sequence_sha256,
    normalize_url,
    LedgerError,
)


class TestComputeHashes(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_compute_video_sha256(self):
        video_path = self.tmpdir / "test.mp4"
        video_path.write_bytes(b"video content bytes")
        expected = hashlib.sha256(b"video content bytes").hexdigest()
        self.assertEqual(compute_video_sha256(video_path), expected)

    def test_compute_image_sequence_sha256_order_matters(self):
        # Create frames A, B, C with different content
        frame_dir = self.tmpdir / "frames"
        frame_dir.mkdir()
        (frame_dir / "frame_1.png").write_bytes(b"AAA")
        (frame_dir / "frame_2.png").write_bytes(b"BBB")
        (frame_dir / "frame_3.png").write_bytes(b"CCC")
        hash_abc = compute_image_sequence_sha256(frame_dir)

        # Reverse order: C, B, A (different filenames but same content order reversed)
        frame_dir2 = self.tmpdir / "frames_rev"
        frame_dir2.mkdir()
        (frame_dir2 / "frame_1.png").write_bytes(b"CCC")
        (frame_dir2 / "frame_2.png").write_bytes(b"BBB")
        (frame_dir2 / "frame_3.png").write_bytes(b"AAA")
        hash_cba = compute_image_sequence_sha256(frame_dir2)

        self.assertNotEqual(hash_abc, hash_cba, "Order must affect identity")

    def test_compute_image_sequence_sha256_same_content_different_filenames(self):
        # Same ordered content, different filenames
        frame_dir1 = self.tmpdir / "frames1"
        frame_dir1.mkdir()
        (frame_dir1 / "frame_001.png").write_bytes(b"AAA")
        (frame_dir1 / "frame_002.png").write_bytes(b"BBB")

        frame_dir2 = self.tmpdir / "frames2"
        frame_dir2.mkdir()
        (frame_dir2 / "img_a.png").write_bytes(b"AAA")
        (frame_dir2 / "img_b.png").write_bytes(b"BBB")

        hash1 = compute_image_sequence_sha256(frame_dir1)
        hash2 = compute_image_sequence_sha256(frame_dir2)
        self.assertEqual(hash1, hash2, "Identical ordered content must yield same identity")

    def test_compute_image_sequence_natural_sort(self):
        # Ensure natural sort: frame_2 before frame_10
        frame_dir = self.tmpdir / "frames_natural"
        frame_dir.mkdir()
        (frame_dir / "frame_1.png").write_bytes(b"1")
        (frame_dir / "frame_2.png").write_bytes(b"2")
        (frame_dir / "frame_10.png").write_bytes(b"10")
        (frame_dir / "frame_3.png").write_bytes(b"3")

        # Expected order: 1, 2, 3, 10
        h = compute_image_sequence_sha256(frame_dir)
        # Compute expected manually
        expected_manifest = "0:" + hashlib.sha256(b"1").hexdigest() + "\n"
        expected_manifest += "1:" + hashlib.sha256(b"2").hexdigest() + "\n"
        expected_manifest += "2:" + hashlib.sha256(b"3").hexdigest() + "\n"
        expected_manifest += "3:" + hashlib.sha256(b"10").hexdigest() + "\n"
        expected = hashlib.sha256(expected_manifest.encode()).hexdigest()
        self.assertEqual(h, expected)

    def test_compute_image_sequence_tiebreaker_deterministic(self):
        # Files with same natural sort key (e.g., frame_01 and frame_1) should be ordered by filename
        frame_dir = self.tmpdir / "frames_tie"
        frame_dir.mkdir()
        (frame_dir / "frame_01.png").write_bytes(b"A")
        (frame_dir / "frame_1.png").write_bytes(b"B")
        # Both have natural key ['frame_', 1, '.png'] -> tie, should sort by filename
        # frame_01.png < frame_1.png lexicographically
        h = compute_image_sequence_sha256(frame_dir)
        # Expected: frame_01.png first (A), then frame_1.png (B)
        expected_manifest = "0:" + hashlib.sha256(b"A").hexdigest() + "\n"
        expected_manifest += "1:" + hashlib.sha256(b"B").hexdigest() + "\n"
        expected = hashlib.sha256(expected_manifest.encode()).hexdigest()
        self.assertEqual(h, expected)

    def test_compute_image_sequence_empty_dir_raises(self):
        # Empty frame directory should raise ValueError
        frame_dir = self.tmpdir / "empty_frames"
        frame_dir.mkdir()
        with self.assertRaises(ValueError) as cm:
            compute_image_sequence_sha256(frame_dir)
        self.assertIn("No image frames found", str(cm.exception))


class TestNormalizeUrl(unittest.TestCase):
    def test_normalize_url_basic(self):
        self.assertEqual(
            normalize_url("https://Example.COM/path?query=1"),
            "https://example.com/path"
        )
        self.assertEqual(
            normalize_url("https://example.com/path/"),
            "https://example.com/path"
        )
        self.assertEqual(
            normalize_url("https://example.com/path"),
            "https://example.com/path"
        )
        self.assertIsNone(normalize_url(None))

    def test_normalize_url_dedupe(self):
        # Same URL after normalization should be treated as same source
        url1 = "https://Example.COM/video?id=123"
        url2 = "https://example.com/video"
        self.assertEqual(normalize_url(url1), normalize_url(url2))

    def test_normalize_url_scheme_preserved(self):
        # Scheme should not be lowercased (spec says lowercase host only)
        self.assertEqual(
            normalize_url("HTTPS://example.com/path"),
            "HTTPS://example.com/path"
        )

    def test_normalize_url_root_trailing_slash_stripped(self):
        # Root URL with trailing slash should dedupe with root without slash
        self.assertEqual(
            normalize_url("https://example.com/"),
            "https://example.com"
        )
        self.assertEqual(
            normalize_url("https://example.com"),
            "https://example.com"
        )


class TestCorpusAdd(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.ledger_path = self.tmpdir / "ledger.json"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_entry(self, sha256, url, versions=None, tags=None, analysis_path=None, analyzed_at=None):
        if versions is None:
            versions = {"analysis": "1", "prompt": "1", "model": "m1"}
        if tags is None:
            tags = {}
        if analysis_path is None:
            analysis_path = f"/analysis/{sha256}.json"
        if analyzed_at is None:
            analyzed_at = "2024-01-01T00:00:00Z"
        return {
            "sha256": sha256,
            "kind": "video",
            "analysis_path": analysis_path,
            "analyzed_at": analyzed_at,
            "versions": versions,
            "sources": [{"source": "local", "origin": "local", "url": url, "creator_id": None}],
            "tags": tags,
        }

    def test_add_first_entry(self):
        entry = self._make_entry("aa", "https://example.com/u1")
        result = corpus_add(self.ledger_path, entry)
        self.assertEqual(result["status"], "ADDED")
        self.assertEqual(result["video_key"], "aa")
        self.assertEqual(result["sources_added"], 1)

        # Verify ledger content
        with open(self.ledger_path) as f:
            ledger = json.load(f)
        self.assertEqual(ledger["schema"], 1)
        self.assertIn("aa", ledger["videos"])
        self.assertEqual(len(ledger["videos"]["aa"]["sources"]), 1)

    def test_add_second_different_video(self):
        corpus_add(self.ledger_path, self._make_entry("aa", "https://example.com/u1"))
        result = corpus_add(self.ledger_path, self._make_entry("bb", "https://example.com/u2"))
        self.assertEqual(result["status"], "ADDED")
        self.assertEqual(result["video_key"], "bb")

    def test_add_duplicate_sha256_different_url_appends_source(self):
        corpus_add(self.ledger_path, self._make_entry("aa", "https://example.com/u1"))
        result = corpus_add(self.ledger_path, self._make_entry("aa", "https://example.com/u3"))
        self.assertEqual(result["status"], "DUPLICATE")
        self.assertEqual(result["video_key"], "aa")
        self.assertEqual(result["sources_added"], 1)

        with open(self.ledger_path) as f:
            ledger = json.load(f)
        sources = ledger["videos"]["aa"]["sources"]
        self.assertEqual(len(sources), 2)
        urls = {normalize_url(s["url"]) for s in sources}
        self.assertIn("https://example.com/u1", urls)
        self.assertIn("https://example.com/u3", urls)

    def test_add_same_sha256_same_versions_same_sources_is_updated_noop(self):
        entry = self._make_entry("aa", "https://example.com/u1")
        corpus_add(self.ledger_path, entry)
        result = corpus_add(self.ledger_path, entry)
        self.assertEqual(result["status"], "UPDATED")
        self.assertEqual(result["sources_added"], 0)

    def test_add_same_sha256_different_versions_updates_and_history(self):
        v1 = {"analysis": "1", "prompt": "1", "model": "m1"}
        v2 = {"analysis": "2", "prompt": "1", "model": "m1"}
        corpus_add(self.ledger_path, self._make_entry("aa", "https://example.com/u1", versions=v1))
        result = corpus_add(self.ledger_path, self._make_entry("aa", "https://example.com/u1", versions=v2))
        self.assertEqual(result["status"], "UPDATED")
        self.assertEqual(result["sources_added"], 0)

        with open(self.ledger_path) as f:
            ledger = json.load(f)
        video = ledger["videos"]["aa"]
        self.assertEqual(video["versions"]["analysis"], "2")
        self.assertEqual(len(video["history"]), 1)
        self.assertEqual(video["history"][0]["versions"]["analysis"], "1")

    def test_add_same_sha256_different_versions_and_new_source(self):
        v1 = {"analysis": "1", "prompt": "1", "model": "m1"}
        v2 = {"analysis": "2", "prompt": "1", "model": "m1"}
        corpus_add(self.ledger_path, self._make_entry("aa", "https://example.com/u1", versions=v1))
        entry2 = self._make_entry("aa", "https://example.com/u2", versions=v2)
        result = corpus_add(self.ledger_path, entry2)
        self.assertEqual(result["status"], "UPDATED")
        self.assertEqual(result["sources_added"], 1)

        with open(self.ledger_path) as f:
            ledger = json.load(f)
        video = ledger["videos"]["aa"]
        self.assertEqual(len(video["sources"]), 2)
        self.assertEqual(len(video["history"]), 1)

    def test_atomic_write_no_leftover_tmp(self):
        # Write should be atomic: no leftover .tmp files after successful write
        entry = self._make_entry("aa", "https://example.com/u1")
        corpus_add(self.ledger_path, entry)
        # Verify file exists and is valid JSON
        with open(self.ledger_path) as f:
            json.load(f)
        # Check no .tmp files left in directory
        tmp_files = list(self.tmpdir.glob("*.tmp"))
        self.assertEqual(len(tmp_files), 0, "No temporary files should remain after atomic write")

    def test_atomic_write_cleans_up_on_error(self):
        # Simulate json.dump failure by passing non-serializable data directly to _save_ledger
        from f1_corpus import _save_ledger
        bad_data = {"schema": 1, "videos": {"aa": {"bad": object()}}}
        with self.assertRaises(TypeError):
            _save_ledger(self.ledger_path, bad_data)
        # Verify no .tmp files left
        tmp_files = list(self.tmpdir.glob("*.tmp"))
        self.assertEqual(len(tmp_files), 0, "Temporary file should be cleaned up on dump failure")

    def test_corrupt_ledger_raises(self):
        self.ledger_path.write_text("{not valid json")
        with self.assertRaises(LedgerError):
            corpus_add(self.ledger_path, self._make_entry("aa", "https://example.com/u1"))

    def test_invalid_schema_raises(self):
        self.ledger_path.write_text('{"schema": 2, "videos": {}}')
        with self.assertRaises(LedgerError):
            corpus_add(self.ledger_path, self._make_entry("aa", "https://example.com/u1"))

    def test_missing_required_keys_raises(self):
        entry = {"sha256": "aa"}  # missing keys
        with self.assertRaises(ValueError):
            corpus_add(self.ledger_path, entry)

    def test_source_dedupe_by_normalized_url(self):
        # Two sources with same normalized URL should be deduped
        entry = self._make_entry("aa", "https://example.com/u1")
        entry["sources"] = [
            {"source": "local", "origin": "local", "url": "https://Example.COM/u1?x=1", "creator_id": None},
            {"source": "local", "origin": "local", "url": "https://example.com/u1", "creator_id": None},
        ]
        result = corpus_add(self.ledger_path, entry)
        self.assertEqual(result["sources_added"], 1)
        with open(self.ledger_path) as f:
            ledger = json.load(f)
        self.assertEqual(len(ledger["videos"]["aa"]["sources"]), 1)

    def test_source_dedupe_by_source_path_when_url_none(self):
        # When URL is None, dedupe by source path
        entry = self._make_entry("aa", None)
        entry["sources"] = [
            {"source": "/path/to/file", "origin": "local", "url": None, "creator_id": None},
            {"source": "/path/to/file", "origin": "local", "url": None, "creator_id": None},
        ]
        result = corpus_add(self.ledger_path, entry)
        self.assertEqual(result["sources_added"], 1)

    def test_deleted_url_source_not_collapsed(self):
        # A source with URL and a source without URL (deleted) should not be collapsed
        entry = self._make_entry("aa", "https://example.com/u1")
        corpus_add(self.ledger_path, entry)
        # Add same sha256 with a source that has no URL (simulating deleted URL)
        entry2 = self._make_entry("aa", None)
        entry2["sources"] = [{"source": "local", "origin": "local", "url": None, "creator_id": None}]
        result = corpus_add(self.ledger_path, entry2)
        self.assertEqual(result["sources_added"], 1)
        with open(self.ledger_path) as f:
            ledger = json.load(f)
        sources = ledger["videos"]["aa"]["sources"]
        self.assertEqual(len(sources), 2)
        urls = [s.get("url") for s in sources]
        self.assertIn("https://example.com/u1", urls)
        self.assertIn(None, urls)

    def test_same_versions_different_analysis_path_no_history_no_overwrite(self):
        # MED fix: same versions, different analysis_path/analyzed_at/tags, no new sources -> UPDATED no-op
        v1 = {"analysis": "1", "prompt": "1", "model": "m1"}
        entry1 = self._make_entry("aa", "https://example.com/u1", versions=v1, analysis_path="/a1.json", analyzed_at="2024-01-01T00:00:00Z", tags={"t": "1"})
        corpus_add(self.ledger_path, entry1)
        # Re-add with same versions but different analysis_path, analyzed_at, tags
        entry2 = self._make_entry("aa", "https://example.com/u1", versions=v1, analysis_path="/a2.json", analyzed_at="2024-01-02T00:00:00Z", tags={"t": "2"})
        result = corpus_add(self.ledger_path, entry2)
        self.assertEqual(result["status"], "UPDATED")
        self.assertEqual(result["sources_added"], 0)

        with open(self.ledger_path) as f:
            ledger = json.load(f)
        video = ledger["videos"]["aa"]
        # Analysis fields should NOT be overwritten
        self.assertEqual(video["analysis_path"], "/a1.json")
        self.assertEqual(video["analyzed_at"], "2024-01-01T00:00:00Z")
        self.assertEqual(video["tags"], {"t": "1"})
        # History should be empty
        self.assertEqual(len(video["history"]), 0)

    def test_same_versions_new_source_does_not_overwrite_analysis(self):
        # MED fix: same versions, new source -> DUPLICATE, analysis unchanged, no history
        v1 = {"analysis": "1", "prompt": "1", "model": "m1"}
        entry1 = self._make_entry("aa", "https://example.com/u1", versions=v1, analysis_path="/a1.json", analyzed_at="2024-01-01T00:00:00Z", tags={"t": "1"})
        corpus_add(self.ledger_path, entry1)
        # Add same sha, same versions, new URL, different analysis_path
        entry2 = self._make_entry("aa", "https://example.com/u2", versions=v1, analysis_path="/a2.json", analyzed_at="2024-01-02T00:00:00Z", tags={"t": "2"})
        result = corpus_add(self.ledger_path, entry2)
        self.assertEqual(result["status"], "DUPLICATE")
        self.assertEqual(result["sources_added"], 1)

        with open(self.ledger_path) as f:
            ledger = json.load(f)
        video = ledger["videos"]["aa"]
        # Analysis fields should NOT be overwritten
        self.assertEqual(video["analysis_path"], "/a1.json")
        self.assertEqual(video["analyzed_at"], "2024-01-01T00:00:00Z")
        self.assertEqual(video["tags"], {"t": "1"})
        # History should be empty
        self.assertEqual(len(video["history"]), 0)
        # But sources should have both URLs
        self.assertEqual(len(video["sources"]), 2)
        urls = {normalize_url(s["url"]) for s in video["sources"]}
        self.assertIn("https://example.com/u1", urls)
        self.assertIn("https://example.com/u2", urls)

    def test_kind_mismatch_raises(self):
        entry1 = self._make_entry("aa", "https://example.com/u1")
        entry1["kind"] = "video"
        corpus_add(self.ledger_path, entry1)
        entry2 = self._make_entry("aa", "https://example.com/u2")
        entry2["kind"] = "image_sequence"
        with self.assertRaises(ValueError) as cm:
            corpus_add(self.ledger_path, entry2)
        self.assertIn("Kind mismatch", str(cm.exception))

    def test_invalid_source_raises(self):
        entry = self._make_entry("aa", "https://example.com/u1")
        entry["sources"] = [{"source": "local", "origin": "invalid", "url": "https://example.com/u1", "creator_id": None}]
        with self.assertRaises(ValueError):
            corpus_add(self.ledger_path, entry)

    def test_malformed_versions_in_ledger_raises(self):
        # Write a ledger with malformed versions (null)
        bad_ledger = {
            "schema": 1,
            "videos": {
                "aa": {
                    "sha256": "aa",
                    "kind": "video",
                    "analysis_path": "/a.json",
                    "analyzed_at": "2024-01-01T00:00:00Z",
                    "versions": None,
                    "sources": [{"source": "local", "origin": "local", "url": "https://example.com/u1", "creator_id": None}],
                    "tags": {},
                    "history": []
                }
            }
        }
        self.ledger_path.write_text(json.dumps(bad_ledger))
        with self.assertRaises(LedgerError):
            corpus_add(self.ledger_path, self._make_entry("bb", "https://example.com/u2"))

    def test_deepcopy_prevents_aliasing(self):
        # Ensure stored versions/tags are deep copies, not aliases
        versions = {"analysis": "1", "prompt": "1", "model": "m1"}
        tags = {"t": "1"}
        entry = self._make_entry("aa", "https://example.com/u1", versions=versions, tags=tags)
        corpus_add(self.ledger_path, entry)
        # Mutate caller's dicts
        versions["analysis"] = "999"
        tags["t"] = "999"
        # Reload ledger
        with open(self.ledger_path) as f:
            ledger = json.load(f)
        video = ledger["videos"]["aa"]
        self.assertEqual(video["versions"]["analysis"], "1")
        self.assertEqual(video["tags"]["t"], "1")

    def test_invalid_sha256_raises(self):
        # sha256 must be non-empty string
        entry = self._make_entry("", "https://example.com/u1")
        with self.assertRaises(ValueError) as cm:
            corpus_add(self.ledger_path, entry)
        self.assertIn("sha256 must be a non-empty string", str(cm.exception))

        entry = self._make_entry(123, "https://example.com/u1")
        with self.assertRaises(ValueError):
            corpus_add(self.ledger_path, entry)

    def test_invalid_tags_raises(self):
        # tags must be a dict - construct entry directly to bypass helper defaults
        entry = {
            "sha256": "aa",
            "kind": "video",
            "analysis_path": "/analysis/aa.json",
            "analyzed_at": "2024-01-01T00:00:00Z",
            "versions": {"analysis": "1", "prompt": "1", "model": "m1"},
            "sources": [{"source": "local", "origin": "local", "url": "https://example.com/u1", "creator_id": None}],
            "tags": None,
        }
        with self.assertRaises(ValueError) as cm:
            corpus_add(self.ledger_path, entry)
        self.assertIn("tags must be a dictionary", str(cm.exception))

        entry["tags"] = "not a dict"
        with self.assertRaises(ValueError):
            corpus_add(self.ledger_path, entry)

    def test_invalid_versions_raises(self):
        # versions must be a dict with required keys - construct entry directly
        entry = {
            "sha256": "aa",
            "kind": "video",
            "analysis_path": "/analysis/aa.json",
            "analyzed_at": "2024-01-01T00:00:00Z",
            "versions": None,
            "sources": [{"source": "local", "origin": "local", "url": "https://example.com/u1", "creator_id": None}],
            "tags": {},
        }
        with self.assertRaises(ValueError) as cm:
            corpus_add(self.ledger_path, entry)
        self.assertIn("versions must be a dictionary", str(cm.exception))

        entry["versions"] = {"analysis": "1"}  # missing keys
        with self.assertRaises(ValueError):
            corpus_add(self.ledger_path, entry)


class TestCorpusStatus(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.ledger_path = self.tmpdir / "ledger.json"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_entry(self, sha256, url, versions=None, tags=None, analysis_path=None, analyzed_at=None):
        if versions is None:
            versions = {"analysis": "1", "prompt": "1", "model": "m1"}
        if tags is None:
            tags = {}
        if analysis_path is None:
            analysis_path = f"/analysis/{sha256}.json"
        if analyzed_at is None:
            analyzed_at = "2024-01-01T00:00:00Z"
        return {
            "sha256": sha256,
            "kind": "video",
            "analysis_path": analysis_path,
            "analyzed_at": analyzed_at,
            "versions": versions,
            "sources": [{"source": "local", "origin": "local", "url": url, "creator_id": None}],
            "tags": tags,
        }

    def _add_video(self, sha256, url):
        entry = self._make_entry(sha256, url)
        corpus_add(self.ledger_path, entry)

    def test_status_basic(self):
        self._add_video("aa", "https://example.com/u1")
        self._add_video("bb", "https://example.com/u2")
        queue = ["https://example.com/u1", "https://example.com/u4"]
        result = corpus_status(self.ledger_path, queue)
        self.assertEqual(result["analyzed"], 1)
        self.assertEqual(result["queued_not_analyzed"], ["https://example.com/u4"])
        self.assertEqual(result["failed"], [])
        self.assertEqual(result["total"], 2)

    def test_status_with_failed_urls(self):
        self._add_video("aa", "https://example.com/u1")
        queue = ["https://example.com/u1", "https://example.com/u4"]
        failed = ["https://example.com/u4"]
        result = corpus_status(self.ledger_path, queue, failed_urls=failed)
        self.assertEqual(result["failed"], ["https://example.com/u4"])

    def test_status_normalizes_queue_urls(self):
        self._add_video("aa", "https://Example.COM/u1")
        queue = ["https://example.com/u1"]  # different case
        result = corpus_status(self.ledger_path, queue)
        self.assertEqual(result["analyzed"], 1)
        self.assertEqual(result["queued_not_analyzed"], [])

    def test_status_queued_never_counted_as_analyzed(self):
        # Queue URLs not in ledger are never counted as analyzed
        queue = ["https://example.com/u1", "https://example.com/u2"]
        result = corpus_status(self.ledger_path, queue)
        self.assertEqual(result["analyzed"], 0)
        self.assertEqual(len(result["queued_not_analyzed"]), 2)

    def test_worked_example_sequence(self):
        # Worked example from spec: add A(sha "aa", url u1), add B("bb", u2), add "aa" again with url u3
        # => ADDED, ADDED, DUPLICATE and A has 2 sources
        # corpus_status(queue [u1,u4]) => queued_not_analyzed ["u4"]
        result1 = corpus_add(self.ledger_path, self._make_entry("aa", "https://example.com/u1"))
        self.assertEqual(result1["status"], "ADDED")
        result2 = corpus_add(self.ledger_path, self._make_entry("bb", "https://example.com/u2"))
        self.assertEqual(result2["status"], "ADDED")
        result3 = corpus_add(self.ledger_path, self._make_entry("aa", "https://example.com/u3"))
        self.assertEqual(result3["status"], "DUPLICATE")
        self.assertEqual(result3["sources_added"], 1)

        with open(self.ledger_path) as f:
            ledger = json.load(f)
        self.assertEqual(len(ledger["videos"]["aa"]["sources"]), 2)

        queue = ["https://example.com/u1", "https://example.com/u4"]
        result = corpus_status(self.ledger_path, queue)
        self.assertEqual(result["analyzed"], 1)
        self.assertEqual(result["queued_not_analyzed"], ["https://example.com/u4"])


class TestStaleEntries(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.ledger_path = self.tmpdir / "ledger.json"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _add_video(self, sha256, versions):
        entry = {
            "sha256": sha256,
            "kind": "video",
            "analysis_path": f"/a/{sha256}.json",
            "analyzed_at": "2024-01-01T00:00:00Z",
            "versions": versions,
            "sources": [{"source": "local", "origin": "local", "url": f"https://example.com/{sha256}", "creator_id": None}],
            "tags": {},
        }
        corpus_add(self.ledger_path, entry)

    def test_stale_analysis_version(self):
        self._add_video("aa", {"analysis": "1", "prompt": "1", "model": "m1"})
        self._add_video("bb", {"analysis": "1", "prompt": "1", "model": "m1"})
        current = {"analysis": "2", "prompt": "1", "model": "m1"}
        stale = stale_entries(self.ledger_path, current)
        self.assertEqual(len(stale), 2)
        self.assertEqual({s["sha256"] for s in stale}, {"aa", "bb"})
        for s in stale:
            self.assertIn("analysis_version", s["reason"])

    def test_stale_prompt_version(self):
        self._add_video("aa", {"analysis": "1", "prompt": "1", "model": "m1"})
        current = {"analysis": "1", "prompt": "2", "model": "m1"}
        stale = stale_entries(self.ledger_path, current)
        self.assertEqual(len(stale), 1)
        self.assertIn("prompt_version", stale[0]["reason"])

    def test_not_stale_model_change_default(self):
        self._add_video("aa", {"analysis": "1", "prompt": "1", "model": "m1"})
        current = {"analysis": "1", "prompt": "1", "model": "m2"}
        stale = stale_entries(self.ledger_path, current)
        self.assertEqual(len(stale), 0)

    def test_stale_model_change_strict(self):
        self._add_video("aa", {"analysis": "1", "prompt": "1", "model": "m1"})
        current = {"analysis": "1", "prompt": "1", "model": "m2"}
        stale = stale_entries(self.ledger_path, current, strict=True)
        self.assertEqual(len(stale), 1)
        self.assertIn("model_version", stale[0]["reason"])

    def test_stale_returns_sorted_list(self):
        self._add_video("bb", {"analysis": "1", "prompt": "1", "model": "m1"})
        self._add_video("aa", {"analysis": "1", "prompt": "1", "model": "m1"})
        current = {"analysis": "2", "prompt": "1", "model": "m1"}
        stale = stale_entries(self.ledger_path, current)
        self.assertEqual([s["sha256"] for s in stale], ["aa", "bb"])

    def test_stale_returns_reason_dict(self):
        self._add_video("aa", {"analysis": "1", "prompt": "1", "model": "m1"})
        current = {"analysis": "2", "prompt": "2", "model": "m1"}
        stale = stale_entries(self.ledger_path, current)
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]["sha256"], "aa")
        self.assertIn("analysis_version", stale[0]["reason"])
        self.assertIn("prompt_version", stale[0]["reason"])

    def test_stale_entries_corrupt_ledger_raises(self):
        self.ledger_path.write_text("{bad json")
        with self.assertRaises(LedgerError):
            stale_entries(self.ledger_path, {"analysis": "1", "prompt": "1", "model": "m1"})


class TestImageSequenceIdentity(unittest.TestCase):
    """Tests for the FINAL CORRECTION: image_sequence identity preserves temporal order."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_A_B_C_vs_C_B_A_different_identity(self):
        # A-B-C order
        dir1 = self.tmpdir / "seq1"
        dir1.mkdir()
        (dir1 / "frame_1.png").write_bytes(b"A")
        (dir1 / "frame_2.png").write_bytes(b"B")
        (dir1 / "frame_3.png").write_bytes(b"C")
        hash1 = compute_image_sequence_sha256(dir1)

        # C-B-A order (different temporal order)
        dir2 = self.tmpdir / "seq2"
        dir2.mkdir()
        (dir2 / "frame_1.png").write_bytes(b"C")
        (dir2 / "frame_2.png").write_bytes(b"B")
        (dir2 / "frame_3.png").write_bytes(b"A")
        hash2 = compute_image_sequence_sha256(dir2)

        self.assertNotEqual(hash1, hash2, "A-B-C and C-B-A must have different identities")

    def test_identical_ordered_content_different_filenames_same_identity(self):
        # Same content in same order, different filenames
        dir1 = self.tmpdir / "seq1"
        dir1.mkdir()
        (dir1 / "frame_001.png").write_bytes(b"AAA")
        (dir1 / "frame_002.png").write_bytes(b"BBB")

        dir2 = self.tmpdir / "seq2"
        dir2.mkdir()
        (dir2 / "img_x.png").write_bytes(b"AAA")
        (dir2 / "img_y.png").write_bytes(b"BBB")

        hash1 = compute_image_sequence_sha256(dir1)
        hash2 = compute_image_sequence_sha256(dir2)
        self.assertEqual(hash1, hash2, "Identical ordered content must yield same identity")


class TestMalformedSources(unittest.TestCase):
    """Tests for malformed source validation."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.ledger_path = self.tmpdir / "ledger.json"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_entry(self, sha256, url, versions=None, tags=None, analysis_path=None, analyzed_at=None):
        if versions is None:
            versions = {"analysis": "1", "prompt": "1", "model": "m1"}
        if tags is None:
            tags = {}
        if analysis_path is None:
            analysis_path = f"/analysis/{sha256}.json"
        if analyzed_at is None:
            analyzed_at = "2024-01-01T00:00:00Z"
        return {
            "sha256": sha256,
            "kind": "video",
            "analysis_path": analysis_path,
            "analyzed_at": analyzed_at,
            "versions": versions,
            "sources": [{"source": "local", "origin": "local", "url": url, "creator_id": None}],
            "tags": tags,
        }

    def test_malformed_sources_rejected(self):
        # Test various malformed source dicts
        malformed_sources = [
            {},  # empty dict
            {"source": 123, "origin": "local", "url": "https://example.com", "creator_id": None},  # non-str source
            {"source": "local", "origin": 123, "url": "https://example.com", "creator_id": None},  # non-str origin
            {"source": "local", "origin": "local", "url": 123, "creator_id": None},  # non-str url
            {"source": "local", "origin": "local", "url": "https://example.com", "creator_id": 123},  # non-str creator_id
            {"source": ["list"], "origin": "local", "url": "https://example.com", "creator_id": None},  # unhashable source
            {"source": "local", "origin": "invalid", "url": "https://example.com", "creator_id": None},  # invalid origin
            {"source": "local", "origin": "local", "url": "https://example.com"},  # missing creator_id
        ]
        for bad_source in malformed_sources:
            with self.subTest(source=bad_source):
                entry = self._make_entry("aa", "https://example.com/u1")
                entry["sources"] = [bad_source]
                with self.assertRaises((ValueError, LedgerError)):
                    corpus_add(self.ledger_path, entry)


if __name__ == "__main__":
    unittest.main()
