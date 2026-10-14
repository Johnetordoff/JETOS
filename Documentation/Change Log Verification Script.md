# Change Log Verification Script

JETOS uses `tools/verify_behind_a_log.py` to measure how far its pinned upstream source lineages have drifted from current stable releases.

The persistent ledgers are:

- `Documentation/Behind a Log of Gentoo.md` — Gentoo-informed system-substrate ledger, with Linux kernel versions used as the numeric drift measure because Gentoo itself is rolling-release.
- `Documentation/Behind a Log of Python.md` — JetLang/CPython lineage ledger.

## Normal use

```bash
python3 tools/verify_behind_a_log.py
```

This prints the current detected drift without modifying the repository.

```bash
python3 tools/verify_behind_a_log.py --write
```

This refreshes the machine-managed current-status blocks and appends a new historical fingerprint only when either the JetOS pin or detected upstream release changes.

```bash
python3 tools/verify_behind_a_log.py --json
```

This emits machine-readable status suitable for other repository-owned tooling.

## Sources

The verifier uses authoritative upstream release surfaces:

- Linux release metadata: `https://www.kernel.org/releases.json`
- kernel.org release changelogs under `https://cdn.kernel.org/pub/linux/kernel/`
- Python release index: `https://www.python.org/downloads/`
- Python release notes and What's New pages on python.org/docs.python.org

It has no third-party Python dependencies.

## Update policy

A detected upstream release is not merely a number bump. When the version fingerprint changes, the corresponding Behind a Log must retain the upstream release/changelog references and receive a concise human-readable digest of the important changes. That digest is evidence for the subsequent JetOS/JetLang rebase or kernel update work.

The logs should distinguish:

- current pinned version and exact commit;
- current stable upstream version;
- same-maintenance-line drift when applicable;
- feature/major-series drift;
- official changelog/release-note references;
- the important changes likely to affect JetOS or JetLang;
- the date the drift was observed;
- the date/version at which the gap was closed.

During boot stabilization, upstream drift is visible technical debt but is not permission to interrupt repair of a known broken build merely to chase a new release. Once a known-good baseline exists, `MANDATE_004H_UPSTREAM_CURRENCY.md` requires prompt stable-upstream intake and qualification.

## Periodic verification

The normal JetOS engineering/reporting cycle should run the verifier periodically. If no fingerprint changed, no history entry is added. If upstream moved, the current status is refreshed and the engineering report must call out the new gap. Before an upstream update is considered fully handled, the corresponding release-change digest and qualification evidence must be recorded.

The verifier itself does not silently rewrite JetOS pins and does not claim a new release qualified. Updating the pin remains an explicit source change followed by the full JetOS/JetLang build, boot, compatibility, integration, architecture, and target qualification chain.
