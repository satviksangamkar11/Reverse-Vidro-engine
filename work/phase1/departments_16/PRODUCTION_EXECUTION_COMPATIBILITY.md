# Production and execution compatibility (department 16)

Source: PRODUCTION_EXECUTION_COMPATIBILITY.json, generated from the current granth module (read-only). GranthStudio was not modified and no Kimi call was made.

Results:
- Registered presets in the GranthStudio preset index: 11.
- Candidate techniques from the F4 diagnosis: 13. All 13 have no registered preset (preset_id null) and no available assets. Need: NEEDS_NEW_CAPABILITY for all 13.
- Lessons: 7. Each is NOT_EXECUTABLE_WITHOUT_PRESET, with the story guidance kept separate from renderer executability.
- Consumer search: 124 lines in GranthStudio scripts and src that mention the preset index or presets. These are candidate Kimi input paths, not confirmed call sites.

Conclusion: no candidate technique is executable with the current presets and assets. Story and directing guidance can be stated, but renderer executability is zero.

Status: PARTIAL_RESEARCH (compatibility checked; no executable path).

Open: the Windows-specific symlink test in the granth module is SKIPPED and UNVERIFIED.
