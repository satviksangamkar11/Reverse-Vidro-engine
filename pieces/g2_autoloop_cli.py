import argparse
import json
import os
import sys
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Import g1_autoloop by path
sys.path.insert(0, str(Path(__file__).parent))
from g1_autoloop import run_cycles, decide, merge_findings  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO.parent / "animation_research_tool" / "_loop"

MODULE_OF = {
    "wpA1": "a1_queue",
    "wpA2": "a2_collect",
    "wpA3": "a3_cli",
    "wpB1": "a1_audio_io",
    "wpB2": "a2_transcribe",
    "wpB3": "a3_align",
    "wpC1": "c1_cluster",
    "wpC2": "c2_review",
    "wpC3": "c3_state",
    "wpD1": "d1_beat_schema",
    "wpD2": "d2_recipe_compiler",
    "wpD3": "d3_deliverables",
    "wpD4": "d4_reconstruct",
    "wpE1": "a1_scene_selection",
    "wpE2": "a2_recipe_prompts",
    "wpE3": "a3_blind_scoring",
    "wpF1": "f1_corpus",
    "wpF2": "f2_bias",
    "wpF3": "f3_publish",
    "wpF4": "f4_classify",
}

STATE_FILE = REPO / "_loop" / "autoloop_state.json"


def _read_state_file(path: Optional[Path] = None) -> Dict[str, Any]:
    if path is None:
        path = STATE_FILE
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Corrupt state file: {path}") from e


def _write_state_file(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False)
        tmp_path = Path(tmp.name)
    try:
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _get_module_and_test_paths(repo: Path, piece_id: str) -> tuple[Path, Path]:
    module_name = MODULE_OF[piece_id]
    module_path = repo / "research" / "pieces" / f"{module_name}.py"
    test_path = repo / "research" / "pieces" / f"test_{module_name}.py"
    return module_path, test_path


def build_deps(
    repo: Path,
    tools: Path,
    runner: Callable[..., subprocess.CompletedProcess],
    reviews_dir: Path,
    sleep: Callable[[int], None] = time.sleep,
    state_path: Optional[Path] = None,
) -> Dict[str, Callable]:
    if state_path is None:
        state_path = repo / "_loop" / "autoloop_state.json"

    def read_local_state() -> Dict[str, Any]:
        return _read_state_file(state_path)

    def write_local_state(data: Dict[str, Any]) -> None:
        _write_state_file(state_path, data)

    def get_state(piece_id: str) -> Dict[str, Any]:
        # Read status.json
        status_file = repo / "_loop" / f"research_{piece_id}" / "status.json"
        if status_file.exists():
            try:
                with status_file.open("r", encoding="utf-8") as f:
                    status_data = json.load(f)
                job = status_data.get("state", "missing")
            except (json.JSONDecodeError, OSError):
                job = "missing"
        else:
            job = "missing"

        # tests_green via pytest
        module_name = MODULE_OF[piece_id]
        pytest_argv = [
            "uv",
            "run",
            "python",
            "-m",
            "pytest",
            "-q",
            "--tb=no",
            f"research/pieces/test_{module_name}.py",
        ]
        result = runner(pytest_argv, cwd=repo)
        tests_green = result.returncode == 0

        # Read autoloop state
        autoloop_state = read_local_state()
        piece_state = autoloop_state.get(piece_id, {})

        last_review = piece_state.get("last_review")
        escalations = piece_state.get("escalations", 0)

        # Reset escalations if job is passed/passed-no-review and tests are green
        if job in ("passed", "passed-no-review") and tests_green and escalations != 0:
            piece_state["escalations"] = 0
            autoloop_state[piece_id] = piece_state
            write_local_state(autoloop_state)
            escalations = 0

        # Compute changed_since_review from mtimes
        if last_review is not None:
            module_path, test_path = _get_module_and_test_paths(repo, piece_id)
            try:
                module_mtime = module_path.stat().st_mtime if module_path.exists() else 0
                test_mtime = test_path.stat().st_mtime if test_path.exists() else 0
                newest_mtime = max(module_mtime, test_mtime)
                changed_since_review = newest_mtime > last_review
            except OSError:
                changed_since_review = True
        else:
            changed_since_review = True

        return {
            "job": job,
            "tests_green": tests_green,
            "last_review": last_review,
            "changed_since_review": changed_since_review,
            "escalations": escalations,
        }

    def relaunch(piece_id: str) -> None:
        job_dir = repo / "_loop" / f"research_{piece_id}"
        if job_dir.exists():
            import shutil
            shutil.rmtree(job_dir)

        relaunch_argv = [
            "uv",
            "run",
            "python",
            "scripts/source/fix_loop_stable.py",
            "--job",
            f"_loop/jobs/research_{piece_id}.json",
        ]
        runner(relaunch_argv, cwd=repo, background=True)

    def run_reviewers(piece_id: str) -> Dict[str, str]:
        reviewers_argv = ["python", str(tools / "luna_review.py"), piece_id]
        result = runner(reviewers_argv, cwd=repo)

        combined_file = reviews_dir / f"combined_{piece_id}.md"
        if result.returncode != 0 or not combined_file.exists():
            return {"luna": "NO_REVIEW", "glm": "NO_REVIEW", "minimax": "NO_REVIEW"}

        try:
            with combined_file.open("r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            return {"luna": "NO_REVIEW", "glm": "NO_REVIEW", "minimax": "NO_REVIEW"}

        # Parse by headings
        sections = {"luna": "", "glm": "", "minimax": ""}
        current = None
        for line in content.splitlines():
            if line.startswith("## LUNA"):
                current = "luna"
                continue
            elif line.startswith("## GLM 5.3 Flash"):
                current = "glm"
                continue
            elif line.startswith("## MiniMax M3.1 Flash"):
                current = "minimax"
                continue
            if current is not None:
                sections[current] += line + "\n"

        # If a section is empty, it means PASS (no findings); strip trailing whitespace
        for key in sections:
            stripped = sections[key].rstrip()
            if not stripped:
                sections[key] = "PASS"
            else:
                sections[key] = stripped

        return sections

    def apply_findings(piece_id: str, text: str) -> None:
        auto_file = reviews_dir / f"auto_{piece_id}.md"
        reviews_dir.mkdir(parents=True, exist_ok=True)
        with auto_file.open("w", encoding="utf-8") as f:
            f.write(text)

        apply_argv = [
            "python",
            str(tools / "apply_review.py"),
            str(auto_file),
            piece_id,
        ]
        runner(apply_argv, cwd=repo)

    def escalate(piece_id: str, diagnose: Callable[[str], str]) -> None:
        # Read ESCALATE.md
        escalate_file = repo / "_loop" / f"research_{piece_id}" / "ESCALATE.md"
        escalate_text = ""
        if escalate_file.exists():
            try:
                with escalate_file.open("r", encoding="utf-8") as f:
                    escalate_text = f.read()
            except OSError:
                pass

        # Read spec
        spec_file = repo / "docs" / "pilot" / "nemotron_specs" / f"research_{piece_id}.md"
        spec_text = ""
        if spec_file.exists():
            try:
                with spec_file.open("r", encoding="utf-8") as f:
                    spec_text = f.read()
            except OSError:
                pass

        # Read module and test
        module_path, test_path = _get_module_and_test_paths(repo, piece_id)
        module_text = ""
        test_text = ""
        if module_path.exists():
            try:
                with module_path.open("r", encoding="utf-8") as f:
                    module_text = f.read()
            except OSError:
                pass
        if test_path.exists():
            try:
                with test_path.open("r", encoding="utf-8") as f:
                    test_text = f.read()
            except OSError:
                pass

        # Build prompt
        prompt = f"""ESCALATE.md:
{escalate_text}

SPEC (research_{piece_id}.md):
{spec_text}

MODULE ({module_path.name}):
{module_text}

TEST (test_{module_path.name}):
{test_text}
"""
        diagnosis = diagnose(prompt)

        # Write diag file
        diag_file = reviews_dir / f"diag_{piece_id}.md"
        reviews_dir.mkdir(parents=True, exist_ok=True)
        with diag_file.open("w", encoding="utf-8") as f:
            f.write(diagnosis)

        # Apply like apply_findings
        apply_argv = [
            "python",
            str(tools / "apply_review.py"),
            str(diag_file),
            piece_id,
        ]
        runner(apply_argv, cwd=repo)

        # Increment escalations in state
        autoloop_state = read_local_state()
        piece_state = autoloop_state.get(piece_id, {})
        piece_state["escalations"] = piece_state.get("escalations", 0) + 1
        autoloop_state[piece_id] = piece_state
        write_local_state(autoloop_state)

    return {
        "get_state": get_state,
        "relaunch": relaunch,
        "run_reviewers": run_reviewers,
        "apply_findings": apply_findings,
        "escalate": escalate,
        "sleep": sleep,
    }


def _default_runner(
    argv: List[str],
    cwd: Optional[Path] = None,
    background: bool = False,
) -> subprocess.CompletedProcess:
    if background:
        creationflags = 0
        if sys.platform == "win32":
            creationflags = 0x08000000
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        class _FakeCompleted:
            returncode = 0
        return _FakeCompleted()
    else:
        return subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
        )


def _default_diagnose(prompt: str) -> str:
    # This is the untested default; tests always inject a fake
    try:
        sys.path.insert(0, str(REPO.parent / "animation_research_tool"))
        from nvidia_scheduler import NvidiaScheduler  # type: ignore
    except Exception:
        return "DIAGNOSIS_UNAVAILABLE: nvidia_scheduler not available"

    # Read API keys from secret files (never printed or logged)
    key_dir = REPO.parent / "secrets" / "nvidia"
    api_key = None
    for key_file in key_dir.glob("nvidia_api_key*.txt"):
        try:
            with key_file.open("r", encoding="utf-8") as f:
                api_key = f.read().strip()
                if api_key:
                    break
        except OSError:
            continue

    if not api_key:
        return "DIAGNOSIS_UNAVAILABLE: no API key found"

    scheduler = NvidiaScheduler(api_key=api_key)
    try:
        response = scheduler.chat(
            model="nemotron-3-ultra",
            messages=[{"role": "user", "content": prompt}],
            thinking=True,
            thinking_budget="medium",
        )
        return response
    except Exception as e:
        return f"DIAGNOSIS_ERROR: {e}"


def main(
    argv: List[str],
    runner: Optional[Callable[..., subprocess.CompletedProcess]] = None,
    diagnose: Optional[Callable[[str], str]] = None,
) -> int:
    parser = argparse.ArgumentParser(description="Autonomous research loop CLI")
    parser.add_argument(
        "--ids",
        nargs="+",
        default=list(MODULE_OF.keys()),
        help="Piece IDs to process (default: all 20)",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=50,
        help="Maximum cycles per piece (default: 50)",
    )
    parser.add_argument(
        "--sleep",
        type=int,
        default=60,
        help="Sleep seconds between cycles (default: 60)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print decide() action per piece and exit",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=None,
        help="Path to autoloop state file (default: <repo>/_loop/autoloop_state.json)",
    )
    args = parser.parse_args(argv)

    if runner is None:
        runner = _default_runner
    if diagnose is None:
        diagnose = _default_diagnose

    reviews_dir = REPO / "_loop" / "reviews"

    if args.dry_run:
        deps = build_deps(REPO, TOOLS, runner, reviews_dir, sleep=time.sleep, state_path=args.state_file)
        dry_run_report = {}
        for piece_id in args.ids:
            state = deps["get_state"](piece_id)
            action = decide(state)
            dry_run_report[piece_id] = {
                "job": state["job"],
                "tests_green": state["tests_green"],
                "action": action,
            }
        print(json.dumps(dry_run_report, ensure_ascii=False))
        return 0

    deps = build_deps(REPO, TOOLS, runner, reviews_dir, sleep=time.sleep, state_path=args.state_file)

    # Wrap escalate to inject diagnose
    original_escalate = deps["escalate"]

    def wrapped_escalate(piece_id: str) -> None:
        original_escalate(piece_id, diagnose)

    deps["escalate"] = wrapped_escalate

    report = run_cycles(
        ids=args.ids,
        max_cycles=args.max_cycles,
        sleep_s=args.sleep,
        deps=deps,
    )

    print(json.dumps(report, ensure_ascii=False))

    # Exit code 0 when no piece is stuck, 1 otherwise
    stuck = any(v.get("stuck", False) for v in report.values())
    return 1 if stuck else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
