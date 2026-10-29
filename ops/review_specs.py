from pathlib import Path
L = Path(__file__).parent
ctx = "FINAL SPEC REVIEW. These four specs are being FROZEN. Report ONLY concrete bugs, contradictions between specs, or untestable statements (with spec name and quote). NO enhancements, NO new features, NO new modules. If none, reply exactly PASS. Max 300 words.\n\n"
for w in ("F1", "F2", "F3", "F4"): ctx += f"=== SPEC {w} ===\n" + (L / f"wp{w}.spec.md").read_text(encoding="utf-8") + "\n"
(L / "arch_context.txt").write_text(ctx, encoding="utf-8")
