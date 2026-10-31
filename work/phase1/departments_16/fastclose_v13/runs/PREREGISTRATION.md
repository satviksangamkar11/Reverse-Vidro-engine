# Fast-Close V1.3 A/B: pre-registration (written 2026-11-01, before the first Kimi call)

Frozen primary protocol: `../EVAL_PROTOCOL.json` (protocol_sha256 f236523739365b39d92febec7546c9eb425824cee782a1b1000b1da653e01086). Unchanged.

## Secondary readings (reported separately; never replace the primary verdict)
1. Q3 and Q4 are worded close to lessons L3 and L4. The same frozen decision rule is also applied to the total of Q1, Q2, Q5 and Q6 only. If the primary verdict depends on Q3/Q4, the result is reported as possibly "obedience, not better direction".
2. If A and B are near-identical in lesson-relevant shot structure (presets, transitions, quiet-beat presets), the result is reported as "lessons possibly not received at low effort", not as "lessons do not help". A medium-effort pair would need separate owner approval. It is not authorised.
3. S6 is the position-control pair (B ran first). A pattern in S6 opposite to S3 and S8 is reported as a possible order or timing effect.
4. Truncated, invalid or non-JSON outputs are results. They are rated as shown (the blinded view says "NO VALID PLAN") and listed separately. Nothing is excluded or regenerated.
5. Cost and latency are not compared between arms (provider caching may favour the second call of a pair).
6. Temperature is not set by the adapter: the provider default applies to both arms. The adapter saves reply text, tokens, finish reason, latency, cost and reservation, not the full HTTP body, the returned model string or cached tokens.
7. "Passed the deterministic validator" = result UNREVIEWED (no Nemotron review by design). INVALID or FAILED = did not pass.

## Lesson-to-preset map (all ids registered; gains from the registry snapshot)
| Lesson | Applies to | Registered presets / transitions named |
|---|---|---|
| L1 opening | shot 1 of each scene | 01_establishing_shot 0.28 (place), 10_object_hand_insert 0.14 (object or action), 03_slow_cinematic_push 0.20 (subject image), 02_environmental_parallax 0.13 (setting depth) |
| L2 camera variation | every consecutive pair | strong pushes 01 0.28, 03 0.20, 06_blessing_gesture 0.30, 08_emotional_closeup 0.25 |
| L3 visible reactions | shots whose ovi states a response | 07_character_reaction 0.14, 08 0.25, 03 0.20, 09_dialogue_composition 0.13, 05_bowing_prayer 0.14 |
| L4 shot progression | shot order and transition_out | all 11 presets; transitions cut, slide, pan_bridge |
| L5 emotional restraint | visual-only shots: S3 shot 6; S6 shots 5-6; S8 shot 5; ovis stating silence or stillness | 09 0.13; 05, 07, 10 0.14 |
No lesson names an unregistered preset or transition; none is untestable in this run.

## Run
- Order: A S3, B S3, B S6, A S6, A S8, B S8.
- Settings: kimi-k3.1-pro, effort low, max 16,000 tokens, `--one-call --reviewers ""`.
- One shared ledger (`D:/kaggle_upload/v5_ledger.jsonl`); P4 cap $2.00 in both copies only.
- Before each call: 0 unreconciled and committed + $0.20 <= $2.00, else stop.
