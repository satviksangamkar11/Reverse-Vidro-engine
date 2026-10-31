"""Finding lifecycle for the Loop System.

Pure stdlib. Tracks reviewer findings across rounds with stable ids, an
append-only ledger, dispositions, bounded retries and test freezing.
Calls no model. Writes only inside the job_dir it is given; frozen test
paths are read-only.

Report line format: "SEV - [FILE.py:LINE - ]summary", where SEV is HIGH,
MED, MEDIUM (read as MED) or LOW.
"""

import datetime
import hashlib
import json
import os
import re

OPEN = "OPEN"
RESOLVED = "RESOLVED"
DISMISSED = "DISMISSED"

LEDGER_FILE = "findings_ledger.jsonl"
FROZEN_FILE = "frozen_tests.json"
ATTEMPTS_FILE = "attempts.json"

_LINE_RE = re.compile(r"^(HIGH|MEDIUM|MED|LOW) - (.+)$")
_LOC_RE = re.compile(r"^(\S+\.py):(\d+) - (.+)$")
_TEST_REF_RE = re.compile(r"\btest_\w+")
_FILE_REF_RE = re.compile(r"\S+\.py:\d+")
_SEVERITY = {"HIGH": "HIGH", "MED": "MED", "MEDIUM": "MED", "LOW": "LOW"}
_STATUS_OF_EVENT = {"OPENED": OPEN, "RESOLVED": RESOLVED, "DISMISSED": DISMISSED}
_BLOCKING = ("HIGH", "MED")


def _norm(text):
    return " ".join(str(text).lower().split())


def stable_id(job, reviewer, file, line, summary):
    joined = "|".join(_norm(x) for x in (job, reviewer, file, line, summary))
    return "F-" + hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12]


def parse_findings(report_text, reviewer, round_no, job=""):
    findings = []
    for raw in report_text.splitlines():
        m = _LINE_RE.match(raw.rstrip())
        if not m:
            continue
        severity = _SEVERITY[m.group(1)]
        rest = m.group(2).strip()
        loc = _LOC_RE.match(rest)
        if loc:
            file, line, summary = loc.group(1), int(loc.group(2)), loc.group(3)
        else:
            file, line, summary = "", 0, rest
        findings.append({
            "id": stable_id(job, reviewer, file, line, summary),
            "reviewer": reviewer,
            "round": round_no,
            "severity": severity,
            "file": file,
            "line": line,
            "summary": summary,
        })
    return findings


def _job_name(job_dir):
    return os.path.basename(os.path.normpath(job_dir))


def _append(job_dir, event):
    os.makedirs(job_dir, exist_ok=True)
    with open(os.path.join(job_dir, LEDGER_FILE), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")


def _event(kind, base, evidence=None, adjudication=None):
    return {
        "event": kind,
        "id": base["id"],
        "job": base["job"],
        "reviewer": base["reviewer"],
        "round": base["round"],
        "severity": base["severity"],
        "file": base["file"],
        "line": base["line"],
        "summary": base["summary"],
        "evidence": evidence,
        "adjudication": adjudication,
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def load_ledger(job_dir):
    path = os.path.join(job_dir, LEDGER_FILE)
    state = {}
    if not os.path.exists(path):
        return state
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            if not raw.strip():
                continue
            event = json.loads(raw)
            record = dict(event)
            record["status"] = _STATUS_OF_EVENT[event["event"]]
            state[event["id"]] = record
    return state


def _current(job_dir, finding_id):
    ledger = load_ledger(job_dir)
    if finding_id not in ledger:
        raise ValueError("unknown finding id: %s" % finding_id)
    return ledger[finding_id]


def open_findings(job_dir, reviewer, round_no, report_text):
    job = _job_name(job_dir)
    ledger = load_ledger(job_dir)
    appended = []
    for f in parse_findings(report_text, reviewer, round_no, job=job):
        if f["id"] in ledger:
            continue
        event = _event("OPENED", dict(f, job=job))
        _append(job_dir, event)
        ledger[f["id"]] = dict(event, status=OPEN)
        appended.append(f["id"])
    return appended


def resolve(job_dir, finding_id, evidence):
    if not isinstance(evidence, dict):
        raise ValueError("RESOLVED needs evidence as a dict")
    test = evidence.get("test")
    if not isinstance(test, str) or not test.strip() or evidence.get("passed") is not True:
        raise ValueError("RESOLVED needs evidence with a non-empty test and passed True")
    base = _current(job_dir, finding_id)
    _append(job_dir, _event("RESOLVED", base, evidence=dict(evidence)))


def dismiss(job_dir, finding_id, adjudication):
    if not isinstance(adjudication, dict):
        raise ValueError("DISMISSED needs an adjudication dict")
    text = adjudication.get("text")
    ref = adjudication.get("evidence_ref")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("DISMISSED needs non-empty text")
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError("DISMISSED needs a non-empty evidence_ref")
    text = text.strip()
    base = _current(job_dir, finding_id)
    if base["severity"] in _BLOCKING:
        if not text.startswith("EVIDENCE:"):
            raise ValueError("HIGH and MED dismissals must start with EVIDENCE:")
        if not (_TEST_REF_RE.search(text) or _FILE_REF_RE.search(text)):
            raise ValueError("HIGH and MED dismissals need a test name or file:line reference")
    _append(job_dir, _event("DISMISSED", base, adjudication=dict(adjudication)))


def blocking_findings(job_dir):
    return [r for r in load_ledger(job_dir).values()
            if r["status"] == OPEN and r["severity"] in _BLOCKING]


def can_accept(job_dir, judge_verdict):
    # A blocking finding vetoes acceptance whatever the verdict says.
    if blocking_findings(job_dir):
        return False
    return judge_verdict == "READY"


def _attempt_count(job_dir):
    path = os.path.join(job_dir, ATTEMPTS_FILE)
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as fh:
        return int(json.load(fh)["count"])


def record_attempt(job_dir):
    os.makedirs(job_dir, exist_ok=True)
    count = _attempt_count(job_dir) + 1
    with open(os.path.join(job_dir, ATTEMPTS_FILE), "w", encoding="utf-8") as fh:
        json.dump({"count": count}, fh)
    return count


def attempts_allowed(job_dir, max_attempts):
    return _attempt_count(job_dir) < max_attempts


def _sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def freeze_tests(root, job_dir, paths):
    frozen = {p: _sha256_file(os.path.join(root, p)) for p in paths}
    os.makedirs(job_dir, exist_ok=True)
    with open(os.path.join(job_dir, FROZEN_FILE), "w", encoding="utf-8") as fh:
        json.dump(frozen, fh, indent=2, sort_keys=True)
    return frozen


def verify_frozen(root, job_dir):
    path = os.path.join(job_dir, FROZEN_FILE)
    if not os.path.exists(path):
        raise ValueError("no frozen_tests.json in job_dir")
    with open(path, encoding="utf-8") as fh:
        frozen = json.load(fh)
    changed = []
    for p in sorted(frozen):
        full = os.path.join(root, p)
        # A missing frozen file counts as changed.
        if not os.path.isfile(full) or _sha256_file(full) != frozen[p]:
            changed.append(p)
    return changed
