import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from PIL import Image

import animation_research as ar
from nvidia_scheduler import NvidiaScheduler, load_env_keys
from frame_selection import analyze_local_frames, build_selection


class ResearchTests(unittest.TestCase):
    def test_synthetic_video_coverage_and_timing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "synthetic.mp4"
            out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (160, 90))
            for frame in range(60):
                a = np.full((90, 160, 3), 50 if frame < 35 else 180, np.uint8)
                if 10 <= frame < 25:
                    cv2.rectangle(a, (50, 30 - (frame - 10), 60, 70), (255, 255, 255), -1)
                if 25 <= frame < 35:
                    a = np.roll(a, frame - 25, axis=1)
                if frame >= 45:
                    a = cv2.add(a, min(60, frame - 45))
                out.write(a)
            out.release()
            source = ar.discover(root)[0]
            folder, manifest = ar.prepare(source, root, root / "output")
            frames = manifest["frames"]
            self.assertEqual(frames[0]["frame"], 0)
            self.assertEqual(frames[-1]["frame"], 59)
            self.assertTrue(all(abs(f["time"] - f["frame"] / 10) < .01 for f in frames))
            self.assertTrue(any(10 <= f["frame"] <= 25 for f in frames))
            self.assertTrue(any(f["frame"] >= 35 for f in frames))
            self.assertTrue(any(f["frame"] >= 45 for f in frames))
            self.assertGreaterEqual(len(manifest["shot_starts"]), 2)
            self.assertTrue((folder / "contact_sheet.jpg").exists())

    def test_zip_order_and_unknown_timing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with zipfile.ZipFile(root / "frames.zip", "w") as z:
                for name, color in [("frame10.png", 200), ("frame2.png", 100), ("frame1.png", 0)]:
                    b = io.BytesIO(); Image.new("RGB", (20, 20), (color, color, color)).save(b, "PNG")
                    z.writestr(name, b.getvalue())
                z.writestr("../ignore.txt", "ignore")
            source = ar.discover(root)[0]
            self.assertEqual(source.entries, ["frame1.png", "frame2.png", "frame10.png"])
            folder, manifest = ar.prepare(source, root, root / "output")
            self.assertIsNone(manifest["metadata"]["fps"])
            self.assertTrue(all(f["time"] is None for f in manifest["frames"]))

    def test_invalid_json_and_resume_budget(self):
        group = {"frames": [{"frame": 1, "time": 0.1, "file": "x.jpg"}]}
        self.assertIsNone(ar.validate_report("not json", "v", group))
        self.assertIsNone(ar.validate_report(json.dumps({"video_id": "v"}), "v", group))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); source = root / "input"; source.mkdir()
            out = root / "output"
            with zipfile.ZipFile(source / "frames.zip", "w") as z:
                for i in range(2):
                    b = io.BytesIO(); Image.new("RGB", (20, 20), (i * 200, 0, 0)).save(b, "PNG")
                    z.writestr(f"f{i}.png", b.getvalue())
            ar.main(["--input", str(source), "--output", str(out), "--review", "--dry-run", "--max-api-calls", "0"])
            plan = ar.read_json(out / "RUN_PLAN.json", {})
            self.assertEqual(plan["planned_requests_this_run"], 0)
            folder = next(out.glob("frames_*"))
            state = ar.read_json(folder / "api_log.json", {})
            self.assertTrue(all(x["status"] == "PENDING" for x in state.values()))
            with patch.object(NvidiaScheduler, "call", side_effect=AssertionError("No API call expected")):
                ar.main(["--input", str(source), "--output", str(out), "--review", "--resume", "--max-api-calls", "0"])
            report = {k: "UNKNOWN" for k in ar.FIELDS}
            report.update({"video_id": folder.name, "scene_id": "pilot_storyboard", "granthstudio_capability": "UNKNOWN", "evidence_frames": []})
            state["pilot_storyboard"] = {"status": "COMPLETE", "report": report}
            report2 = dict(report, scene_id="pilot_action")
            state["pilot_action"] = {"status": "COMPLETE", "report": report2}
            ar.save_json(folder / "api_log.json", state)
            with patch.object(NvidiaScheduler, "call", side_effect=AssertionError("Completed jobs must not repeat")):
                ar.main(["--input", str(source), "--output", str(out), "--review", "--resume", "--max-api-calls", "20"])
            self.assertEqual(ar.read_json(out / "RUN_PLAN.json", {})["pending_groups"], 0)

    def test_fourteen_key_rolling_window_and_concurrency(self):
        now = [0.0]
        scheduler = NvidiaScheduler([f"test-key-{i}" for i in range(14)], clock=lambda: now[0], sleep=lambda _: None, max_calls=140, global_limit=140)
        with ThreadPoolExecutor(max_workers=14) as pool:
            slots = list(pool.map(lambda _: scheduler.acquire(), range(140)))
        self.assertEqual(len(slots), 140)
        self.assertEqual([slots.count(i) for i in range(14)], [10] * 14)
        self.assertEqual(scheduler.acquire(), None)
        with scheduler.lock:
            i, wait = scheduler._choose_at(59.9)
            self.assertIsNone(i)
            self.assertGreater(wait, 0)
            i, wait = scheduler._choose_at(60.0)
            self.assertIsNotNone(i)

    def test_429_global_pause_and_key_loader(self):
        class Response:
            status_code = 429
            headers = {"Retry-After": "75"}
        calls = []
        def post(*args, **kwargs):
            calls.append(kwargs["headers"]["Authorization"])
            return Response()
        scheduler = NvidiaScheduler([f"test-key-{i}" for i in range(14)], max_calls=1, post=post)
        result = scheduler.call([{"type": "text", "text": "test"}])
        self.assertEqual(result["status"], "PENDING_BUDGET")
        self.assertEqual(len(calls), 1)
        self.assertEqual(scheduler.snapshot()["available_keys"], 0)
        with tempfile.TemporaryDirectory() as td:
            env = Path(td) / ".env"
            env.write_text("\n".join(f"NVIDIA_API_KEY_{i:02d}=test-key-{i}" for i in range(1, 15)))
            self.assertEqual(len(load_env_keys(env)), 14)

    def test_global_http_budget(self):
        class Response:
            status_code = 200
            headers = {}
            def raise_for_status(self):
                pass
            def json(self):
                return {"choices": [{"message": {"content": "ok"}}], "usage": {"total_tokens": 1}}
        scheduler = NvidiaScheduler([f"test-key-{i}" for i in range(14)], max_calls=20, global_limit=20, post=lambda *a, **kw: Response())
        outcomes = []
        scheduler.run_jobs([{"content": [{"type": "text", "text": "test"}]} for _ in range(30)], lambda job, result, status: outcomes.append(result["status"]))
        self.assertEqual(scheduler.calls, 20)
        self.assertEqual(outcomes.count("OK"), 20)
        self.assertEqual(outcomes.count("PENDING_BUDGET"), 10)

    def test_payment_restriction_stops_all_keys(self):
        class Response:
            status_code = 402
            headers = {}
        calls = []
        def post(*args, **kwargs):
            calls.append(1)
            return Response()
        scheduler = NvidiaScheduler([f"test-key-{i}" for i in range(14)], post=post)
        self.assertEqual(scheduler.call([{"type": "text", "text": "test"}])["status"], "PAYMENT_RESTRICTION")
        self.assertEqual(scheduler.snapshot()["disabled_keys"], 14)
        self.assertEqual(scheduler.call([{"type": "text", "text": "test"}])["status"], "PENDING_BUDGET")
        self.assertEqual(len(calls), 1)

    def test_null_model_content_is_safe(self):
        class Response:
            status_code = 200
            headers = {}
            def raise_for_status(self):
                pass
            def json(self):
                return {"choices": [{"message": {"content": None}}], "usage": {"completion_tokens": 100}}
        scheduler = NvidiaScheduler(["test-key"], max_calls=1, post=lambda *a, **kw: Response())
        self.assertEqual(scheduler.call([{"type": "text", "text": "test"}])["text"], "")

    def test_saved_json_repair_precedes_image_resend(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / "video"; (folder / "raw_responses").mkdir(parents=True)
            group = {"id": "pilot_action", "frames": [{"frame": 15}]}
            manifest = {"video_id": "video"}
            state = {"pilot_action": {"status": "PENDING", "reason": "INVALID_JSON", "frames": [15]}}
            (folder / "raw_responses" / "pilot_action.txt").write_text('{"bad":')
            valid = {k: "UNKNOWN" for k in ar.FIELDS}
            valid.update({"video_id": "video", "scene_id": "pilot_action", "granthstudio_capability": "UNKNOWN", "evidence_frames": [15]})
            class Scheduler:
                calls = 0
                max_calls = 2
                def call(self, content, max_tokens):
                    self.calls += 1
                    self.content = content
                    return {"status": "OK", "text": json.dumps(valid), "usage": {"total_tokens": 5}}
            scheduler = Scheduler()
            item = (folder, manifest, state, group)
            self.assertEqual(ar.repair_saved_invalid([item], scheduler), [])
            self.assertEqual(state["pilot_action"]["status"], "COMPLETE")
            self.assertEqual(scheduler.calls, 1)
            self.assertEqual(ar.repair_saved_invalid([item], scheduler), [])
            self.assertEqual(scheduler.calls, 1)
            self.assertEqual((folder / "raw_responses" / "pilot_action.txt").read_text(), '{"bad":')

    def test_local_motion_sequences_and_pan(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root / "motion"; (folder / "selected_frames").mkdir(parents=True)
            base = np.full((108, 192, 3), 35, np.uint8)
            cv2.rectangle(base, (78, 25), (116, 96), (120, 120, 120), -1)
            for i in range(20):
                a = base.copy()
                if 5 <= i <= 11:
                    cv2.line(a, (90, 42), (90 + (i - 5) * 4, 68 - (i - 5) * 5), (235, 235, 235), 6)
                if 12 <= i <= 14:
                    cv2.rectangle(a, (78, 25 + (i - 11) * 4), (116, 96), (145, 145, 145), -1)
                if i >= 15:
                    cv2.circle(a, (96, 48), 4 if i % 2 else 2, (240, 240, 240), -1)
                cv2.imwrite(str(folder / "selected_frames" / f"frame_{i:08d}.jpg"), a)
            manifest = {"source": "unused", "kind": "sequence", "video_id": "motion", "frames": []}
            frames, cuts = analyze_local_frames(folder, manifest)
            self.assertTrue(any(frames[i]["motion_score"] > .035 for i in range(5, 12)))
            self.assertTrue(any(frames[i]["motion_score"] > .035 for i in range(12, 15)))
            selection = build_selection(folder, manifest)
            self.assertTrue(selection["events"])
            self.assertLessEqual(selection["overview_frames"], 12)
            self.assertTrue(all(b - a == 1 for a, b in zip(selection["primary_action_frames"], selection["primary_action_frames"][1:])))
            pan = root / "pan"; (pan / "selected_frames").mkdir(parents=True)
            rng = np.random.default_rng(3)
            base = rng.integers(30, 200, (108, 192, 3), dtype=np.uint8)
            for i in range(12):
                cv2.imwrite(str(pan / "selected_frames" / f"frame_{i:08d}.jpg"), np.roll(base, i * 2, axis=1))
            pframes, pcuts = analyze_local_frames(pan, manifest)
            self.assertEqual(len(pcuts), 1)
            self.assertLess(max(f["motion_score"] for f in pframes[1:]), .035)


if __name__ == "__main__":
    unittest.main()
