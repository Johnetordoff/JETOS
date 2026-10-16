# Behind a Log of Gentoo

Status: **HISTORICAL / FROZEN**

This document preserves the Gentoo-informed configuration and Linux provenance that helped shape the current JetOS source estate. It is no longer an upstream-drift ledger and creates no requirement to track, follow, or update Gentoo or upstream Linux simply because those projects release newer versions.

JetOS is now its own source-built Linux distribution. The recorded Linux baseline below is provenance for the source that became JetOS-owned kernel code. Future kernel changes are deliberate JetOS integrations, not rolling-distribution maintenance.

## Frozen provenance snapshot

Recorded on 2026-10-14:

- JetOS Linux provenance baseline: **6.12.96**
- Recorded upstream commit: `6d15a1029d425b15c59463910ebdccc4afe760d6`
- At the time of the old drift check, kernel.org stable was **7.2.10**.
- At the time of the old drift check, the 6.12 longterm line had reached **6.12.112**.

Those version differences are retained only as historical context. They are not current JetOS debt, an update schedule, or an instruction to replace the vendored `source/linux` tree.

## Historical record

The previous automatic drift system characterized the baseline as one major-number line behind upstream stable and sixteen maintenance releases behind the then-current 6.12 longterm release. That model was retired on 2026-10-16 when JetOS adopted the source-ownership rule: `source/linux` is JetOS kernel source, not a rolling Linux-distribution mirror.

If JetOS later needs an upstream Linux change for a security fix, hardware target, correctness issue, capability, or deliberate engineering improvement, that specific change may be examined and integrated with provenance and qualification. Upstream release movement alone is not sufficient reason to update JetOS.
