"""Tests for a1_queue.py - Link Queue Management."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from a1_queue import queue_links, queue_status, read_queue_file


class TestQueueLinks(unittest.TestCase):
    def test_queue_links_dedupe_and_rejects(self):
        # Worked example from spec
        with tempfile.TemporaryDirectory() as td:
            queue_file = Path(td) / "test_queue.txt"
            # Initial queue content
            queue_file.write_text("# comment line\nhttps://www.instagram.com/reel/ABC123/\n", encoding="utf-8")

            def normalize_reel_url(u):
                if "ABC123" in u:
                    return "https://www.instagram.com/reel/ABC123/"
                if "NEW789" in u:
                    return "https://www.instagram.com/reel/NEW789/"
                return None

            clock_now = lambda: "2024-01-15T10:30:00Z"

            urls = [
                "https://instagram.com/reel/ABC123/",
                "https://www.instagram.com/reel/ABC123/?utm_source=ig",
                "https://instagram.com/reel/NEW789/",
                "not-a-url",
                "https://instagram.com/p/POST123/",
            ]

            result = queue_links(urls, str(queue_file), normalize_reel_url, clock_now)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["added"], ["https://www.instagram.com/reel/NEW789/"])
            self.assertEqual(result["already_queued"], ["https://www.instagram.com/reel/ABC123/"])
            self.assertEqual(len(result["rejected"]), 2)
            rejected_urls = {r["url"] for r in result["rejected"]}
            self.assertIn("not-a-url", rejected_urls)
            self.assertIn("https://instagram.com/p/POST123/", rejected_urls)
            for r in result["rejected"]:
                self.assertEqual(r["error"], "Invalid Instagram Reel URL")

            # Verify queue file content preserved comments and order
            content = queue_file.read_text(encoding="utf-8")
            lines = content.strip().split("\n")
            self.assertEqual(lines[0], "# comment line")
            self.assertEqual(lines[1], "https://www.instagram.com/reel/ABC123/")
            self.assertEqual(lines[2], "https://www.instagram.com/reel/NEW789/")

    def test_queue_links_empty_input(self):
        with tempfile.TemporaryDirectory() as td:
            queue_file = Path(td) / "empty_queue.txt"
            queue_file.write_text("# only comment\n", encoding="utf-8")

            def normalize_reel_url(u):
                return None

            clock_now = lambda: "2024-01-15T10:30:00Z"

            result = queue_links([], str(queue_file), normalize_reel_url, clock_now)
            self.assertEqual(result["added"], [])
            self.assertEqual(result["already_queued"], [])
            self.assertEqual(result["rejected"], [])
            self.assertEqual(result["status"], "ok")

    def test_queue_links_all_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            queue_file = Path(td) / "invalid_queue.txt"
            queue_file.write_text("", encoding="utf-8")

            def normalize_reel_url(u):
                return None

            clock_now = lambda: "2024-01-15T10:30:00Z"

            urls = ["not-a-url", "http://example.com", "https://instagram.com/p/POST/"]
            result = queue_links(urls, str(queue_file), normalize_reel_url, clock_now)
            self.assertEqual(result["added"], [])
            self.assertEqual(result["already_queued"], [])
            self.assertEqual(len(result["rejected"]), 3)
            self.assertEqual(result["status"], "ok")

    def test_queue_links_missing_queue_file(self):
        with tempfile.TemporaryDirectory() as td:
            queue_file = Path(td) / "missing_queue.txt"
            # File does not exist

            def normalize_reel_url(u):
                if "NEW" in u:
                    return "https://www.instagram.com/reel/NEW/"
                return None

            clock_now = lambda: "2024-01-15T10:30:00Z"

            urls = ["https://instagram.com/reel/NEW/"]
            result = queue_links(urls, str(queue_file), normalize_reel_url, clock_now)
            self.assertEqual(result["added"], ["https://www.instagram.com/reel/NEW/"])
            self.assertEqual(result["already_queued"], [])
            self.assertEqual(result["rejected"], [])
            self.assertEqual(result["status"], "ok")
            # File should be created
            self.assertTrue(queue_file.exists())
            content = queue_file.read_text(encoding="utf-8")
            self.assertEqual(content.strip(), "https://www.instagram.com/reel/NEW/")

    def test_queue_links_dedupe_within_batch(self):
        """Same URL appearing multiple times in input batch - first occurrence decides bucket."""
        with tempfile.TemporaryDirectory() as td:
            queue_file = Path(td) / "dupe_queue.txt"
            queue_file.write_text("", encoding="utf-8")

            def normalize_reel_url(u):
                if "ABC" in u:
                    return "https://www.instagram.com/reel/ABC/"
                return None

            clock_now = lambda: "2024-01-15T10:30:00Z"

            urls = [
                "https://instagram.com/reel/ABC/",
                "https://instagram.com/reel/ABC/?utm=1",
                "https://instagram.com/reel/ABC/",
            ]
            result = queue_links(urls, str(queue_file), normalize_reel_url, clock_now)
            self.assertEqual(result["added"], ["https://www.instagram.com/reel/ABC/"])
            self.assertEqual(result["already_queued"], [])
            self.assertEqual(result["rejected"], [])
            # Queue file should have only one entry
            content = queue_file.read_text(encoding="utf-8")
            self.assertEqual(content.strip().count("ABC"), 1)


class TestQueueStatus(unittest.TestCase):
    def test_queue_status_three_states(self):
        # Worked example from spec
        with tempfile.TemporaryDirectory() as td:
            queue_file = Path(td) / "test_queue.txt"
            queue_file.write_text(
                "# comment\n"
                "https://www.instagram.com/reel/ABC123/\n"
                "https://www.instagram.com/reel/NEW789/\n"
                "https://www.instagram.com/reel/FAIL456/\n",
                encoding="utf-8",
            )

            ledger_path = Path(td) / "test_log.jsonl"
            ledger_lines = [
                json.dumps({
                    "url": "https://www.instagram.com/reel/ABC123/",
                    "status": "DOWNLOADED",
                    "error": None,
                    "timestamp": "2024-01-15T10:30:00Z"
                }),
                json.dumps({
                    "url": "https://www.instagram.com/reel/FAIL456/",
                    "status": "FAILED_INACCESSIBLE",
                    "error": "Private account",
                    "timestamp": "2024-01-15T10:31:00Z"
                }),
            ]
            ledger_path.write_text("\n".join(ledger_lines), encoding="utf-8")

            def read_text_file(p):
                return Path(p).read_text(encoding="utf-8")

            def parse_json_lines(s):
                return [json.loads(line) for line in s.strip().split("\n") if line]

            result = queue_status(str(queue_file), str(ledger_path), read_text_file, parse_json_lines)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(len(result["items"]), 3)

            # Check each item
            items_by_url = {item["url"]: item for item in result["items"]}

            self.assertEqual(items_by_url["https://www.instagram.com/reel/ABC123/"]["state"], "DOWNLOADED")
            self.assertIsNone(items_by_url["https://www.instagram.com/reel/ABC123/"]["error"])

            self.assertEqual(items_by_url["https://www.instagram.com/reel/NEW789/"]["state"], "QUEUED")
            self.assertIsNone(items_by_url["https://www.instagram.com/reel/NEW789/"]["error"])

            self.assertEqual(items_by_url["https://www.instagram.com/reel/FAIL456/"]["state"], "FAILED_INACCESSIBLE")
            self.assertEqual(items_by_url["https://www.instagram.com/reel/FAIL456/"]["error"], "Private account")

    def test_queue_status_url_in_queue_not_in_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            queue_file = Path(td) / "queue.txt"
            queue_file.write_text("https://www.instagram.com/reel/ONLY_IN_QUEUE/\n", encoding="utf-8")

            ledger_path = Path(td) / "ledger.jsonl"
            ledger_path.write_text("", encoding="utf-8")

            def read_text_file(p):
                return Path(p).read_text(encoding="utf-8")

            def parse_json_lines(s):
                return []

            result = queue_status(str(queue_file), str(ledger_path), read_text_file, parse_json_lines)
            self.assertEqual(result["items"][0]["state"], "QUEUED")
            self.assertIsNone(result["items"][0]["error"])

    def test_queue_status_url_in_ledger_downloaded(self):
        with tempfile.TemporaryDirectory() as td:
            queue_file = Path(td) / "queue.txt"
            queue_file.write_text("https://www.instagram.com/reel/DOWNLOADED/\n", encoding="utf-8")

            ledger_path = Path(td) / "ledger.jsonl"
            ledger_path.write_text(json.dumps({
                "url": "https://www.instagram.com/reel/DOWNLOADED/",
                "status": "DOWNLOADED",
                "error": None,
                "timestamp": "2024-01-15T10:30:00Z"
            }), encoding="utf-8")

            def read_text_file(p):
                return Path(p).read_text(encoding="utf-8")

            def parse_json_lines(s):
                return [json.loads(s)]

            result = queue_status(str(queue_file), str(ledger_path), read_text_file, parse_json_lines)
            self.assertEqual(result["items"][0]["state"], "DOWNLOADED")
            self.assertIsNone(result["items"][0]["error"])

    def test_queue_status_url_in_ledger_failed_with_error(self):
        with tempfile.TemporaryDirectory() as td:
            queue_file = Path(td) / "queue.txt"
            queue_file.write_text("https://www.instagram.com/reel/FAILED/\n", encoding="utf-8")

            ledger_path = Path(td) / "ledger.jsonl"
            ledger_path.write_text(json.dumps({
                "url": "https://www.instagram.com/reel/FAILED/",
                "status": "FAILED_INACCESSIBLE",
                "error": "Private account",
                "timestamp": "2024-01-15T10:31:00Z"
            }), encoding="utf-8")

            def read_text_file(p):
                return Path(p).read_text(encoding="utf-8")

            def parse_json_lines(s):
                return [json.loads(s)]

            result = queue_status(str(queue_file), str(ledger_path), read_text_file, parse_json_lines)
            self.assertEqual(result["items"][0]["state"], "FAILED_INACCESSIBLE")
            self.assertEqual(result["items"][0]["error"], "Private account")


class TestReadQueueFile(unittest.TestCase):
    def test_read_queue_file_preserves_comments_and_order(self):
        # Worked example from spec
        with tempfile.TemporaryDirectory() as td:
            queue_file = Path(td) / "test_queue.txt"
            queue_file.write_text(
                "# first comment\n"
                "https://www.instagram.com/reel/ABC123/\n"
                "# second comment\n"
                "https://www.instagram.com/reel/NEW789/\n",
                encoding="utf-8",
            )

            def read_text_file(p):
                return Path(p).read_text(encoding="utf-8")

            result = read_queue_file(str(queue_file), read_text_file)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["urls"], [
                "https://www.instagram.com/reel/ABC123/",
                "https://www.instagram.com/reel/NEW789/",
            ])
            self.assertEqual(result["comments"], [
                "# first comment",
                "# second comment",
            ])

    def test_read_queue_file_empty(self):
        with tempfile.TemporaryDirectory() as td:
            queue_file = Path(td) / "empty.txt"
            queue_file.write_text("", encoding="utf-8")

            def read_text_file(p):
                return Path(p).read_text(encoding="utf-8")

            result = read_queue_file(str(queue_file), read_text_file)
            self.assertEqual(result["urls"], [])
            self.assertEqual(result["comments"], [])
            self.assertEqual(result["status"], "ok")

    def test_read_queue_file_only_comments(self):
        with tempfile.TemporaryDirectory() as td:
            queue_file = Path(td) / "comments.txt"
            queue_file.write_text("# comment 1\n# comment 2\n", encoding="utf-8")

            def read_text_file(p):
                return Path(p).read_text(encoding="utf-8")

            result = read_queue_file(str(queue_file), read_text_file)
            self.assertEqual(result["urls"], [])
            self.assertEqual(result["comments"], ["# comment 1", "# comment 2"])
            self.assertEqual(result["status"], "ok")


class TestAddLinkCLINeverCallsDownloader(unittest.TestCase):
    """Verify that queue_links never calls any downloader/network code."""

    def test_add_link_cli_never_calls_downloader(self):
        with tempfile.TemporaryDirectory() as td:
            queue_file = Path(td) / "queue.txt"
            queue_file.write_text("", encoding="utf-8")

            # Mock normalize to return a valid URL
            mock_normalize = MagicMock(return_value="https://www.instagram.com/reel/TEST/")
            clock_now = lambda: "2024-01-15T10:30:00Z"

            # Patch any potential downloader entry points to raise if called
            def raise_if_called(*args, **kwargs):
                raise AssertionError("downloader called")

            with patch("subprocess.run", side_effect=raise_if_called) as mock_subprocess, \
                 patch("subprocess.Popen", side_effect=raise_if_called) as mock_popen, \
                 patch("urllib.request.urlopen", side_effect=raise_if_called) as mock_urlopen, \
                 patch("http.client.HTTPSConnection", side_effect=raise_if_called) as mock_https:

                result = queue_links(
                    ["https://instagram.com/reel/TEST/"],
                    str(queue_file),
                    mock_normalize,
                    clock_now
                )

                # Verify normalize was called
                mock_normalize.assert_called_once_with("https://instagram.com/reel/TEST/")

                # Verify no network/downloader calls were made (they would have raised)
                mock_subprocess.assert_not_called()
                mock_popen.assert_not_called()
                mock_urlopen.assert_not_called()
                mock_https.assert_not_called()

                # Verify result
                self.assertEqual(result["added"], ["https://www.instagram.com/reel/TEST/"])
                self.assertEqual(result["status"], "ok")


if __name__ == "__main__":
    unittest.main()
