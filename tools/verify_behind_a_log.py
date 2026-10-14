#!/usr/bin/env python3
"""Track JETOS drift from stable Linux/Gentoo-informed and CPython upstreams.

This tool is deliberately dependency-free. It reads the currently pinned
versions from tools/dev.py, queries authoritative upstream release metadata,
prints the drift/integration backlog, and optionally updates the two persistent
Behind a Log Markdown documents. A history entry is appended only when either
the JETOS baseline or the detected upstream release changes.
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
GENTOO_LOG = DOCS / "Behind a Log of Gentoo.md"
PYTHON_LOG = DOCS / "Behind a Log of Python.md"

KERNEL_RELEASES = "https://www.kernel.org/releases.json"
PYTHON_DOWNLOADS = "https://www.python.org/downloads/"
USER_AGENT = "JETOS-Behind-A-Log/1.0"

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
        "linux_version": read_constant(text, "LINUX_VERSION"),
        "linux_commit": read_constant(text, "LINUX_COMMIT"),
        "python_version": read_constant(text, "CPYTHON_VERSION"),
        "python_commit": read_constant(text, "CPYTHON_COMMIT"),
    }


def linux_state(raw: str, pinned_version: str):
    data = json.loads(raw)
    releases = data.get("releases", [])
    stable = next((item for item in releases if item.get("moniker") == "stable"), None)
    if not stable:
        raise SystemExit("kernel.org releases.json did not expose a stable release")

    pinned_series = ".".join(pinned_version.split(".")[:2])
    same_line = None
    for item in releases:
        if item.get("moniker") != "longterm":
            continue
        version = str(item.get("version", ""))
        if version.startswith(pinned_series + "."):
            same_line = item
            break

    return {
        "stable": str(stable["version"]),
        "stable_released": str(stable.get("released", {}).get("isodate", "unknown")),
        "same_line": str(same_line["version"]) if same_line else None,
        "same_line_released": str(same_line.get("released", {}).get("isodate", "unknown")) if same_line else None,
    }


def python_state(html: str):
    versions = set(re.findall(r'Python\s+(3\.\d+\.\d+)(?![A-Za-z0-9])', html))
    if not versions:
        raise SystemExit("python.org downloads page exposed no final Python versions")
    latest = max(versions, key=version_tuple)
    return {"stable": latest}


def python_release_url(version: str) -> str:
    return "https://www.python.org/downloads/release/python-%s/" % version.replace(".", "")


def linux_changelog_url(version: str) -> str:
    major = version.split(".")[0]
    return "https://cdn.kernel.org/pub/linux/kernel/v%s.x/ChangeLog-%s" % (major, version)


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


def render_gentoo(pins, linux, checked: str) -> tuple[str, str, str]:
    pinned = pins["linux_version"]
    latest = linux["stable"]
    same_line = linux["same_line"]
    same_line_text = "not advertised as current longterm" if not same_line else same_line
    same_line_drift = "n/a"
    if same_line:
        same_line_drift = drift_description(pinned, same_line, "kernel")
    status = f"""Checked: {checked}

- JetOS pinned Linux base: **{pinned}** (`{pins['linux_commit']}`)
- Latest kernel.org stable: **{latest}**
- Stable drift: **{drift_description(pinned, latest, 'kernel')}**
- Latest release on the pinned `{'.'.join(pinned.split('.')[:2])}` longterm line: **{same_line_text}**
- Same-line maintenance drift: **{same_line_drift}**
- Stable changelog: {linux_changelog_url(latest)}
- Pinned-line changelog: {linux_changelog_url(same_line) if same_line else 'n/a'}
- Release metadata: {KERNEL_RELEASES}
"""
    fingerprint = "linux:%s:%s:%s" % (pinned, latest, same_line or "none")
    entry = f"""### {checked[:10]} — Linux drift check

- JetOS pin: `{pinned}` / `{pins['linux_commit']}`
- Upstream stable observed: `{latest}`
- Pinned longterm line observed: `{same_line_text}`
- Drift summary: {drift_description(pinned, latest, 'kernel')}; same-line: {same_line_drift}.
- Official upstream change sources: {linux_changelog_url(latest)} and {linux_changelog_url(same_line) if same_line else KERNEL_RELEASES}
- Digest rule: before adopting a newly detected release line, append a concise categorized summary of the upstream changelog to this file and preserve the previous entry.
"""
    return status, fingerprint, entry


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
- Digest rule: whenever a new stable Python release is detected, append the important language/runtime/build/stdlib changes here before or alongside JetLang integration work. Upstream source is a change/reference stream; it does not replace the JetLang-owned tree.
"""
    return status, fingerprint, entry


def ensure_document(path: Path, title: str, intro: str) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return "# %s\n\n%s\n\n## Current status\n\n%s\n%s\n\n## History\n\n%s\n" % (
        title,
        intro,
        STATUS_BEGIN,
        STATUS_END,
        HISTORY_BEGIN,
    )


def write_logs(pins, linux, py, checked: str) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    gentoo_intro = (
        "This is the persistent upstream-drift ledger for the Gentoo-informed JetOS system substrate. "
        "Gentoo is rolling-release and does not have one comparable product version, so this log uses the "
        "Linux kernel lineage as the numeric drift measure while retaining Gentoo as source/build/configuration intelligence."
    )
    python_intro = (
        "This is the persistent upstream-integration backlog for JetLang's CPython lineage. JetLang deliberately diverges "
        "and owns its source after the initial import; stable CPython releases remain compatibility, regression-test, "
        "standard-library, bug-fix, and change-reference inputs rather than replacement source trees."
    )

    g_status, g_fp, g_entry = render_gentoo(pins, linux, checked)
    p_status, p_fp, p_entry = render_python(pins, py, checked)

    g_text = ensure_document(GENTOO_LOG, "Behind a Log of Gentoo", gentoo_intro)
    g_text = replace_status(g_text, g_status)
    g_text = append_history_once(g_text, g_fp, g_entry)
    GENTOO_LOG.write_text(g_text, encoding="utf-8")

    p_text = ensure_document(PYTHON_LOG, "Behind a Log of Python", python_intro)
    p_text = replace_status(p_text, p_status)
    p_text = append_history_once(p_text, p_fp, p_entry)
    PYTHON_LOG.write_text(p_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="measure JetOS upstream version drift/integration backlog")
    parser.add_argument("--write", action="store_true", help="refresh Behind a Log documents and append new history fingerprints")
    parser.add_argument("--json", action="store_true", help="emit machine-readable status")
    args = parser.parse_args()

    pins = read_pins()
    linux = linux_state(fetch_text(KERNEL_RELEASES), pins["linux_version"])
    py = python_state(fetch_text(PYTHON_DOWNLOADS))
    checked = _datetime.datetime.now(_datetime.timezone.utc).replace(microsecond=0).isoformat()

    result = {"checked": checked, "pins": pins, "linux": linux, "python": py}
    if args.write:
        write_logs(pins, linux, py, checked)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Behind a Log — Gentoo/Linux: %s -> %s (%s)" % (
            pins["linux_version"], linux["stable"], drift_description(pins["linux_version"], linux["stable"], "kernel")
        ))
        if linux["same_line"]:
            print("  pinned longterm line: %s -> %s (%s)" % (
                pins["linux_version"], linux["same_line"], drift_description(pins["linux_version"], linux["same_line"], "kernel")
            ))
        print("Behind a Log — Python integration backlog: %s -> %s (%s)" % (
            pins["python_version"], py["stable"], drift_description(pins["python_version"], py["stable"], "feature")
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
