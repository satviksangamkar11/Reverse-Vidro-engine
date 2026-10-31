# Colour, sound, graphics and pacing (departments 12 to 15)

Updated 2026-10-31 from the repaired media CSVs in `work/phase1/departments_16/media/`. Media loop state: review-open, not re-run. The supervisor PASS (shared key-gap check, Opus review, full suite) is unchanged. Everything below is an extracted measurement or an AI reading, not verified filmmaking knowledge. Teaching eligibility stays CLOSED for all four departments.

## Department 12, colour, lighting and art direction: PARTIAL_RESEARCH (measurements only)

Source: `media/colour_brightness_summary.csv`.

- MEASURED (6 of 10 dev videos): 264e48c4, 5c93ec37, 69a00a0f, 7434a0f7, a44aef0b, caf6fb64.
  - Mean luma 0.210 to 0.266 (7434a0f7: 0.249).
  - Near-black fraction 0.000 to 0.052 (7434a0f7: 0.009).
  - Mean saturation 0.344 to 0.590 (7434a0f7: 0.400).
- BLOCKED_BY_SOURCE (4): 10151cce, 585b32de, 7a1e2b26, 85c38505. Reason: "no reference file mapped". For 7a1e2b26 the clay original exists in `reference_videos/instagram/` but the media module does not map Instagram reels. This is a mapping gap, not a missing source.
- Reference folder 9.47.17 is UNMAPPED and not analysed.
- Not established: lighting setup, palette meaning, art direction, and any claim about how colour serves the story.

## Department 13, sound and audiovisual editing: PARTIAL_RESEARCH

Source: `media/audio_timing_summary.csv` (analysed = Y for all 10 dev videos).

- Speech coverage 0.82 to 0.99 for 9 videos (speech segments 15 to 77 per video).
- 5c93ec37: 0 speech segments, empty transcript (BLOCKED for that cell).
- Silence and low-volume time is small. Largest: 7434a0f7 silence 4.54 s and low volume 4.49 s; caf6fb64 silence 5.15 s.
- transcript_status is UNVERIFIED for every video. sound_classes is UNKNOWN for every video ("sound classes never analysed").
- Not established: sound sources, music, microphone claims.

## Department 14, captions and motion graphics: PARTIAL_RESEARCH (inventory only)

Source: `media/caption_text_inventory.csv` (599 rows) and `media/media_gaps.csv`.

- Per-video counts: 10151cce 60, 264e48c4 32, 585b32de 13, 5c93ec37 30, 69a00a0f 52, 7434a0f7 56, 7a1e2b26 85, 85c38505 44, a44aef0b 37, caf6fb64 190.
- Every row is `AI_READING_UNVERIFIED`. The quoted text is the AI reading of on-screen subtitles, not checked against the frames.
- Not established: motion-graphic design, typography, text animation.

## Department 15, pacing and attention: PARTIAL_RESEARCH (two caveats)

Source: `media/pacing_rhythm_summary.csv`. All 10 dev videos are PACING_OK.

- Beats per video (total / zero-length): 10151cce 54/0, 264e48c4 61/14, 585b32de 65/1, 5c93ec37 45/6, 69a00a0f 30/0, 7434a0f7 36/5, 7a1e2b26 61/0, 85c38505 45/1, a44aef0b 66/2, caf6fb64 102/10. Zero-length beats are excluded from duration statistics; their ids are listed in the CSV.
- **Caveat 1, not accepted:** `median_nonzero_beat_seconds` is exactly 1.5 for all 10 videos. A value identical across videos looks like a default or grid value, not a measurement. Check against the beat files before any use.
- **Caveat 2:** `overlapping_pairs` (24 to 75 per video) are shot and event records over the same span. This is the design of the beat records, not a defect.
- Hard-cut counts exist for 2 videos only:
  - 7a1e2b26: 33 hard cuts from the frozen detector, 27.76 per minute.
  - 7434a0f7: 0 hard cuts under the frozen rule, 0.0 per minute. This is the frozen-rule count, not a claim that the clip has no cuts. The 7-entry file is superseded (see `CUT_COUNT_RECONCILIATION.md`, section "7434a0f7").
  - Other 8 videos: UNKNOWN_NOT_MEASURED.
- Example union coverage: 7434a0f7 covers 47.5 s of 53.9 s.
- Not established: attention claims, rhythm relative to story.

## Teachable now

Nothing in departments 12 to 15 is accepted for teaching. Teaching eligibility is closed until a separate owner decision.
