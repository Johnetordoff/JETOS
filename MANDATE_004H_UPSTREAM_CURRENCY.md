# MANDATE_004H — Upstream currency

Status: **PERMANENT DEVELOPER ONE HARD RULE**
Scope: JETOS language/runtime and upstream source governance
Authority: Developer One / repository owner

## Python hard rule

JETOS must keep up to date with **stable CPython**.

- The default JETOS language base tracks the latest stable CPython maintenance release that is reasonably available for qualification.
- Development, alpha, beta, release-candidate, or `main` snapshots are not the normal JETOS language base unless Developer One explicitly authorizes an experiment.
- Every adopted Python release is pinned to an exact upstream tag/commit for reproducibility.
- Security and maintenance updates are high-priority source updates rather than optional backlog work.
- A new Python release is first built and qualified in **Fat Mode**.
- The complete JETOS standard-library and Python↔OS qualification surfaces must pass before that release becomes the basis of a **Skinny Mode** image.
- If a Python update exposes a missing Linux/kernel capability, JETOS adapts the operating-system substrate. JETOS does not solve the problem by silently trimming Python functionality.
- Skinny Mode may lag the upstream release only for the time required to make the exact pinned release pass qualification on the target hardware. Such lag is explicit technical debt, not a permanent version fork.

The governing direction is therefore:

> **Python moves forward; JETOS follows it; the Linux substrate is adjusted to preserve the qualifying Python surface.**

## Gentoo provisional rule

Gentoo is a preferred upstream **source/build/package-intelligence** system for JETOS Fat Mode because it provides current source-oriented package metadata, patches, architecture knowledge, dependency information, and build recipes.

For now this is a preferred input, not an unconditional rolling-runtime dependency:

- monitor and consume useful current Gentoo knowledge in Fat Mode;
- pin every imported Gentoo-derived input or decision that affects a reproducible JETOS build;
- do not blindly synchronize Skinny Mode with Portage or a moving Gentoo tree;
- do not install Gentoo components merely to claim currency;
- only qualified outputs required by the JETOS device role belong in Skinny Mode.

Developer One may later promote Gentoo currency to the same mandatory status as Python. Until then, Python currency is the hard rule and Gentoo currency is the preferred source/build strategy.

## Relationship to Fat and Skinny Mode

**Fat Mode is where upgrades are absorbed, built, diagnosed, and qualified. Skinny Mode is a qualified projection of Fat Mode for a specific target.**

An upstream update therefore follows this path:

1. identify the new stable upstream release;
2. pin it exactly;
3. build it in Fat Mode;
4. run language, standard-library, Python↔OS, architecture, and target tests;
5. repair JETOS/Linux/native substrate gaps without reducing the protected Python surface;
6. regenerate the target Skinny image only after qualification passes;
7. record the exact source revisions and resulting image provenance.

## Conflict rule

Any stale document, tool, generated recommendation, or historical pin that would keep JETOS indefinitely on an obsolete Python release conflicts with this mandate. Reproducible pinning is a checkpoint, not permission to stop updating.
