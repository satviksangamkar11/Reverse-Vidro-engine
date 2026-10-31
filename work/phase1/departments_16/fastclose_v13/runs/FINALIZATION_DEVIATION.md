# Finalization without a human rating (recorded 2026-11-01, BEFORE the blinding key was opened)

Owner instruction (chat): "use opus and gemini review to finalize".
- The frozen protocol names the owner's human blind rating as primary. No human rating was made.
- Instead, the frozen decision rule (fc13_eval.decide, unchanged) is applied SEPARATELY to each of two frozen AI ratings:
  - Opus: opus_review/OPUS_BLIND_RATING_SHEET.csv (manifest sha 2f185a08...).
  - Gemini: ai_ratings/GEMINI_BLIND_RATING_SHEET.csv (sha bd804a95...); known input omission (dress note) recorded in GEMINI_REVIEW_LIMITATIONS.md.
- The two AI verdicts are reported side by side. They are not averaged. If they disagree, the result is NOT CONCLUSIVE.
- Secondary reading: the same rule on Q1, Q2, Q5 and Q6 only (Q3 and Q4 neutralised equally for both plans).
- Disclosed limits: no human rating; S3 partly unblinded to the owner (B S3 known INVALID before rating); n = 1 sample per arm per scene.
