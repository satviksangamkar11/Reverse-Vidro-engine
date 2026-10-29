"""Unit tests for c1_cluster.py - Event Clustering & Representative Selection."""
from __future__ import annotations

import unittest

import c1_cluster


class TestClusterWindows(unittest.TestCase):
    """Tests for cluster_windows function."""

    def test_basic_clustering_worked_example(self):
        """Test the worked example from the spec with round-based score bands."""
        events = [
            {"event_id": "e1", "shot": "s1", "start_frame": 0, "end_frame": 30, "score": 0.92, "uncertain": False, "burst_frames": [0,15,30], "disposition": "PENDING_REVIEW"},
            {"event_id": "e2", "shot": "s1", "start_frame": 60, "end_frame": 90, "score": 0.88, "uncertain": True, "burst_frames": [60,75,90], "disposition": "PENDING_REVIEW"},
            {"event_id": "e3", "shot": "s2", "start_frame": 0, "end_frame": 15, "score": 0.45, "uncertain": False, "burst_frames": [0,7,15], "disposition": "PENDING_REVIEW"},
        ]
        features = [
            {"event_id": "e1", "mean_residual": 0.12, "peak_residual": 0.3, "direction_hint": "left", "region": "upper"},
            {"event_id": "e2", "mean_residual": 0.15, "peak_residual": 0.4, "direction_hint": "left", "region": "upper"},
            {"event_id": "e3", "mean_residual": 0.05, "peak_residual": 0.2, "direction_hint": "right", "region": "lower"},
        ]
        result = c1_cluster.cluster_windows(events, features)
        self.assertEqual(result["status"], "ok")
        # With round: e1->0.9, e2->0.9, e3->0.4 => 2 clusters
        self.assertEqual(len(result["clusters"]), 2)

        # Assert cluster order matches event processing order (e1/e2 cluster first, then e3)
        cluster_1 = result["clusters"][0]
        cluster_2 = result["clusters"][1]

        # First cluster: e1 and e2 (score_band 0.9)
        self.assertEqual(cluster_1["members"], ["e1", "e2"])
        self.assertEqual(cluster_1["signature"]["score_band"], 0.9)
        self.assertEqual(cluster_1["signature"]["duration_band"], 1.0)
        self.assertEqual(cluster_1["signature"]["residual_band"], 0.1)
        self.assertEqual(cluster_1["signature"]["direction_hint"], "left")
        self.assertEqual(cluster_1["signature"]["region"], "upper")
        self.assertEqual(cluster_1["cluster_id"], "C_0.9_1.0_0.1_left_upper")

        # Second cluster: e3 (score_band 0.4)
        self.assertEqual(cluster_2["members"], ["e3"])
        self.assertEqual(cluster_2["signature"]["score_band"], 0.4)
        self.assertEqual(cluster_2["signature"]["duration_band"], 0.5)
        self.assertEqual(cluster_2["signature"]["residual_band"], 0.0)
        self.assertEqual(cluster_2["signature"]["direction_hint"], "right")
        self.assertEqual(cluster_2["signature"]["region"], "lower")
        self.assertEqual(cluster_2["cluster_id"], "C_0.4_0.5_0.0_right_lower")

    def test_clustering_without_features(self):
        """Test clustering when features list is None - all events get none/none."""
        events = [
            {"event_id": "e1", "shot": "s1", "start_frame": 0, "end_frame": 30, "score": 0.92, "uncertain": False, "burst_frames": [], "disposition": "PENDING_REVIEW"},
            {"event_id": "e2", "shot": "s1", "start_frame": 60, "end_frame": 90, "score": 0.88, "uncertain": True, "burst_frames": [], "disposition": "PENDING_REVIEW"},
        ]
        result = c1_cluster.cluster_windows(events, features=None)
        self.assertEqual(result["status"], "ok")
        # With round: both e1 and e2 -> score_band 0.9, same duration/residual/direction/region => 1 cluster
        self.assertEqual(len(result["clusters"]), 1)
        cluster = result["clusters"][0]
        self.assertEqual(cluster["members"], ["e1", "e2"])
        self.assertEqual(cluster["signature"]["score_band"], 0.9)
        self.assertEqual(cluster["signature"]["duration_band"], 1.0)
        self.assertEqual(cluster["signature"]["residual_band"], 0.0)
        self.assertEqual(cluster["signature"]["direction_hint"], "none")
        self.assertEqual(cluster["signature"]["region"], "none")
        self.assertEqual(cluster["cluster_id"], "C_0.9_1.0_0.0_none_none")

    def test_clustering_empty_events(self):
        """Test clustering with empty events list."""
        result = c1_cluster.cluster_windows([])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["clusters"], [])

    def test_clustering_event_missing_event_id(self):
        """Test that events without event_id are skipped."""
        events = [
            {"event_id": "e1", "shot": "s1", "start_frame": 0, "end_frame": 30, "score": 0.92},
            {"shot": "s1", "start_frame": 60, "end_frame": 90, "score": 0.88},  # missing event_id
        ]
        result = c1_cluster.cluster_windows(events)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["clusters"]), 1)
        self.assertEqual(result["clusters"][0]["members"], ["e1"])

    def test_clustering_score_band_float_precision(self):
        """Test score band 0.3 doesn't produce floating point artifacts in cluster_id."""
        events = [
            {"event_id": "e1", "shot": "s1", "start_frame": 0, "end_frame": 30, "score": 0.3, "uncertain": False},
            {"event_id": "e2", "shot": "s1", "start_frame": 60, "end_frame": 90, "score": 0.3, "uncertain": False},
        ]
        result = c1_cluster.cluster_windows(events)
        self.assertEqual(len(result["clusters"]), 1)
        cluster_id = result["clusters"][0]["cluster_id"]
        # Should be "C_0.3_1.0_0.0_none_none" not "C_0.30000000000000004_..."
        self.assertEqual(cluster_id, "C_0.3_1.0_0.0_none_none")

    def test_clustering_residual_band_float_precision(self):
        """Test residual band 0.3 doesn't produce floating point artifacts."""
        events = [
            {"event_id": "e1", "shot": "s1", "start_frame": 0, "end_frame": 30, "score": 0.5, "uncertain": False},
        ]
        features = [
            {"event_id": "e1", "mean_residual": 0.3, "direction_hint": "none", "region": "none"},
        ]
        result = c1_cluster.cluster_windows(events, features)
        self.assertEqual(len(result["clusters"]), 1)
        cluster_id = result["clusters"][0]["cluster_id"]
        self.assertEqual(cluster_id, "C_0.5_1.0_0.3_none_none")

    def test_clustering_duration_band_boundaries(self):
        """Test duration bands at 14 frames (0.466s -> 0.0) and 15 frames (0.5s -> 0.5)."""
        events = [
            {"event_id": "e1", "shot": "s1", "start_frame": 0, "end_frame": 14, "score": 0.5, "uncertain": False},  # 14/30 = 0.466... -> floor to 0.0
            {"event_id": "e2", "shot": "s1", "start_frame": 0, "end_frame": 15, "score": 0.5, "uncertain": False},  # 15/30 = 0.5 -> floor to 0.5
        ]
        result = c1_cluster.cluster_windows(events)
        self.assertEqual(len(result["clusters"]), 2)
        # Assert order: e1 first (0.0), then e2 (0.5)
        self.assertEqual(result["clusters"][0]["signature"]["duration_band"], 0.0)
        self.assertEqual(result["clusters"][0]["members"], ["e1"])
        self.assertEqual(result["clusters"][1]["signature"]["duration_band"], 0.5)
        self.assertEqual(result["clusters"][1]["members"], ["e2"])


class TestPickRepresentatives(unittest.TestCase):
    """Tests for pick_representatives function."""

    def test_pick_representatives_worked_example(self):
        """Test the worked example from the spec - duplicates allowed."""
        cluster = {"cluster_id": "C_0.9_1.0_0.1_left_upper", "members": ["e1", "e2"], "signature": {}}
        events = [
            {"event_id": "e1", "score": 0.92, "uncertain": False},
            {"event_id": "e2", "score": 0.88, "uncertain": True},
        ]
        result = c1_cluster.pick_representatives(cluster, events)
        self.assertEqual(result["status"], "ok")
        reps = result["representatives"]
        self.assertEqual(reps["best"], "e1")
        self.assertEqual(reps["ambiguous"], "e2")
        self.assertEqual(reps["failure"], "e2")  # duplicate allowed per worked example

    def test_pick_representatives_no_uncertain_nearest_half(self):
        """Test ambiguous picks nearest to 0.5 when no uncertain, tie-break lower event_id."""
        cluster = {"cluster_id": "C_test", "members": ["e1", "e2", "e3"], "signature": {}}
        events = [
            {"event_id": "e1", "score": 0.9, "uncertain": False},
            {"event_id": "e2", "score": 0.25, "uncertain": False},  # dist 0.25
            {"event_id": "e3", "score": 0.75, "uncertain": False},  # dist 0.25, but e2 < e3
        ]
        result = c1_cluster.pick_representatives(cluster, events)
        self.assertEqual(result["representatives"]["best"], "e1")
        self.assertEqual(result["representatives"]["ambiguous"], "e2")  # tie-break lower id
        self.assertEqual(result["representatives"]["failure"], "e2")

    def test_pick_representatives_empty_members(self):
        """Test empty members list returns all None."""
        cluster = {"cluster_id": "C_test", "members": [], "signature": {}}
        events = []
        result = c1_cluster.pick_representatives(cluster, events)
        self.assertEqual(result["representatives"], {"best": None, "ambiguous": None, "failure": None})

    def test_pick_representatives_single_member(self):
        """Test single member returns same id for all three."""
        cluster = {"cluster_id": "C_test", "members": ["e1"], "signature": {}}
        events = [{"event_id": "e1", "score": 0.5, "uncertain": False}]
        result = c1_cluster.pick_representatives(cluster, events)
        self.assertEqual(result["representatives"], {"best": "e1", "ambiguous": "e1", "failure": "e1"})


class TestFpsFor(unittest.TestCase):
    """Tests for fps_for function."""

    def test_fps_for_worked_example_1(self):
        """Test worked example 1: duration=1.0s, score>=0.8 -> 8 fps."""
        event = {"event_id": "e1", "start_frame": 0, "end_frame": 30, "score": 0.92, "uncertain": False}
        result = c1_cluster.fps_for(event)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["fps"], 8)

    def test_fps_for_worked_example_2(self):
        """Test worked example 2: duration=0.5s, score<0.8, not uncertain -> 4 fps."""
        event = {"event_id": "e3", "start_frame": 0, "end_frame": 15, "score": 0.45, "uncertain": False}
        result = c1_cluster.fps_for(event)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["fps"], 4)

    def test_fps_for_score_exactly_0_8(self):
        """Test score exactly 0.8 triggers 8 fps."""
        event = {"event_id": "e1", "start_frame": 0, "end_frame": 30, "score": 0.8, "uncertain": False}
        result = c1_cluster.fps_for(event)
        self.assertEqual(result["fps"], 8)

    def test_fps_for_14_frames_duration_lt_0_5(self):
        """Test 14 frames (0.466s) triggers 8 fps due to duration < 0.5."""
        event = {"event_id": "e1", "start_frame": 0, "end_frame": 14, "score": 0.5, "uncertain": False}
        result = c1_cluster.fps_for(event)
        self.assertEqual(result["fps"], 8)

    def test_fps_for_uncertain_triggers_8(self):
        """Test uncertain=True triggers 8 fps regardless of other factors."""
        event = {"event_id": "e1", "start_frame": 0, "end_frame": 30, "score": 0.1, "uncertain": True}
        result = c1_cluster.fps_for(event)
        self.assertEqual(result["fps"], 8)

    def test_fps_for_missing_end_frame_defaults_to_0_5s(self):
        """Test missing end_frame defaults to start+15 giving 0.5s duration -> 4 fps if score<0.8."""
        event = {"event_id": "e1", "start_frame": 100, "score": 0.5, "uncertain": False}
        result = c1_cluster.fps_for(event)
        self.assertEqual(result["fps"], 4)


if __name__ == "__main__":
    unittest.main()
