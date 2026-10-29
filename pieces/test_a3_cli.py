import json
import tempfile
import contextlib
import io
import os
import argparse
import ast
from unittest.mock import Mock

# Import the module under test
import a3_cli


class TestCLIAddLink:
    def test_cli_add_link_calls_queue_links_and_prints_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = os.path.join(tmpdir, "test_queue.txt")
            urls = ["https://instagram.com/reel/NEW789/"]
            expected_result = {
                "added": ["https://www.instagram.com/reel/NEW789/"],
                "already_queued": [],
                "rejected": [],
                "status": "ok"
            }

            mock_queue_links_fn = Mock(return_value=expected_result)
            mock_normalize = Mock(return_value="https://www.instagram.com/reel/NEW789/")
            mock_clock = Mock(return_value="2024-01-15T10:30:00Z")
            mock_write = Mock()

            stdout_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture):
                result = a3_cli.run_add_link(
                    urls=urls,
                    queue_file=queue_file,
                    queue_links_fn=mock_queue_links_fn,
                    normalize_reel_url=mock_normalize,
                    clock_now=mock_clock,
                    write_text_file=mock_write,
                )

            assert result == expected_result
            mock_queue_links_fn.assert_called_once_with(
                urls=urls,
                queue_file=queue_file,
                normalize_reel_url=mock_normalize,
                clock_now=mock_clock,
            )
            output = stdout_capture.getvalue().strip()
            parsed = json.loads(output)
            assert parsed == expected_result

    def test_cli_add_link_never_calls_downloader(self):
        # Verify a3_cli doesn't import any downloader/network/kimi modules
        with open(a3_cli.__file__, "r") as f:
            source = f.read()
        tree = ast.parse(source)
        imported_names = set()
        dynamic_imports = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.add(node.module.split('.')[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("__import__", "importlib"):
                    dynamic_imports = True
                elif isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
                    dynamic_imports = True

        prohibited = {'requests', 'urllib', 'http', 'subprocess', 'socket', 'ftplib', 'telnetlib', 'poplib', 'imaplib', 'smtplib', 'nntplib', 'xmlrpc', 'kimi', 'downloader', 'yt_dlp', 'instaloader'}
        found = imported_names & prohibited
        assert not found, f"a3_cli imports prohibited modules: {found}"
        assert not dynamic_imports, "a3_cli uses dynamic imports (__import__ or importlib)"


class TestCLICollect:
    def test_cli_collect_calls_collect_inputs_and_prints_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = os.path.join(tmpdir, "video.mp4")
            with open(src_file, "wb") as f:
                f.write(b"fake video content")
            dest_dir = os.path.join(tmpdir, "dest")
            os.makedirs(dest_dir, exist_ok=True)

            inputs = [src_file]
            dest = dest_dir
            expected_result = {
                "copied": [os.path.join(dest_dir, "video.mp4")],
                "duplicates": [],
                "rejected": [],
                "status": "ok"
            }

            mock_collect_fn = Mock(return_value=expected_result)
            dummy = Mock()

            stdout_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture):
                result = a3_cli.run_collect(
                    inputs=inputs,
                    dest=dest,
                    collect_inputs_fn=mock_collect_fn,
                    sha256_file=dummy,
                    copy_file=dummy,
                    make_dirs=dummy,
                    list_dir=dummy,
                    is_file=dummy,
                    is_dir=dummy,
                    get_size=dummy,
                    extract_zip_safe=dummy,
                )

            assert result == expected_result
            mock_collect_fn.assert_called_once()
            call_kwargs = mock_collect_fn.call_args.kwargs
            assert call_kwargs["inputs"] == inputs
            assert call_kwargs["dest"] == dest
            output = stdout_capture.getvalue().strip()
            parsed = json.loads(output)
            assert parsed == expected_result


class TestCLIStatus:
    def test_cli_status_calls_queue_status_and_prints_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = os.path.join(tmpdir, "queue.txt")
            ledger_path = os.path.join(tmpdir, "log.jsonl")

            expected_result = {
                "items": [{"url": "https://www.instagram.com/reel/ABC123/", "state": "QUEUED", "error": None}],
                "status": "ok"
            }

            mock_status_fn = Mock(return_value=expected_result)
            mock_read = Mock(return_value="")
            mock_parse = Mock(return_value=[])

            stdout_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture):
                result = a3_cli.run_status(
                    queue_file=queue_file,
                    ledger_path=ledger_path,
                    queue_status_fn=mock_status_fn,
                    read_text_file=mock_read,
                    parse_json_lines=mock_parse,
                )

            assert result == expected_result
            mock_status_fn.assert_called_once_with(
                queue_file=queue_file,
                ledger_path=ledger_path,
                read_text_file=mock_read,
                parse_json_lines=mock_parse,
            )
            output = stdout_capture.getvalue().strip()
            parsed = json.loads(output)
            assert parsed == expected_result


class TestCLIMain:
    def test_build_parser_returns_parser_with_correct_commands(self):
        result = a3_cli.build_parser()
        assert result["status"] == "ok"
        parser = result["parser"]
        assert isinstance(parser, argparse.ArgumentParser)
        
        # Test add-link subcommand
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = os.path.join(tmpdir, "q.txt")
            ns = parser.parse_args(["add-link", "https://ig.com/reel/ABC/", "--queue-file", queue_file])
            assert ns.command == "add_link"
            assert ns.urls == ["https://ig.com/reel/ABC/"]
            assert ns.queue_file == queue_file
        
        # Test collect subcommand
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = os.path.join(tmpdir, "vid.mp4")
            dest_dir = os.path.join(tmpdir, "dest")
            os.makedirs(dest_dir, exist_ok=True)
            ns = parser.parse_args(["collect", src_file, "--dest", dest_dir])
            assert ns.command == "collect"
            assert ns.inputs == [src_file]
            assert ns.dest == dest_dir
        
        # Test status subcommand
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = os.path.join(tmpdir, "q.txt")
            ledger_path = os.path.join(tmpdir, "log.jsonl")
            ns = parser.parse_args(["status", "--queue-file", queue_file, "--ledger", ledger_path])
            assert ns.command == "status"
            assert ns.queue_file == queue_file
            assert ns.ledger == ledger_path

    def test_cli_invalid_subcommand_shows_usage(self):
        argv = ["invalid-command"]
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        dummies = {name: Mock() for name in [
            "build_parser", "run_add_link", "run_collect", "run_status",
            "read_text_file", "write_text_file", "clock_now", "normalize_reel_url",
            "sha256_file", "copy_file", "make_dirs", "list_dir", "is_file",
            "is_dir", "get_size", "extract_zip_safe", "open_zip", "get_zip_info",
            "extract_member", "parse_json_lines", "queue_links_fn", "collect_inputs_fn", "queue_status_fn"
        ]}
        dummies["build_parser"] = a3_cli.build_parser

        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            exit_code = a3_cli.main(argv, **dummies)

        assert exit_code == 2
        stderr_output = stderr_capture.getvalue()
        assert "usage:" in stderr_output.lower() or "usage:" in stdout_capture.getvalue().lower()

    def test_main_add_link_real_runner_with_temp_queue(self):
        """Test main with real run_add_link and temp queue file, verifying argv reaches queue_links_fn."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = os.path.join(tmpdir, "queue.txt")
            argv = ["add-link", "https://instagram.com/reel/NEW789/", "--queue-file", queue_file]
            expected_result = {"added": ["https://www.instagram.com/reel/NEW789/"], "already_queued": [], "rejected": [], "status": "ok"}

            captured_kwargs = {}

            def mock_queue_links_fn(**kw):
                captured_kwargs.update(kw)
                # Write to the queue file to verify it's used
                with open(kw["queue_file"], "w") as f:
                    f.write("test")
                return expected_result

            def mock_normalize(url):
                return "https://www.instagram.com/reel/NEW789/"

            def mock_clock():
                return "2024-01-15T10:30:00Z"

            def mock_write(path, content):
                pass

            dummies = {name: Mock() for name in [
                "build_parser", "run_collect", "run_status",
                "read_text_file", "write_text_file", "clock_now", "normalize_reel_url",
                "sha256_file", "copy_file", "make_dirs", "list_dir", "is_file",
                "is_dir", "get_size", "extract_zip_safe", "open_zip", "get_zip_info",
                "extract_member", "parse_json_lines", "queue_links_fn", "collect_inputs_fn", "queue_status_fn"
            ]}
            dummies["build_parser"] = a3_cli.build_parser
            dummies["run_add_link"] = a3_cli.run_add_link
            dummies["queue_links_fn"] = mock_queue_links_fn
            dummies["normalize_reel_url"] = mock_normalize
            dummies["clock_now"] = mock_clock
            dummies["write_text_file"] = mock_write

            stdout_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture):
                exit_code = a3_cli.main(argv, **dummies)

            assert exit_code == 0
            assert captured_kwargs["queue_file"] == queue_file
            assert captured_kwargs["urls"] == ["https://instagram.com/reel/NEW789/"]
            # Verify the queue file was written to
            assert os.path.exists(queue_file)
            with open(queue_file) as f:
                assert f.read() == "test"
            output = stdout_capture.getvalue().strip()
            parsed = json.loads(output)
            assert parsed == expected_result

    def test_main_add_link_returns_exit_code_1_on_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = os.path.join(tmpdir, "queue.txt")
            argv = ["add-link", "https://instagram.com/reel/BAD/", "--queue-file", queue_file]
            expected_result = {"added": [], "already_queued": [], "rejected": ["https://instagram.com/reel/BAD/"], "status": "ok"}

            mock_run_add_link = Mock(return_value=expected_result)
            dummies = {name: Mock() for name in [
                "build_parser", "run_collect", "run_status",
                "read_text_file", "write_text_file", "clock_now", "normalize_reel_url",
                "sha256_file", "copy_file", "make_dirs", "list_dir", "is_file",
                "is_dir", "get_size", "extract_zip_safe", "open_zip", "get_zip_info",
                "extract_member", "parse_json_lines", "queue_links_fn", "collect_inputs_fn", "queue_status_fn"
            ]}
            dummies["build_parser"] = a3_cli.build_parser
            dummies["run_add_link"] = mock_run_add_link
            dummies["queue_links_fn"] = Mock()

            stdout_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture):
                exit_code = a3_cli.main(argv, **dummies)

            assert exit_code == 1

    def test_main_add_link_returns_exit_code_1_on_error_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = os.path.join(tmpdir, "queue.txt")
            argv = ["add-link", "https://instagram.com/reel/ERR/", "--queue-file", queue_file]
            expected_result = {"added": [], "already_queued": [], "rejected": [], "status": "error"}

            mock_run_add_link = Mock(return_value=expected_result)
            dummies = {name: Mock() for name in [
                "build_parser", "run_collect", "run_status",
                "read_text_file", "write_text_file", "clock_now", "normalize_reel_url",
                "sha256_file", "copy_file", "make_dirs", "list_dir", "is_file",
                "is_dir", "get_size", "extract_zip_safe", "open_zip", "get_zip_info",
                "extract_member", "parse_json_lines", "queue_links_fn", "collect_inputs_fn", "queue_status_fn"
            ]}
            dummies["build_parser"] = a3_cli.build_parser
            dummies["run_add_link"] = mock_run_add_link
            dummies["queue_links_fn"] = Mock()

            stdout_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture):
                exit_code = a3_cli.main(argv, **dummies)

            assert exit_code == 1

    def test_main_collect_real_runner_with_temp_dirs(self):
        """Test main with real run_collect and temp dirs, verifying argv reaches collect_inputs_fn."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = os.path.join(tmpdir, "video.mp4")
            with open(src_file, "wb") as f:
                f.write(b"fake video content")
            dest_dir = os.path.join(tmpdir, "dest")
            os.makedirs(dest_dir, exist_ok=True)

            argv = ["collect", src_file, "--dest", dest_dir]
            expected_result = {"copied": [os.path.join(dest_dir, "video.mp4")], "duplicates": [], "rejected": [], "status": "ok"}

            captured_kwargs = {}

            def mock_collect_inputs_fn(**kw):
                captured_kwargs.update(kw)
                return expected_result

            dummy = Mock()

            dummies = {name: Mock() for name in [
                "build_parser", "run_add_link", "run_status",
                "read_text_file", "write_text_file", "clock_now", "normalize_reel_url",
                "sha256_file", "copy_file", "make_dirs", "list_dir", "is_file",
                "is_dir", "get_size", "extract_zip_safe", "open_zip", "get_zip_info",
                "extract_member", "parse_json_lines", "queue_links_fn", "collect_inputs_fn", "queue_status_fn"
            ]}
            dummies["build_parser"] = a3_cli.build_parser
            dummies["run_collect"] = a3_cli.run_collect
            dummies["collect_inputs_fn"] = mock_collect_inputs_fn
            dummies["sha256_file"] = dummy
            dummies["copy_file"] = dummy
            dummies["make_dirs"] = dummy
            dummies["list_dir"] = dummy
            dummies["is_file"] = dummy
            dummies["is_dir"] = dummy
            dummies["get_size"] = dummy
            dummies["extract_zip_safe"] = dummy

            stdout_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture):
                exit_code = a3_cli.main(argv, **dummies)

            assert exit_code == 0
            assert captured_kwargs["inputs"] == [src_file]
            assert captured_kwargs["dest"] == dest_dir
            output = stdout_capture.getvalue().strip()
            parsed = json.loads(output)
            assert parsed == expected_result

    def test_main_collect_returns_exit_code_1_on_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = os.path.join(tmpdir, "bad.mp4")
            dest_dir = os.path.join(tmpdir, "dest")
            os.makedirs(dest_dir, exist_ok=True)
            argv = ["collect", src_file, "--dest", dest_dir]
            expected_result = {"copied": [], "duplicates": [], "rejected": [src_file], "status": "ok"}

            mock_run_collect = Mock(return_value=expected_result)
            dummies = {name: Mock() for name in [
                "build_parser", "run_add_link", "run_status",
                "read_text_file", "write_text_file", "clock_now", "normalize_reel_url",
                "sha256_file", "copy_file", "make_dirs", "list_dir", "is_file",
                "is_dir", "get_size", "extract_zip_safe", "open_zip", "get_zip_info",
                "extract_member", "parse_json_lines", "queue_links_fn", "collect_inputs_fn", "queue_status_fn"
            ]}
            dummies["build_parser"] = a3_cli.build_parser
            dummies["run_collect"] = mock_run_collect
            dummies["collect_inputs_fn"] = Mock()

            stdout_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture):
                exit_code = a3_cli.main(argv, **dummies)

            assert exit_code == 1

    def test_main_collect_returns_exit_code_1_on_error_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = os.path.join(tmpdir, "err.mp4")
            dest_dir = os.path.join(tmpdir, "dest")
            os.makedirs(dest_dir, exist_ok=True)
            argv = ["collect", src_file, "--dest", dest_dir]
            expected_result = {"copied": [], "duplicates": [], "rejected": [], "status": "error"}

            mock_run_collect = Mock(return_value=expected_result)
            dummies = {name: Mock() for name in [
                "build_parser", "run_add_link", "run_status",
                "read_text_file", "write_text_file", "clock_now", "normalize_reel_url",
                "sha256_file", "copy_file", "make_dirs", "list_dir", "is_file",
                "is_dir", "get_size", "extract_zip_safe", "open_zip", "get_zip_info",
                "extract_member", "parse_json_lines", "queue_links_fn", "collect_inputs_fn", "queue_status_fn"
            ]}
            dummies["build_parser"] = a3_cli.build_parser
            dummies["run_collect"] = mock_run_collect
            dummies["collect_inputs_fn"] = Mock()

            stdout_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture):
                exit_code = a3_cli.main(argv, **dummies)

            assert exit_code == 1

    def test_main_status_real_runner_with_temp_files(self):
        """Test main with real run_status and temp files, verifying argv reaches queue_status_fn."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = os.path.join(tmpdir, "queue.txt")
            ledger_path = os.path.join(tmpdir, "log.jsonl")
            argv = ["status", "--queue-file", queue_file, "--ledger", ledger_path]
            expected_result = {"items": [{"url": "https://www.instagram.com/reel/ABC123/", "state": "QUEUED", "error": None}], "status": "ok"}

            captured_kwargs = {}

            def mock_queue_status_fn(**kw):
                captured_kwargs.update(kw)
                return expected_result

            def mock_read(path):
                return ""

            def mock_parse(content):
                return []

            dummies = {name: Mock() for name in [
                "build_parser", "run_add_link", "run_collect",
                "read_text_file", "write_text_file", "clock_now", "normalize_reel_url",
                "sha256_file", "copy_file", "make_dirs", "list_dir", "is_file",
                "is_dir", "get_size", "extract_zip_safe", "open_zip", "get_zip_info",
                "extract_member", "parse_json_lines", "queue_links_fn", "collect_inputs_fn", "queue_status_fn"
            ]}
            dummies["build_parser"] = a3_cli.build_parser
            dummies["run_status"] = a3_cli.run_status
            dummies["queue_status_fn"] = mock_queue_status_fn
            dummies["read_text_file"] = mock_read
            dummies["parse_json_lines"] = mock_parse

            stdout_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture):
                exit_code = a3_cli.main(argv, **dummies)

            assert exit_code == 0
            assert captured_kwargs["queue_file"] == queue_file
            assert captured_kwargs["ledger_path"] == ledger_path
            output = stdout_capture.getvalue().strip()
            parsed = json.loads(output)
            assert parsed == expected_result

    def test_main_status_returns_exit_code_1_on_failed_inaccessible_item(self):
        """Test that status returns exit_code 1 when any item has FAILED_INACCESSIBLE state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = os.path.join(tmpdir, "queue.txt")
            ledger_path = os.path.join(tmpdir, "log.jsonl")
            argv = ["status", "--queue-file", queue_file, "--ledger", ledger_path]
            expected_result = {
                "items": [{"url": "https://www.instagram.com/reel/ABC123/", "state": "FAILED_INACCESSIBLE", "error": "permission denied"}],
                "status": "ok"
            }

            def mock_queue_status_fn(**kw):
                return expected_result

            def mock_read(path):
                return ""

            def mock_parse(content):
                return []

            dummies = {name: Mock() for name in [
                "build_parser", "run_add_link", "run_collect",
                "read_text_file", "write_text_file", "clock_now", "normalize_reel_url",
                "sha256_file", "copy_file", "make_dirs", "list_dir", "is_file",
                "is_dir", "get_size", "extract_zip_safe", "open_zip", "get_zip_info",
                "extract_member", "parse_json_lines", "queue_links_fn", "collect_inputs_fn", "queue_status_fn"
            ]}
            dummies["build_parser"] = a3_cli.build_parser
            dummies["run_status"] = a3_cli.run_status
            dummies["queue_status_fn"] = mock_queue_status_fn
            dummies["read_text_file"] = mock_read
            dummies["parse_json_lines"] = mock_parse

            stdout_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture):
                exit_code = a3_cli.main(argv, **dummies)

            assert exit_code == 1
            output = stdout_capture.getvalue().strip()
            parsed = json.loads(output)
            assert parsed == expected_result

    def test_main_status_returns_exit_code_1_on_error_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = os.path.join(tmpdir, "q.txt")
            ledger_path = os.path.join(tmpdir, "log.jsonl")
            argv = ["status", "--queue-file", queue_file, "--ledger", ledger_path]
            expected_result = {"items": [], "status": "error"}

            mock_run_status = Mock(return_value=expected_result)
            dummies = {name: Mock() for name in [
                "build_parser", "run_add_link", "run_collect",
                "read_text_file", "write_text_file", "clock_now", "normalize_reel_url",
                "sha256_file", "copy_file", "make_dirs", "list_dir", "is_file",
                "is_dir", "get_size", "extract_zip_safe", "open_zip", "get_zip_info",
                "extract_member", "parse_json_lines", "queue_links_fn", "collect_inputs_fn", "queue_status_fn"
            ]}
            dummies["build_parser"] = a3_cli.build_parser
            dummies["run_status"] = mock_run_status
            dummies["queue_status_fn"] = Mock()

            stdout_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture):
                exit_code = a3_cli.main(argv, **dummies)

            assert exit_code == 1

    def test_main_help_returns_exit_code_0(self):
        argv = ["--help"]
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        dummies = {name: Mock() for name in [
            "build_parser", "run_add_link", "run_collect", "run_status",
            "read_text_file", "write_text_file", "clock_now", "normalize_reel_url",
            "sha256_file", "copy_file", "make_dirs", "list_dir", "is_file",
            "is_dir", "get_size", "extract_zip_safe", "open_zip", "get_zip_info",
            "extract_member", "parse_json_lines", "queue_links_fn", "collect_inputs_fn", "queue_status_fn"
        ]}
        dummies["build_parser"] = a3_cli.build_parser

        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            exit_code = a3_cli.main(argv, **dummies)

        assert exit_code == 0
