# WP-F2: corpus balance and evidence counting (pure functions; no network/model/Kimi). NO equal-weighting of rare types: counts are reported honestly.
1. `tag_video(meta)` -> dict keys: aspect ("9:16"|"16:9"|"1:1"|"other"), duration_band ("<15s","15-45s","45-120s",">120s"), has_audio (True/False/"UNAVAILABLE"), origin, art_style (str or "UNKNOWN"), pacing_band (cuts/min <12 "slow", 12-30 "medium", >30 "fast", else "UNKNOWN"), creator_id (str or "UNKNOWN"). Never filters a video out.
2. `evidence_counts(refs, tags_by_video)` -> {"videos": distinct video count, "independent_creators": distinct KNOWN creator_ids (UNKNOWN never counted as independent), "unknown_creator_videos": n, "by_type": {art_style: distinct videos}, "total_corpus": len(tags_by_video), "prevalence": videos/total_corpus rounded 3}. A technique seen in one video stays videos==1.
3. `balance_report(tags_list, expected=None)` -> {"counts": {dimension:{value:n}}, "dominant":[{"dimension","value","share"}] where share>0.5 and n>=3, "gaps":[values in expected with 0 videos]}. Gaps are RESEARCH GAPS only; they never change counts or weights.
Worked example: tags aspect 9:16 x4, 16:9 x1 => dominant [{"dimension":"aspect","value":"9:16","share":0.8}]; refs from 4 videos, 2 known creators + 2 UNKNOWN => videos 4, independent_creators 2, unknown_creator_videos 2.
ADDITIONS (reviewer-agreed):
4. `refs` is a list of {"video_key": sha256, "technique": str}; a ref whose video_key is absent from tags_by_video raises ValueError naming the unknown keys. pacing_band may be None when cut data is missing: None/"UNKNOWN" values are excluded from `dominant` and gap calculations and reported as `missing_<dimension>_count` instead, so missing data never creates a fake dominant bucket.


HARD RULES: pure Python 3.14 stdlib (numpy only where the spec says so); tests use tempfile/tmp_path directories, never absolute drive paths; no network; no Kimi; do not import other pieces' modules; do not drop public functions. Module file: research/pieces/f2_bias.py; test file: research/pieces/test_f2_bias.py (tests import the module by its plain file name, e.g. `from f2_bias import ...`).


REVIEW FINDINGS (round 1, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF2
LUNA (gpt-6-luna high):
MED - research/pieces/f2_bias.py:221 - Missing pacing values still dilute the dominance share: 3 `fast` videos plus 7 missing values produce no dominant bucket, though `fast` is 100% of known pacing values - Calculate share using the count of known values for that dimension; assert the share in `test_missing_pacing_excluded_from_dominant_and_reported`.

MED - research/pieces/f2_bias.py:234 - Expected `None` or `"UNKNOWN"` pacing values are reported as research gaps even though the spec excludes missing values from gaps - Skip missing sentinels when building `gaps` and add a regression test.

LOW - research/pieces/f2_bias.py:51 - `has_audio=1` or `0` passes tuple membership because integers compare equal to booleans, so the function can return an `int` instead of the specified boolean - Accept only `is True` or `is False`; test integer inputs.

SONNET (latest):
wpF2 - f2_bias.py + test_f2_bias.py  => PASS (0 HIGH / 0 MED)
- LOW - f2_bias.py:221-223 - `dominant` share denominator is `len(tags_list)` (missing values included), but the test comments (test_f2_bias.py:151-153,165) and the "missing excluded" intent describe a known-only denominator; code/test disagree and nothing asserts the share - decide one denominator, assert `share` in test_missing_pacing_excluded_from_dominant_and_reported.
- LOW - f2_bias.py:51 - `has_audio` of 1/0 passes `in (True, False, ...)` (1==True) and is returned as int, not bool - use `isinstance(has_audio, bool) or has_audio == "UNAVAILABLE"`.
- LOW - f2_bias.py:201-204 - unhashable tag value (list/dict) in a dimension raises TypeError in `Counter` - coerce/skip non-hashables as missing.
- LOW - test_f2_bias.py (whole file) - the spec worked example (aspect 9:16 x4 + 16:9 x1 => share 0.8; refs from 4 videos, 2 known + 2 UNKNOWN creators => 4/2/2) is never reproduced; also unused imports `os, json, tempfile` (lines 2-4). Add the worked-example test.


REVIEW FINDINGS (round 2, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF2
LUNA (gpt-6-luna medium):
MED - research/pieces/f2_bias.py:46 - Missing or nonnumeric duration produces `duration_band="UNAVAILABLE"`, outside the spec’s allowed duration bands - Return one of the four specified bands for every input, or clarify the contract to allow a missing sentinel.

SONNET (latest):
wpF2 - f2_bias.py + test_f2_bias.py  => PASS (0 HIGH / 0 MED)
- LOW - f2_bias.py:221-223 - `dominant` share denominator is `len(tags_list)` (missing values included), but the test comments (test_f2_bias.py:151-153,165) and the "missing excluded" intent describe a known-only denominator; code/test disagree and nothing asserts the share - decide one denominator, assert `share` in test_missing_pacing_excluded_from_dominant_and_reported.
- LOW - f2_bias.py:51 - `has_audio` of 1/0 passes `in (True, False, ...)` (1==True) and is returned as int, not bool - use `isinstance(has_audio, bool) or has_audio == "UNAVAILABLE"`.
- LOW - f2_bias.py:201-204 - unhashable tag value (list/dict) in a dimension raises TypeError in `Counter` - coerce/skip non-hashables as missing.
- LOW - test_f2_bias.py (whole file) - the spec worked example (aspect 9:16 x4 + 16:9 x1 => share 0.8; refs from 4 videos, 2 known + 2 UNKNOWN creators => 4/2/2) is never reproduced; also unused imports `os, json, tempfile` (lines 2-4). Add the worked-example test.

HAIKU (low, stand-in):
Summary
- wpE2: HIGH 1 / MED 0 -> FAIL
- wpF2: HIGH 0 / MED 1 -> FAIL
- wpF4: HIGH 0 / MED 1 -> FAIL


REVIEW FINDINGS (round 3, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF2
LUNA (gpt-6-luna medium):
MED - research/pieces/f2_bias.py:43 - Missing or nonnumeric duration returns `None`, outside the four allowed `duration_band` values - Return a specified band for every input or update the contract to explicitly allow a missing sentinel and test it.

SONNET (latest):
wpF2 - f2_bias.py + test_f2_bias.py  => PASS (0 HIGH / 0 MED)
- LOW - f2_bias.py:221-223 - `dominant` share denominator is `len(tags_list)` (missing values included), but the test comments (test_f2_bias.py:151-153,165) and the "missing excluded" intent describe a known-only denominator; code/test disagree and nothing asserts the share - decide one denominator, assert `share` in test_missing_pacing_excluded_from_dominant_and_reported.
- LOW - f2_bias.py:51 - `has_audio` of 1/0 passes `in (True, False, ...)` (1==True) and is returned as int, not bool - use `isinstance(has_audio, bool) or has_audio == "UNAVAILABLE"`.
- LOW - f2_bias.py:201-204 - unhashable tag value (list/dict) in a dimension raises TypeError in `Counter` - coerce/skip non-hashables as missing.
- LOW - test_f2_bias.py (whole file) - the spec worked example (aspect 9:16 x4 + 16:9 x1 => share 0.8; refs from 4 videos, 2 known + 2 UNKNOWN creators => 4/2/2) is never reproduced; also unused imports `os, json, tempfile` (lines 2-4). Add the worked-example test.

HAIKU (low, stand-in):
Summary

- wpE1: HIGH 0, MED 1 (FAIL)
- wpE2: HIGH 0, MED 1 (FAIL)
- wpF1: HIGH 0, MED 3 (FAIL)
- wpF2: HIGH 0, MED 1 (FAIL)


REVIEW FINDINGS (round 4, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF2
LUNA (gpt-6-luna medium):
MED - research/pieces/f2_bias.py:40 - Missing or nonnumeric `duration_sec` yields `duration_band=None`, outside the four allowed values - Return a specified band for every input, or amend the contract to allow a missing sentinel and test that contract.

SONNET (latest):
wpF2 - f2_bias.py + test_f2_bias.py  => PASS (0 HIGH / 0 MED)
- LOW - f2_bias.py:221-223 - `dominant` share denominator is `len(tags_list)` (missing values included), but the test comments (test_f2_bias.py:151-153,165) and the "missing excluded" intent describe a known-only denominator; code/test disagree and nothing asserts the share - decide one denominator, assert `share` in test_missing_pacing_excluded_from_dominant_and_reported.
- LOW - f2_bias.py:51 - `has_audio` of 1/0 passes `in (True, False, ...)` (1==True) and is returned as int, not bool - use `isinstance(has_audio, bool) or has_audio == "UNAVAILABLE"`.
- LOW - f2_bias.py:201-204 - unhashable tag value (list/dict) in a dimension raises TypeError in `Counter` - coerce/skip non-hashables as missing.
- LOW - test_f2_bias.py (whole file) - the spec worked example (aspect 9:16 x4 + 16:9 x1 => share 0.8; refs from 4 videos, 2 known + 2 UNKNOWN creators => 4/2/2) is never reproduced; also unused imports `os, json, tempfile` (lines 2-4). Add the worked-example test.


REVIEW FINDINGS (round 5, Sonnet 5.5 medium): fix every HIGH and MED item below in the code and/or tests, keep ALL currently passing tests passing, never weaken a test, keep every public function.
wpF2
LUNA (gpt-6-luna medium):
MED - research/pieces/f2_bias.py:40 - Missing or nonnumeric `duration_sec` returns `duration_band=None`, outside the four allowed values - Return an allowed band or amend the contract and tests to allow a missing value

HAIKU (low, stand-in):
MED - f2_bias.py:55 (tag_video) - `duration_band` returns `None` for missing or nonnumeric duration. The spec allows `None` only for `pacing_band`, so this is outside the four allowed bands. - Return the sentinel `"UNKNOWN"`, treat it as missing in `_is_missing_value`, update the docstring, and change the `assertIsNone` duration assertions in `test_duration_bands` to `"UNKNOWN"`.
MED - f2_bias.py:balance_report (`val = tags.get(dim, "UNKNOWN")`) - a tag dict that lacks `has_audio` or `duration_band` is counted as a known value `"UNKNOWN"`, because `_is_missing_value` only recognizes `"UNAVAILABLE"` for has_audio and only `None` for duration_band. Three dicts that carry only `aspect` produce a fake dominant `duration_band="UNKNOWN"` and `has_audio="UNKNOWN"` at share 1.0. The spec's worked example therefore yields extra dominant entries, not just the aspect one. - Use `tags.get(dim)` (None) and treat None or `"UNKNOWN"` as missing for every dimension, plus `"UNAVAILABLE"` for has_audio. Add a test: three `{"aspect":"9:16"}` dicts give no has_audio or duration_band dominant entry and `missing_has_audio_count == 3`. Also assert the full worked-example `dominant` list equals `[aspect 9:16 share 0.8]`.
LOW - f2_bias.py:tag_video (duration and cuts checks) - `float("nan")` passes `isinstance(..., float)`, and every comparison with NaN is False, so `duration_sec=nan` gives `">120s"` and `cuts=nan` gives `"fast"`. - Add `math.isfinite` to those checks.

OUTPUT FORMAT (mandatory, the parser rejects anything else): reply with ONLY these two blocks, no other text. Each block is the line `FILE: <path>` followed immediately by a fenced code block that starts with ```python on its own line and ends with ``` on its own line:
FILE: research/pieces/f2_bias.py
```python
<complete module source>
```
FILE: research/pieces/test_f2_bias.py
```python
<complete test source>
```
