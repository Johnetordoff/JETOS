#!/usr/bin/env python3
"""Track JetLang's CPython upstream integration backlog.

JetOS owns its vendored Linux source and does not treat Gentoo or upstream Linux
release drift as an automatic update obligation. The historical Gentoo/Linux
Behind-a-Log document is provenance only. This tool therefore tracks only the
CPython releases that may be reviewed and deliberately integrated into JetLang.
"""
from __future__ import annotations

import argparse
import datetime as _datetime
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "tools" / "dev.py"
DOCS = ROOT / "Documentation"
PYTHON_LOG = DOCS / "Behind a Log of Python.md"
PYTHON_DOWNLOADS = "https://www.python.org/downloads/"
USER_AGENT = "JETOS-Behind-A-Log/2.0"
STATUS_BEGIN = "<!-- BEGIN AUTO STATUS -->"
STATUS_END = "<!-- END AUTO STATUS -->"
HISTORY_BEGIN = "<!-- BEGIN AUTO HISTORY -->"


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def version_tuple(value: str):
    parts = value.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError("expected final x.y.z version, got %r" % value)
    return tuple(int(part) for part in parts)


def read_constant(text: str, name: str) -> str:
    match = re.search(r'^%s\s*=\s*"([^"]+)"' % re.escape(name), text, re.MULTILINE)
    if not match:
        raise SystemExit("could not find %s in tools/dev.py" % name)
    return match.group(1)


def read_pins():
    text = DEV.read_text(encoding="utf-8")
    return {
        "python_version": read_constant(text, "CPYTHON_VERSION"),
        "python_commit": read_constant(text, "CPYTHON_COMMIT"),
    }


def python_state(html: str):
    versions = set(re.findall(r'Python\s+(3\.\d+\.\d+)(?![A-Za-z0-9])', html))
    if not versions:
        raise SystemExit("python.org downloads page exposed no final Python versions")
    latest = max(versions, key=version_tuple)
    return {"stable": latest}


def python_release_url(version: str) -> str:
    return "https://www.python.org/downloads/release/python-%s/" % version.replace(".", "")


def drift_description(pinned: str, latest: str, noun: str) -> str:
    p = version_tuple(pinned)
    u = version_tuple(latest)
    if p == u:
        return "current"
    if p[0] != u[0]:
        return "%d major-number line(s) behind (%s -> %s)" % (u[0] - p[0], pinned, latest)
    if p[1] != u[1]:
        return "%d %s series behind (%s -> %s)" % (u[1] - p[1], noun, pinned, latest)
    return "%d patch release(s) behind (%s -> %s)" % (u[2] - p[2], pinned, latest)


def replace_status(text: str, block: str) -> str:
    rendered = STATUS_BEGIN + "\n" + block.rstrip() + "\n" + STATUS_END
    if STATUS_BEGIN in text and STATUS_END in text:
        before = text.split(STATUS_BEGIN, 1)[0]
        after = text.split(STATUS_END, 1)[1]
        return before + rendered + after
    return text.rstrip() + "\n\n" + rendered + "\n"


def append_history_once(text: str, fingerprint: str, entry: str) -> str:
    marker = "<!-- STATUS FINGERPRINT: %s -->" % fingerprint
    if marker in text:
        return text
    payload = marker + "\n" + entry.rstrip() + "\n\n"
    if HISTORY_BEGIN in text:
        return text.replace(HISTORY_BEGIN, HISTORY_BEGIN + "\n" + payload, 1)
    return text.rstrip() + "\n\n## History\n\n" + HISTORY_BEGIN + "\n" + payload


def render_python(pins, py, checked: str) -> tuple[str, str, str]:
    baseline = pins["python_version"]
    latest = py["stable"]
    backlog = drift_description(baseline, latest, "feature")
    status = f"""Checked: {checked}

- JetLang integration baseline: **{baseline} lineage** (`{pins['python_commit']}` initial upstream provenance)
- Latest stable CPython observed: **{latest}**
- Integration backlog: **{backlog}**
- Latest release notes: {python_release_url(latest)}
- Major-series change notes: https://docs.python.org/3/whatsnew/{'.'.join(latest.split('.')[:2])}.html
- Release index: {PYTHON_DOWNLOADS}
"""
    fingerprint = "python:%s:%s" % (baseline, latest)
    entry = f"""### {checked[:10]} — Python integration-backlog check

- JetLang baseline: `{baseline}` lineage / initial upstream provenance `{pins['python_commit']}`
- Upstream stable observed: `{latest}`
- Integration backlog: {backlog}.
- Official upstream change sources: {python_release_url(latest)} and https://docs.python.org/3/whatsnew/{'.'.join(latest.split('.')[:2])}.html
- Upstream source is a change/reference stream; it does not replace the JetLang-owned tree.
"""
    return status, fingerprint, entry


def ensure_document(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return (
        "# Behind a Log of Python\n\n"
        "Persistent upstream-integration backlog for JetLang's CPython lineage.\n\n"
        "## Current status\n\n" + STATUS_BEGIN + "\n" + STATUS_END
        + "\n\n## History\n\n" + HISTORY_BEGIN + "\n"
    )


def write_log(pins, py, checked: str) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    status, fingerprint, entry = render_python(pins, py, checked)
    text = ensure_document(PYTHON_LOG)
    text = replace_status(text, status)
    text = append_history_once(text, fingerprint, entry)
    PYTHON_LOG.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="measure JetLang CPython integration backlog")
    parser.add_argument("--write", action="store_true", help="refresh the Python Behind-a-Log document")
    parser.add_argument("--json", action="store_true", help="emit machine-readable status")
    args = parser.parse_args()

    pins = read_pins()
    py = python_state(fetch_text(PYTHON_DOWNLOADS))
    checked = _datetime.datetime.now(_datetime.timezone.utc).replace(microsecond=0).isoformat()
    result = {"checked": checked, "pins": pins, "python": py}
    if args.write:
        write_log(pins, py, checked)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Behind a Log — Python integration backlog: %s -> %s (%s)" % (
            pins["python_version"], py["stable"],
            drift_description(pins["python_version"], py["stable"], "feature")
        ))
        print("Linux/Gentoo drift tracking: retired; vendored JetOS kernel changes are deliberate integrations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
