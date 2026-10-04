# JETOS — John E Tordoff's Operating System

JETOS is a Python-first operating-system project bootstrapped from Gentoo/Linux source ecosystems.

Current repository phase: architecture + migration experiments.

Language direction:
- Python for JETOS-owned control logic.
- C for native substrate and ports.
- Assembly only for explicitly registered architecture-specific irreducibles.
- C++ is migration debt.
- Bash may exist as a shell or in quarantined package-build environments, but not as the JETOS control language.

Text direction:
- Dona Code is the JETOS character-encoding model.
- Unicode is supported across JETOS text APIs.
- UTF-8 is the canonical encoding when JETOS controls the byte representation.
- Raw byte data remains explicitly representable at compatibility boundaries.

See `PHILOSOPHY.md`, `REQUIREMENTS.md`, and `docs/architecture/`.
