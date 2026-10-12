# Frozen vendored sources

JETOS keeps the source inputs required for its Linux-backed Gen 2 build inside the repository. Normal `prepare`, `build`, and `run` operations do **not** clone, fetch, or download Linux or CPython.

`vendor/sources.json` is the canonical provenance and integrity manifest. Each source snapshot is stored as a deterministic `tar.xz` stream split into sub-50 MiB Git-friendly chunks. `tools/vendor_sources.py materialize` verifies every chunk and the reconstructed archive before extracting it into `.build/`.

The frozen inputs are:

- Linux 6.12.96 at commit `6d15a1029d425b15c59463910ebdccc4afe760d6`.
- The JETOS language source snapshot based on CPython commit `9d22a5334bd5273962adceeb697a1337e9a0ca21`, with the JETOS interpreter-identity patch already applied before archival.

Refreshing either source is an explicit maintainer operation: `python tools/vendor_sources.py freeze`. That command is intentionally separate from every ordinary build path and is the only source-freezing operation permitted to use the network. A fresh checkout containing the vendor chunks can prepare and build these source inputs without network access.

The extracted `.build/` copies are disposable working material and remain ignored by Git. The vendor chunks are the repository-owned frozen source-of-truth inputs.
