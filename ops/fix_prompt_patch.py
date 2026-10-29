from pathlib import Path
p = Path(__file__).parent / "loop.py"
lines = p.read_text(encoding="utf-8").split("\n")
i = next(k for k, l in enumerate(lines) if l.startswith('    got = request_files(f"" + ("TEST-EDIT PASS'))
new = '''    if os.environ.get("ALLOW_TEST_EDIT"):
        intro = "TEST-EDIT PASS: the same failures repeated. For each failing test decide using the SPEC (including its REVIEWER DECISIONS section) whether the code or the test is wrong. Correct wrong tests (output the full corrected test file) and wrong code (output the full code file); never weaken a test just to pass, a test may only change to match the spec. Explain each changed test in '=== FILE: TEST_ISSUE.txt ==='."
    else:
        intro = "Fix the CODE so the tests pass. The TEST files are read-only and define correct behaviour; do not output test_ files. If a test is truly impossible or contradicts the spec, output a file '=== FILE: TEST_ISSUE.txt ===' explaining which test and why, plus your best code."
    prompt = intro + " Output complete files (never partial, never drop existing public functions).\\n" + FMT + "\\n\\nSPEC:\\n" + spec + "\\n\\nFULL PYTEST OUTPUT:\\n" + r.stdout[-9000:] + "\\n\\nPREVIOUS ROUNDS (do not repeat failed ideas):\\n" + hist + "\\n\\nREVIEW NOTES:\\n" + notes + "\\n\\nFILES:\\n" + code
    assert "{spec}" not in prompt and "{code}" not in prompt  # guard against the f-string bug
    got = request_files(prompt, [n for n in names if not n.startswith("test_")][:1])
    bak = d / "_bak"; bak.mkdir(exist_ok=True)
    for n in names:
        if (d / n).is_file(): (bak / n).write_text((d / n).read_text(encoding="utf-8"), encoding="utf-8")'''.split("\n")
lines[i:i + 1] = new
p.write_text("\n".join(lines), encoding="utf-8")
import ast; ast.parse("\n".join(lines)); print("fix prompt repaired; line", i)
