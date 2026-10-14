# Behind a Log of Gentoo

This is the persistent upstream-drift ledger for the Gentoo-informed JetOS system substrate. Gentoo is rolling-release and does not have one comparable product version, so this log uses the Linux kernel lineage as the numeric drift measure while retaining Gentoo as source/build/configuration intelligence.

This file is intentionally historical. Do not erase an old drift entry after an upgrade; append the new state so JetOS can see both how far it drifted and how quickly it caught up.

## Current status

<!-- BEGIN AUTO STATUS -->
Checked: 2026-10-14T19:00:00+00:00

- JetOS pinned Linux base: **6.12.96** (`6d15a1029d425b15c59463910ebdccc4afe760d6`)
- Latest kernel.org stable: **7.2.10**
- Stable drift: **1 major-number line behind (6.12.96 -> 7.2.10)**
- Latest release on the pinned `6.12` longterm line: **6.12.112**
- Same-line maintenance drift: **16 patch releases behind (6.12.96 -> 6.12.112)**
- Stable changelog: https://cdn.kernel.org/pub/linux/kernel/v7.x/ChangeLog-7.2.10
- Pinned-line changelog: https://cdn.kernel.org/pub/linux/kernel/v6.x/ChangeLog-6.12.112
- Release metadata: https://www.kernel.org/releases.json
<!-- END AUTO STATUS -->

## Current change backlog

The present upstream gap has two different meanings and must not be collapsed into one number:

- **Maintenance gap on the existing 6.12 LTS line:** JetOS is missing the maintenance changes from 6.12.97 through 6.12.112.
- **Feature-series gap to current stable:** upstream has moved beyond 6.12 through later 6.x series and into the 7.x line; current stable is 7.2.10.

For each newly detected stable or longterm release, the periodic JetOS check should preserve the official changelog reference and append a concise categorized digest before or alongside adoption. The digest should call out at least: kernel/user ABI and syscall changes; ARM64/ARMv7/x86-64 changes; storage/filesystem changes; networking; drivers/device discovery; build/toolchain requirements; security/correctness fixes; and anything that changes the JetLang↔kernel boundary.

The Behind a Log is informational during a stabilization emergency: being behind must be visible, but version drift alone must not prevent a known-good JetOS boot from being restored. Once the baseline is green, upstream currency becomes active engineering debt under `MANDATE_004H_UPSTREAM_CURRENCY.md`.

## History

<!-- BEGIN AUTO HISTORY -->
<!-- STATUS FINGERPRINT: linux:6.12.96:7.2.10:6.12.112 -->
### 2026-10-14 — Linux drift check

- JetOS pin: `6.12.96` / `6d15a1029d425b15c59463910ebdccc4afe760d6`
- Upstream stable observed: `7.2.10`
- Pinned longterm line observed: `6.12.112`
- Drift summary: one major-number line behind current stable; 16 maintenance releases behind on the existing 6.12 LTS line.
- Official upstream change sources: https://cdn.kernel.org/pub/linux/kernel/v7.x/ChangeLog-7.2.10 and https://cdn.kernel.org/pub/linux/kernel/v6.x/ChangeLog-6.12.112
- Immediate upgrade strategy after boot stabilization: first prove the current pin boots; then update the existing 6.12 line and qualify; then advance feature series in bounded steps to current stable, preserving JetOS changes and qualification evidence at every step.
