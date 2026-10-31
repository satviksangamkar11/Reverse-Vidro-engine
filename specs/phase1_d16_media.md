# SPEC D16MED: NEW `pieces/d16_media.py` and `pieces/test_d16_media.py` (departments 12-15 and the timing parts of 5-7: colour, sound, text and pacing summaries)

GOAL: produce six CSV summaries under work/phase1/departments_16/media/ for the unprotected development videos. The module uses only local tools (ffmpeg, ffprobe, numpy) on the local reference video files, and the existing cached transcripts, beat timings and text observations. It records gaps where something cannot be established. It runs no model, does not run the frozen detector, and does not infer music mood, speaker identity or sound sources.

PATH RULE (amended 2026-10-31 after review): no absolute drive path appears in the module or the test.
- ROOT = the repository root: os.path.dirname(os.path.dirname(os.path.abspath(__file__))).
- REFERENCE_DIR = os.path.join(os.path.dirname(ROOT), "reference_videos") (the sibling folder of the repository).
- ANIM_DIR = os.path.join(os.path.dirname(ROOT), "animation_research_tool", "animation_research") is NOT used for media; folders named in the audio files are read as data only (their basenames are used).
- ffmpeg: os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg"). ffprobe: os.environ.get("FFPROBE_BIN") or shutil.which("ffprobe"). If either is missing, every colour row is BLOCKED_BY_SOURCE with the reason "ffmpeg not found".

REAL FACTS (verified 2026-10-31):
- Reference videos in REFERENCE_DIR: 10 files named "WhatsApp Video 2026-10-28 at H.MM.SS PM.mp4". Timestamps present: 9.46.07, 9.46.11, 9.46.15, 9.47.17, 9.47.18, 9.47.32, 9.47.53, 9.47.54, 9.47.55, 9.47.56 (all PM).
- Audio files: work/phase1/v4/audit_<id>/audio_<id>.json. Keys used: video_id, folder, audio_status, availability, wav_seconds, silences (list of dicts start, end), low_volume_intervals (list of dicts start, end, duration, meaning), speech_segments (list of dicts start, end, text, confidence), transcript_status, sound_classes, gap_classes. The folder value is a path string whose basename ends with the timestamp and id for WhatsApp videos, e.g. "WhatsApp_Video_2026-10-28_at_9_46_07_PM_7434a0f7". Reel videos (10151cce, 585b32de, 7a1e2b26, 85c38505) have folders under reels_evidence with no timestamp: they map to no file.
- Verified mapping: 7434a0f7 -> 9.46.07, a44aef0b -> 9.47.18, 5c93ec37 -> 9.47.54, caf6fb64 -> 9.47.53, 264e48c4 -> 9.47.55, 69a00a0f -> 9.47.56. The reference file 9.47.17 PM has no analysed folder: it is UNMAPPED.
- Video 5c93ec37 maps to 9.47.54 PM and is MEASURED_MEDIA for colour; its transcript is empty (speech_segments length 0).
- Beat files: work/phase1/v4/audit_<id>/beats_<id>.json, key "beats"; each beat has beat_id, start_time, end_time, department_findings (dict "1" to "16" -> list of dicts with status, observed).
- Zero-length beat: end_time == start_time. Video 7434a0f7 has 5 zero-length beats: shot_001, shot_004, shot_007, shot_010, shot_014 (verified 2026-10-31).
- Measurements (read only, existing output): work/phase1/step4/STEP4_MEASUREMENTS.json, keys "7434a0f7" and "7a1e2b26"; each has "transitions" with "events" (list of dicts with t and kind; kind "hard_cut" is the detector label). Use these only for the cut count in the pacing summary, labelled as existing detector output.

HELD-OUT RULE (hard): 354a38a0, 37745d70 and baf59433 must never be opened, mapped, decoded, or written into any output. Raise ValueError if they are requested.

DEV VIDEOS: 10151cce, 264e48c4, 585b32de, 5c93ec37, 69a00a0f, 7434a0f7, 7a1e2b26, 85c38505, a44aef0b, caf6fb64.

FUNCTIONS (numpy, standard library, json, csv, re, shutil, subprocess only for ffmpeg/ffprobe; no network):
- resolve_mp4(root, video_id) -> path or None. Read the audio file's folder field; take its basename; match the pattern (\d{1,2})_(\d{2})_(\d{2})_(AM|PM) followed by _<video_id>. If no match, return None. Otherwise build "WhatsApp Video 2026-10-28 at H.MM.SS PM.mp4" and return its path in REFERENCE_DIR if it exists, else None. Never guess a file by similarity.
- probe_duration(path) -> float seconds via ffprobe (format=duration).
- sample_brightness(path, fps=2) -> numpy arrays of mean luma and mean saturation per sample. ffmpeg command: -v error -i <path> -vf fps=2,scale=64:36 -f rawvideo -pix_fmt rgb24 - ; read stdout bytes; reshape to (n, 36, 64, 3). Luma = 0.2126 R + 0.7152 G + 0.0722 B on values scaled to [0,1]. Saturation per pixel = (max - min) / max with max 0 treated as 0; take the frame mean.
- colour_rows(root) -> one dict per dev video for colour_brightness_summary.csv: video_id, status (MEASURED_MEDIA or BLOCKED_BY_SOURCE), reason, mapped_file (basename or empty), duration_s, samples, mean_luma, std_luma, near_black_fraction (fraction of samples with mean luma < 0.08; a summary, not a dip detector), mean_saturation.
- brightness_series(rows) -> rows for brightness_series.csv: video_id, t_s, mean_luma, mean_saturation (only for MEASURED_MEDIA).
- audio_rows(root) -> one dict per dev video for audio_timing_summary.csv: video_id, analysed (Y or N), transcript_status, speech_segment_count (len of speech_segments), speech_seconds_total (sum of end minus start), wav_seconds, speech_coverage_fraction (speech_seconds_total / wav_seconds, empty if wav_seconds is 0 or missing), silence_seconds (sum of silences), low_volume_seconds (sum of low_volume_intervals durations), sound_classes (raw value), gap_note ("sound classes never analysed" when sound_classes is UNKNOWN; "transcript empty" when speech_segment_count is 0).
- pacing_rows(root) -> one dict per dev video for pacing_rhythm_summary.csv: video_id, beat_count, zero_length_beat_count (end_time == start_time), zero_length_beat_ids (semicolon joined), nonzero_beat_count, union_covered_seconds (union of the non-zero-length beat intervals), median_nonzero_beat_seconds, overlapping_pairs (pairs of non-zero beats whose intervals overlap by more than 0), hard_cut_count (count of kind "hard_cut" in STEP4_MEASUREMENTS.json for 7434a0f7 and 7a1e2b26; the text "UNKNOWN_NOT_MEASURED" for the other videos), cuts_per_minute (for measured videos: hard_cut_count divided by duration in minutes, where duration is the largest end_time in the beat file; else empty).
- caption_rows(root) -> one row per quoted text found in an OBSERVED finding's observed string, for caption_text_inventory.csv: video_id, beat_id, start_time, end_time, department_id (int), quoted_text, verification ("AI_READING_UNVERIFIED"). Quoted text is the text between matching single or double quote characters, length 2 or more.
- gap_rows(root) -> rows for media_gaps.csv: video_id, colour_status, audio_analysed, transcript_status, caption_inventory_count, pacing_status, gap_note. Also one row with video_id "9.47.17_UNMAPPED" and gap_note "reference file has no analysed folder; not analysed".
- write_all(root, out_dir) -> writes the six CSVs into out_dir (os.makedirs(exist_ok=True)); returns a dict of row counts.
- main(argv): with no arguments writes to ROOT/work/phase1/departments_16/media/ and prints the counts.

HARD RULES:
- Do not import pieces/p6_measure_track.py, tools/measure_track.py or any module that runs the detector. Do not call any model, any API, or any network function. Do not import urllib, requests, http, socket, openai, anthropic, or any module with "kimi" in its name.
- Do not write outside work/phase1/departments_16/media/.
- No absolute drive path in the module or the test (see PATH RULE).
- Do not print or read any file under the secrets folder or any .env file.
- Do not write the seven-letter name of the 3D software tool anywhere in code or tests.
- If ffmpeg fails on a file, record BLOCKED_BY_SOURCE with the error text; do not stop the run.
- No comment may begin with a tool name followed by a colon.

NO HARD-CODED FACTS IN TESTS (rule added 2026-10-31): every count, id list, mapping and timestamp in a test is recomputed from the real files inside the test. A test may hard-code only the field names and the rules of this spec.

TESTS for `pieces/test_d16_media.py` (pytest; read the real files; use tmp_path for output; ROOT and REFERENCE_DIR computed as in PATH RULE):
1. No held-out id appears in the module source or in any generated CSV after write_all(ROOT, tmp_path).
2. The module source does not contain "measure_track" and does not import the modules listed in HARD RULES (ast check).
3. resolve_mp4 returns None for each reel id in the dev list (no timestamp in folder). For each other dev id: recompute the expected result from the audio folder basename and the REFERENCE_DIR listing; resolve_mp4 must equal that expectation (path or None).
4. Every colour row with status MEASURED_MEDIA has mean_luma between 0 and 1, and samples within 2 of round(duration_s * 2). Every BLOCKED_BY_SOURCE row has a non-empty reason and empty mean_luma.
5. audio_rows: speech_segment_count equals len(speech_segments) read from the real audio file for every dev video; for each video whose real speech_segments list is empty, gap_note contains "transcript empty".
6. pacing_rows: zero_length_beat_ids for 7434a0f7 equals the list recomputed from the real beat file (beats with end_time == start_time), and zero_length_beat_count equals its length.
7. pacing_rows: hard_cut_count for 7434a0f7 and 7a1e2b26 equals the number of kind "hard_cut" events in STEP4_MEASUREMENTS.json recounted in the test; for each other dev video the value is "UNKNOWN_NOT_MEASURED".
8. median_nonzero_beat_seconds equals the median of (end_time - start_time) over the non-zero-length beats, recomputed from the real file.
9. caption_rows: every quoted_text is a substring of the observed text of its beat's finding (check against the real beat file).
10. gap_rows: contains one row per DEV id (count recomputed from the DEV constant) and the 9.47.17 unmapped row.
11. write_all writes exactly six files: colour_brightness_summary.csv, brightness_series.csv, audio_timing_summary.csv, pacing_rhythm_summary.csv, caption_text_inventory.csv, media_gaps.csv.

MISSING-KEY RULE (amended 2026-10-31 after Codex spec review): a beat missing beat_id, start_time, end_time or department_findings, or an audio file missing one of the keys listed in REAL FACTS, is not an error. The affected video gets a gap row in media_gaps.csv with gap_note "missing key <name>" and contributes no rows to the other summaries. Never raise KeyError for a missing key.

REAL-DATA NOTE: check each field name against the real file before using it (open one real audio file and one real beat file in the test and assert the keys exist). If a key is missing for a video, record the gap; do not assume.

REPLY RULE: return the complete source of both files. Do not add any other text.
REPLY PARSER TRAP: no line of any file you write may start with the letters F-I-L-E followed by a colon.
FORBIDDEN-WORD TRAP: the loop refuses any file containing the seven-letter name of the 3D software tool. Never type it.

OUTPUT FORMAT (mandatory): reply with ONLY these two blocks, no other text. Each block starts with the line `FILE: <path>` directly followed by a fenced code block starting with ```python on its own line and ending with ``` on its own line:
FILE: pieces/d16_media.py
```python
<complete source>
```
FILE: pieces/test_d16_media.py
```python
<complete source>
```
