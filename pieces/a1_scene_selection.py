import json
import os
from typing import Callable, Dict, List, Any

REQUIRED_CATEGORIES = [
    "dialogue",
    "interaction",
    "gesture",
    "environment",
    "discourse",
    "complex_transition"
]

FILE_KEY_MAP = {
    "stage1_prompt.txt": "stage1_prompt",
    "stage2_prompt.txt": "stage2_prompt",
    "schema.json": "schema"
}

def select_scenes(catalog: List[Dict[str, str]], n: int = 6) -> Dict[str, Any]:
    if n != 6:
        raise ValueError("n must be 6")
    
    selected = {}
    seen_categories = set()
    
    for item in catalog:
        if not isinstance(item, dict):
            continue
        cat = item.get("category")
        if cat in REQUIRED_CATEGORIES and cat not in seen_categories:
            selected[cat] = item.get("scene_id")
            seen_categories.add(cat)
    
    missing = [c for c in REQUIRED_CATEGORIES if c not in seen_categories]
    if missing:
        return {
            "status": "error",
            "selected": None,
            "error": f"Missing categories: {', '.join(missing)}"
        }
    
    return {
        "status": "ok",
        "selected": selected,
        "error": None
    }

def freeze_baseline(prompts_dir: str, out_json: str, read_file: Callable[[str], str], hash_func: Callable[[str], str]) -> Dict[str, Any]:
    files = ["stage1_prompt.txt", "stage2_prompt.txt", "schema.json"]
    hashes = {}
    
    try:
        for fname in files:
            path = os.path.join(prompts_dir, fname).replace('\\', '/')
            content = read_file(path)
            key = FILE_KEY_MAP[fname]
            hashes[key] = hash_func(content)
        
        output_data = {
            "stage1_prompt": hashes["stage1_prompt"],
            "stage2_prompt": hashes["stage2_prompt"],
            "schema": hashes["schema"]
        }
        
        try:
            with open(out_json, 'w') as f:
                json.dump(output_data, f)
        except OSError as e:
            return {
                "status": "error",
                "hashes": None,
                "error": f"Failed to write baseline file: {e}"
            }
        
        return {
            "status": "ok",
            "hashes": output_data,
            "error": None
        }
    except FileNotFoundError as e:
        return {
            "status": "error",
            "hashes": None,
            "error": f"File not found: {e.filename}"
        }
    except PermissionError as e:
        return {
            "status": "error",
            "hashes": None,
            "error": f"Permission denied: {e.filename}"
        }
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "hashes": None,
            "error": f"JSON encoding error: {e}"
        }
    except Exception as e:
        return {
            "status": "error",
            "hashes": None,
            "error": f"Failed to freeze baseline: {type(e).__name__}"
        }

def check_baseline(prompts_dir: str, baseline_json: str, read_file: Callable[[str], str], hash_func: Callable[[str], str]) -> Dict[str, Any]:
    files = ["stage1_prompt.txt", "stage2_prompt.txt", "schema.json"]
    current_hashes = {}
    
    try:
        for fname in files:
            path = os.path.join(prompts_dir, fname).replace('\\', '/')
            content = read_file(path)
            key = FILE_KEY_MAP[fname]
            current_hashes[key] = hash_func(content)
        
        baseline_content = read_file(baseline_json)
        baseline_data = json.loads(baseline_content)
        
        required_keys = ["stage1_prompt", "stage2_prompt", "schema"]
        for key in required_keys:
            if key not in baseline_data:
                raise KeyError(f"Missing key in baseline: {key}")
        
        matches = {}
        mismatched = []
        for key in required_keys:
            matches[key] = current_hashes[key] == baseline_data[key]
            if not matches[key]:
                mismatched.append(key)
        
        if mismatched:
            return {
                "status": "error",
                "matches": matches,
                "error": f"Baseline drift detected: {', '.join(mismatched)}"
            }
        
        return {
            "status": "ok",
            "matches": matches,
            "error": None
        }
    except FileNotFoundError as e:
        filename = e.filename if e.filename else baseline_json
        return {
            "status": "error",
            "matches": None,
            "error": f"Baseline not found: {filename}"
        }
    except PermissionError as e:
        return {
            "status": "error",
            "matches": None,
            "error": f"Permission denied: {e.filename}"
        }
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "matches": None,
            "error": f"Invalid JSON in baseline: {e}"
        }
    except KeyError as e:
        return {
            "status": "error",
            "matches": None,
            "error": str(e)
        }
    except Exception as e:
        return {
            "status": "error",
            "matches": None,
            "error": f"Failed to check baseline: {type(e).__name__}"
        }
