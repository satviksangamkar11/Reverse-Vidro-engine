import unittest
from f2_bias import tag_video, evidence_counts, balance_report


class TestTagVideo(unittest.TestCase):
    def test_aspect_ratios(self):
        # 9:16
        meta = {"width": 1080, "height": 1920}
        tags = tag_video(meta)
        self.assertEqual(tags["aspect"], "9:16")
        # 16:9
        meta = {"width": 1920, "height": 1080}
        tags = tag_video(meta)
        self.assertEqual(tags["aspect"], "16:9")
        # 1:1
        meta = {"width": 1080, "height": 1080}
        tags = tag_video(meta)
        self.assertEqual(tags["aspect"], "1:1")
        # other
        meta = {"width": 800, "height": 600}
        tags = tag_video(meta)
        self.assertEqual(tags["aspect"], "other")
        # missing dims -> other
        meta = {}
        tags = tag_video(meta)
        self.assertEqual(tags["aspect"], "other")

    def test_duration_bands(self):
        self.assertEqual(tag_video({"duration_sec": 10})["duration_band"], "<15s")
        self.assertEqual(tag_video({"duration_sec": 15})["duration_band"], "15-45s")
        self.assertEqual(tag_video({"duration_sec": 45})["duration_band"], "15-45s")
        self.assertEqual(tag_video({"duration_sec": 46})["duration_band"], "45-120s")
        self.assertEqual(tag_video({"duration_sec": 120})["duration_band"], "45-120s")
        self.assertEqual(tag_video({"duration_sec": 121})["duration_band"], ">120s")
        # Missing or nonnumeric duration -> "UNKNOWN" (missing sentinel)
        self.assertEqual(tag_video({})["duration_band"], "UNKNOWN")
        self.assertEqual(tag_video({"duration_sec": None})["duration_band"], "UNKNOWN")
        self.assertEqual(tag_video({"duration_sec": "long"})["duration_band"], "UNKNOWN")
        # NaN should be treated as missing
        self.assertEqual(tag_video({"duration_sec": float("nan")})["duration_band"], "UNKNOWN")

    def test_has_audio(self):
        self.assertEqual(tag_video({"has_audio": True})["has_audio"], True)
        self.assertEqual(tag_video({"has_audio": False})["has_audio"], False)
        self.assertEqual(tag_video({})["has_audio"], "UNAVAILABLE")
        self.assertEqual(tag_video({"has_audio": "maybe"})["has_audio"], "UNAVAILABLE")
        # Integer 1/0 should NOT pass as boolean
        self.assertEqual(tag_video({"has_audio": 1})["has_audio"], "UNAVAILABLE")
        self.assertEqual(tag_video({"has_audio": 0})["has_audio"], "UNAVAILABLE")

    def test_origin_and_art_style(self):
        self.assertEqual(tag_video({"origin": "tiktok"})["origin"], "tiktok")
        self.assertEqual(tag_video({})["origin"], "UNKNOWN")
        self.assertEqual(tag_video({"art_style": "anime"})["art_style"], "anime")
        self.assertEqual(tag_video({})["art_style"], "UNKNOWN")

    def test_pacing_band(self):
        # slow (<12 cpm)
        self.assertEqual(tag_video({"cuts": 10, "duration_sec": 60})["pacing_band"], "slow")
        # medium (12-30 cpm)
        self.assertEqual(tag_video({"cuts": 12, "duration_sec": 60})["pacing_band"], "medium")
        self.assertEqual(tag_video({"cuts": 30, "duration_sec": 60})["pacing_band"], "medium")
        # fast (>30 cpm)
        self.assertEqual(tag_video({"cuts": 31, "duration_sec": 60})["pacing_band"], "fast")
        # missing cuts or duration -> None
        self.assertIsNone(tag_video({"cuts": 10})["pacing_band"])
        self.assertIsNone(tag_video({"duration_sec": 60})["pacing_band"])
        self.assertIsNone(tag_video({})["pacing_band"])
        # Negative cuts -> None (missing)
        self.assertIsNone(tag_video({"cuts": -1, "duration_sec": 60})["pacing_band"])
        # NaN cuts or duration -> None (missing)
        self.assertIsNone(tag_video({"cuts": float("nan"), "duration_sec": 60})["pacing_band"])
        self.assertIsNone(tag_video({"cuts": 10, "duration_sec": float("nan")})["pacing_band"])

    def test_creator_id(self):
        self.assertEqual(tag_video({"creator_id": "user123"})["creator_id"], "user123")
        self.assertEqual(tag_video({})["creator_id"], "UNKNOWN")
        self.assertEqual(tag_video({"creator_id": ""})["creator_id"], "UNKNOWN")

    def test_never_filters_out(self):
        # Even with completely empty meta, we get a full tag dict with defaults
        tags = tag_video({})
        expected_keys = {"aspect", "duration_band", "has_audio", "origin", "art_style", "pacing_band", "creator_id"}
        self.assertEqual(set(tags.keys()), expected_keys)
        # No exception raised


class TestEvidenceCounts(unittest.TestCase):
    def setUp(self):
        # Build a small tagged corpus
        self.tags_by_video = {
            "v1": {"creator_id": "alice", "art_style": "anime"},
            "v2": {"creator_id": "bob", "art_style": "anime"},
            "v3": {"creator_id": "UNKNOWN", "art_style": "pixel"},
            "v4": {"creator_id": "alice", "art_style": "anime"},
            "v5": {"creator_id": "carol", "art_style": "3d"},
        }
        self.refs = [
            {"video_key": "v1", "technique": "t1"},
            {"video_key": "v2", "technique": "t1"},
            {"video_key": "v3", "technique": "t2"},
        ]

    def test_basic_counts(self):
        ec = evidence_counts(self.refs, self.tags_by_video)
        self.assertEqual(ec["videos"], 3)
        self.assertEqual(ec["independent_creators"], 2)  # alice, bob
        self.assertEqual(ec["unknown_creator_videos"], 1)  # v3
        self.assertEqual(ec["by_type"], {"anime": 2, "pixel": 1})
        self.assertEqual(ec["total_corpus"], 5)
        self.assertEqual(ec["prevalence"], round(3/5, 3))

    def test_unknown_video_key_raises(self):
        bad_refs = self.refs + [{"video_key": "v99", "technique": "t3"}]
        with self.assertRaises(ValueError) as cm:
            evidence_counts(bad_refs, self.tags_by_video)
        self.assertIn("v99", str(cm.exception))

    def test_single_video_technique_stays_one(self):
        # A technique seen in one video stays videos==1
        refs = [{"video_key": "v1", "technique": "t_unique"}]
        ec = evidence_counts(refs, self.tags_by_video)
        self.assertEqual(ec["videos"], 1)

    def test_unknown_creator_not_counted_as_independent(self):
        refs = [{"video_key": "v3", "technique": "t2"}]  # v3 has UNKNOWN creator
        ec = evidence_counts(refs, self.tags_by_video)
        self.assertEqual(ec["independent_creators"], 0)
        self.assertEqual(ec["unknown_creator_videos"], 1)


class TestBalanceReport(unittest.TestCase):
    def test_dominant_and_gaps(self):
        tags_list = [
            {"aspect": "9:16", "duration_band": "<15s", "has_audio": True, "origin": "tiktok", "art_style": "anime", "pacing_band": "fast", "creator_id": "u1"},
            {"aspect": "9:16", "duration_band": "<15s", "has_audio": True, "origin": "tiktok", "art_style": "anime", "pacing_band": "fast", "creator_id": "u2"},
            {"aspect": "9:16", "duration_band": "<15s", "has_audio": True, "origin": "tiktok", "art_style": "anime", "pacing_band": "fast", "creator_id": "u3"},
            {"aspect": "16:9", "duration_band": "15-45s", "has_audio": False, "origin": "youtube", "art_style": "pixel", "pacing_band": "medium", "creator_id": "u4"},
        ]
        expected = {"aspect": ["9:16", "16:9", "1:1"], "art_style": ["anime", "pixel", "3d"]}
        report = balance_report(tags_list, expected=expected)
        # Dominant: aspect 9:16 share 0.75 (3/4), count 3 >=3 -> dominant
        self.assertTrue(any(d["dimension"] == "aspect" and d["value"] == "9:16" and d["share"] == 0.75 for d in report["dominant"]))
        # Gaps: 1:1 and 3d have zero videos
        self.assertIn("1:1", report["gaps"])
        self.assertIn("3d", report["gaps"])
        # Counts
        self.assertEqual(report["counts"]["aspect"]["9:16"], 3)
        self.assertEqual(report["counts"]["aspect"]["16:9"], 1)

    def test_missing_pacing_excluded_from_dominant_and_reported(self):
        tags_list = [
            {"aspect": "9:16", "pacing_band": "fast"},
            {"aspect": "9:16", "pacing_band": "fast"},
            {"aspect": "9:16", "pacing_band": "fast"},
            {"aspect": "9:16", "pacing_band": None},  # missing
            {"aspect": "9:16", "pacing_band": "UNKNOWN"},  # missing
        ]
        report = balance_report(tags_list)
        # pacing_band known values: fast x3, total_known=3 -> share 1.0, count=3 >=3 -> dominant
        dom = next((d for d in report["dominant"] if d["dimension"] == "pacing_band" and d["value"] == "fast"), None)
        self.assertIsNotNone(dom)
        self.assertEqual(dom["share"], 1.0)
        # Missing count reported
        self.assertEqual(report.get("missing_pacing_band_count"), 2)

    def test_missing_unknown_excluded_from_dominant(self):
        # If all values are UNKNOWN/None, no dominant
        tags_list = [
            {"aspect": "9:16", "pacing_band": None},
            {"aspect": "9:16", "pacing_band": "UNKNOWN"},
        ]
        report = balance_report(tags_list)
        # No dominant for pacing_band because total_known = 0
        dom_dims = {d["dimension"] for d in report["dominant"]}
        self.assertNotIn("pacing_band", dom_dims)
        self.assertEqual(report.get("missing_pacing_band_count"), 2)

    def test_gaps_only_research_gaps_never_change_counts(self):
        tags_list = [{"aspect": "9:16"}]
        expected = {"aspect": ["9:16", "16:9", "1:1"]}
        report = balance_report(tags_list, expected=expected)
        # Gaps reported but counts unchanged
        self.assertEqual(report["counts"]["aspect"]["9:16"], 1)
        self.assertIn("16:9", report["gaps"])
        self.assertIn("1:1", report["gaps"])

    def test_empty_tags_list(self):
        report = balance_report([])
        self.assertEqual(report["counts"], {
            "aspect": {},
            "duration_band": {},
            "has_audio": {},
            "origin": {},
            "art_style": {},
            "pacing_band": {}
        })
        self.assertEqual(report["dominant"], [])
        self.assertEqual(report["gaps"], [])

    def test_dominant_requires_n_ge_3(self):
        # Only 2 videos of same value -> not dominant
        tags_list = [
            {"aspect": "9:16"},
            {"aspect": "9:16"},
            {"aspect": "16:9"},
        ]
        report = balance_report(tags_list)
        dom_dims = {d["dimension"] for d in report["dominant"]}
        self.assertNotIn("aspect", dom_dims)

    def test_dominant_requires_share_gt_0_5(self):
        # 4 videos: 3 of A, 1 of B -> share 3/4 = 0.75 > 0.5, n=4 >=3 -> dominant
        tags_list = [
            {"aspect": "9:16"},
            {"aspect": "9:16"},
            {"aspect": "9:16"},
            {"aspect": "16:9"},
        ]
        report = balance_report(tags_list)
        self.assertTrue(any(d["dimension"] == "aspect" and d["value"] == "9:16" for d in report["dominant"]))

    def test_missing_count_for_multiple_dimensions(self):
        tags_list = [
            {"aspect": "9:16", "origin": None},
            {"aspect": "UNKNOWN", "origin": "tiktok"},
        ]
        report = balance_report(tags_list)
        self.assertEqual(report.get("missing_aspect_count"), 1)
        self.assertEqual(report.get("missing_origin_count"), 1)

    def test_unhashable_values_treated_as_missing(self):
        # List/dict values should be treated as missing, not raise TypeError
        tags_list = [
            {"aspect": "9:16", "art_style": ["anime", "manga"]},  # unhashable list
            {"aspect": "16:9", "art_style": {"style": "pixel"}},  # unhashable dict
            {"aspect": "1:1", "art_style": "3d"},
        ]
        report = balance_report(tags_list)
        # The two unhashable art_style values should be counted as missing
        self.assertEqual(report.get("missing_art_style_count"), 2)
        # Only the hashable "3d" should appear in counts
        self.assertEqual(report["counts"]["art_style"], {"3d": 1})

    def test_expected_missing_sentinels_not_in_gaps(self):
        # Expected values that are missing sentinels should not appear in gaps
        tags_list = [{"aspect": "9:16"}]
        expected = {"aspect": ["9:16", "16:9", "UNKNOWN", None]}
        report = balance_report(tags_list, expected=expected)
        # Only "16:9" should be a gap; "UNKNOWN" and None are missing sentinels
        self.assertIn("16:9", report["gaps"])
        self.assertNotIn("UNKNOWN", report["gaps"])
        self.assertNotIn(None, report["gaps"])

    def test_worked_example_from_spec(self):
        """
        Worked example from spec:
        - tags aspect 9:16 x4, 16:9 x1 => dominant [{"dimension":"aspect","value":"9:16","share":0.8}]
        - refs from 4 videos, 2 known creators + 2 UNKNOWN => videos 4, independent_creators 2, unknown_creator_videos 2
        """
        # Build tags_list matching the example
        tags_list = [
            {"aspect": "9:16", "creator_id": "creator_a"},
            {"aspect": "9:16", "creator_id": "creator_b"},
            {"aspect": "9:16", "creator_id": "UNKNOWN"},
            {"aspect": "9:16", "creator_id": "UNKNOWN"},
            {"aspect": "16:9", "creator_id": "creator_c"},
        ]
        
        # Test balance_report dominant
        report = balance_report(tags_list)
        dom = next((d for d in report["dominant"] if d["dimension"] == "aspect" and d["value"] == "9:16"), None)
        self.assertIsNotNone(dom)
        self.assertEqual(dom["share"], 0.8)  # 4/5 = 0.8
        # Only aspect should be dominant (no has_audio, duration_band, etc. dominant entries)
        self.assertEqual(len(report["dominant"]), 1)
        
        # Build tags_by_video for evidence_counts (using video keys v1-v5)
        tags_by_video = {
            "v1": {"creator_id": "creator_a", "art_style": "anime"},
            "v2": {"creator_id": "creator_b", "art_style": "anime"},
            "v3": {"creator_id": "UNKNOWN", "art_style": "pixel"},
            "v4": {"creator_id": "UNKNOWN", "art_style": "pixel"},
            "v5": {"creator_id": "creator_c", "art_style": "3d"},
        }
        refs = [
            {"video_key": "v1", "technique": "t1"},
            {"video_key": "v2", "technique": "t1"},
            {"video_key": "v3", "technique": "t2"},
            {"video_key": "v4", "technique": "t2"},
        ]
        ec = evidence_counts(refs, tags_by_video)
        self.assertEqual(ec["videos"], 4)
        self.assertEqual(ec["independent_creators"], 2)  # creator_a, creator_b
        self.assertEqual(ec["unknown_creator_videos"], 2)  # v3, v4

    def test_missing_has_audio_and_duration_band_not_dominant(self):
        """
        Three dicts with only 'aspect' key should not produce fake dominant
        entries for has_audio or duration_band, and should report missing counts.
        """
        tags_list = [
            {"aspect": "9:16"},
            {"aspect": "9:16"},
            {"aspect": "9:16"},
        ]
        report = balance_report(tags_list)
        # Only aspect should be dominant
        dom_dims = {d["dimension"] for d in report["dominant"]}
        self.assertEqual(dom_dims, {"aspect"})
        # Missing counts should be reported for has_audio and duration_band
        self.assertEqual(report.get("missing_has_audio_count"), 3)
        self.assertEqual(report.get("missing_duration_band_count"), 3)
        # No fake dominant entries for has_audio or duration_band
        self.assertNotIn("has_audio", dom_dims)
        self.assertNotIn("duration_band", dom_dims)


if __name__ == "__main__":
    unittest.main()
