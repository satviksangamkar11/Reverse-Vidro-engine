"""Tests for a2_collect.py"""
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from a2_collect import (
    collect_inputs,
    extract_zip_safe,
    scan_for_media,
    _is_media_file,
    _is_unsafe_path,
    VIDEO_EXTS,
    IMAGE_EXTS,
    MAX_TOTAL_SIZE,
    MAX_MEMBERS,
)


class TestIsMediaFile(unittest.TestCase):
    def test_video_extensions(self):
        for ext in VIDEO_EXTS:
            self.assertTrue(_is_media_file(f"video{ext}"))
            self.assertTrue(_is_media_file(f"video{ext.upper()}"))
            self.assertTrue(_is_media_file(f"VIDEO{ext}"))

    def test_image_extensions(self):
        for ext in IMAGE_EXTS:
            self.assertTrue(_is_media_file(f"image{ext}"))
            self.assertTrue(_is_media_file(f"image{ext.upper()}"))

    def test_non_media_extensions(self):
        for ext in [".txt", ".exe", ".pdf", ".zip", ".mov.txt"]:
            self.assertFalse(_is_media_file(f"file{ext}"))


class TestIsUnsafePath(unittest.TestCase):
    def test_absolute_path(self):
        # Test POSIX absolute path
        unsafe, error = _is_unsafe_path("/absolute/path")
        self.assertTrue(unsafe)
        self.assertIn("Absolute path not allowed", error)

        # Test Windows absolute path (drive letter)
        unsafe, error = _is_unsafe_path("C:\\absolute\\path")
        self.assertTrue(unsafe)
        self.assertIn("Absolute path not allowed", error)

        # Test Windows absolute path (UNC)
        unsafe, error = _is_unsafe_path("\\\\server\\share\\path")
        self.assertTrue(unsafe)
        self.assertIn("Absolute path not allowed", error)

    def test_path_traversal(self):
        unsafe, error = _is_unsafe_path("../escape")
        self.assertTrue(unsafe)
        self.assertIn("Zip-slip attempt", error)

        unsafe, error = _is_unsafe_path("folder/../escape")
        self.assertTrue(unsafe)
        self.assertIn("Zip-slip attempt", error)

        # Test with backslash
        unsafe, error = _is_unsafe_path("folder\\..\\escape")
        self.assertTrue(unsafe)
        self.assertIn("Zip-slip attempt", error)

    def test_backslash(self):
        unsafe, error = _is_unsafe_path("folder\\file")
        self.assertTrue(unsafe)
        self.assertIn("Unsafe path", error)

    def test_colon(self):
        unsafe, error = _is_unsafe_path("file:name")
        self.assertTrue(unsafe)
        self.assertIn("Unsafe path", error)

    def test_safe_paths(self):
        for path in ["file.txt", "folder/file.txt", "folder/sub/file.txt"]:
            unsafe, error = _is_unsafe_path(path)
            self.assertFalse(unsafe)


class TestScanForMedia(unittest.TestCase):
    def test_scan_for_media_filters_extensions_case_insensitive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Create test files
            (root / "clip1.MOV").write_bytes(b"video")
            (root / "clip2.mp4").write_bytes(b"video")
            (root / "frame.PNG").write_bytes(b"image")
            (root / "frame.jpg").write_bytes(b"image")
            (root / "document.txt").write_bytes(b"text")
            sub = root / "sub"
            sub.mkdir()
            (sub / "frame001.JPEG").write_bytes(b"image")
            (sub / "readme.md").write_bytes(b"text")

            def list_dir(p):
                return [str(x) for x in Path(p).iterdir()]

            def is_file(p):
                return Path(p).is_file()

            def is_dir(p):
                return Path(p).is_dir()

            result = scan_for_media(str(root), VIDEO_EXTS, IMAGE_EXTS, list_dir, is_file, is_dir)
            media_files = result["media_files"]

            self.assertEqual(len(media_files), 5)
            names = [os.path.basename(f) for f in media_files]
            self.assertIn("clip1.MOV", names)
            self.assertIn("clip2.mp4", names)
            self.assertIn("frame.PNG", names)
            self.assertIn("frame.jpg", names)
            self.assertIn("frame001.JPEG", names)
            self.assertEqual(result["status"], "ok")


class TestExtractZipSafe(unittest.TestCase):
    def create_test_zip(self, zip_path: str, members: list):
        """Create a test zip with given members. Each member is (name, content, is_dir, external_attr)."""
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for name, content, is_dir, external_attr in members:
                info = zipfile.ZipInfo(name)
                info.file_size = len(content) if not is_dir else 0
                info.external_attr = external_attr
                if is_dir:
                    info.external_attr |= 0x10 << 16  # directory attribute
                zf.writestr(info, content if not is_dir else b"")

    def test_extract_zip_safe_rejects_malicious_entries(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = os.path.join(td, "test.zip")
            dest_dir = os.path.join(td, "extracted")

            # Create zip with malicious entries
            members = [
                ("video.mp4", b"video content", False, 0),
                ("../escape.txt", b"escape", False, 0),
                ("/absolute.txt", b"absolute", False, 0),
                ("images/frame.jpg", b"image content", False, 0),
                ("symlink.txt", b"", False, 0xA1FF0000),  # symlink
            ]
            self.create_test_zip(zip_path, members)

            result = extract_zip_safe(
                zip_path, dest_dir, MAX_TOTAL_SIZE, MAX_MEMBERS,
                lambda p: zipfile.ZipFile(p, 'r'),
                lambda zf: zf.infolist(),
                lambda zf, info, d: zf.extract(info, os.path.dirname(d)),
                lambda p: os.makedirs(p, exist_ok=True)
            )

            extracted = result["extracted"]
            rejected = result["rejected"]

            # Normalize extracted paths relative to dest_dir for comparison
            extracted_rel = [os.path.relpath(p, dest_dir) for p in extracted]

            self.assertEqual(len(extracted_rel), 2)
            self.assertIn("video.mp4", extracted_rel)
            self.assertIn(os.path.join("images", "frame.jpg"), extracted_rel)

            self.assertEqual(len(rejected), 3)
            rejected_items = {r["item"]: r["error"] for r in rejected}
            self.assertIn("../escape.txt", rejected_items)
            self.assertIn("Zip-slip attempt", rejected_items["../escape.txt"])
            self.assertIn("/absolute.txt", rejected_items)
            self.assertIn("Absolute path not allowed", rejected_items["/absolute.txt"])
            self.assertIn("symlink.txt", rejected_items)
            self.assertIn("Symlink not allowed", rejected_items["symlink.txt"])
            self.assertEqual(result["status"], "ok")

    def test_extract_zip_safe_size_and_count_caps(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = os.path.join(td, "test.zip")
            dest_dir = os.path.join(td, "extracted")

            # Test member count limit
            members = [(f"video{i}.mp4", b"x" * 100, False, 0) for i in range(MAX_MEMBERS + 1)]
            self.create_test_zip(zip_path, members)

            result = extract_zip_safe(
                zip_path, dest_dir, MAX_TOTAL_SIZE, MAX_MEMBERS,
                lambda p: zipfile.ZipFile(p, 'r'),
                lambda zf: zf.infolist(),
                lambda zf, info, d: zf.extract(info, os.path.dirname(d)),
                lambda p: os.makedirs(p, exist_ok=True)
            )

            self.assertEqual(len(result["extracted"]), 0)
            self.assertEqual(len(result["rejected"]), MAX_MEMBERS + 1)
            for r in result["rejected"]:
                self.assertIn("Too many members", r["error"])

            # Test total size limit - use a small cap to avoid huge files
            small_max_size = 1000
            members = [("video.mp4", b"x" * 2000, False, 0)]
            self.create_test_zip(zip_path, members)

            result = extract_zip_safe(
                zip_path, dest_dir, small_max_size, MAX_MEMBERS,
                lambda p: zipfile.ZipFile(p, 'r'),
                lambda zf: zf.infolist(),
                lambda zf, info, d: zf.extract(info, os.path.dirname(d)),
                lambda p: os.makedirs(p, exist_ok=True)
            )

            self.assertEqual(len(result["extracted"]), 0)
            self.assertEqual(len(result["rejected"]), 1)
            self.assertIn("Total size exceeds limit", result["rejected"][0]["error"])

    def test_extract_zip_safe_rejects_duplicate_existing_file(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = os.path.join(td, "test.zip")
            dest_dir = os.path.join(td, "extracted")
            os.makedirs(dest_dir, exist_ok=True)

            # Pre-create a file in dest_dir
            existing_file = os.path.join(dest_dir, "video.mp4")
            with open(existing_file, "wb") as f:
                f.write(b"existing content")

            # Create zip with same filename
            members = [
                ("video.mp4", b"new content", False, 0),
                ("image.jpg", b"image content", False, 0),
            ]
            self.create_test_zip(zip_path, members)

            result = extract_zip_safe(
                zip_path, dest_dir, MAX_TOTAL_SIZE, MAX_MEMBERS,
                lambda p: zipfile.ZipFile(p, 'r'),
                lambda zf: zf.infolist(),
                lambda zf, info, d: zf.extract(info, os.path.dirname(d)),
                lambda p: os.makedirs(p, exist_ok=True)
            )

            extracted = result["extracted"]
            rejected = result["rejected"]

            # Normalize extracted paths relative to dest_dir
            extracted_rel = [os.path.relpath(p, dest_dir) for p in extracted]

            # Only image.jpg should be extracted, video.mp4 rejected as duplicate
            self.assertEqual(len(extracted_rel), 1)
            self.assertIn("image.jpg", extracted_rel)

            self.assertEqual(len(rejected), 1)
            self.assertEqual(rejected[0]["item"], "video.mp4")
            self.assertIn("Destination file exists", rejected[0]["error"])

            # Original file should remain unchanged
            with open(existing_file, "rb") as f:
                self.assertEqual(f.read(), b"existing content")


class TestCollectInputs(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.src = Path(self.temp_dir.name) / "src"
        self.dest = Path(self.temp_dir.name) / "dest"
        self.src.mkdir()
        self.dest.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _make_sha256(self, content_map: dict):
        """Create a sha256_file function that returns hash based on content."""
        import hashlib
        def sha256_file(path):
            content = content_map.get(os.path.basename(path), b"")
            return hashlib.sha256(content).hexdigest()
        return sha256_file

    def test_collect_inputs_copies_videos_and_images_recursive(self):
        # Create source structure
        (self.src / "video.mp4").write_bytes(b"video1")
        clips = self.src / "clips"
        clips.mkdir()
        (clips / "clip1.mov").write_bytes(b"video2")
        (clips / "clip2.txt").write_bytes(b"text")
        sub = clips / "sub"
        sub.mkdir()
        (sub / "frame.png").write_bytes(b"image1")

        content_map = {
            "video.mp4": b"video1",
            "clip1.mov": b"video2",
            "frame.png": b"image1",
        }
        sha256_file = self._make_sha256(content_map)

        def copy_file(src, dst):
            Path(dst).write_bytes(Path(src).read_bytes())

        def make_dirs(path):
            Path(path).mkdir(parents=True, exist_ok=True)

        def list_dir(path):
            return [str(p) for p in Path(path).iterdir()]

        def is_file(path):
            return Path(path).is_file()

        def is_dir(path):
            return Path(path).is_dir()

        def get_size(path):
            return Path(path).stat().st_size

        def extract_zip_safe_func(zip_path, dest_dir, max_total_size, max_members):
            return {"extracted": [], "rejected": [], "status": "ok"}

        inputs = [str(self.src / "video.mp4"), str(clips)]
        result = collect_inputs(
            inputs, str(self.dest), sha256_file, copy_file, make_dirs,
            list_dir, is_file, is_dir, get_size, extract_zip_safe_func
        )

        copied = result["copied"]
        rejected = result["rejected"]

        self.assertEqual(len(copied), 3)
        copied_names = [os.path.basename(f) for f in copied]
        self.assertIn("video.mp4", copied_names)
        self.assertIn("clip1.mov", copied_names)
        self.assertIn("frame.png", copied_names)

        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0]["item"], str(clips / "clip2.txt"))
        self.assertIn("Not a video or image-sequence file", rejected[0]["error"])
        self.assertEqual(result["status"], "ok")

    def test_collect_inputs_zip_slip_rejection(self):
        # Create a zip with malicious entries
        zip_path = self.src / "archive.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("video.mp4", b"video")
            zf.writestr("../escape.txt", b"escape")
            zf.writestr("/absolute.txt", b"absolute")
            zf.writestr("images/frame.jpg", b"image")
            info = zipfile.ZipInfo("symlink.txt")
            info.external_attr = 0xA1FF0000
            zf.writestr(info, b"")

        content_map = {
            "video.mp4": b"video",
            "frame.jpg": b"image",
        }
        sha256_file = self._make_sha256(content_map)

        def copy_file(src, dst):
            Path(dst).write_bytes(Path(src).read_bytes())

        def make_dirs(path):
            Path(path).mkdir(parents=True, exist_ok=True)

        def list_dir(path):
            return [str(p) for p in Path(path).iterdir()]

        def is_file(path):
            return Path(path).is_file()

        def is_dir(path):
            return Path(path).is_dir()

        def get_size(path):
            return Path(path).stat().st_size

        def extract_zip_safe_func(zip_path, dest_dir, max_total_size, max_members):
            return extract_zip_safe(
                zip_path, dest_dir, max_total_size, max_members,
                lambda p: zipfile.ZipFile(p, 'r'),
                lambda zf: zf.infolist(),
                lambda zf, info, d: zf.extract(info, os.path.dirname(d)),
                make_dirs
            )

        inputs = [str(zip_path)]
        result = collect_inputs(
            inputs, str(self.dest), sha256_file, copy_file, make_dirs,
            list_dir, is_file, is_dir, get_size, extract_zip_safe_func
        )

        copied = result["copied"]
        rejected = result["rejected"]

        self.assertEqual(len(copied), 2)
        copied_names = [os.path.basename(f) for f in copied]
        self.assertIn("video.mp4", copied_names)
        self.assertIn("frame.jpg", copied_names)

        rejected_items = {r["item"]: r["error"] for r in rejected}
        self.assertIn("../escape.txt", rejected_items)
        self.assertIn("Zip-slip attempt", rejected_items["../escape.txt"])
        self.assertIn("/absolute.txt", rejected_items)
        self.assertIn("Absolute path not allowed", rejected_items["/absolute.txt"])
        self.assertIn("symlink.txt", rejected_items)
        self.assertIn("Symlink not allowed", rejected_items["symlink.txt"])
        self.assertEqual(result["status"], "ok")

    def test_collect_inputs_zip_size_and_count_caps(self):
        # Test member count limit
        zip_path = self.src / "many.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for i in range(MAX_MEMBERS + 1):
                zf.writestr(f"video{i}.mp4", b"x" * 100)

        content_map = {f"video{i}.mp4": b"x" * 100 for i in range(MAX_MEMBERS + 1)}
        sha256_file = self._make_sha256(content_map)

        def copy_file(src, dst):
            Path(dst).write_bytes(Path(src).read_bytes())

        def make_dirs(path):
            Path(path).mkdir(parents=True, exist_ok=True)

        def list_dir(path):
            return [str(p) for p in Path(path).iterdir()]

        def is_file(path):
            return Path(path).is_file()

        def is_dir(path):
            return Path(path).is_dir()

        def get_size(path):
            return Path(path).stat().st_size

        def extract_zip_safe_func(zip_path, dest_dir, max_total_size, max_members):
            return extract_zip_safe(
                zip_path, dest_dir, max_total_size, max_members,
                lambda p: zipfile.ZipFile(p, 'r'),
                lambda zf: zf.infolist(),
                lambda zf, info, d: zf.extract(info, os.path.dirname(d)),
                make_dirs
            )

        inputs = [str(zip_path)]
        result = collect_inputs(
            inputs, str(self.dest), sha256_file, copy_file, make_dirs,
            list_dir, is_file, is_dir, get_size, extract_zip_safe_func
        )

        self.assertEqual(len(result["copied"]), 0)
        self.assertEqual(len(result["rejected"]), MAX_MEMBERS + 1)
        for r in result["rejected"]:
            self.assertIn("Too many members", r["error"])

        # Test total size limit - use a small cap to avoid huge files
        zip_path2 = self.src / "large.zip"
        with zipfile.ZipFile(zip_path2, 'w') as zf:
            zf.writestr("video.mp4", b"x" * 2000)

        content_map2 = {"video.mp4": b"x" * 2000}
        sha256_file2 = self._make_sha256(content_map2)

        # Override the max_total_size in the wrapper to use a small value
        def extract_zip_safe_func_small(zip_path, dest_dir, max_total_size, max_members):
            return extract_zip_safe(
                zip_path, dest_dir, 1000, max_members,  # Use small cap
                lambda p: zipfile.ZipFile(p, 'r'),
                lambda zf: zf.infolist(),
                lambda zf, info, d: zf.extract(info, os.path.dirname(d)),
                make_dirs
            )

        inputs = [str(zip_path2)]
        result = collect_inputs(
            inputs, str(self.dest), sha256_file2, copy_file, make_dirs,
            list_dir, is_file, is_dir, get_size, extract_zip_safe_func_small
        )

        self.assertEqual(len(result["copied"]), 0)
        self.assertEqual(len(result["rejected"]), 1)
        self.assertIn("Total size exceeds limit", result["rejected"][0]["error"])

    def test_collect_inputs_duplicate_detection_via_sha256(self):
        # Create two identical files
        (self.src / "video1.mp4").write_bytes(b"same content")
        (self.src / "video2.mp4").write_bytes(b"same content")

        content_map = {"video1.mp4": b"same content", "video2.mp4": b"same content"}
        sha256_file = self._make_sha256(content_map)

        def copy_file(src, dst):
            Path(dst).write_bytes(Path(src).read_bytes())

        def make_dirs(path):
            Path(path).mkdir(parents=True, exist_ok=True)

        def list_dir(path):
            return [str(p) for p in Path(path).iterdir()]

        def is_file(path):
            return Path(path).is_file()

        def is_dir(path):
            return Path(path).is_dir()

        def get_size(path):
            return Path(path).stat().st_size

        def extract_zip_safe_func(zip_path, dest_dir, max_total_size, max_members):
            return {"extracted": [], "rejected": [], "status": "ok"}

        inputs = [str(self.src / "video1.mp4"), str(self.src / "video2.mp4")]
        result = collect_inputs(
            inputs, str(self.dest), sha256_file, copy_file, make_dirs,
            list_dir, is_file, is_dir, get_size, extract_zip_safe_func
        )

        self.assertEqual(len(result["copied"]), 1)
        self.assertEqual(len(result["duplicates"]), 1)
        self.assertEqual(result["duplicates"][0]["file"], str(self.src / "video2.mp4"))
        self.assertEqual(result["duplicates"][0]["duplicate_of"], str(self.dest / "video1.mp4"))

    def test_collect_inputs_no_overwrite(self):
        # Pre-create a file in dest
        (self.dest / "video.mp4").write_bytes(b"existing content")
        (self.src / "video.mp4").write_bytes(b"new content")

        content_map = {
            "video.mp4": b"new content",  # source file
        }
        sha256_file = self._make_sha256(content_map)

        def copy_file(src, dst):
            Path(dst).write_bytes(Path(src).read_bytes())

        def make_dirs(path):
            Path(path).mkdir(parents=True, exist_ok=True)

        def list_dir(path):
            return [str(p) for p in Path(path).iterdir()]

        def is_file(path):
            return Path(path).is_file()

        def is_dir(path):
            return Path(path).is_dir()

        def get_size(path):
            return Path(path).stat().st_size

        def extract_zip_safe_func(zip_path, dest_dir, max_total_size, max_members):
            return {"extracted": [], "rejected": [], "status": "ok"}

        inputs = [str(self.src / "video.mp4")]
        result = collect_inputs(
            inputs, str(self.dest), sha256_file, copy_file, make_dirs,
            list_dir, is_file, is_dir, get_size, extract_zip_safe_func
        )

        self.assertEqual(len(result["copied"]), 0)
        self.assertEqual(len(result["duplicates"]), 1)
        self.assertEqual(result["duplicates"][0]["file"], str(self.src / "video.mp4"))
        self.assertEqual(result["duplicates"][0]["duplicate_of"], str(self.dest / "video.mp4"))
        # Original file should remain unchanged
        self.assertEqual((self.dest / "video.mp4").read_bytes(), b"existing content")

    def test_collect_inputs_zip_no_overwrite_existing(self):
        # Pre-create a file in dest/archive/
        archive_dest = self.dest / "archive"
        archive_dest.mkdir()
        (archive_dest / "video.mp4").write_bytes(b"existing content")

        # Create a zip with same filename
        zip_path = self.src / "archive.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("video.mp4", b"new content")
            zf.writestr("image.jpg", b"image content")

        content_map = {
            "video.mp4": b"new content",
            "image.jpg": b"image content",
        }
        sha256_file = self._make_sha256(content_map)

        def copy_file(src, dst):
            Path(dst).write_bytes(Path(src).read_bytes())

        def make_dirs(path):
            Path(path).mkdir(parents=True, exist_ok=True)

        def list_dir(path):
            return [str(p) for p in Path(path).iterdir()]

        def is_file(path):
            return Path(path).is_file()

        def is_dir(path):
            return Path(path).is_dir()

        def get_size(path):
            return Path(path).stat().st_size

        def extract_zip_safe_func(zip_path, dest_dir, max_total_size, max_members):
            return extract_zip_safe(
                zip_path, dest_dir, max_total_size, max_members,
                lambda p: zipfile.ZipFile(p, 'r'),
                lambda zf: zf.infolist(),
                lambda zf, info, d: zf.extract(info, os.path.dirname(d)),
                make_dirs
            )

        inputs = [str(zip_path)]
        result = collect_inputs(
            inputs, str(self.dest), sha256_file, copy_file, make_dirs,
            list_dir, is_file, is_dir, get_size, extract_zip_safe_func
        )

        copied = result["copied"]
        duplicates = result["duplicates"]
        rejected = result["rejected"]

        # Only image.jpg should be copied, video.mp4 reported as duplicate
        self.assertEqual(len(copied), 1)
        self.assertEqual(os.path.basename(copied[0]), "image.jpg")

        # Check duplicates contains the collision
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["file"], "video.mp4")
        self.assertEqual(duplicates[0]["duplicate_of"], str(archive_dest / "video.mp4"))

        # No rejected items for this case
        self.assertEqual(len(rejected), 0)

        # Original file should remain unchanged
        self.assertEqual((archive_dest / "video.mp4").read_bytes(), b"existing content")


if __name__ == "__main__":
    unittest.main()
