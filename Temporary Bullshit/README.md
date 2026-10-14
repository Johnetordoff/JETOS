# Temporary Bullshit

Status: **Fat/development-only temporary tooling. Never ship in Skinny Mode.**

This directory exists because JETOS needs practical source-accounting tools now without allowing inventory work to block kernel/JetLang engineering. It is intentionally disposable; nothing in the production/runtime contract may depend on it.

## Commands

```bash
python3 "Temporary Bullshit/prepare_sources.py"
python3 "Temporary Bullshit/count_loc.py"
python3 "Temporary Bullshit/list_file_types.py"
python3 "Temporary Bullshit/write_inventory.py"
python3 "Temporary Bullshit/print_hierarchy.py"
python3 "Temporary Bullshit/full_report.py"
```

`prepare_sources.py` ensures `source/linux` and the CPython-derived `source/cpython` JetLang lineage are present. While transitional `.gitmodules` still exists, it may initialize the pinned gitlinks so `tools/absorb_source.py` can safely absorb them. In the canonical unified repository it only verifies ordinary tracked source trees.

The other commands reuse `tools/source_inventory.py`; they do not maintain a second source-counting implementation. `print_hierarchy.py` produces a compact project hierarchy. `full_report.py` writes the complete inventory under `Temporary Bullshit/output/` by default and includes key totals, file types, and a compact hierarchy.

## Rules

- This folder is not JetOS runtime code or JetLang source.
- The canonical source-control end state is one outer JETOS repository, with source under `source/` and no nested `.git` metadata.
- The scripts should remain deterministic and testable even though the workspace is temporary.
- A missing full LOC baseline must never block engineering work.
- Prefer local recursive filesystem/Git traversal over one remote API request per file.
- Skinny Mode must remove this entire directory.
- Once permanent source-accounting/reporting machinery supersedes it, delete this directory rather than retaining dead tooling.
