# Department master status (16 departments, 13 reference videos, 2026-10-31)

Scope: the 10 non-held-out videos (160 cells). The 3 protected held-out videos (354a38a0, 37745d70, baf59433; 48 cells) were not read, and are marked PROTECTED in DEPARTMENT_VIDEO_MATRIX.csv. Counts come from that matrix and from CROSS_VIDEO_TEACHER_CANDIDATES.json.

Status vocabulary: RESEARCH_COMPLETE_FROM_AVAILABLE_EVIDENCE (none assigned), PARTIAL_RESEARCH, NOT_EXAMINED, BLOCKED_BY_SOURCE, UNKNOWN. Human verification is listed separately and is never implied by these statuses.

| Dept | Name | Status | Evidence in the 10 videos | Teacher candidates | Human-verified (specific items only) | Missing | Blocked from delivery |
|---|---|---|---|---|---|---|---|
| 1 | Storytelling / screenwriting | NOT_EXAMINED | none recorded | 0 | none | story function, hooks, reveal, payoff | yes |
| 2 | Narrative construction | NOT_EXAMINED | none recorded | 0 | none | causality, scene order | yes |
| 3 | Direction | NOT_EXAMINED | none recorded | 0 | none | scene purpose, staging, eyelines | yes |
| 4 | Shot planning | NOT_EXAMINED | none recorded | 0 | none | shot-size inventory | yes |
| 5 | Camera language | PARTIAL_RESEARCH | 8 AI observations; 2 measured (7434a0f7, 7a1e2b26) | 532 | 7434a0f7 specific camera reads only | camera meaning; 7434a0f7 47.5-53 s conflict open | partly |
| 6 | Composition / visual hierarchy | NOT_EXAMINED | none recorded | 0 | none | framing, eyeline, look room | yes |
| 7 | Editing / transitions | PARTIAL_RESEARCH | 2 measured videos; 8 cells not examined | 0 | 7434a0f7 dark dips; 7a1e2b26 9.96 s cut; 7a1e2b26 36-cut total (owner-approved) | 7a1e2b26: frozen tool gives 33, owner total 36, not reproduced by repo tool; 7434a0f7: owner total open (frozen rule 0 hard cuts) | partly |
| 8 | Animation principles | PARTIAL_RESEARCH | 10 AI observations | 528 | none | verification | partly |
| 9 | Character performance | PARTIAL_RESEARCH | 10 AI observations | 536 | none | verification; reactions | partly |
| 10 | Animation production | UNKNOWN | no method recorded | 0 | none | production method | yes |
| 11 | VFX / compositing | PARTIAL_RESEARCH | 10 AI observations | 551 | none | verification; method | partly |
| 12 | Colour / lighting / art direction | PARTIAL_RESEARCH | brightness and saturation measured for 6 of 10 videos (media CSV); 4 BLOCKED (no reference mapped) | 0 | none | lighting setup, palette meaning, art direction | partly |
| 13 | Sound / audiovisual editing | PARTIAL_RESEARCH | speech timing for 9 videos (transcripts UNVERIFIED); 5c93ec37 has no speech; sound classes not analysed | 0 | none | transcript verification; sound classes | partly |
| 14 | Captions / motion graphics | PARTIAL_RESEARCH | 599 caption readings across 10 videos, all AI_READING_UNVERIFIED (media CSV) | 0 | none | verification of readings; motion-graphic design | partly |
| 15 | Pacing / attention | PARTIAL_RESEARCH | beat rhythm for 10 videos (media CSV); hard-cut counts for 2 videos; median beat 1.5 s identical for all 10 (check before use) | 0 | none | 1.5 s median check; attention | partly |
| 16 | Practical execution | PARTIAL_RESEARCH | GranthStudio read-only check done: 0 of 13 techniques executable | 0 | none | executable preset; assets | yes (no executable path) |

Totals across the 160 non-held-out cells (from DEPARTMENT_VIDEO_MATRIX.csv): NOT_EXAMINED 80 (depts 1, 2, 3, 4, 6, 12, 14, 15); PARTIAL_RESEARCH 61; BLOCKED_BY_SOURCE 1; UNKNOWN 20 (depts 10 and 16). No department is RESEARCH_COMPLETE.

Note (2026-10-31): the totals above are from `DEPARTMENT_VIDEO_MATRIX.csv` as generated before the media repair. The matrix generator (`pieces/d16_matrix.py`) does not read the media CSVs, so matrix rows for departments 12, 14 and 15 still show NOT_EXAMINED. The table above and `COLOUR_SOUND_GRAPHICS_PACING.md` are the current status for those departments. Regenerating the matrix from media needs a code change and is not done here.

Human verification: only the specific owner-reviewed items listed above. No department is marked human-verified as a whole.
