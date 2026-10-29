import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the module under test
sys.path.insert(0, str(Path(__file__).parent))
from g2_autoloop_cli import (  # noqa: E402
    REPO,
    TOOLS,
    MODULE_OF,
    STATE_FILE,
    build_deps,
    main,
    _read_state_file,
    _write_state_file,
    _default_runner,
)
from g1_autoloop import decide, run_cycles  # noqa: E402


class FakeCompletedProcess:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class RecordingRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, argv, cwd=None, background=False):
        self.calls.append({"argv": list(argv), "cwd": cwd, "background": background})
        # Default: pytest passes (returncode 0)
        if "pytest" in argv:
            return FakeCompletedProcess(0)
        return FakeCompletedProcess(0)


def noop_sleep(seconds: int) -> None:
    pass


def test_get_state_reads_status_json_and_runs_pytest(tmp_path):
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    # Create status.json with state "running"
    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "running"}), encoding="utf-8")

    # Create module and test files
    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    state = deps["get_state"]("wpA1")

    assert state["job"] == "running"
    assert state["tests_green"] is True
    # Check pytest was called with exact argv
    pytest_calls = [c for c in runner.calls if "pytest" in c["argv"]]
    assert len(pytest_calls) == 1
    assert pytest_calls[0]["argv"] == [
        "uv",
        "run",
        "python",
        "-m",
        "pytest",
        "-q",
        "--tb=no",
        "research/pieces/test_a1_queue.py",
    ]
    assert pytest_calls[0]["cwd"] == repo
    assert pytest_calls[0]["background"] is False


def test_get_state_missing_status_json_returns_missing(tmp_path):
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    state = deps["get_state"]("wpA1")

    assert state["job"] == "missing"


def test_get_state_corrupt_status_json_returns_missing(tmp_path):
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True)
    (status_dir / "status.json").write_text("not json", encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    state = deps["get_state"]("wpA1")

    assert state["job"] == "missing"


def test_get_state_tests_green_false_when_pytest_fails(tmp_path):
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"

    class FailingRunner:
        def __call__(self, argv, cwd=None, background=False):
            if "pytest" in argv:
                return FakeCompletedProcess(1)
            return FakeCompletedProcess(0)

    runner = FailingRunner()

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    state = deps["get_state"]("wpA1")

    assert state["tests_green"] is False


def test_state_file_corrupt_raises_value_error(tmp_path):
    repo = tmp_path
    state_file = repo / "autoloop_state.json"
    state_file.write_text("not json", encoding="utf-8")

    with patch("g2_autoloop_cli.STATE_FILE", state_file):
        with pytest.raises(ValueError, match="Corrupt state file"):
            _read_state_file()


def test_relaunch_removes_job_dir_and_calls_fix_loop_with_background(tmp_path):
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    job_dir = repo / "_loop" / "research_wpA1"
    job_dir.mkdir(parents=True)
    (job_dir / "some_file.txt").write_text("data", encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    deps["relaunch"]("wpA1")

    assert not job_dir.exists()
    relaunch_calls = [c for c in runner.calls if any("fix_loop_stable.py" in arg for arg in c["argv"])]
    assert len(relaunch_calls) == 1
    assert relaunch_calls[0]["argv"] == [
        "uv",
        "run",
        "python",
        "scripts/source/fix_loop_stable.py",
        "--job",
        "_loop/jobs/research_wpA1.json",
    ]
    assert relaunch_calls[0]["cwd"] == repo
    assert relaunch_calls[0]["background"] is True


def test_run_reviewers_parses_combined_file_with_findings(tmp_path):
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    reviews_dir.mkdir(parents=True)

    runner = RecordingRunner()

    combined_content = """## LUNA
Found issue A.

## GLM 5.3 Flash
Found issue B.

## MiniMax M3.1 Flash
Found issue C.
"""
    (reviews_dir / "combined_wpA1.md").write_text(combined_content, encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    result = deps["run_reviewers"]("wpA1")

    assert result["luna"] == "Found issue A."
    assert result["glm"] == "Found issue B."
    assert result["minimax"] == "Found issue C."

    reviewer_calls = [c for c in runner.calls if any("luna_review.py" in arg for arg in c["argv"])]
    assert len(reviewer_calls) == 1
    assert reviewer_calls[0]["argv"] == [
        "python",
        str(tools / "luna_review.py"),
        "wpA1",
    ]


def test_run_reviewers_absent_reviewer_returns_pass(tmp_path):
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    reviews_dir.mkdir(parents=True)

    runner = RecordingRunner()

    # Only LUNA has findings
    combined_content = """## LUNA
Found issue A.
"""
    (reviews_dir / "combined_wpA1.md").write_text(combined_content, encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    result = deps["run_reviewers"]("wpA1")

    assert result["luna"] == "Found issue A."
    assert result["glm"] == "PASS"
    assert result["minimax"] == "PASS"


def test_run_reviewers_failed_run_returns_no_review(tmp_path):
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"

    class FailingRunner:
        def __call__(self, argv, cwd=None, background=False):
            return FakeCompletedProcess(1)

    runner = FailingRunner()

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    result = deps["run_reviewers"]("wpA1")

    assert result["luna"] == "NO_REVIEW"
    assert result["glm"] == "NO_REVIEW"
    assert result["minimax"] == "NO_REVIEW"


def test_apply_findings_writes_auto_file_and_calls_apply_review(tmp_path):
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    deps["apply_findings"]("wpA1", "Some findings text")

    auto_file = reviews_dir / "auto_wpA1.md"
    assert auto_file.exists()
    assert auto_file.read_text(encoding="utf-8") == "Some findings text"

    apply_calls = [c for c in runner.calls if any("apply_review.py" in arg for arg in c["argv"])]
    assert len(apply_calls) == 1
    assert apply_calls[0]["argv"] == [
        "python",
        str(tools / "apply_review.py"),
        str(auto_file),
        "wpA1",
    ]
    assert apply_calls[0]["cwd"] == repo
    assert apply_calls[0]["background"] is False


def test_escalate_calls_diagnose_with_prompt_and_writes_diag_file(tmp_path):
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    # Create ESCALATE.md
    escalate_dir = repo / "_loop" / "research_wpA1"
    escalate_dir.mkdir(parents=True)
    (escalate_dir / "ESCALATE.md").write_text("Escalation details", encoding="utf-8")

    # Create spec
    spec_dir = repo / "docs" / "pilot" / "nemotron_specs"
    spec_dir.mkdir(parents=True)
    (spec_dir / "research_wpA1.md").write_text("Spec content", encoding="utf-8")

    # Create module and test
    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("module code", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("test code", encoding="utf-8")

    diagnose_calls = []

    def fake_diagnose(prompt: str) -> str:
        diagnose_calls.append(prompt)
        return "Diagnosis result"

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    deps["escalate"]("wpA1", fake_diagnose)

    # Check diagnose was called with prompt containing ESCALATE.md text
    assert len(diagnose_calls) == 1
    prompt = diagnose_calls[0]
    assert "Escalation details" in prompt
    assert "Spec content" in prompt
    assert "module code" in prompt
    assert "test code" in prompt

    # Check diag file written
    diag_file = reviews_dir / "diag_wpA1.md"
    assert diag_file.exists()
    assert diag_file.read_text(encoding="utf-8") == "Diagnosis result"

    # Check apply_review called with diag file
    apply_calls = [c for c in runner.calls if any("apply_review.py" in arg for arg in c["argv"])]
    assert len(apply_calls) == 1
    assert apply_calls[0]["argv"] == [
        "python",
        str(tools / "apply_review.py"),
        str(diag_file),
        "wpA1",
    ]


def test_escalate_increments_escalations_in_state(tmp_path):
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    escalate_dir = repo / "_loop" / "research_wpA1"
    escalate_dir.mkdir(parents=True)
    (escalate_dir / "ESCALATE.md").write_text("Escalation", encoding="utf-8")

    spec_dir = repo / "docs" / "pilot" / "nemotron_specs"
    spec_dir.mkdir(parents=True)
    (spec_dir / "research_wpA1.md").write_text("Spec", encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("test", encoding="utf-8")

    def fake_diagnose(prompt: str) -> str:
        return "Diag"

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    deps["escalate"]("wpA1", fake_diagnose)
    deps["escalate"]("wpA1", fake_diagnose)

    # Check state file has escalations=2
    state_file = repo / "_loop" / "autoloop_state.json"
    state_data = _read_state_file(state_file)
    assert state_data["wpA1"]["escalations"] == 2


def test_main_dry_run_prints_json_and_only_calls_pytest(tmp_path):
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"

    runner = RecordingRunner()

    # Create status.json for wpA1
    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "running"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    with patch("g2_autoloop_cli.REPO", repo), \
         patch("g2_autoloop_cli.TOOLS", tools):
        exit_code = main(["--ids", "wpA1", "--dry-run"], runner=runner)

    assert exit_code == 0

    # Only pytest should have been called (for tests_green)
    pytest_calls = [c for c in runner.calls if "pytest" in c["argv"]]
    assert len(pytest_calls) == 1

    # No relaunch, reviewers, apply, or escalate calls
    for call in runner.calls:
        argv = call["argv"]
        assert "fix_loop_stable.py" not in argv
        assert "luna_review.py" not in argv
        assert "apply_review.py" not in argv


def test_main_dry_run_output_is_valid_json(tmp_path):
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"

    runner = RecordingRunner()

    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "passed"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    import io
    from contextlib import redirect_stdout

    with patch("g2_autoloop_cli.REPO", repo), \
         patch("g2_autoloop_cli.TOOLS", tools):
        f = io.StringIO()
        with redirect_stdout(f):
            main(["--ids", "wpA1", "--dry-run"], runner=runner)
        output = f.getvalue().strip()

    parsed = json.loads(output)
    assert "wpA1" in parsed
    assert "action" in parsed["wpA1"]
    assert "job" in parsed["wpA1"]
    assert "tests_green" in parsed["wpA1"]


def test_main_non_dry_run_calls_run_cycles_and_returns_exit_code(tmp_path):
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"

    runner = RecordingRunner()

    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "passed"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    # Mock run_cycles to return a report
    with patch("g2_autoloop_cli.run_cycles") as mock_run_cycles, \
         patch("g2_autoloop_cli.REPO", repo), \
         patch("g2_autoloop_cli.TOOLS", tools):
        mock_run_cycles.return_value = {"wpA1": {"stuck": False, "cycles": 1}}
        exit_code = main(["--ids", "wpA1", "--max-cycles", "1"], runner=runner)

    assert exit_code == 0
    mock_run_cycles.assert_called_once()


def test_main_returns_1_when_piece_stuck(tmp_path):
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"

    runner = RecordingRunner()

    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "passed"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    with patch("g2_autoloop_cli.run_cycles") as mock_run_cycles, \
         patch("g2_autoloop_cli.REPO", repo), \
         patch("g2_autoloop_cli.TOOLS", tools):
        mock_run_cycles.return_value = {"wpA1": {"stuck": True, "cycles": 50}}
        exit_code = main(["--ids", "wpA1", "--max-cycles", "50"], runner=runner)

    assert exit_code == 1


def test_no_argv_contains_shell_strings(tmp_path):
    """Ensure no argv uses shell=True patterns (no '&&', '|', ';', etc.)"""
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "running"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    deps["get_state"]("wpA1")
    deps["relaunch"]("wpA1")
    deps["run_reviewers"]("wpA1")
    deps["apply_findings"]("wpA1", "text")
    deps["escalate"]("wpA1", lambda p: "diag")

    shell_chars = ["&&", "||", "|", ";", "`", "$(", ">", "<"]
    for call in runner.calls:
        for arg in call["argv"]:
            for ch in shell_chars:
                assert ch not in arg, f"Shell character {ch!r} found in argv: {call['argv']}"


def test_get_state_computes_changed_since_review_from_mtimes(tmp_path):
    """changed_since_review should be True only if module or test mtime > last_review."""
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    # Create status.json with state "passed"
    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True, exist_ok=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "passed"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    module_path = pieces_dir / "a1_queue.py"
    test_path = pieces_dir / "test_a1_queue.py"
    module_path.write_text("# module", encoding="utf-8")
    test_path.write_text("# test", encoding="utf-8")

    # Set up autoloop state with last_review timestamp older than files
    state_file = repo / "_loop" / "autoloop_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    # Use a timestamp far in the past
    old_time = 1000000000.0
    _write_state_file(state_file, {"wpA1": {"last_review": old_time, "escalations": 0}})

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    state = deps["get_state"]("wpA1")

    # Files are newer than old_time, so changed_since_review should be True
    assert state["changed_since_review"] is True

    # Now set last_review to a future time (newer than files)
    future_time = 9999999999.0
    _write_state_file(state_file, {"wpA1": {"last_review": future_time, "escalations": 0}})
    state2 = deps["get_state"]("wpA1")
    assert state2["changed_since_review"] is False


def test_get_state_no_last_review_means_changed_true(tmp_path):
    """When last_review is None, changed_since_review should be True."""
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "passed"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    # No autoloop state file -> last_review is None
    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    state = deps["get_state"]("wpA1")
    assert state["last_review"] is None
    assert state["changed_since_review"] is True


def test_dry_run_wpD4_missing_job_and_failing_tests(tmp_path):
    """wpD4 has no job directory and 2 failing tests -> RELAUNCH."""
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    # No status.json for wpD4
    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "d4_reconstruct.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_d4_reconstruct.py").write_text("# test", encoding="utf-8")

    class FailingRunner:
        def __call__(self, argv, cwd=None, background=False):
            if "pytest" in argv:
                return FakeCompletedProcess(1)
            return FakeCompletedProcess(0)

    runner = FailingRunner()
    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    state = deps["get_state"]("wpD4")
    action = decide(state)

    assert state["job"] == "missing"
    assert state["tests_green"] is False
    assert action == "RELAUNCH"


def test_dry_run_wpD2_running_job(tmp_path):
    """wpD2 has a RUNNING job -> WAIT."""
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    status_dir = repo / "_loop" / "research_wpD2"
    status_dir.mkdir(parents=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "running"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "d2_recipe_compiler.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_d2_recipe_compiler.py").write_text("# test", encoding="utf-8")

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    state = deps["get_state"]("wpD2")
    action = decide(state)

    assert state["job"] == "running"
    assert action == "WAIT"


def test_dry_run_passed_no_review_green_tests_no_review(tmp_path):
    """Piece with job 'passed-no-review' and green tests, no current review -> REVIEW."""
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "passed-no-review"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    state = deps["get_state"]("wpA1")
    action = decide(state)

    assert state["job"] == "passed-no-review"
    assert state["tests_green"] is True
    assert state["last_review"] is None
    assert action == "REVIEW"


def test_dry_run_escalate_job(tmp_path):
    """Piece with job 'escalate' -> ESCALATE."""
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "escalate"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    state = deps["get_state"]("wpA1")
    action = decide(state)

    assert state["job"] == "escalate"
    assert action == "ESCALATE"


def test_end_to_end_get_state_decide_for_each_real_state(tmp_path):
    """Write tmp status.json files with each real state and check get_state + decide."""
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    # We'll test each state by writing status.json and checking decide
    states_and_expected = [
        ("running", True, "WAIT"),
        ("missing", True, "RELAUNCH"),
        ("failed", True, "RELAUNCH"),
        ("escalate", True, "ESCALATE"),
        ("passed", False, "FIX_TESTS"),
        ("passed-no-review", False, "FIX_TESTS"),
        ("passed", True, "REVIEW"),  # no last_review
        ("passed-no-review", True, "REVIEW"),  # no last_review
    ]

    for job_state, tests_green, expected_action in states_and_expected:
        status_dir = repo / "_loop" / "research_wpA1"
        status_dir.mkdir(parents=True, exist_ok=True)
        (status_dir / "status.json").write_text(json.dumps({"state": job_state}), encoding="utf-8")

        if not tests_green:
            # Make pytest fail
            class FailingRunner:
                def __call__(self, argv, cwd=None, background=False):
                    if "pytest" in argv:
                        return FakeCompletedProcess(1)
                    return FakeCompletedProcess(0)
            runner = FailingRunner()
        else:
            runner = RecordingRunner()

        deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
        state = deps["get_state"]("wpA1")
        action = decide(state)
        assert state["job"] == job_state
        assert state["tests_green"] == tests_green
        assert action == expected_action, f"For job={job_state}, tests_green={tests_green}: expected {expected_action}, got {action}"


def test_escalation_reset_on_passed_and_green_tests(tmp_path):
    """Escalation counter should be reset to 0 when job is passed/passed-no-review and tests green."""
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    # Create status.json with state "passed"
    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True, exist_ok=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "passed"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    # Pre-populate state file with escalations=4
    state_file = repo / "_loop" / "autoloop_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    _write_state_file(state_file, {"wpA1": {"escalations": 4, "last_review": 1234567890.0}})

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)
    state = deps["get_state"]("wpA1")

    # Escalations should be reset to 0
    assert state["escalations"] == 0
    # State file should be updated
    updated_state = _read_state_file(state_file)
    assert updated_state["wpA1"]["escalations"] == 0


def test_end_to_end_run_cycles_with_build_deps_calls_sleep(tmp_path):
    """Integration test: run_cycles with build_deps, fake runner, recording sleep."""
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "running"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    sleep_calls = []
    def recording_sleep(seconds):
        sleep_calls.append(seconds)

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=recording_sleep)
    # Run one cycle
    report = run_cycles(["wpA1"], deps, max_cycles=1, sleep_s=42)

    assert report["cycles"] == 1
    assert sleep_calls == [42]
    # No runner calls except pytest (for tests_green)
    pytest_calls = [c for c in runner.calls if "pytest" in c["argv"]]
    assert len(pytest_calls) == 1


def test_stale_escalations_reset_and_not_stuck(tmp_path):
    """Stale escalations=4 should be reset, piece should not be marked STUCK."""
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    # Status: passed, tests green
    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True, exist_ok=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "passed"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    # Pre-populate state file with escalations=4
    state_file = repo / "_loop" / "autoloop_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    _write_state_file(state_file, {"wpA1": {"escalations": 4, "last_review": 1234567890.0}})

    sleep_calls = []
    def recording_sleep(seconds):
        sleep_calls.append(seconds)

    deps = build_deps(repo, tools, runner, reviews_dir, sleep=recording_sleep)
    # Run one cycle
    report = run_cycles(["wpA1"], deps, max_cycles=1, sleep_s=5)

    # Piece should be DONE (since passed, tests green, no review -> REVIEW, but then next cycle? Actually decide returns REVIEW for passed+green+no review.
    # But run_cycles only runs one cycle, so it will do REVIEW action (call run_reviewers) and then sleep.
    # The piece is not done or stuck after one cycle.
    assert "wpA1" not in report["done"]
    assert "wpA1" not in report["stuck"]
    assert report["cycles"] == 1
    # Sleep called once
    assert sleep_calls == [5]
    # run_reviewers should have been called
    reviewer_calls = [c for c in runner.calls if any("luna_review.py" in arg for arg in c["argv"])]
    assert len(reviewer_calls) == 1


# --- NEW TESTS FOR --state-file ---

def test_custom_state_path_used_and_default_not_created(tmp_path):
    """Custom state_path is used for read/write; default file is not created."""
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    # Create status.json for wpA1
    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "passed"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    custom_state = tmp_path / "custom_state.json"
    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep, state_path=custom_state)

    # Trigger a write via escalate
    escalate_dir = repo / "_loop" / "research_wpA1"
    escalate_dir.mkdir(parents=True, exist_ok=True)
    (escalate_dir / "ESCALATE.md").write_text("Escalation", encoding="utf-8")
    spec_dir = repo / "docs" / "pilot" / "nemotron_specs"
    spec_dir.mkdir(parents=True)
    (spec_dir / "research_wpA1.md").write_text("Spec", encoding="utf-8")

    def fake_diagnose(prompt: str) -> str:
        return "Diag"

    deps["escalate"]("wpA1", fake_diagnose)

    # Custom state file should exist and have escalations=1
    assert custom_state.exists()
    custom_data = _read_state_file(custom_state)
    assert custom_data["wpA1"]["escalations"] == 1

    # Default state file should NOT exist
    default_state = repo / "_loop" / "autoloop_state.json"
    assert not default_state.exists()


def test_default_state_path_behavior_unchanged(tmp_path):
    """When state_path is None, default file is used."""
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "passed"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    # No state_path provided
    deps = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep)

    escalate_dir = repo / "_loop" / "research_wpA1"
    escalate_dir.mkdir(parents=True, exist_ok=True)
    (escalate_dir / "ESCALATE.md").write_text("Escalation", encoding="utf-8")
    spec_dir = repo / "docs" / "pilot" / "nemotron_specs"
    spec_dir.mkdir(parents=True)
    (spec_dir / "research_wpA1.md").write_text("Spec", encoding="utf-8")

    def fake_diagnose(prompt: str) -> str:
        return "Diag"

    deps["escalate"]("wpA1", fake_diagnose)

    default_state = repo / "_loop" / "autoloop_state.json"
    assert default_state.exists()
    default_data = _read_state_file(default_state)
    assert default_data["wpA1"]["escalations"] == 1


def test_main_parses_state_file_argument(tmp_path):
    """main() parses --state-file and passes it to build_deps."""
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"

    runner = RecordingRunner()

    status_dir = repo / "_loop" / "research_wpA1"
    status_dir.mkdir(parents=True)
    (status_dir / "status.json").write_text(json.dumps({"state": "passed"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")

    custom_state = tmp_path / "my_state.json"

    with patch("g2_autoloop_cli.REPO", repo), \
         patch("g2_autoloop_cli.TOOLS", tools), \
         patch("g2_autoloop_cli.build_deps") as mock_build_deps:
        mock_build_deps.return_value = {
            "get_state": lambda pid: {"job": "passed", "tests_green": True, "last_review": None, "changed_since_review": True, "escalations": 0},
            "relaunch": lambda pid: None,
            "run_reviewers": lambda pid: {"luna": "PASS", "glm": "PASS", "minimax": "PASS"},
            "apply_findings": lambda pid, text: None,
            "escalate": lambda pid, diagnose: None,
            "sleep": noop_sleep,
        }
        # Run with --state-file
        main(["--ids", "wpA1", "--dry-run", "--state-file", str(custom_state)], runner=runner)

        # Check build_deps was called with the custom state_path
        mock_build_deps.assert_called_once()
        call_kwargs = mock_build_deps.call_args.kwargs
        assert "state_path" in call_kwargs
        assert call_kwargs["state_path"] == custom_state


def test_two_loop_isolation(tmp_path):
    """Two loops with different state files never touch each other's file."""
    repo = tmp_path
    tools = tmp_path / "tools"
    reviews_dir = tmp_path / "reviews"
    runner = RecordingRunner()

    # Create status.json for two pieces
    for pid in ("wpA1", "wpB1"):
        status_dir = repo / "_loop" / f"research_{pid}"
        status_dir.mkdir(parents=True)
        (status_dir / "status.json").write_text(json.dumps({"state": "passed"}), encoding="utf-8")

    pieces_dir = repo / "research" / "pieces"
    pieces_dir.mkdir(parents=True)
    (pieces_dir / "a1_queue.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a1_queue.py").write_text("# test", encoding="utf-8")
    (pieces_dir / "a2_collect.py").write_text("# module", encoding="utf-8")
    (pieces_dir / "test_a2_collect.py").write_text("# test", encoding="utf-8")

    state_file_1 = tmp_path / "state1.json"
    state_file_2 = tmp_path / "state2.json"

    # Loop 1: escalate wpA1
    deps1 = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep, state_path=state_file_1)
    escalate_dir = repo / "_loop" / "research_wpA1"
    escalate_dir.mkdir(parents=True, exist_ok=True)
    (escalate_dir / "ESCALATE.md").write_text("Escalation A1", encoding="utf-8")
    spec_dir = repo / "docs" / "pilot" / "nemotron_specs"
    spec_dir.mkdir(parents=True)
    (spec_dir / "research_wpA1.md").write_text("Spec A1", encoding="utf-8")

    def fake_diagnose(prompt: str) -> str:
        return "Diag"

    deps1["escalate"]("wpA1", fake_diagnose)

    # Loop 2: escalate wpB1
    deps2 = build_deps(repo, tools, runner, reviews_dir, sleep=noop_sleep, state_path=state_file_2)
    escalate_dir_b = repo / "_loop" / "research_wpB1"
    escalate_dir_b.mkdir(parents=True, exist_ok=True)
    (escalate_dir_b / "ESCALATE.md").write_text("Escalation B1", encoding="utf-8")
    (spec_dir / "research_wpB1.md").write_text("Spec B1", encoding="utf-8")

    deps2["escalate"]("wpB1", fake_diagnose)

    # Check state1.json only has wpA1
    data1 = _read_state_file(state_file_1)
    assert "wpA1" in data1
    assert "wpB1" not in data1
    assert data1["wpA1"]["escalations"] == 1

    # Check state2.json only has wpB1
    data2 = _read_state_file(state_file_2)
    assert "wpB1" in data2
    assert "wpA1" not in data2
    assert data2["wpB1"]["escalations"] == 1

    # Default state file should not exist
    default_state = repo / "_loop" / "autoloop_state.json"
    assert not default_state.exists()


if __name__ == "__main__":
    pytest.main([__file__])
