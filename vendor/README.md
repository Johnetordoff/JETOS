# Frozen source inputs

JETOS freezes its two large imported Gen 2 source inputs at exact Git commits:

- `vendor/linux` — Linux 6.12.96, commit `6d15a1029d425b15c59463910ebdccc4afe760d6`.
- `vendor/cpython` — CPython 3.14.8, commit `8e6e75d9102e39bed2a2b279203a396741180f12`.

They are shallow Git submodules so the JETOS repository stays small while the source checkout still has explicit, immutable revisions. Acquire them as part of checking out JETOS (for example with a recursive clone). That is source acquisition, not an operating-system runtime/build action.

`python jetos.py dev`, `python tools/dev.py prepare`, `build`, and `run` never initialize, clone, fetch, pull, or update either source. They fail visibly if a frozen source is absent or at the wrong revision.

For builds, JETOS copies the already-present frozen sources into ignored `.build/` working trees. The CPython copy then receives the small JETOS interpreter-identity patch locally; the pinned upstream source itself remains untouched. Linux is configured and compiled from its local frozen copy.

Updating either gitlink is an explicit source-governance change and therefore changes the frozen JETOS source graph.
