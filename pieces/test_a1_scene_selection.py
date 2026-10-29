import unittest
import tempfile
import os
import json
from a1_scene_selection import select_scenes, freeze_baseline, check_baseline

class TestSelectScenes(unittest.TestCase):
    def test_select_scenes_success(self):
        catalog = [
            {"scene_id": "s1", "category": "dialogue"},
            {"scene_id": "s2", "category": "interaction"},
            {"scene_id": "s3", "category": "gesture"},
            {"scene_id": "s4", "category": "environment"},
            {"scene_id": "s5", "category": "discourse"},
            {"scene_id": "s6", "category": "complex_transition"},
            {"scene_id": "s7", "category": "dialogue"}
        ]
        result = select_scenes(catalog, n=6)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["selected"], {
            "dialogue": "s1",
            "interaction": "s2",
            "gesture": "s3",
            "environment": "s4",
            "discourse": "s5",
            "complex_transition": "s6"
        })
        self.assertIsNone(result["error"])

    def test_select_scenes_missing_categories(self):
        catalog = [
            {"scene_id": "s1", "category": "dialogue"},
            {"scene_id": "s2", "category": "interaction"}
        ]
        result = select_scenes(catalog, n=6)
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["selected"])
        self.assertIn("Missing categories: gesture, environment, discourse, complex_transition", result["error"])

    def test_select_scenes_n_not_six_raises(self):
        catalog = [
            {"scene_id": "s1", "category": "dialogue"},
            {"scene_id": "s2", "category": "interaction"},
            {"scene_id": "s3", "category": "gesture"},
            {"scene_id": "s4", "category": "environment"},
            {"scene_id": "s5", "category": "discourse"},
            {"scene_id": "s6", "category": "complex_transition"}
        ]
        with self.assertRaises(ValueError) as cm:
            select_scenes(catalog, n=5)
        self.assertEqual(str(cm.exception), "n must be 6")

    def test_select_scenes_first_match_per_category(self):
        catalog = [
            {"scene_id": "s1", "category": "dialogue"},
            {"scene_id": "s2", "category": "dialogue"},
            {"scene_id": "s3", "category": "interaction"},
            {"scene_id": "s4", "category": "gesture"},
            {"scene_id": "s5", "category": "environment"},
            {"scene_id": "s6", "category": "discourse"},
            {"scene_id": "s7", "category": "complex_transition"}
        ]
        result = select_scenes(catalog, n=6)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["selected"]["dialogue"], "s1")

    def test_select_scenes_non_dict_items_ignored(self):
        catalog = [
            "not a dict",
            {"scene_id": "s1", "category": "dialogue"},
            None,
            {"scene_id": "s2", "category": "interaction"},
            {"scene_id": "s3", "category": "gesture"},
            {"scene_id": "s4", "category": "environment"},
            {"scene_id": "s5", "category": "discourse"},
            {"scene_id": "s6", "category": "complex_transition"}
        ]
        result = select_scenes(catalog, n=6)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["selected"]["dialogue"], "s1")

class TestFreezeBaseline(unittest.TestCase):
    def test_freeze_baseline_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = os.path.join(tmpdir, "prompts")
            os.makedirs(prompts_dir)
            out_json = os.path.join(tmpdir, "baseline_hashes.json")
            
            # Create test files
            with open(os.path.join(prompts_dir, "stage1_prompt.txt"), "w") as f:
                f.write("STAGE1 CONTENT")
            with open(os.path.join(prompts_dir, "stage2_prompt.txt"), "w") as f:
                f.write("STAGE2 CONTENT")
            with open(os.path.join(prompts_dir, "schema.json"), "w") as f:
                f.write('{"type": "object"}')
            
            def mock_read_file(path):
                with open(path, "r") as f:
                    return f.read()
            
            def mock_hash(content):
                import hashlib
                return hashlib.sha256(content.encode()).hexdigest()
            
            result = freeze_baseline(prompts_dir, out_json, mock_read_file, mock_hash)
            self.assertEqual(result["status"], "ok")
            self.assertIsNotNone(result["hashes"])
            self.assertIsNone(result["error"])
            
            # Verify the output file was written correctly
            self.assertTrue(os.path.exists(out_json))
            with open(out_json, "r") as f:
                saved = json.load(f)
            self.assertEqual(saved, result["hashes"])
            self.assertIn("stage1_prompt", saved)
            self.assertIn("stage2_prompt", saved)
            self.assertIn("schema", saved)

    def test_freeze_baseline_error_on_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = os.path.join(tmpdir, "prompts")
            os.makedirs(prompts_dir)
            out_json = os.path.join(tmpdir, "baseline_hashes.json")
            
            def mock_read_file(path):
                raise FileNotFoundError("File not found")
            
            def mock_hash(content):
                return "hash"
            
            result = freeze_baseline(prompts_dir, out_json, mock_read_file, mock_hash)
            self.assertEqual(result["status"], "error")
            self.assertIsNone(result["hashes"])
            self.assertIn("File not found", result["error"])

    def test_freeze_baseline_write_failure_returns_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = os.path.join(tmpdir, "prompts")
            os.makedirs(prompts_dir)
            # Create test files
            with open(os.path.join(prompts_dir, "stage1_prompt.txt"), "w") as f:
                f.write("STAGE1 CONTENT")
            with open(os.path.join(prompts_dir, "stage2_prompt.txt"), "w") as f:
                f.write("STAGE2 CONTENT")
            with open(os.path.join(prompts_dir, "schema.json"), "w") as f:
                f.write('{"type": "object"}')
            
            # out_json points to a directory (not writable as file)
            out_json = os.path.join(tmpdir, "not_a_file")
            os.makedirs(out_json)  # Create as directory to cause write failure
            
            def mock_read_file(path):
                with open(path, "r") as f:
                    return f.read()
            
            def mock_hash(content):
                import hashlib
                return hashlib.sha256(content.encode()).hexdigest()
            
            result = freeze_baseline(prompts_dir, out_json, mock_read_file, mock_hash)
            self.assertEqual(result["status"], "error")
            self.assertIsNone(result["hashes"])
            self.assertIn("Failed to write baseline file", result["error"])

class TestCheckBaseline(unittest.TestCase):
    def test_check_baseline_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = os.path.join(tmpdir, "prompts")
            os.makedirs(prompts_dir)
            baseline_json = os.path.join(tmpdir, "baseline_hashes.json")
            
            # Create test files
            with open(os.path.join(prompts_dir, "stage1_prompt.txt"), "w") as f:
                f.write("STAGE1 CONTENT")
            with open(os.path.join(prompts_dir, "stage2_prompt.txt"), "w") as f:
                f.write("STAGE2 CONTENT")
            with open(os.path.join(prompts_dir, "schema.json"), "w") as f:
                f.write('{"type": "object"}')
            
            def mock_read_file(path):
                with open(path, "r") as f:
                    return f.read()
            
            def mock_hash(content):
                import hashlib
                return hashlib.sha256(content.encode()).hexdigest()
            
            # First freeze the baseline
            freeze_result = freeze_baseline(prompts_dir, baseline_json, mock_read_file, mock_hash)
            self.assertEqual(freeze_result["status"], "ok")
            
            # Now check it
            result = check_baseline(prompts_dir, baseline_json, mock_read_file, mock_hash)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["matches"], {
                "stage1_prompt": True,
                "stage2_prompt": True,
                "schema": True
            })
            self.assertIsNone(result["error"])

    def test_check_baseline_drift(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = os.path.join(tmpdir, "prompts")
            os.makedirs(prompts_dir)
            baseline_json = os.path.join(tmpdir, "baseline_hashes.json")
            
            # Create test files with modified stage1
            with open(os.path.join(prompts_dir, "stage1_prompt.txt"), "w") as f:
                f.write("STAGE1 MODIFIED")
            with open(os.path.join(prompts_dir, "stage2_prompt.txt"), "w") as f:
                f.write("STAGE2 CONTENT")
            with open(os.path.join(prompts_dir, "schema.json"), "w") as f:
                f.write('{"type": "object"}')
            
            # Create baseline with original hashes
            original_hashes = {
                "stage1_prompt": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "stage2_prompt": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "schema": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
            }
            with open(baseline_json, "w") as f:
                json.dump(original_hashes, f)
            
            def mock_read_file(path):
                with open(path, "r") as f:
                    return f.read()
            
            def mock_hash(content):
                return {
                    "STAGE1 MODIFIED": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
                    "STAGE2 CONTENT": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    '{"type": "object"}': "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
                }[content]
            
            result = check_baseline(prompts_dir, baseline_json, mock_read_file, mock_hash)
            self.assertEqual(result["status"], "error")
            self.assertEqual(result["matches"], {
                "stage1_prompt": False,
                "stage2_prompt": True,
                "schema": True
            })
            self.assertEqual(result["error"], "Baseline drift detected: stage1_prompt")

    def test_check_baseline_error_on_missing_baseline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = os.path.join(tmpdir, "prompts")
            os.makedirs(prompts_dir)
            baseline_json = os.path.join(tmpdir, "nonexistent_baseline.json")
            
            def mock_read_file(path):
                if path == baseline_json:
                    raise FileNotFoundError("Baseline not found")
                return "content"
            
            def mock_hash(content):
                return "hash"
            
            result = check_baseline(prompts_dir, baseline_json, mock_read_file, mock_hash)
            self.assertEqual(result["status"], "error")
            self.assertIsNone(result["matches"])
            self.assertIn("Baseline not found", result["error"])

if __name__ == "__main__":
    unittest.main()
