import unittest
from a2_recipe_prompts import select_recipes, build_prompts


class TestSelectRecipes(unittest.TestCase):
    def setUp(self):
        self.playbook_recipes = [
            {"recipe_id": "r1", "category": "dialogue", "purpose": "character speaking", "text": "Recipe 1: Detailed dialogue technique for character speaking scenes. " * 10},
            {"recipe_id": "r2", "category": "gesture", "purpose": "dialogue emphasis", "text": "Recipe 2: Gesture techniques for dialogue emphasis."},
            {"recipe_id": "r3", "category": "dialogue", "purpose": "subtext", "text": "Recipe 3: Subtext in dialogue."},
            {"recipe_id": "r4", "category": "action", "purpose": "fight choreography", "text": "Recipe 4: Fight scenes."}
        ]
        self.scene = {"scene_id": "s1", "category": "dialogue"}

    def test_select_recipes_worked_example(self):
        """Test the exact worked example from the spec (with 200-char per-recipe truncation)."""
        result = select_recipes(self.playbook_recipes, self.scene, limit=5, max_chars=2500)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["selected_recipe_ids"], ["r1", "r2", "r3"])
        # Recipe 1 text is 690 chars, truncated to 200 (197 + "...")
        # Recipe 2: ~45 chars, Recipe 3: ~28 chars, separators: 10 chars
        # Total: 200 + 5 + 45 + 5 + 28 = 283
        r1_full = "Recipe 1: Detailed dialogue technique for character speaking scenes. " * 10
        r1_compact = r1_full[:197] + "..."
        r2_text = "Recipe 2: Gesture techniques for dialogue emphasis."
        r3_text = "Recipe 3: Subtext in dialogue."
        expected_compact = f"{r1_compact}\n---\n{r2_text}\n---\n{r3_text}"
        self.assertEqual(result["compact_text"], expected_compact)
        self.assertEqual(result["total_chars"], len(expected_compact))
        self.assertIsNone(result["error"])

    def test_select_recipes_limit(self):
        """Test that limit restricts number of selected recipes."""
        result = select_recipes(self.playbook_recipes, self.scene, limit=2, max_chars=2500)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["selected_recipe_ids"]), 2)
        self.assertEqual(result["selected_recipe_ids"], ["r1", "r2"])

    def test_select_recipes_max_chars_truncation_single_recipe(self):
        """Test truncation when a single recipe exceeds max_chars."""
        long_recipes = [
            {"recipe_id": "r1", "category": "dialogue", "purpose": "speaking", "text": "A" * 300},
        ]
        scene = {"scene_id": "s1", "category": "dialogue"}
        result = select_recipes(long_recipes, scene, limit=5, max_chars=150)
        self.assertEqual(result["status"], "ok")
        self.assertLessEqual(result["total_chars"], 150)
        self.assertEqual(result["selected_recipe_ids"], ["r1"])
        # Should be truncated to 150 chars (147 + "...")
        self.assertTrue(result["compact_text"].endswith("..."))
        self.assertEqual(len(result["compact_text"]), 150)

    def test_select_recipes_max_chars_truncation_multi_recipe_overflow(self):
        """Test truncation when prefix exceeds max_chars (overflow rebuild branch)."""
        # Three recipes, each compacted to 200 chars, separator is 5 chars
        # Total would be 200 + 5 + 200 + 5 + 200 = 610
        # Set max_chars=300 so we can only fit first recipe + part of second
        recipes = [
            {"recipe_id": "r1", "category": "dialogue", "purpose": "speaking", "text": "A" * 300},  # compacted to 200
            {"recipe_id": "r2", "category": "dialogue", "purpose": "speaking", "text": "B" * 300},  # compacted to 200
            {"recipe_id": "r3", "category": "dialogue", "purpose": "speaking", "text": "C" * 300},  # compacted to 200
        ]
        scene = {"scene_id": "s1", "category": "dialogue"}
        result = select_recipes(recipes, scene, limit=5, max_chars=300)
        self.assertEqual(result["status"], "ok")
        self.assertLessEqual(result["total_chars"], 300)
        # Should have r1 (200) + separator (5) + truncated r2 (95) = 300
        self.assertEqual(result["selected_recipe_ids"], ["r1", "r2"])
        self.assertIn("\n---\n", result["compact_text"])
        # Verify exact structure: r1 + separator + truncated r2
        parts = result["compact_text"].split("\n---\n")
        self.assertEqual(len(parts), 2)
        self.assertEqual(len(parts[0]), 200)  # r1 full
        self.assertEqual(len(parts[1]), 95)   # r2 truncated to fit

    def test_select_recipes_compact_200_chars(self):
        """Test each recipe text is compacted to max 200 chars."""
        long_text = "X" * 300
        recipes = [{"recipe_id": "r1", "category": "dialogue", "purpose": "speaking", "text": long_text}]
        scene = {"scene_id": "s1", "category": "dialogue"}
        result = select_recipes(recipes, scene, limit=5, max_chars=2500)
        self.assertEqual(result["status"], "ok")
        # Should be truncated to 197 + "..." = 200
        self.assertLessEqual(len(result["compact_text"]), 200)
        self.assertTrue(result["compact_text"].endswith("..."))

    def test_select_recipes_case_insensitive_purpose(self):
        """Test purpose matching is case-insensitive."""
        recipes = [
            {"recipe_id": "r1", "category": "other", "purpose": "DIALOGUE emphasis", "text": "Recipe for dialogue."},
        ]
        scene = {"scene_id": "s1", "category": "dialogue"}
        result = select_recipes(recipes, scene, limit=5, max_chars=2500)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["selected_recipe_ids"], ["r1"])

    def test_select_recipes_empty_scene_category(self):
        """Test behavior when scene category is empty string."""
        recipes = [
            {"recipe_id": "r1", "category": "dialogue", "purpose": "speaking", "text": "Recipe."},
        ]
        scene = {"scene_id": "s1", "category": ""}
        result = select_recipes(recipes, scene, limit=5, max_chars=2500)
        self.assertEqual(result["status"], "ok")
        # Empty category should not match (guarded by `if scene_category`)
        self.assertEqual(result["selected_recipe_ids"], [])

    def test_select_recipes_invalid_playbook_recipes(self):
        """Test error when playbook_recipes is not a list."""
        result = select_recipes("not a list", self.scene)
        self.assertEqual(result["status"], "error")
        self.assertIn("playbook_recipes must be a list", result["error"])

    def test_select_recipes_invalid_scene(self):
        """Test error when scene is not a dict or missing category."""
        result = select_recipes(self.playbook_recipes, "not a dict")
        self.assertEqual(result["status"], "error")
        self.assertIn("scene must be a dict", result["error"])

        result = select_recipes(self.playbook_recipes, {"scene_id": "s1"})
        self.assertEqual(result["status"], "error")
        self.assertIn("scene must be a dict with 'category' key", result["error"])

    def test_select_recipes_invalid_limit(self):
        """Test error when limit is negative."""
        result = select_recipes(self.playbook_recipes, self.scene, limit=-1)
        self.assertEqual(result["status"], "error")
        self.assertIn("limit must be a non-negative integer", result["error"])

    def test_select_recipes_invalid_max_chars(self):
        """Test error when max_chars is negative."""
        result = select_recipes(self.playbook_recipes, self.scene, max_chars=-1)
        self.assertEqual(result["status"], "error")
        self.assertIn("max_chars must be a non-negative integer", result["error"])

    def test_select_recipes_deterministic_sort(self):
        """Test recipes are sorted by recipe_id for determinism."""
        recipes = [
            {"recipe_id": "r3", "category": "dialogue", "purpose": "speaking", "text": "Recipe 3"},
            {"recipe_id": "r1", "category": "dialogue", "purpose": "speaking", "text": "Recipe 1"},
            {"recipe_id": "r2", "category": "dialogue", "purpose": "speaking", "text": "Recipe 2"},
        ]
        scene = {"scene_id": "s1", "category": "dialogue"}
        result = select_recipes(recipes, scene, limit=5, max_chars=2500)
        self.assertEqual(result["selected_recipe_ids"], ["r1", "r2", "r3"])

    def test_select_recipes_no_matches(self):
        """Test when no recipes match the scene category."""
        recipes = [
            {"recipe_id": "r1", "category": "action", "purpose": "fight", "text": "Recipe 1"},
        ]
        scene = {"scene_id": "s1", "category": "dialogue"}
        result = select_recipes(recipes, scene, limit=5, max_chars=2500)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["selected_recipe_ids"], [])
        self.assertEqual(result["compact_text"], "")
        self.assertEqual(result["total_chars"], 0)

    def test_select_recipes_none_values_coerced(self):
        """Test that None values in category/purpose/text are handled gracefully."""
        recipes = [
            {"recipe_id": "r1", "category": None, "purpose": "dialogue test", "text": "Recipe 1"},
            {"recipe_id": "r2", "category": "dialogue", "purpose": None, "text": "Recipe 2"},
            {"recipe_id": "r3", "category": "dialogue", "purpose": "test", "text": None},
        ]
        scene = {"scene_id": "s1", "category": "dialogue"}
        result = select_recipes(recipes, scene, limit=5, max_chars=2500)
        self.assertEqual(result["status"], "ok")
        # r1 matches via purpose, r2 matches via category, r3 matches via category
        self.assertEqual(set(result["selected_recipe_ids"]), {"r1", "r2", "r3"})
        # r3 text should be treated as empty string
        self.assertIn("Recipe 1", result["compact_text"])
        self.assertIn("Recipe 2", result["compact_text"])

    def test_select_recipes_overflow_negative_text_avail(self):
        """Test overflow rebuild branch handles negative text_avail correctly (3 recipes of 30 chars, max_chars=34)."""
        recipes = [
            {"recipe_id": "r1", "category": "dialogue", "purpose": "speaking", "text": "A" * 30},
            {"recipe_id": "r2", "category": "dialogue", "purpose": "speaking", "text": "B" * 30},
            {"recipe_id": "r3", "category": "dialogue", "purpose": "speaking", "text": "C" * 30},
        ]
        scene = {"scene_id": "s1", "category": "dialogue"}
        result = select_recipes(recipes, scene, limit=5, max_chars=34)
        self.assertEqual(result["status"], "ok")
        self.assertLessEqual(result["total_chars"], 34)
        # Should fit r1 (30) + separator (5) = 35 > 34, so only r1 fits
        # Actually r1=30, then separator=5, remaining=34-30=4, text_avail=4-5=-1 <=0, break
        # So only r1 should be included
        self.assertEqual(result["selected_recipe_ids"], ["r1"])
        self.assertEqual(result["compact_text"], "A" * 30)

    def test_select_recipes_available_zero_exact_fit(self):
        """Test when prefix exactly fills max_chars (available == 0), last recipe omitted."""
        # Two 30-char recipes, max_chars=35: r1 (30) + separator (5) = 35 exactly
        recipes = [
            {"recipe_id": "r1", "category": "dialogue", "purpose": "speaking", "text": "A" * 30},
            {"recipe_id": "r2", "category": "dialogue", "purpose": "speaking", "text": "B" * 30},
        ]
        scene = {"scene_id": "s1", "category": "dialogue"}
        result = select_recipes(recipes, scene, limit=5, max_chars=35)
        self.assertEqual(result["status"], "ok")
        self.assertLessEqual(result["total_chars"], 35)
        # Only r1 should be included, no trailing separator
        self.assertEqual(result["selected_recipe_ids"], ["r1"])
        self.assertEqual(result["compact_text"], "A" * 30)

    def test_select_recipes_non_string_values_coerced(self):
        """Test that non-string category/purpose/text are coerced to empty string (not stringified)."""
        recipes = [
            {"recipe_id": "r1", "category": 5, "purpose": "dialogue test", "text": "Recipe 1"},
            {"recipe_id": "r2", "category": "dialogue", "purpose": 123, "text": "Recipe 2"},
            {"recipe_id": "r3", "category": "dialogue", "purpose": "test", "text": 456},
        ]
        scene = {"scene_id": "s1", "category": "dialogue"}
        result = select_recipes(recipes, scene, limit=5, max_chars=2500)
        self.assertEqual(result["status"], "ok")
        # r1: category=5 (non-str -> "") != "dialogue", purpose contains "dialogue" -> match
        # r2: category="dialogue" -> match
        # r3: category="dialogue" -> match
        self.assertEqual(set(result["selected_recipe_ids"]), {"r1", "r2", "r3"})
        self.assertIn("Recipe 1", result["compact_text"])
        self.assertIn("Recipe 2", result["compact_text"])
        # r3 text is non-str -> treated as empty string
        self.assertNotIn("456", result["compact_text"])

    def test_select_recipes_max_chars_zero(self):
        """Test max_chars=0 returns empty text and no recipe IDs."""
        recipes = [
            {"recipe_id": "r1", "category": "dialogue", "purpose": "speaking", "text": "Recipe 1"},
        ]
        scene = {"scene_id": "s1", "category": "dialogue"}
        result = select_recipes(recipes, scene, limit=5, max_chars=0)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["selected_recipe_ids"], [])
        self.assertEqual(result["compact_text"], "")
        self.assertEqual(result["total_chars"], 0)


class TestBuildPrompts(unittest.TestCase):
    def setUp(self):
        self.base_prompt = "Create a shot plan for the scene."
        self.recipes_result_ok = {
            "status": "ok",
            "selected_recipe_ids": ["r1", "r2"],
            "compact_text": "Recipe 1 text.\n---\nRecipe 2 text.",
            "total_chars": 32,
            "error": None
        }

    def test_build_prompts_basic(self):
        """Test basic A and B prompt construction."""
        result = build_prompts(self.base_prompt, self.recipes_result_ok)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["A_prompt"], self.base_prompt)
        expected_B = (
            self.base_prompt
            + "\n\n=== READ-ONLY RESEARCH HINTS ===\n"
            + "Recipe 1 text.\n---\nRecipe 2 text."
            + "\n=== END RESEARCH HINTS ==="
        )
        self.assertEqual(result["B_prompt"], expected_B)
        self.assertEqual(result["extra_tokens_estimate"], 32 // 4)
        self.assertIsNone(result["error"])

    def test_build_prompts_error_recipes_result(self):
        """Test error when recipes_result status is error."""
        recipes_result_bad = {"status": "error", "compact_text": None, "error": "no recipes"}
        result = build_prompts(self.base_prompt, recipes_result_bad)
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["A_prompt"])
        self.assertIsNone(result["B_prompt"])
        self.assertIsNone(result["extra_tokens_estimate"])
        self.assertIn("Invalid recipes_result: status=error", result["error"])

    def test_build_prompts_none_compact_text(self):
        """Test error when recipes_result has status ok but compact_text is None."""
        recipes_result_bad = {"status": "ok", "compact_text": None, "error": None}
        result = build_prompts(self.base_prompt, recipes_result_bad)
        self.assertEqual(result["status"], "error")
        self.assertIn("compact_text is None", result["error"])

    def test_build_prompts_invalid_base_prompt(self):
        """Test error when base_prompt is not a string."""
        result = build_prompts(123, self.recipes_result_ok)
        self.assertEqual(result["status"], "error")
        self.assertIn("base_prompt must be a string", result["error"])

    def test_build_prompts_invalid_recipes_result_type(self):
        """Test error when recipes_result is not a dict."""
        result = build_prompts(self.base_prompt, "not a dict")
        self.assertEqual(result["status"], "error")
        self.assertIn("recipes_result must be a dict", result["error"])

    def test_build_prompts_extra_tokens_estimate(self):
        """Test extra_tokens_estimate calculation."""
        recipes_result = {
            "status": "ok",
            "selected_recipe_ids": ["r1"],
            "compact_text": "A" * 100,  # 100 chars
            "total_chars": 100,
            "error": None
        }
        result = build_prompts(self.base_prompt, recipes_result)
        self.assertEqual(result["extra_tokens_estimate"], 25)  # 100 // 4 = 25

    def test_build_prompts_compact_text_not_string(self):
        """Test error when compact_text is not a string."""
        recipes_result_bad = {"status": "ok", "compact_text": 123, "error": None}
        result = build_prompts(self.base_prompt, recipes_result_bad)
        self.assertEqual(result["status"], "error")
        self.assertIn("compact_text is not a string", result["error"])


if __name__ == "__main__":
    unittest.main()
