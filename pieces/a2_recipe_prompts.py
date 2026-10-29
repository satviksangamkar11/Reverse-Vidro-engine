def select_recipes(playbook_recipes: list[dict], scene: dict, limit: int = 5, max_chars: int = 2500) -> dict:
    """
    Select recipes matching the scene category, compact them, and return a text block.
    """
    # Validate inputs
    if not isinstance(playbook_recipes, list):
        return {
            "status": "error",
            "selected_recipe_ids": None,
            "compact_text": None,
            "total_chars": None,
            "error": "playbook_recipes must be a list"
        }
    if not isinstance(scene, dict) or "category" not in scene:
        return {
            "status": "error",
            "selected_recipe_ids": None,
            "compact_text": None,
            "total_chars": None,
            "error": "scene must be a dict with 'category' key"
        }
    if not isinstance(limit, int) or limit < 0:
        return {
            "status": "error",
            "selected_recipe_ids": None,
            "compact_text": None,
            "total_chars": None,
            "error": "limit must be a non-negative integer"
        }
    if not isinstance(max_chars, int) or max_chars < 0:
        return {
            "status": "error",
            "selected_recipe_ids": None,
            "compact_text": None,
            "total_chars": None,
            "error": "max_chars must be a non-negative integer"
        }

    scene_category = scene.get("category", "") or ""
    if not isinstance(scene_category, str):
        scene_category = ""

    # Filter recipes: category match (exact equality, case-insensitive) OR purpose contains scene_category (case-insensitive substring)
    matched = []
    for recipe in playbook_recipes:
        if not isinstance(recipe, dict):
            continue
        recipe_cat = recipe.get("category", "") or ""
        recipe_purpose = recipe.get("purpose", "") or ""
        # Accept only strings; non-strings treated as empty
        if not isinstance(recipe_cat, str):
            recipe_cat = ""
        if not isinstance(recipe_purpose, str):
            recipe_purpose = ""
        # Category match: exact equality (case-insensitive)
        cat_match = False
        if scene_category:
            cat_match = (recipe_cat.lower() == scene_category.lower())
        # Purpose match: scene_category is substring of recipe_purpose (case-insensitive)
        purpose_match = False
        if scene_category:
            purpose_match = (scene_category.lower() in recipe_purpose.lower())
        if cat_match or purpose_match:
            # Validate recipe_id is non-empty string
            recipe_id = recipe.get("recipe_id", "")
            if not isinstance(recipe_id, str) or recipe_id == "":
                continue
            matched.append(recipe)

    # Sort by recipe_id for determinism
    matched.sort(key=lambda r: r.get("recipe_id", ""))

    # Take first `limit` recipes
    selected = matched[:limit]

    # Compact each recipe text to max 200 chars (truncate with "..." if longer, ellipsis included in 200)
    compacted_texts = []
    selected_ids = []
    for recipe in selected:
        text = recipe.get("text", "") or ""
        if not isinstance(text, str):
            text = ""
        if len(text) > 200:
            text = text[:197] + "..."
        compacted_texts.append(text)
        selected_ids.append(recipe.get("recipe_id", ""))

    # Join with separator (only between recipes, not after last)
    separator = "\n---\n"
    compact_text = separator.join(compacted_texts)

    # Truncate to max_chars if needed (keep separators intact by truncating last recipe)
    if len(compact_text) > max_chars and compacted_texts:
        # We need to truncate the last compacted text to fit
        # Calculate available chars for last recipe
        prefix = separator.join(compacted_texts[:-1])
        if prefix:
            prefix += separator
        available = max_chars - len(prefix)
        if available <= 0:
            # Even prefix is too long (or exactly fills max_chars), drop recipes from end until prefix fits or no recipes left
            # Rebuild by adding recipes one by one until we exceed max_chars
            rebuilt_texts = []
            rebuilt_ids = []
            current_len = 0
            for i, (ctext, cid) in enumerate(zip(compacted_texts, selected_ids)):
                if i == 0:
                    candidate = ctext
                else:
                    candidate = separator + ctext
                if current_len + len(candidate) <= max_chars:
                    rebuilt_texts.append(candidate)
                    rebuilt_ids.append(cid)
                    current_len += len(candidate)
                else:
                    # Try to truncate this recipe to fit
                    remaining = max_chars - current_len
                    if remaining <= 0:
                        break
                    sep_len = len(separator) if i > 0 else 0
                    text_avail = remaining - sep_len
                    if text_avail <= 0:
                        break
                    if text_avail >= 4:
                        truncated = ctext[:text_avail - 3] + "..."
                    else:
                        truncated = ctext[:text_avail]
                    if i > 0:
                        rebuilt_texts.append(separator + truncated)
                    else:
                        rebuilt_texts.append(truncated)
                    rebuilt_ids.append(cid)
                    break
            compact_text = "".join(rebuilt_texts)
            selected_ids = rebuilt_ids
        else:
            last_text = compacted_texts[-1]
            if len(last_text) > available:
                if available >= 4:
                    last_text = last_text[:available - 3] + "..."
                else:
                    last_text = last_text[:available]
            compact_text = prefix + last_text

    total_chars = len(compact_text)

    return {
        "status": "ok",
        "selected_recipe_ids": selected_ids,
        "compact_text": compact_text,
        "total_chars": total_chars,
        "error": None
    }


def build_prompts(base_prompt: str, recipes_result: dict) -> dict:
    """
    Build A and B prompts from base_prompt and recipes_result.
    """
    # Validate inputs
    if not isinstance(base_prompt, str):
        return {
            "status": "error",
            "A_prompt": None,
            "B_prompt": None,
            "extra_tokens_estimate": None,
            "error": "base_prompt must be a string"
        }
    if not isinstance(recipes_result, dict):
        return {
            "status": "error",
            "A_prompt": None,
            "B_prompt": None,
            "extra_tokens_estimate": None,
            "error": "recipes_result must be a dict"
        }

    status = recipes_result.get("status")
    if status != "ok":
        return {
            "status": "error",
            "A_prompt": None,
            "B_prompt": None,
            "extra_tokens_estimate": None,
            "error": f"Invalid recipes_result: status={status}"
        }

    compact_text = recipes_result.get("compact_text")
    if compact_text is None:
        return {
            "status": "error",
            "A_prompt": None,
            "B_prompt": None,
            "extra_tokens_estimate": None,
            "error": "compact_text is None"
        }
    if not isinstance(compact_text, str):
        return {
            "status": "error",
            "A_prompt": None,
            "B_prompt": None,
            "extra_tokens_estimate": None,
            "error": "Invalid recipes_result: compact_text is not a string"
        }

    A_prompt = base_prompt
    B_prompt = (
        base_prompt
        + "\n\n=== READ-ONLY RESEARCH HINTS ===\n"
        + compact_text
        + "\n=== END RESEARCH HINTS ==="
    )
    extra_tokens_estimate = len(compact_text) // 4

    return {
        "status": "ok",
        "A_prompt": A_prompt,
        "B_prompt": B_prompt,
        "extra_tokens_estimate": extra_tokens_estimate,
        "error": None
    }
