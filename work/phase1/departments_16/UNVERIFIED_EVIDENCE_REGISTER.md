# Unverified evidence register

Everything below is evidence that is NOT verified, or is verified only in part. Nothing here upgrades any department.

| Item | Source | Status | Limit |
|---|---|---|---|
| 2,147 teacher candidates | CROSS_VIDEO_TEACHER_CANDIDATES.json | AI_OBSERVATION_UNVERIFIED | model output; creators unknown; 0 independent creators; 4 departments only (5, 8, 9, 11) |
| Vision observations per beat | beat files (department_findings) | model output, LOW confidence | not human-checked |
| Speech-to-text transcripts | audio files | UNVERIFIED | wording not checked; 5c93ec37 empty |
| Hard cuts (2 videos) | STEP4_MEASUREMENTS.json | detector output | total count 33 / 36 / 75 unresolved; 1.88 s and 3.04 s are not hard_cut events; 9.96 s owner-confirmed only |
| Owner-reviewed items | ledger human_verified_items | human, specific items only | not generalised to any other item or video |
| Tutorial transcript (YouTube) | user-supplied | REFERENCE_CONCEPT only | not evidence about any video; some explanations are inaccurate |
| Quarantined media outputs | departments_16/_quarantine_2026-10-31_media_heldout_labels | NOT VALID | listed held-out reference timestamps as unmapped; not evidence |
| Granth consumer hits (124) | PRODUCTION_EXECUTION_COMPATIBILITY.json | candidate paths only | not confirmed call sites |
| Groq reviewer verdicts | loop reviews | NONE on several rounds | truncated input; recorded as no review |
| Symlink refusal test | granth test suite | SKIPPED / UNVERIFIED | not supported on this Windows system |
| Protected held-out videos | matrix rows | NOT READ | no content inspected; metadata and ids only |

Held-out data: 354a38a0, 37745d70 and baf59433 were not used for any evidence, statistic or teacher candidate.
