# reverse-video-engine: checkpoint and review document

Status date: 2026-10-29, evening. Audience: a reviewing agent. Everything here is labelled **VERIFIED** (a test passed or a real run produced the number) or **OPINION / NOT VERIFIED**. Please challenge the unverified parts first.

---

## 1. Objective

Build a **teacher for Kimi**. The engine reverse-engineers reference videos (local MP4 files, ZIPs of frames, Instagram reels) into evidence-backed filmmaking knowledge that makes a two-stage AI animation director better at its job.

| Stage | Kimi's job | What the teacher must provide |
|---|---|---|
| **Stage 1: direction** | decide what the viewer should see: shot choices, framing, camera, character performance, image briefs, justified sound | lessons on shot sequencing, composition, performance, pacing, editing, and **when not to use** a technique |
| **Stage 2: animation selection** | choose EXISTING presets and valid JSON arrangements for the approved shots; report `NEED_NEW` when a capability or asset is missing | which arrangement reproduces an observed effect, the artwork each needs, and honest `NEED_NEW` gaps (never an invented preset id) |

**Deliverables (three files, rebuilt from the evidence each time):**
1. `MASTER_REPORT.md`: the evidence (per video: what is seen, frame and time references, uncertainties).
2. `MASTER_TECHNIQUES.json`: structured knowledge (techniques, requirements, counterexamples, classification, confidence).
3. `KIMI_ANIMATION_PLAYBOOK.md`: short practical Stage 1 and Stage 2 guidance.

**Hard constraints (owner rules):**
- No Kimi calls anywhere in this tool. A comparison of Kimi with and without the teacher needs the owner's explicit approval.
- Teacher output is read-only guidance. Source canon, the output schema, approved presets, the sound palette and owner approvals always win.
- Never invent story events, dialogue, preset ids, original editing software, lenses, hidden rigs or screenplay text. Observed facts and inferred intent are stored separately; intent is a hypothesis.
- Reference music is research only and prohibited in production. Reference dialogue never alters approved wording.
- Frame-only inputs (ZIPs of frames) get no fabricated audio findings.
- Reels are vertical, fast and dramatic; the target film is 16:9 and calmer. Techniques are adapted, never copied by default.
- Instagram links are only recorded; nothing is downloaded until the owner says run.

This repository does **not** build the film, and it does not modify the film pipeline.

---

## 2. System overview

```
sources (MP4 / ZIP frames / reels)
   -> discover + dedupe (byte-identical files skipped)
   -> local analysis: frames, shot cuts, motion windows, audio silence evidence
   -> vision review (Nemotron vision model) of shots and motion windows -> structured reports with frame evidence
   -> compile the teacher: per-video digests -> cross-video recipes -> playbook + techniques + report
   -> audit: ONE audio reference reconstructed beat by beat and checked against the real video
```

Verified facts about the current run (all 9 unique local videos):

| Item | Value | Status |
|---|---|---|
| Files seen / unique videos | 10 / 9 (one byte-identical duplicate skipped) | VERIFIED |
| Frames retained with timestamps | 1,596 | VERIFIED |
| Vision reviews completed | **539 of 539** (199 shot reviews, 322 motion-window reviews, 18 pilot reviews) | VERIFIED (api logs) |
| Vision model | `nvidia/nemotron-3.5-super-vl-120b-a12b` via NVIDIA API, 14 keys, <= 10 calls per key per minute | VERIFIED |
| Capability class assigned by the reviews | V2_REUSE 372, V2_EXTENSION 140, NEW_ARTWORK 14, V3_ACTION 6, UNKNOWN 7 | VERIFIED counts; classes themselves are model OPINION |
| Reports that name a technique | 537 of 539, with 536 distinct free-text strings (no normalisation yet) | VERIFIED |
| Audio | silence detection only (ffmpeg `silencedetect`, -35 dB, >= 0.35 s); the result means "low volume", not proven speech pause or intentional silence | VERIFIED; narration, SFX, music NOT analysed |

Per-video review counts (video id = last 8 chars of the folder name): 7434a0f7: 14 shots, 22 events; 354a38a0: 26, 40; 37745d70: 15, 25; a44aef0b: 25, 41; baf59433: 22, 53; caf6fb64: 40, 62; 5c93ec37: 19, 26; 264e48c4: 33, 28; 69a00a0f: 5, 25.

### Review report schema (one JSON object per review group)
`video_id, scene_id (shot_NNN | event_ID | pilot_*), start_frame, end_frame, start_time, end_time, characters, observed_animation, inferred_technique, camera_motion, character_motion, visual_effects, required_assets, potential_blender_implementation, granthstudio_capability (V2_REUSE | V2_EXTENSION | V3_ACTION | NEW_ARTWORK | UNKNOWN), evidence_frames, confidence, uncertainties`. Many fields are the literal string `UNKNOWN` by design.

**Known data-quality issue (VERIFIED):** the `confidence` field is heterogeneous (`HIGH`, `High`, `MEDIUM`, numeric `0.95`, `0.9`, even a sentence). It needs normalisation before any statistic uses it.

---

## 3. Components

### 3.1 `engine/` (the working pipeline; its own tests passed earlier: 12 of 12)
- `animation_research.py`: main CLI. Discovers sources (videos, ZIP frame sequences), skips byte-identical duplicates, extracts frames, builds groups, runs vision reviews with checkpoints and resume, validates replies, writes reports.
  Flags: `--input --output --mode {pilot,full} --review|--extract-only --resume --dry-run --max-api-calls --workers --per-key-limit --global-limit --window-seconds --target-per-30 --smoke-only --url --urls-file --download-links`.
- `frame_selection.py`: local overview and action-evidence selection (no network). Defaults: cut histogram threshold 0.30, cut SSIM 0.68, action residual 0.035; produces shot starts, motion windows ("events"), storyboard sheets.
- `cinematic_analysis.py`: evidence accounting and audio timing: every motion candidate gets a disposition; ffmpeg silence intervals; writes the (currently thin) playbook. **Known gap:** its playbook writer only uses the 18 pilot reports, not the 539 full reports.
- `nvidia_scheduler.py`: per-key rolling windows, shared queue, cooldown on HTTP 429, auth/payment errors disable keys, call budget.
- `instagram_import.py`: URL normalisation (HTTPS `/reel/<code>/` only), queue plus dry-run, resumable download ledger with sha256 and duplicate detection. Never downloads without `--run`.

### 3.2 `pieces/` (hardened building blocks, each with its own tests; not yet wired into `engine/`)
Test counts below are from the last full run (2026-10-29 20:40), VERIFIED. All modules are plain Python 3.14; B1/B2 use numpy.

| Id | Module | Purpose | Tests |
|---|---|---|---|
| A1 | `a1_queue` | record reel links only (normalise, dedupe, never download); queue status QUEUED / DOWNLOADED / FAILED | 13 pass |
| A2 | `a2_collect` | collect videos/ZIP image sequences; zip-slip safe (absolute paths, `..`, symlinks, size caps), sha256 dedupe, no overwrite | 18 pass |
| A3 | `a3_cli` | CLI for A1/A2: exactly one JSON object on stdout, exit code 0 or 1 | 16 pass |
| B1 | `a1_audio_io` | audio extraction, RMS profile, silences, onsets; image sequences report UNAVAILABLE (not silent) | 32 pass |
| B2 | `a2_transcribe` | transcription wrapper (faster-whisper, injectable), low-confidence flags, gap classification as candidates only | 9 pass |
| B3 | `a3_align` | align cuts with silences/onsets/speech as CO_OCCURS (never causal), cached audio evidence | 31 pass |
| C1 | `c1_cluster` | cluster motion windows by signature, pick representatives (best, ambiguous, failure) | 17 pass |
| C2 | `c2_review` | review plan under a call budget, fps rule for ambiguous fast motion, ffmpeg re-extraction command builder | 19 pass |
| C3 | `c3_state` | per-window dispositions; a cluster never counts as reviewing its members; coverage must reach unaccounted == 0 | 23 pass |
| D1 | `d1_beat_schema` | beat schema: purpose, how filmed, how animated, sound, observed vs inferred, 16 department findings, OBSERVED / NOT_OBSERVED / UNKNOWN / NOT_EXAMINED, evidence rules, forbidden-fact checks, no audio findings without audio | 84 pass |
| D2 | `d2_recipe_compiler` | merge beats across videos into recipes, keep ordered sequence patterns and all source refs, registered preset ids only | 37 pass |
| D3 | `d3_deliverables` | write report/techniques/playbook sections atomically; playbook guard against invented ids, timings, EASY rewrites, music | 51 pass |
| D4 | `d4_reconstruct` | full-sequence reconstruction of one video plus mechanical truth check (structure only; semantic status is always `NOT_VERIFIED` until a human audit is recorded) | 23 pass (in progress) |
| E1 | `a1_scene_selection` | pick one scene per category, freeze baseline hashes | 11 pass |
| E2 | `a2_recipe_prompts` | build baseline vs research-informed prompts (read-only hints block, size limits) | 25 pass |
| E3 | `a3_blind_scoring` | blind A/B pairing with a separate key file, plan scoring, promotion verdict (never without owner approval and an animatic comparison) | 66 pass, **1 failing** |
| F1 | `f1_corpus` | cumulative corpus ledger keyed by content hash, source identity kept separate, version tracking, stale detection | 48 pass |
| F2 | `f2_bias` | video tags, honest evidence counts (no up-weighting of rare types), balance report, research gaps | 23 pass |
| F3 | `f3_publish` | exclusive file lock, immutable snapshot folders, one pointer file replaced last, readers resolve the pointer once | 37 pass |
| F4 | `f4_classify` | GENERAL / STYLE_SPECIFIC / EXPERIMENTAL, research confidence vs executability, USABLE_NOW / USEFUL_BUT_BLOCKED / RESEARCH_ONLY, Stage 1 and Stage 2 views | 49 pass |

Totals: **632 tests pass, 1 fails (E3) at the last run.** Passing tests prove behaviour only as far as the tests go. Several of these tests were written together with the code, so test strength is itself a review target.

### 3.3 `specs/`, `docs/`
- `specs/` the behaviour specs of the pieces (they also contain generation instructions and review notes; read them as requirements).
- `docs/GRAMMAR_REQUIREMENT.md` the owner's full filmmaking-grammar requirement: 16 departments (storytelling, narrative construction, direction, shot planning, camera, composition, editing and transitions, animation principles, performance, production techniques, VFX, colour and light, sound, captions, pacing, practical execution), four analysis levels (video, sequence, shot, technique) with relationships kept, mandatory per-beat questions, evidence fields per finding.
- `queue/instagram_links.txt` recorded reel links (none downloaded).

---

## 4. Checklist (checkpoints)

Legend: [x] verified done, [~] partly done, [ ] not done.

**A. Engine and evidence**
- [x] Ingest, dedupe, frame extraction, shot and motion selection on 9 unique videos (1,596 frames).
- [x] Full vision analysis of all 9 videos: 539 of 539 reviews.
- [x] Instagram import: queue, normalisation, resumable ledger (dry-run only, nothing downloaded).
- [ ] Confidence field normalised; technique strings clustered into a controlled vocabulary.

**B. The teacher (the actual product)**
- [~] Compile 539 reviews into per-video digests and cross-video recipes with evidence, Stage 1 and Stage 2 lessons, `NEED_NEW`, classification (compiler is being finished; **the current playbook file is only a thin draft from the 18 pilot reviews**).
- [ ] Final `MASTER_REPORT.md`, `MASTER_TECHNIQUES.json`, `KIMI_ANIMATION_PLAYBOOK.md` produced from the compiler and read through by a person.
- [ ] Sound lessons: transcription (Marathi and Hindi), narration/pause/SFX/music identification, alignment with cuts. Today: silence detection only.
- [ ] Beat-level reconstruction of ONE reference video with audio: story progression, shots, transitions, character and camera performance, animation and effects, sound/image relations, simplest reproduction, unknowns.
- [ ] Human audit of that reconstruction against the real video, covering story structure, shot planning, editing, animation, sound, and Kimi lessons without invented facts. A critical finding means the teacher fails and is repaired.
- [ ] Analysis of the 30 queued reels (needs the owner's go to download).
- [ ] Stage 1 / Stage 2 compatibility check of the final playbook against Kimi's existing schemas and rules.
- [ ] Offline comparison of Kimi decisions with and without the playbook (needs the owner's approval; no Kimi calls until then).

**C. Building blocks**
- [~] 20 modules written with tests (632 pass, 1 fails). Not wired into `engine/`; wiring is not required for a first teacher.
- [ ] End-to-end runner (URL or MP4 -> evidence -> teacher files) built from these blocks.

**D. Two claims kept apart**
- Research pipeline passes = the tool runs, evidence is accurate, Stage 1/2 handoffs are valid. **Not yet claimed.**
- Kimi improvement proven = a later approved comparison shows better directing and execution. **Not claimed; not started.**

---

## 5. Decisions already taken (please challenge)
1. Equal weighting of video types was rejected: a rare type must not count like ten common ones. Report honest counts, counts by type, independent creators (unknown creators are never counted as independent), and use balance only to find research gaps.
2. Technique classes: GENERAL (>= 3 videos), STYLE_SPECIFIC (2), EXPERIMENTAL (1); research confidence and executability are separate fields; useful-but-blocked lessons stay visible to Stage 1 (reported as `NEED_NEW`) but never reach Stage 2 as presets.
3. Cumulative outputs come from one writer: immutable snapshot folders plus a single pointer file replaced last (no half-new, half-old file sets).
4. Image-sequence identity is an ordered manifest of frame hashes (order matters); raw file hash is used for exact MP4 duplicates and is not perceptual duplicate detection.
5. A missing audio stream is reported as `NO_AUDIO_STREAM`, a ZIP of frames as `UNAVAILABLE`; neither is "silent".
6. Cluster membership never counts as a review; every motion window needs its own evidence-backed disposition.

---

## 6. Risks and areas to review first
1. **Evidence quality:** 537 technique strings are free text from a vision model. Spot-check 20 reviews against their frames: are `observed_animation` and `inferred_technique` supported, or plausible but wrong? Check the 7 UNKNOWN and 20 NEW_ARTWORK / V3_ACTION classes.
2. **Playbook honesty:** when the compiler output arrives, check every lesson for a video id and frame reference, for single-source lessons presented as general rules, and for any claim about sound (none is allowed beyond silence).
3. **Test strength:** pick any piece and ask whether its tests would fail if the behaviour were wrong. Pay attention to D1 (audio rule when `audio_status` is not passed), D3 (timing and "invented id" guards), F1 (URL normalisation, input type checks), F2 (missing values must not become a bucket), F3 (Windows file names, line endings), E3 (the one failing test).
4. **Spec versus tests conflicts** were settled in writing in `specs/` (sections named REVIEWER DECISIONS); confirm they are reasonable.
5. **Heterogeneous data:** the `confidence` field, mixed-case labels, `UNKNOWN` strings.
6. **Stage 2 safety:** can any path put a preset id into Stage 2 guidance that is not in a registered list?
7. **Audio gap** is the largest content gap: the teacher cannot yet say anything about narration, sound effects, silence as a device or synchronisation.

## 7. Open questions for the reviewer
- Is a 3-video threshold for GENERAL reasonable with 9 videos of mixed style and unknown creators?
- Is the review report schema enough for a Stage 1 director, or is a beat-level schema needed earlier (D1)?
- What is the smallest additional evidence that would make the sound section trustworthy?
- Which two or three techniques would you expect a viewer to notice that the 539 reviews are likely to miss (camera push, held pose, parallax, cut on action)?

## 8. Reproduce / verify
- Engine: `cd engine && python -m pytest -q` (needs opencv, numpy, requests, ffmpeg on PATH).
- Pieces: `cd pieces && python -m pytest -q` (tests import modules by plain name; Python 3.14; numpy for B1/B2).
- Analysis run (needs 14 NVIDIA keys in a local `.env` as `NVIDIA_API_KEY_01..14`, not in this repo): `python engine/animation_research.py --input <videos> --output <out> --mode full --review --resume --global-limit 140 --per-key-limit 10 --workers 12 --max-api-calls 900`.
- Not in the repository: videos, extracted frames, the 562 KB generated report, API keys.
