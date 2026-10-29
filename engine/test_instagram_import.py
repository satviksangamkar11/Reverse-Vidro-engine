import tempfile
import unittest
from pathlib import Path

from instagram_import import import_reels, normalize_reel_url, read_urls


class InstagramImportTests(unittest.TestCase):
    def test_normalization_and_rejection(self):
        url = "https://www.instagram.com/reel/ABC_123/?igsh=tracking"
        self.assertEqual(normalize_reel_url(url), "https://www.instagram.com/reel/ABC_123/")
        self.assertEqual(read_urls([url, "https://instagram.com/reel/ABC_123/"], None), ["https://www.instagram.com/reel/ABC_123/"])
        for bad in ("http://www.instagram.com/reel/ABC/", "https://evil.example/reel/ABC/", "https://www.instagram.com/stories/ABC/"):
            with self.assertRaises(ValueError):
                normalize_reel_url(bad)

    def test_dry_run_download_and_resume(self):
        class FakeDownloader:
            calls = 0
            def download(self, url, output_path):
                self.calls += 1
                path = Path(output_path) / "clip.mp4"
                path.write_bytes(b"fake video")
                return str(path)
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            url = "https://www.instagram.com/reel/ABC/"
            fake = FakeDownloader()
            self.assertEqual(import_reels([url], folder)["planned"], 1)
            self.assertEqual(fake.calls, 0)
            self.assertEqual(import_reels([url], folder, run=True, downloader=fake, verifier=lambda _: {"duration": 1, "has_audio": True})["downloaded"], 1)
            self.assertEqual(import_reels([url], folder, run=True, downloader=fake, verifier=lambda _: {"duration": 1, "has_audio": True})["already_downloaded"], 1)
            self.assertEqual(fake.calls, 1)


if __name__ == "__main__":
    unittest.main()
