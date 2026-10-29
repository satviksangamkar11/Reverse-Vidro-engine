# Animation research tool

Standalone frame selection and NVIDIA Nemotron vision review. It does not edit GranthStudio.

## Setup

Python 3.11+, FFmpeg and FFprobe on `PATH`, then `pip install -r requirements.txt`.
Put 14 distinct values in a local `.env` as `NVIDIA_API_KEY_01` through `NVIDIA_API_KEY_14`. The local `.env` and research output are gitignored. Never commit keys. Key values are not written to reports.

## Commands

```powershell
python animation_research.py --input "D:\aai work\reference_videos" --output "D:\aai work\animation_research_tool\animation_research" --extract-only
python animation_research.py --input "D:\aai work\reference_videos" --output "D:\aai work\animation_research_tool\animation_research" --review --dry-run --resume --mode pilot --max-api-calls 20
python animation_research.py --input "D:\aai work\reference_videos" --output "D:\aai work\animation_research_tool\animation_research" --review --resume --mode pilot --smoke-only --max-api-calls 2
python animation_research.py --input "D:\aai work\reference_videos" --output "D:\aai work\animation_research_tool\animation_research" --review --resume --mode pilot --max-api-calls 20
python animation_research.py --input "D:\aai work\reference_videos" --output "D:\aai work\animation_research_tool\animation_research" --review --resume --mode full --max-api-calls 100
python -m unittest -v test_animation_research.py test_instagram_import.py
```

## Add Instagram reel links later

Paste one public reel link per line in `instagram_links.txt`. The importer uses [parth-dl](https://github.com/parthmax2/parth-dl) and does not log in to Instagram. It accepts public `/reel/<shortcode>/` links, strips tracking parameters, records downloads, and skips links already imported. A link behind a login wall will be reported as failed.

```powershell
python instagram_import.py --urls-file "D:\aai work\animation_research_tool\instagram_links.txt" --output "D:\aai work\reference_videos"
python instagram_import.py --urls-file "D:\aai work\animation_research_tool\instagram_links.txt" --output "D:\aai work\reference_videos" --run
python animation_research.py --input "D:\aai work\reference_videos" --output "D:\aai work\animation_research_tool\animation_research" --extract-only --resume
```

The first import command is a dry run. `--run` downloads, but never starts frame analysis or NVIDIA calls. Run analysis explicitly after checking the imported files.

Pilot mode schedules one labeled storyboard and one short motion burst per video. It is an initial review, not a full motion audit; other detected events remain pending. `frame_selection_manifest.json` records local frame analysis, API selections, scores, uncertainty and reasons. Full mode schedules every shot and detected motion event.

The live review sends a real single image smoke test, then a small multi image probe. It stops if the smoke test fails. `--smoke-only` stops after those probes. Every HTTP attempt counts against `--max-api-calls`. The scheduler has rolling 60-second limits of 10 requests per key and, conservatively, 10 requests across all keys until a higher account limit is confirmed. Configure the latter with `--global-limit` only when provider terms and account limits permit it. A 429 pauses the entire scheduler for `Retry-After` or at least 60 seconds. Four workers are used by default. Results are checkpointed per job. ZIP frames retain natural order and unknown timestamps. Capability labels are hypotheses until checked against the engine.
