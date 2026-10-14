# Change Log Verification Script

JETOS uses `tools/verify_behind_a_log.py` to measure how far its pinned upstream source lineages have drifted from current stable releases.

The persistent ledgers are:

- `Documentation/Behind a Log of Gentoo.md` — Gentoo-informed system-substrate ledger, with Linux kernel versions used as the numeric drift measure because Gentoo itself is rolling-release.
- `Documentation/Behind a Log of Python.md` — JetLang/CPython lineage ledger.

## Normal use

```bash
python3 tools/verify_behind_a_log.py
python3 tools/verify_behind_a_log.py --write
python3 tools/verify_behind_a_log.py --json
```

The first prints detected drift without modifying the repository. `--write` refreshes machine-managed current-status blocks and appends a historical fingerprint only when the JetOS pin or detected upstream release changes. `--json` emits machine-readable status for repository-owned tooling.

## Sources

The verifier uses authoritative upstream release surfaces: kernel.org release metadata/changelogs and Python release/download/What's-New pages. It has no third-party Python dependencies.

## Update policy

A detected upstream release is not merely a number bump. When a version fingerprint changes, the corresponding Behind a Log retains upstream release/changelog references and receives a concise digest of changes relevant to JetOS or JetLang.

The logs distinguish current pinned version/commit, current stable upstream, same-maintenance-line drift where applicable, feature/major-series drift, authoritative change references, relevant changes, observation date, and closure date/version.

During boot stabilization, upstream drift is visible technical debt but does not override repair of a known broken build. Once a known-good baseline exists, `MANDATE.md` requires stable-upstream intake and qualification.

## Periodic verification

The normal engineering/reporting cycle should run the verifier periodically. If no fingerprint changed, no history entry is added. If upstream moved, the current status is refreshed and the engineering report calls out the new gap. Before an update is fully handled, the release-change digest and qualification evidence must be recorded.

The verifier does not silently rewrite JetOS pins and does not claim a new release qualified. Updating a pin remains an explicit source change followed by the full JetOS/JetLang build, boot, compatibility, integration, architecture, and target qualification chain.
