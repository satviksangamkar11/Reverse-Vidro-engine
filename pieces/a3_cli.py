import argparse
import json
import sys
from typing import Any, Callable, Dict, List


def build_parser() -> Dict[str, Any]:
    parser = argparse.ArgumentParser(prog="ingest", description="Ingest CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add-link
    p_add = subparsers.add_parser("add-link", help="Add Instagram reel URLs to queue")
    p_add.add_argument("urls", nargs="+", help="Reel URL(s) to add")
    p_add.add_argument("--queue-file", required=True, help="Path to queue file")
    p_add.set_defaults(command="add_link")

    # collect
    p_collect = subparsers.add_parser("collect", help="Collect media files into destination")
    p_collect.add_argument("inputs", nargs="+", help="Input file(s) or directory(ies)")
    p_collect.add_argument("--dest", required=True, help="Destination directory")
    p_collect.set_defaults(command="collect")

    # status
    p_status = subparsers.add_parser("status", help="Show queue and ledger status")
    p_status.add_argument("--queue-file", required=True, help="Path to queue file")
    p_status.add_argument("--ledger", required=True, help="Path to ledger file")
    p_status.set_defaults(command="status")

    return {"parser": parser, "status": "ok"}


def run_add_link(
    urls: List[str],
    queue_file: str,
    queue_links_fn: Callable,
    normalize_reel_url: Callable,
    clock_now: Callable,
    write_text_file: Callable,
) -> Dict[str, Any]:
    # write_text_file is reserved for future use (e.g., writing queue file directly)
    result = queue_links_fn(
        urls=urls,
        queue_file=queue_file,
        normalize_reel_url=normalize_reel_url,
        clock_now=clock_now,
    )
    json.dump(result, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return result


def run_collect(
    inputs: List[str],
    dest: str,
    collect_inputs_fn: Callable,
    sha256_file: Callable,
    copy_file: Callable,
    make_dirs: Callable,
    list_dir: Callable,
    is_file: Callable,
    is_dir: Callable,
    get_size: Callable,
    extract_zip_safe: Callable,
) -> Dict[str, Any]:
    result = collect_inputs_fn(
        inputs=inputs,
        dest=dest,
        sha256_file=sha256_file,
        copy_file=copy_file,
        make_dirs=make_dirs,
        list_dir=list_dir,
        is_file=is_file,
        is_dir=is_dir,
        get_size=get_size,
        extract_zip_safe=extract_zip_safe,
    )
    json.dump(result, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return result


def run_status(
    queue_file: str,
    ledger_path: str,
    queue_status_fn: Callable,
    read_text_file: Callable,
    parse_json_lines: Callable,
) -> Dict[str, Any]:
    result = queue_status_fn(
        queue_file=queue_file,
        ledger_path=ledger_path,
        read_text_file=read_text_file,
        parse_json_lines=parse_json_lines,
    )
    json.dump(result, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return result


def _has_failed_items(result: Dict[str, Any]) -> bool:
    """Check if result contains any failed items (rejected, error status, or FAILED_* states)."""
    if result.get("status") == "error":
        return True
    if result.get("rejected"):
        return True
    items = result.get("items")
    if items:
        for item in items:
            state = item.get("state", "")
            if state.startswith("FAILED_"):
                return True
    return False


def main(
    argv: List[str],
    build_parser: Callable,
    run_add_link: Callable,
    run_collect: Callable,
    run_status: Callable,
    read_text_file: Callable,
    write_text_file: Callable,
    clock_now: Callable,
    normalize_reel_url: Callable,
    sha256_file: Callable,
    copy_file: Callable,
    make_dirs: Callable,
    list_dir: Callable,
    is_file: Callable,
    is_dir: Callable,
    get_size: Callable,
    extract_zip_safe: Callable,
    open_zip: Callable,
    get_zip_info: Callable,
    extract_member: Callable,
    parse_json_lines: Callable,
    queue_links_fn: Callable,
    collect_inputs_fn: Callable,
    queue_status_fn: Callable,
) -> int:
    parser_result = build_parser()
    parser = parser_result["parser"]
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        if e.code is None:
            return 0
        if isinstance(e.code, int):
            return e.code
        return 1

    if args.command == "add_link":
        result = run_add_link(
            urls=args.urls,
            queue_file=args.queue_file,
            queue_links_fn=queue_links_fn,
            normalize_reel_url=normalize_reel_url,
            clock_now=clock_now,
            write_text_file=write_text_file,
        )
        return 1 if _has_failed_items(result) else 0

    elif args.command == "collect":
        result = run_collect(
            inputs=args.inputs,
            dest=args.dest,
            collect_inputs_fn=collect_inputs_fn,
            sha256_file=sha256_file,
            copy_file=copy_file,
            make_dirs=make_dirs,
            list_dir=list_dir,
            is_file=is_file,
            is_dir=is_dir,
            get_size=get_size,
            extract_zip_safe=extract_zip_safe,
        )
        return 1 if _has_failed_items(result) else 0

    elif args.command == "status":
        result = run_status(
            queue_file=args.queue_file,
            ledger_path=args.ledger,
            queue_status_fn=queue_status_fn,
            read_text_file=read_text_file,
            parse_json_lines=parse_json_lines,
        )
        return 1 if _has_failed_items(result) else 0

    # Unreachable because subparser is required=True, kept for completeness
    parser.print_usage(sys.stderr)
    return 2
