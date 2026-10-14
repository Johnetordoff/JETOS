# Behind a Log of Python

This is the persistent upstream-integration backlog for JetLang's CPython lineage. JetLang deliberately diverges and owns its source after the initial import; stable CPython releases remain first-class compatibility, regression-test, standard-library, bug-fix, and change-reference inputs.

This file is intentionally historical. Do not erase old backlog entries after an integration; append the new state so JetOS can see which upstream changes were pending, which were reconciled into JetLang, and when qualification completed.

## Current status

<!-- BEGIN AUTO STATUS -->
Checked: 2026-10-14T19:00:00+00:00

- JetLang integration baseline: **3.14.8 lineage** (`8e6e75d9102e39bed2a2b279203a396741180f12` initial upstream provenance)
- Latest stable CPython observed: **3.15.0**
- Integration backlog: **1 feature series (3.14.8 -> 3.15.0)**
- Latest release notes: https://www.python.org/downloads/release/python-3150/
- Major-series change notes: https://docs.python.org/3/whatsnew/3.15.html
- Release index: https://www.python.org/downloads/
<!-- END AUTO STATUS -->

## Current release-change digest

The first recorded feature-series integration target is Python 3.15 relative to JetLang's 3.14.8 stabilization baseline. Important upstream changes called out by the official 3.15 release material include:

- a built-in `sentinel` type;
- UTF-8 as the default encoding;
- unpacking in comprehensions;
- explicit lazy imports intended to improve startup behavior;
- a built-in `frozendict` type;
- package startup configuration files;
- substantial further work on the experimental JIT, including reported performance improvements on both x86-64 Linux and AArch64 macOS.

For every newly detected stable Python release, the periodic JetOS check should preserve the official release-note and What's New references and append a concise categorized digest covering at least: language semantics; parser/compiler/interpreter changes; C API/ABI; standard library; import/startup behavior; packaging/build/toolchain changes; architecture-specific behavior; performance work; removed/deprecated functionality; and likely JetLang conflict/integration areas.

A new CPython release does not overwrite JetLang and is not imported as a replacement source tree. The update flow is: identify the upstream change set, reconcile relevant changes and fixes into the existing JetLang-owned source, preserve deliberate JetLang divergences, build the resulting JetLang, run CPython-derived regression tests plus JetLang-native and JetOS same-runtime tests, and promote the new compatibility baseline only after integrated qualification.

The immediate priority remains stabilization of the 3.14-based JetLang build. The 3.15 backlog is recorded now so that once 3.14 is stable, the 3.15 changes can be integrated systematically rather than by replacing the tree.

## History

<!-- BEGIN AUTO HISTORY -->
<!-- STATUS FINGERPRINT: python:3.14.8:3.15.0 -->
### 2026-10-14 — Python integration-backlog check

- JetLang baseline: `3.14.8` lineage / initial upstream provenance `8e6e75d9102e39bed2a2b279203a396741180f12`
- Upstream stable observed: `3.15.0`
- Integration backlog: one Python feature series.
- Official upstream change sources: https://www.python.org/downloads/release/python-3150/ and https://docs.python.org/3/whatsnew/3.15.html
- Initial digest: new sentinel and frozendict built-ins, UTF-8 default encoding, comprehension unpacking, lazy imports, package startup configuration, and substantial JIT work are among the notable 3.15 changes that must be reconciled into JetLang rather than ignored.
- Ownership rule: 3.15 is a change/reference stream to integrate into JetLang; it is not a source-tree replacement or rebase target.
