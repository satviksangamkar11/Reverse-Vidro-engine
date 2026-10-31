# Review clip index

Sources: 7434a0f7 = reference_videos/WhatsApp Video 2026-10-28 at 9.46.07 PM.mp4 (30 fps, 1,614 frames, 53.89 s); 7a1e2b26 = reference_videos/instagram/DfF8Z8tMVhK/clayrified-DfF8Z8tMVhK.mp4 (24 fps, 1,713 frames, 71.49 s). Both match the frame counts and frame rates in the analysed beat records.

Evaluated interval = the beat or span being reviewed (from the beat files, checked against the packets). Extraction interval = the evaluated interval plus up to 1 s of context on each side. In each clip, the evaluated part starts at (evaluated start - extraction start) seconds.

No detector prediction, proposed answer, overlay or label is added to any clip. Subtitles in the clips are part of the original videos. Clips are re-encoded only so that cuts land on exact frames; speed and frame rate are unchanged; original audio is kept (AAC).

| Review | Item | Records | Evaluated (s) | Extraction (s) | Evaluated part starts at (s in clip) | File | Duration (s) | Audio | Check | Question |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | B01 | shot_001 | 0.0-0.0 (zero length, FLAG) | frame 0 only | n/a | R1_7434a0f7_B01_shot_001_0.0-0.0s_FLAG_ZERO_LENGTH.png | n/a | n/a | frame extracted | FLAG: zero-length beat (shot_001). Frame reference only. Judge only what is visible in this single frame; do not use it for any duration or timing judgement. UNKNOWN is a valid answer. |
| 1 | B02 | shot_002 | 0.5-4.5 | 0.0-5.5 | 0.5 | R1_7434a0f7_B02_shot_002_0.5-4.5s.mp4 | 5.5 | yes | PASS | Does the clip show the observable action described for shot_002 in HUMAN_REVIEW_1_STORY_SCENE.md? Then mark APPROVE, CORRECT or UNKNOWN for story function, scene purpose, shot type and reveal. |
| 1 | B03 | event_001 | 1.0-2.5 | 0.0-3.5 | 1.0 | R1_7434a0f7_B03_event_001_1.0-2.5s.mp4 | 3.5 | yes | PASS | Does the clip show the observable action described for event_001 in HUMAN_REVIEW_1_STORY_SCENE.md? Then mark APPROVE, CORRECT or UNKNOWN for story function, scene purpose, shot type and reveal. |
| 1 | B04 | event_002 | 3.0-4.5 | 2.0-5.5 | 1.0 | R1_7434a0f7_B04_event_002_3.0-4.5s.mp4 | 3.5 | yes | PASS | Does the clip show the observable action described for event_002 in HUMAN_REVIEW_1_STORY_SCENE.md? Then mark APPROVE, CORRECT or UNKNOWN for story function, scene purpose, shot type and reveal. |
| 1 | B05 | event_003 | 5.0-6.5 | 4.0-7.5 | 1.0 | R1_7434a0f7_B05_event_003_5.0-6.5s.mp4 | 3.5 | yes | PASS | Does the clip show the observable action described for event_003 in HUMAN_REVIEW_1_STORY_SCENE.md? Then mark APPROVE, CORRECT or UNKNOWN for story function, scene purpose, shot type and reveal. |
| 1 | B06 | shot_003 | 5.0-8.5 | 4.0-9.5 | 1.0 | R1_7434a0f7_B06_shot_003_5.0-8.5s.mp4 | 5.5 | yes | PASS | Does the clip show the observable action described for shot_003 in HUMAN_REVIEW_1_STORY_SCENE.md? Then mark APPROVE, CORRECT or UNKNOWN for story function, scene purpose, shot type and reveal. |
| 1 | B07 | event_004 | 7.0-8.5 | 6.0-9.5 | 1.0 | R1_7434a0f7_B07_event_004_7.0-8.5s.mp4 | 3.5 | yes | PASS | Does the clip show the observable action described for event_004 in HUMAN_REVIEW_1_STORY_SCENE.md? Then mark APPROVE, CORRECT or UNKNOWN for story function, scene purpose, shot type and reveal. |
| 1 | B08 | shot_004 | 9.0-9.0 (zero length, FLAG) | frame 270 only | n/a | R1_7434a0f7_B08_shot_004_9.0-9.0s_FLAG_ZERO_LENGTH.png | n/a | n/a | frame extracted | FLAG: zero-length beat (shot_004). Frame reference only. Judge only what is visible in this single frame; do not use it for any duration or timing judgement. UNKNOWN is a valid answer. |
| 1 | B09 | event_005 | 9.5-11.0 | 8.5-12.0 | 1.0 | R1_7434a0f7_B09_event_005_9.5-11.0s.mp4 | 3.5 | yes | PASS | Does the clip show the observable action described for event_005 in HUMAN_REVIEW_1_STORY_SCENE.md? Then mark APPROVE, CORRECT or UNKNOWN for story function, scene purpose, shot type and reveal. |
| 1 | B10 | shot_005 | 9.5-12.5 | 8.5-13.5 | 1.0 | R1_7434a0f7_B10_shot_005_9.5-12.5s.mp4 | 5.0 | yes | PASS | Does the clip show the observable action described for shot_005 in HUMAN_REVIEW_1_STORY_SCENE.md? Then mark APPROVE, CORRECT or UNKNOWN for story function, scene purpose, shot type and reveal. |
| 2 | S01 | shot_001+event_001 | 0.0-1.5 | 0.0-2.5 | 0.0 | R2_7a1e2b26_S01_0.0-1.5s.mp4 | 2.5 | yes | PASS | Does the clip show the observable action described for shot_001 and event_001 in HUMAN_REVIEW_2_VISUAL_STORY.md? Then mark APPROVE, CORRECT or UNKNOWN for editing, sequencing, performance and pacing. Cut times in the packet are detector output, not ground truth. |
| 2 | S02 | shot_002+event_002 | 2.0-3.0 | 1.0-4.0 | 1.0 | R2_7a1e2b26_S02_2.0-3.0s.mp4 | 3.0 | yes | PASS | Does the clip show the observable action described for shot_002 and event_002 in HUMAN_REVIEW_2_VISUAL_STORY.md? Then mark APPROVE, CORRECT or UNKNOWN for editing, sequencing, performance and pacing. Cut times in the packet are detector output, not ground truth. |
| 2 | S03 | shot_003 | 3.5-4.0 | 2.5-5.0 | 1.0 | R2_7a1e2b26_S03_3.5-4.0s.mp4 | 2.5 | yes | PASS | Does the clip show the observable action described for shot_003 in HUMAN_REVIEW_2_VISUAL_STORY.md? Then mark APPROVE, CORRECT or UNKNOWN for editing, sequencing, performance and pacing. Cut times in the packet are detector output, not ground truth. |
| 2 | S04 | shot_004+event_003 | 4.5-5.5 | 3.5-6.5 | 1.0 | R2_7a1e2b26_S04_4.5-5.5s.mp4 | 3.0 | yes | PASS | Does the clip show the observable action described for shot_004 and event_003 in HUMAN_REVIEW_2_VISUAL_STORY.md? Then mark APPROVE, CORRECT or UNKNOWN for editing, sequencing, performance and pacing. Cut times in the packet are detector output, not ground truth. |
| 2 | S05 | shot_005+event_004 | 6.0-7.5 | 5.0-8.5 | 1.0 | R2_7a1e2b26_S05_6.0-7.5s.mp4 | 3.5 | yes | PASS | Does the clip show the observable action described for shot_005 and event_004 in HUMAN_REVIEW_2_VISUAL_STORY.md? Then mark APPROVE, CORRECT or UNKNOWN for editing, sequencing, performance and pacing. Cut times in the packet are detector output, not ground truth. |
| 2 | S06 | shot_006 | 8.0-9.5 | 7.0-10.5 | 1.0 | R2_7a1e2b26_S06_8.0-9.5s.mp4 | 3.5 | yes | PASS | Does the clip show the observable action described for shot_006 in HUMAN_REVIEW_2_VISUAL_STORY.md? Then mark APPROVE, CORRECT or UNKNOWN for editing, sequencing, performance and pacing. Cut times in the packet are detector output, not ground truth. |

Contact sheet: REVIEW_CONTACT_SHEET.jpg (one frame from the middle of each evaluated interval; labels are clip names only).

Verification (2026-10-31): every clip opened with ffprobe; each duration equals its extraction interval within one frame; each clip has a video and an audio stream; the frame at the start of the evaluated interval matches the source frame at that time (mean absolute difference under 0.3 on a 0-255 scale). The two zero-length beats have valid source frames (frame 0 and frame 270).

Held-out videos (354a38a0, 37745d70, baf59433) are not included. No human-approved label is included.

## SHA-256
- R1_7434a0f7_B01_shot_001_0.0-0.0s_FLAG_ZERO_LENGTH.png: fd4cd72eb30e2bb7e9916203b18456298f5d78d63646cda76e34b6483d31fa31
- R1_7434a0f7_B02_shot_002_0.5-4.5s.mp4: 4027e39ea464aaba824fe31de5ae1b36c572ec667dcc1ccd00c36889ce914e38
- R1_7434a0f7_B03_event_001_1.0-2.5s.mp4: 2b2f37848042344fd80534fa9907b7a862add1cf2dc5656b2c346c0597bdf7df
- R1_7434a0f7_B04_event_002_3.0-4.5s.mp4: 28da492f12451e379aa96ddd4465382ab8be01d0d008c34471b81a5c344344e2
- R1_7434a0f7_B05_event_003_5.0-6.5s.mp4: 4c2cb54dc22edfc2c04e9b99279f36ad7bb0d97ee69046468c0f621ff7ad23d5
- R1_7434a0f7_B06_shot_003_5.0-8.5s.mp4: b6d75c4f414ecb2151467b0f2d711a46d80a2f4d358ae49d2d6bde8d8637475e
- R1_7434a0f7_B07_event_004_7.0-8.5s.mp4: 9bbe19a5a0748949f5db0afea3453854dd5b666902aed1cb4eb10d4ca455fa0f
- R1_7434a0f7_B08_shot_004_9.0-9.0s_FLAG_ZERO_LENGTH.png: 625fd412aa417bc9b12b4f9146105c67f3d1b1b1613adbf1193ae17fc93047e9
- R1_7434a0f7_B09_event_005_9.5-11.0s.mp4: 8806d5fcb63f5747462d9569f5929fce0e9bc91f3b7b44d63e4e0af0be06fb1f
- R1_7434a0f7_B10_shot_005_9.5-12.5s.mp4: fc397293e8a82451da19cc883e337cd05942ae8c2bb0b8a0b8ea156d45cdf5ad
- R2_7a1e2b26_S01_0.0-1.5s.mp4: d129cd7295835e1ae9e8b710f102da1df52d87f639d1644dc8a68640a402e4b0
- R2_7a1e2b26_S02_2.0-3.0s.mp4: 7d1bfbbf46efe754f26f476b8ed4b1b4409d0e5881ebcff049970edf322ffb91
- R2_7a1e2b26_S03_3.5-4.0s.mp4: d26557d854e603f5ba989b159958a63c59f81f9ecc33bd76958ac33747abfba2
- R2_7a1e2b26_S04_4.5-5.5s.mp4: c846feccf63f9509880dcde88281507c7d9c8761087a41b3517ce4d94bbbf816
- R2_7a1e2b26_S05_6.0-7.5s.mp4: 77221ce8ebb67ce2e58482480212769e7f73a001fd0082fd077466a7e792bc41
- R2_7a1e2b26_S06_8.0-9.5s.mp4: 3c7cb493c30f9aa1accbc421e1b6db8866b69dfd9b6df37cc7575610f038d27b

## Notes on the two zero-length beats
- B01 shot_001 (frame 0): the frame is completely black (mean brightness 0). It matches the packet's description. Reviewable only as "black frame"; UNKNOWN is expected for story fields.
- B08 shot_004 (frame 270): the frame shows the standing character with the subtitle "Devayani stopped him", dimmed because it falls in a fade. Reviewable as a single frame only.

## Separate issue recorded (not fixed here)
- The clay original exists at reference_videos/instagram/DfF8Z8tMVhK/clayrified-DfF8Z8tMVhK.mp4, but the media module does not map Instagram reels, so its colour row for 7a1e2b26 is BLOCKED_BY_SOURCE ("no reference file mapped"). This is a mapping gap in the media module, not a missing source.
