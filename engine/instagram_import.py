"""Import user supplied public Instagram reels into reference_videos."""
from __future__ import annotations

import argparse
import json
import re
import hashlib
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def normalize_reel_url(raw: str):
    parsed = urlparse(raw.strip())
    if parsed.scheme != "https" or parsed.hostname not in {"instagram.com", "www.instagram.com"}:
        raise ValueError("Expected an HTTPS Instagram reel URL")
    match = re.fullmatch(r"/reel/([A-Za-z0-9_-]+)/?", parsed.path)
    if not match:
        raise ValueError("Only /reel/<shortcode>/ links are supported")
    return f"https://www.instagram.com/reel/{match.group(1)}/"


def read_urls(urls, urls_file):
    supplied = list(urls)
    if urls_file:
        supplied += [line.strip() for line in urls_file.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]
    result = []
    for raw in supplied:
        url = normalize_reel_url(raw)
        if url not in result:
            result.append(url)
    return result


def verify_video(path: Path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration", "-of", "json", str(path)], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise ValueError("Downloaded file is not readable media")
    data = json.loads(result.stdout)
    if not any(s.get("codec_type") == "video" for s in data.get("streams", [])) or float(data.get("format", {}).get("duration") or 0) <= 0:
        raise ValueError("Downloaded file has no decodable video stream")
    return {"duration": float(data["format"]["duration"]), "has_audio": any(s.get("codec_type") == "audio" for s in data.get("streams", []))}


def sha256_file(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def import_reels(urls, output: Path, *, run=False, downloader=None, verifier=verify_video):
    output.mkdir(parents=True, exist_ok=True)
    log_path = output / "instagram_import_log.json"
    try:
        ledger = json.loads(log_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        ledger = {}
    if run and downloader is None:
        try:
            from parth_dl import InstagramDownloader
        except ImportError as exc:
            raise RuntimeError("Install parth-dl first: python -m pip install parth-dl") from exc
        downloader = InstagramDownloader(quiet=True, rate_limit=True, overwrite=False)
    summary = {"links": len(urls), "already_downloaded": 0, "downloaded": 0, "failed": 0, "planned": 0, "results": []}
    for url in urls:
        old = ledger.get(url, {})
        if old.get("status") == "COMPLETE" and old.get("files") and all(Path(name).is_file() and Path(name).stat().st_size > 0 for name in old["files"]):
            summary["already_downloaded"] += 1
            summary["results"].append({"url": url, "status": "ALREADY_DOWNLOADED"})
            continue
        if not run:
            summary["planned"] += 1
            summary["results"].append({"url": url, "status": "PLANNED"})
            continue
        try:
            shortcode = url.rstrip("/").split("/")[-1]
            target = output / "instagram" / shortcode
            target.mkdir(parents=True, exist_ok=True)
            result = downloader.download(url, output_path=str(target))
            files = [Path(x).resolve() for x in ([result] if isinstance(result, str) else result or [])]
            files = [p for p in files if p.is_file() and p.stat().st_size > 0 and p.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}]
            if not files or any(output.resolve() not in p.parents for p in files):
                raise ValueError("No usable video file was returned inside the reference folder")
            media = [verifier(p) for p in files]
            hashes = [sha256_file(p) for p in files]
            duplicates = [prior_url for prior_url, item in ledger.items() if prior_url != url and item.get("status") == "COMPLETE" and set(hashes) & set(item.get("sha256", []))]
            ledger[url] = {"status": "COMPLETE", "files": [str(p) for p in files], "sha256": hashes, "media": media, "duplicate_of": duplicates}
            summary["downloaded"] += 1
            summary["results"].append({"url": url, "status": "DOWNLOADED", "files": [str(p) for p in files], "duplicate_of": duplicates})
        except Exception as exc:
            ledger[url] = {"status": "FAILED", "error": f"{type(exc).__name__}: {str(exc)[:250]}"}
            summary["failed"] += 1
            summary["results"].append({"url": url, "status": "FAILED", "error": ledger[url]["error"]})
        temp = log_path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
        temp.replace(log_path)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="Download public Instagram reels only; research must be started separately.")
    parser.add_argument("urls", nargs="*")
    parser.add_argument("--urls-file", type=Path)
    parser.add_argument("--output", type=Path, default=Path(r"D:\aai work\reference_videos"))
    parser.add_argument("--run", action="store_true", help="Actually download. Without this, only print the plan.")
    args = parser.parse_args(argv)
    if not args.urls and not args.urls_file:
        parser.error("Provide reel links or --urls-file")
    urls = read_urls(args.urls, args.urls_file)
    print(json.dumps(import_reels(urls, args.output, run=args.run), indent=2))


if __name__ == "__main__":
    main()
