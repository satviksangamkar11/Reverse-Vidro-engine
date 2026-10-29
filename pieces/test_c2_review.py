"""Unit tests for c2_review module."""
import math
import tempfile
import unittest

from c2_review import pick_representatives, fps_for, plan_review, reextract_cmd


class TestPickRepresentatives(unittest.TestCase):
    def test_pick_representatives_basic(self):
        cluster = {"cluster_id": "C1", "members": ["e1", "e2", "e3"], "signature": {}}
        events = [
            {"event_id": "e1", "score": 0.9, "uncertain": False},
            {"event_id": "e2", "score": 0.5, "uncertain": True},
            {"event_id": "e3", "score": 0.2, "uncertain": False},
        ]
        result = pick_representatives(cluster, events)
        reps = result["representatives"]
        self.assertEqual(reps["best"], "e1")
        self.assertEqual(reps["failure"], "e3")
        self.assertEqual(reps["ambiguous"], "e2")

    def test_pick_representatives_ambiguous_closest_to_05(self):
        cluster = {"cluster_id": "C1", "members": ["e1", "e2", "e3"], "signature": {}}
        events = [
            {"event_id": "e1", "score": 0.9, "uncertain": False},
            {"event_id": "e2", "score": 0.6, "uncertain": False},
            {"event_id": "e3", "score": 0.4, "uncertain": False},
        ]
        result = pick_representatives(cluster, events)
        reps = result["representatives"]
        # e3 (0.4) is closer to 0.5 than e2 (0.6) -> distance 0.1 vs 0.1, tie -> min picks first? min returns first encountered
        # Actually min with key returns first minimum. Both 0.1 away. e2 comes first in sorted_events? sorted by score desc: e1, e2, e3.
        # min over sorted_events: e2 (0.6, dist 0.1), e3 (0.4, dist 0.1) -> e2 wins.
        self.assertEqual(reps["ambiguous"], "e2")


class TestFpsFor(unittest.TestCase):
    def test_fps_for_uncertain(self):
        event = {"event_id": "e1", "score": 0.9, "uncertain": True, "start_frame": 0, "end_frame": 30}
        self.assertEqual(fps_for(event), 8)

    def test_fps_for_high_score_short_duration(self):
        event = {"event_id": "e1", "score": 0.85, "uncertain": False, "start_frame": 0, "end_frame": 30}
        self.assertEqual(fps_for(event), 8)

    def test_fps_for_high_score_long_duration(self):
        event = {"event_id": "e1", "score": 0.85, "uncertain": False, "start_frame": 0, "end_frame": 60}
        self.assertEqual(fps_for(event), 4)

    def test_fps_for_low_score(self):
        event = {"event_id": "e1", "score": 0.3, "uncertain": False, "start_frame": 0, "end_frame": 30}
        self.assertEqual(fps_for(event), 4)


class TestPlanReview(unittest.TestCase):
    def setUp(self):
        self.clusters = [
            {"cluster_id": "C_A", "members": ["e1", "e2", "e3", "e4", "e5"], "signature": {}},
            {"cluster_id": "C_B", "members": ["e6", "e7"], "signature": {}},
        ]
        self.events = [
            {"event_id": "e1", "score": 0.9, "uncertain": False, "disposition": "REVIEWED", "start_frame": 0, "end_frame": 30},
            {"event_id": "e2", "score": 0.5, "uncertain": True, "disposition": "PENDING_REVIEW", "start_frame": 30, "end_frame": 60},
            {"event_id": "e3", "score": 0.4, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 60, "end_frame": 90},
            {"event_id": "e4", "score": 0.3, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 90, "end_frame": 120},
            {"event_id": "e5", "score": 0.2, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 120, "end_frame": 150},
            {"event_id": "e6", "score": 0.8, "uncertain": False, "disposition": "REVIEWED", "start_frame": 0, "end_frame": 15},
            {"event_id": "e7", "score": 0.7, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 15, "end_frame": 30},
        ]
        self.reviewed_ids = {"e1", "e6"}

    def test_plan_review_worked_example(self):
        result = plan_review(self.clusters, self.events, self.reviewed_ids, budget=3)
        self.assertEqual(result["status"], "ok")
        jobs = result["jobs"]
        self.assertEqual(len(jobs), 3)
        # Check job order and reasons
        self.assertEqual(jobs[0]["event_id"], "e2")
        self.assertEqual(jobs[0]["reason"], "REPRESENTATIVE_AMBIGUOUS")
        self.assertEqual(jobs[0]["fps"], 8)  # uncertain
        self.assertEqual(jobs[1]["event_id"], "e5")
        self.assertEqual(jobs[1]["reason"], "REPRESENTATIVE_FAILURE")
        self.assertEqual(jobs[1]["fps"], 4)
        self.assertEqual(jobs[2]["event_id"], "e7")
        self.assertEqual(jobs[2]["reason"], "REPRESENTATIVE_AMBIGUOUS")
        self.assertEqual(jobs[2]["fps"], 4)  # score 0.7 < 0.8

        # No duplicate event_ids in jobs
        job_ids = [j["event_id"] for j in jobs]
        self.assertEqual(len(job_ids), len(set(job_ids)))

        inferred = result["inferred"]
        self.assertEqual(len(inferred), 2)
        inf_ids = {i["event_id"] for i in inferred}
        self.assertEqual(inf_ids, {"e3", "e4"})
        for inf in inferred:
            self.assertEqual(inf["disposition"], "INFERRED_FROM_CLUSTER")
            self.assertEqual(inf["basis_event_ids"], ["e1"])

        self.assertEqual(result["pending"], [])

    def test_plan_review_disagreement_expansion(self):
        # Two reviewed reps with different dispositions
        clusters = [{"cluster_id": "C1", "members": ["e1", "e2", "e3"], "signature": {}}]
        events = [
            {"event_id": "e1", "score": 0.9, "uncertain": False, "disposition": "REVIEWED", "start_frame": 0, "end_frame": 30},
            {"event_id": "e2", "score": 0.5, "uncertain": False, "disposition": "REVIEWED", "start_frame": 30, "end_frame": 60},
            {"event_id": "e3", "score": 0.4, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 60, "end_frame": 90},
        ]
        reviewed_ids = {"e1", "e2"}
        # Simulate different verdicts by using different disposition strings
        events[0]["disposition"] = "POSE_SWAP"
        events[1]["disposition"] = "CAMERA_MOVE"
        result = plan_review(clusters, events, reviewed_ids, budget=10)
        jobs = result["jobs"]
        # All unreviewed members become jobs with reason DISAGREEMENT
        job_ids = {j["event_id"] for j in jobs}
        self.assertEqual(job_ids, {"e3"})
        self.assertEqual(jobs[0]["reason"], "DISAGREEMENT")

    def test_plan_review_uncertain_reviewed_rep_expansion(self):
        # Reviewed rep has uncertain=True
        clusters = [{"cluster_id": "C1", "members": ["e1", "e2", "e3"], "signature": {}}]
        events = [
            {"event_id": "e1", "score": 0.9, "uncertain": True, "disposition": "REVIEWED", "start_frame": 0, "end_frame": 30},
            {"event_id": "e2", "score": 0.5, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 30, "end_frame": 60},
            {"event_id": "e3", "score": 0.4, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 60, "end_frame": 90},
        ]
        reviewed_ids = {"e1"}
        result = plan_review(clusters, events, reviewed_ids, budget=10)
        jobs = result["jobs"]
        job_ids = {j["event_id"] for j in jobs}
        self.assertEqual(job_ids, {"e2", "e3"})
        self.assertEqual(jobs[0]["reason"], "UNCERTAIN")

    def test_plan_review_budget_overflow(self):
        # Budget smaller than jobs
        result = plan_review(self.clusters, self.events, self.reviewed_ids, budget=2)
        jobs = result["jobs"]
        self.assertEqual(len(jobs), 2)
        # With deduplication, e7 appears only once in jobs (as REPRESENTATIVE_AMBIGUOUS)
        # Jobs order: e2 (REP_AMBIGUOUS), e5 (REP_FAILURE), e7 (REP_AMBIGUOUS)
        # Budget=2 -> e2, e5 within budget; e7 pending
        self.assertEqual(result["pending"], ["e7"])

    def test_plan_review_no_reviewed_reps(self):
        # No reviewed reps in cluster
        clusters = [{"cluster_id": "C1", "members": ["e1", "e2", "e3", "e4", "e5"], "signature": {}}]
        events = [
            {"event_id": "e1", "score": 0.9, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 0, "end_frame": 30},
            {"event_id": "e2", "score": 0.5, "uncertain": True, "disposition": "PENDING_REVIEW", "start_frame": 30, "end_frame": 60},
            {"event_id": "e3", "score": 0.4, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 60, "end_frame": 90},
            {"event_id": "e4", "score": 0.3, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 90, "end_frame": 120},
            {"event_id": "e5", "score": 0.2, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 120, "end_frame": 150},
        ]
        reviewed_ids = set()
        result = plan_review(clusters, events, reviewed_ids, budget=10)
        jobs = result["jobs"]
        # Representatives: e1 (best), e2 (ambiguous), e5 (failure) -> all unreviewed
        job_ids = {j["event_id"] for j in jobs}
        self.assertIn("e1", job_ids)
        self.assertIn("e2", job_ids)
        self.assertIn("e5", job_ids)
        # Verification: every 4th -> indices 0,4 -> e1, e5 (already jobs)
        # Inferred: e3, e4 with basis_event_ids = all reps [e1, e2, e5]
        inferred = result["inferred"]
        inf_ids = {i["event_id"] for i in inferred}
        self.assertEqual(inf_ids, {"e3", "e4"})
        for inf in inferred:
            self.assertEqual(set(inf["basis_event_ids"]), {"e1", "e2", "e5"})

    def test_plan_review_cross_cluster_rep_ordering(self):
        # Representatives from all clusters come before verification from any cluster
        clusters = [
            {"cluster_id": "C_A", "members": ["a1", "a2", "a3", "a4", "a5"], "signature": {}},
            {"cluster_id": "C_B", "members": ["b1", "b2", "b3", "b4", "b5"], "signature": {}},
        ]
        events = [
            {"event_id": "a1", "score": 0.9, "uncertain": False, "disposition": "REVIEWED", "start_frame": 0, "end_frame": 30},
            {"event_id": "a2", "score": 0.5, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 30, "end_frame": 60},
            {"event_id": "a3", "score": 0.4, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 60, "end_frame": 90},
            {"event_id": "a4", "score": 0.3, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 90, "end_frame": 120},
            {"event_id": "a5", "score": 0.2, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 120, "end_frame": 150},
            {"event_id": "b1", "score": 0.9, "uncertain": False, "disposition": "REVIEWED", "start_frame": 0, "end_frame": 30},
            {"event_id": "b2", "score": 0.5, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 30, "end_frame": 60},
            {"event_id": "b3", "score": 0.4, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 60, "end_frame": 90},
            {"event_id": "b4", "score": 0.3, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 90, "end_frame": 120},
            {"event_id": "b5", "score": 0.2, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 120, "end_frame": 150},
        ]
        reviewed_ids = {"a1", "b1"}
        # Budget tight: only 3 jobs allowed
        # Reps: C_A: a2 (ambiguous), a5 (failure); C_B: b2 (ambiguous), b5 (failure)
        # Verification: C_A: a5 (already rep), C_B: b5 (already rep)
        # Total rep jobs: 4 (a2, a5, b2, b5). Budget=3 -> first 3 reps by cluster_id then rep priority
        # C_A reps: a2 (ambiguous, priority 1), a5 (failure, priority 2)
        # C_B reps: b2 (ambiguous, priority 1), b5 (failure, priority 2)
        # Sorted: (group=0, C_A, 1, a2), (group=0, C_A, 2, a5), (group=0, C_B, 1, b2), (group=0, C_B, 2, b5)
        # Budget=3 -> a2, a5, b2 within budget; b5 pending
        result = plan_review(clusters, events, reviewed_ids, budget=3)
        jobs = result["jobs"]
        self.assertEqual(len(jobs), 3)
        job_ids = [j["event_id"] for j in jobs]
        self.assertEqual(job_ids, ["a2", "a5", "b2"])
        self.assertEqual(result["pending"], ["b5"])

    def test_plan_review_negative_budget(self):
        # Negative budget should be clamped to 0
        result = plan_review(self.clusters, self.events, self.reviewed_ids, budget=-5)
        self.assertEqual(result["jobs"], [])
        self.assertEqual(result["pending"], ["e2", "e5", "e7"])

    def test_plan_review_min_one_verification(self):
        # Cluster where every 4th member is already a rep job, but other unreviewed members exist
        # Per spec worked example: sampling hits rep jobs, no separate verification job created
        clusters = [{"cluster_id": "C1", "members": ["e1", "e2", "e3", "e4", "e5"], "signature": {}}]
        events = [
            {"event_id": "e1", "score": 0.9, "uncertain": False, "disposition": "REVIEWED", "start_frame": 0, "end_frame": 30},
            {"event_id": "e2", "score": 0.5, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 30, "end_frame": 60},
            {"event_id": "e3", "score": 0.4, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 60, "end_frame": 90},
            {"event_id": "e4", "score": 0.3, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 90, "end_frame": 120},
            {"event_id": "e5", "score": 0.2, "uncertain": False, "disposition": "PENDING_REVIEW", "start_frame": 120, "end_frame": 150},
        ]
        reviewed_ids = {"e1"}
        # Reps: best=e1 (reviewed), ambiguous=e2, failure=e5
        # Verification indices: 0,4 -> e1 (reviewed), e5 (already rep job)
        # No verification job added (sampled members are reviewed or already jobs)
        # Inferred: e3, e4 with basis_event_ids = [e1]
        result = plan_review(clusters, events, reviewed_ids, budget=10)
        jobs = result["jobs"]
        job_ids = {j["event_id"] for j in jobs}
        self.assertIn("e2", job_ids)  # REPRESENTATIVE_AMBIGUOUS
        self.assertIn("e5", job_ids)  # REPRESENTATIVE_FAILURE
        # No VERIFICATION job (sampling hit reviewed/rep members)
        verification_jobs = [j for j in jobs if j["reason"] == "VERIFICATION"]
        self.assertEqual(len(verification_jobs), 0)
        # e3, e4 should be inferred
        inferred = result["inferred"]
        inf_ids = {i["event_id"] for i in inferred}
        self.assertEqual(inf_ids, {"e3", "e4"})


class TestReextractCmd(unittest.TestCase):
    def test_reextract_cmd_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = f"{tmpdir}/video.mp4"
            event = {"event_id": "e1", "start_frame": 0, "end_frame": 30}
            fps = 8
            out_dir = f"{tmpdir}/frames"
            result = reextract_cmd(source, event, fps, out_dir)
            self.assertEqual(result["status"], "ok")
            argv = result["argv"]
            self.assertEqual(argv[0], "ffmpeg")
            self.assertEqual(argv[1], "-y")
            self.assertEqual(argv[2], "-ss")
            self.assertEqual(argv[3], "0.0")  # str(0.0) not "0.000"
            self.assertEqual(argv[4], "-i")
            self.assertEqual(argv[5], source)
            self.assertEqual(argv[6], "-vf")
            self.assertEqual(argv[7], "fps=8")
            self.assertEqual(argv[8], "-frames:v")
            self.assertEqual(argv[9], "9")  # ceil(1.0 * 8) + 1 = 9
            self.assertEqual(argv[10], f"{out_dir}/frame_%04d.png")

    def test_reextract_cmd_nonzero_start(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = f"{tmpdir}/video.mp4"
            event = {"event_id": "e1", "start_frame": 30, "end_frame": 60}
            fps = 4
            out_dir = f"{tmpdir}/frames"
            result = reextract_cmd(source, event, fps, out_dir)
            argv = result["argv"]
            self.assertEqual(argv[3], "1.0")  # 30/30 = 1.0
            duration = (60 - 30) / 30.0  # 1.0
            num_frames = math.ceil(duration * 4) + 1  # 5
            self.assertEqual(argv[9], str(num_frames))

    def test_reextract_cmd_fractional_duration(self):
        # Non-integral duration * fps to exercise ceiling
        with tempfile.TemporaryDirectory() as tmpdir:
            source = f"{tmpdir}/video.mp4"
            event = {"event_id": "e1", "start_frame": 0, "end_frame": 12}  # 0.4 sec
            fps = 8
            out_dir = f"{tmpdir}/frames"
            result = reextract_cmd(source, event, fps, out_dir)
            argv = result["argv"]
            # duration = 0.4, 0.4 * 8 = 3.2, ceil = 4, +1 = 5
            self.assertEqual(argv[9], "5")
            self.assertEqual(argv[3], "0.0")

    def test_reextract_cmd_invalid_end_before_start(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = f"{tmpdir}/video.mp4"
            event = {"event_id": "e1", "start_frame": 60, "end_frame": 30}
            fps = 8
            out_dir = f"{tmpdir}/frames"
            result = reextract_cmd(source, event, fps, out_dir)
            self.assertEqual(result["status"], "ERROR")
            self.assertIn("end_frame < start_frame", result["error"])

    def test_reextract_cmd_invalid_fps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = f"{tmpdir}/video.mp4"
            event = {"event_id": "e1", "start_frame": 0, "end_frame": 30}
            fps = 6
            out_dir = f"{tmpdir}/frames"
            result = reextract_cmd(source, event, fps, out_dir)
            self.assertEqual(result["status"], "ERROR")
            self.assertIn("fps must be 4 or 8", result["error"])


if __name__ == "__main__":
    unittest.main()
