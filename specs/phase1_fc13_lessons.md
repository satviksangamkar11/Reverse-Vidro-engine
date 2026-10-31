# SPEC FC13L: NEW `pieces/fc13_lessons.py` and `pieces/test_fc13_lessons.py` (Fast-Close V1.3: final five director lessons)

GOAL: one small module that holds the five final EXPERIMENTAL director lessons as data, checks them against the real preset registry snapshot, and writes `work/phase1/departments_16/fastclose_v13/LESSONS_FINAL.json`. No lesson becomes production-eligible: status stays EXPERIMENTAL and F4 stays UNCHANGED.

REAL FACTS (verified 2026-11-01 against the real files):
- Snapshot folder (read only): `work/phase1/departments_16/fastclose_v13/inputs/`. It holds `presets/index.json`, eleven preset files `presets/<preset_id>.json`, and `SNAPSHOT_MANIFEST.json`.
- `presets/index.json` is a JSON list of 11 dicts with keys `preset`, `use`, `assets` (list of role names), `simplest_renderer`.
- A preset file has key `segments` (a list). The start zoom is `segments[0]["camera"]["start"]["zoom"]`; the end zoom is `segments[-1]["camera"]["end"]["zoom"]`. Gain = end zoom minus start zoom, rounded to 2 decimals.
- Real gains (independent expected values; the test must hardcode exactly these): 01_establishing_shot 0.28; 02_environmental_parallax 0.13; 03_slow_cinematic_push 0.20; 04_character_entrance 0.14; 05_bowing_prayer 0.14; 06_blessing_gesture 0.30; 07_character_reaction 0.14; 08_emotional_closeup 0.25; 09_dialogue_composition 0.13; 10_object_hand_insert 0.14; 11_scene_transition 0.00.
- Supported transitions in the consumer (fixed fact, do not read any other repository): "cut", "slide", "pan_bridge".

CONSTANTS: ROOT = repository root (the folder that contains `pieces/`); INPUTS = ROOT/work/phase1/departments_16/fastclose_v13/inputs; OUT = ROOT/work/phase1/departments_16/fastclose_v13/LESSONS_FINAL.json; TRANSITIONS = ("cut", "slide", "pan_bridge"); OWNER_PHRASE = "the owner's notes above always win"; FORBIDDEN = ("drill", "clay", "devayani", "kacha", "vow", "marry", "7434a0f7", "7a1e2b26") (reference-video content must never reach the prompt; compare case-insensitively).

LESSONS: a module-level list LESSONS of exactly five dicts, in this order, each with keys id, topic, text, presets, when_applies, evidence, status ("EXPERIMENTAL"), f4 ("UNCHANGED"). `text` must be EXACTLY the string below (copy it character for character). `presets` is a list of dicts {"preset", "use"}. `evidence` is a list of dicts {"video", "interval_s", "observation", "provenance"} copied from the table below.

L1 id "L1", topic "opening".
text: EXPERIMENTAL DIRECTOR LESSON 1, opening (technique only; the owner's notes above always win): open on the scene's most relevant source-supported subject, action, object or setting, cited to its ovi. Establish the place when the viewer needs it to follow the action; 01_establishing_shot is one option, not a rule. Show nothing the ovis or the PACKET do not name.
presets: 01_establishing_shot (the place itself matters first); 10_object_hand_insert (a named object or action leads); 03_slow_cinematic_push (one complete image of the subject); 02_environmental_parallax (a setting whose depth matters).
when_applies: the first shot of every scene.
evidence: 7a1e2b26, 0.0-1.88 and 3.5-4.0, "opens on the drill bit before the first wide view", "owner Review 2 S01 and S03 (recorded by statement)".

L2 id "L2", topic "camera variation".
text: EXPERIMENTAL DIRECTOR LESSON 2, camera variation (technique only; the owner's notes above always win): choose each registered preset for the shot's action, attention and emotion. Avoid strong push-ins back to back (01_establishing_shot, 03_slow_cinematic_push, 06_blessing_gesture, 08_emotional_closeup: fixed zoom gain 0.20 or more) unless the beat gives a specific dramatic reason; repeating a preset is fine when continuity benefits.
presets: the four strong ones above, each with use "strong push (gain 0.20 or more)".
when_applies: every pair of consecutive shots.
evidence: 7434a0f7, 0.5-11.0 and 11.7-12.8, "slow zooms through the setup; the one strong zoom lands on the proposal line", "owner Review 1 B03, B04, B06 and B10 (owner-confirmed)".

L3 id "L3", topic "visible reactions".
text: EXPERIMENTAL DIRECTOR LESSON 3, visible reactions (technique only; the owner's notes above always win): when an ovi describes an important character response, give it visible emphasis with a supported framing and a held pose that matches the ovi; the narrator may tell it too, but must not replace it entirely. Do not invent gestures, feelings or events the ovi does not state.
presets: 07_character_reaction (one face); 08_emotional_closeup (a quiet face beat); 03_slow_cinematic_push (a complete close image); 09_dialogue_composition (two people facing each other); 05_bowing_prayer (a bow the ovi states).
when_applies: a shot whose ovi states a person's response.
evidence: 7434a0f7, 3.0-4.5 and 5.0-6.5, "one character acts, then the other responds, in order", "owner Review 1 B04 and B05 (owner's words)"; 7434a0f7, 9.5-11.0, "an entrance read as a reveal", "owner Review 1 B09 (owner-confirmed)".

L4 id "L4", topic "shot progression".
text: EXPERIMENTAL DIRECTOR LESSON 4, shot progression (technique only; the owner's notes above always win): choose framing and transitions so that events, reactions, reveals and who-is-where stay clear; use only the registered presets and the transitions cut, slide and pan_bridge. Wide-to-close is not required, and slide or pan_bridge do not need a change of place.
presets: all eleven registered presets, each with use "registered".
when_applies: the order of shots and every transition_out.
evidence: 7434a0f7, 8.97-46.9, "transitions through black between scenes; cuts within", "frozen detector STEP4_MEASUREMENTS.json plus owner visual read round 2; 4.93 s and 12.9 s OPEN".

L5 id "L5", topic "emotional restraint".
text: EXPERIMENTAL DIRECTOR LESSON 5, emotional restraint (technique only; the owner's notes above always win): in quiet or emotional moments prefer the least distracting movement whose image roles fit (09_dialogue_composition 0.13; 05_bowing_prayer, 07_character_reaction, 10_object_hand_insert 0.14), avoid unnecessary consecutive pushes, and never let a camera move suggest a story event the ovis do not state.
presets: the four above with their gains as use; 02_environmental_parallax and 04_character_entrance are NOT listed (lateral move or walking pan); 11_scene_transition is NOT listed (it joins two scenes).
when_applies: visual-only shots of the timeline and ovis that state silence, stillness or devotion.
evidence: 7a1e2b26, 0.0-12.0, "the camera stays still between cuts", "owner round 3 (owner-reported, not human-verified)".

FUNCTIONS (standard library only: json, re, hashlib, os, pathlib, sys):
- load_registry(inputs_dir) -> dict preset_id -> {"gain": float, "zoom": [start, end], "roles": list}. Roles come from index.json `assets`. Raise ValueError if a preset in index.json has no preset file, or if the index does not list exactly 11 presets.
- preset_ids(text) -> list of the unique preset ids in text, in order of first appearance, matched with the regex `[0-9][0-9]_[a-z_]+` (write the pattern in a raw string; never use a backslash-b sequence in a normal string).
- check(lessons, registry) -> list of problem strings (empty = fine). Report: wrong count (not 5); a text not starting with "EXPERIMENTAL DIRECTOR LESSON n," for its position n; OWNER_PHRASE missing; any preset id in text or in `presets` not in the registry; a FORBIDDEN word in text; text longer than 700 characters; status not "EXPERIMENTAL" or f4 not "UNCHANGED"; empty evidence or an evidence item missing one of its four keys; L2's preset ids in text not equal to the set of registry ids with gain >= 0.20; any L5 preset id in text with gain > 0.14 or equal to "11_scene_transition"; L4's text missing any of the three TRANSITIONS words.
- build(root) -> dict {"schema": 1, "name": "FASTCLOSE_V13_LESSONS_FINAL", "status": "EXPERIMENTAL", "f4": "UNCHANGED", "snapshot_manifest_sha256": sha256 hex of the bytes of INPUTS/SNAPSHOT_MANIFEST.json, "registry": {id: gain}, "lessons": LESSONS, "prompt_lines": [the five texts in order], "problems": check(...)}.
- main(argv=None) -> int: write build(ROOT) to OUT (UTF-8, ensure_ascii False, indent 1; create the parent folder), print the number of problems, return 0 if there are none, else 1.

HARD RULES:
- Read only the snapshot folder. The only write is OUT. No network, no subprocess, no model call, no import from outside the standard library.
- Never print or open anything under a `secrets` folder or any .env file.
- Do not write the seven-letter name of the 3D software tool anywhere in code, tests or comments (the index file contains it as data; never copy that value into code).

TESTS for `pieces/test_fc13_lessons.py` (pytest; import the module by path from pieces/; expected values are the literals in this spec, never computed by the module under test):
1. load_registry on the real snapshot returns exactly the 11 gains listed in REAL FACTS (hardcode the dict).
2. The set of ids with gain >= 0.20 is exactly {"01_establishing_shot", "03_slow_cinematic_push", "06_blessing_gesture", "08_emotional_closeup"} (hardcoded).
3. Each LESSONS[i]["text"] equals the exact text of this spec (hardcode all five strings in the test).
4. check(LESSONS, real registry) returns [].
5. check flags: a copy whose L1 text contains "12_made_up_preset"; a copy whose L3 text contains "Devayani"; a copy with OWNER_PHRASE removed from L4; a copy with "02_environmental_parallax" added to L5's text; a copy with only four lessons. Each must yield at least one problem.
6. main() with OUT monkeypatched to tmp_path writes valid JSON whose prompt_lines equal the five hardcoded texts and whose problems list is empty, and returns 0.
7. No file under INPUTS changes during main() (compare sha256 of every file before and after).

OUTPUT FORMAT (mandatory): reply with ONLY these two blocks, no other text. Each block starts with the line `FILE: <path>` directly followed by a fenced code block starting with ```python on its own line and ending with ``` on its own line:
FILE: pieces/fc13_lessons.py
```python
<complete source>
```
FILE: pieces/test_fc13_lessons.py
```python
<complete source>
```
