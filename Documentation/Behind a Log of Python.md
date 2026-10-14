# Behind a Log of Python

This is the persistent upstream-drift ledger for JetLang's CPython lineage. JetLang deliberately diverges, but stable CPython releases remain first-class source, compatibility, regression-test, and standard-library inputs.

This file is intentionally historical. Do not erase old drift entries after a rebase; append the new state so JetOS can see how much divergence existed and when it was reconciled.

## Current status

<!-- BEGIN AUTO STATUS -->
Checked: 2026-10-14T19:00:00+00:00

- JetLang CPython ancestor pinned by JetOS: **3.14.8** (`8e6e75d9102e39bed2a2b279203a396741180f12`)
- Latest stable CPython: **3.15.0**
- Stable drift: **1 feature series behind (3.14.8 -> 3.15.0)**
- Latest release notes: https://www.python.org/downloads/release/python-3150/
- Major-series change notes: https://docs.python.org/3/whatsnew/3.15.html
- Release index: https://www.python.org/downloads/
<!-- END AUTO STATUS -->

## Current release-change digest

The first recorded gap is Python 3.15 relative to JetLang's 3.14.8 ancestor. Important upstream changes called out by the official 3.15 release material include:

- a built-in `sentinel` type;
- UTF-8 as the default encoding;
- unpacking in comprehensions;
- explicit lazy imports intended to improve startup behavior;
- a built-in `frozendict` type;
- package startup configuration files;
- substantial further work on the experimental JIT, including reported performance improvements on both x86-64 Linux and AArch64 macOS.

For every newly detected stable Python release, the periodic JetOS check should preserve the official release-note and What's New references and append a concise categorized digest covering at least: language semantics; parser/compiler/interpreter changes; C API/ABI; standard library; import/startup behavior; packaging/build/toolchain changes; architecture-specific behavior; performance work; removed/deprecated functionality; and likely JetLang merge/conflict areas.

A new CPython release does not overwrite JetLang. The update flow is: import/reconcile the new upstream source, preserve deliberate JetLang divergences, build the new JetLang, run CPython-derived regression tests plus JetLang-native and JetOS same-runtime tests, then promote only after qualification.

## History

<!-- BEGIN AUTO HISTORY -->
<!-- STATUS FINGERPRINT: python:3.14.8:3.15.0 -->
### 2026-10-14 — Python drift check

- JetLang ancestor pin: `3.14.8` / `8e6e75d9102e39bed2a2b279203a396741180f12`
- Upstream stable observed: `3.15.0`
- Drift summary: one Python feature series behind.
- Official upstream change sources: https://www.python.org/downloads/release/python-3150/ and https://docs.python.org/3/whatsnew/3.15.html
- Initial digest: new sentinel and frozendict built-ins, UTF-8 default encoding, comprehension unpacking, lazy imports, package startup configuration, and substantial JIT work are among the notable 3.15 changes that must be reconciled into JetLang rather than ignored.
