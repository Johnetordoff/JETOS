# Temporary Bullshit

Status: **Fat/development-only temporary tooling. Never ship in Skinny Mode.**

This directory exists because JETOS needs practical source-accounting tools now, without allowing source-inventory work to block kernel/JetLang engineering.

It is intentionally disposable. Skinny packaging must remove this entire directory if it appears in a root filesystem. Nothing in the production/runtime contract may depend on it.

## Commands

Run these from the repository root or directly by path:

```bash
python3 "Temporary Bullshit/prepare_sources.py"
python3 "Temporary Bullshit/count_loc.py"
python3 "Temporary Bullshit/list_file_types.py"
python3 "Temporary Bullshit/write_inventory.py"
python3 "Temporary Bullshit/print_hierarchy.py"
python3 "Temporary Bullshit/full_report.py"
```

`prepare_sources.py` initializes the pinned `source-brain/linux` and `source-brain/cpython` source trees in one Git operation while that migration path remains in use. The other commands reuse the canonical repository scanner in `tools/source_inventory.py`; they do not maintain a second implementation of source counting.

`print_hierarchy.py` prints a compact visual hierarchy of the project and writes the same result under `Temporary Bullshit/output/`. It defaults to two visible levels so hourly reports can show the project shape without flooding the report with every Linux/JetLang source file. Use `--depth N` to change the view.

`full_report.py` writes the complete inventory under `Temporary Bullshit/output/` by default, prints the key totals plus every discovered file type, and now includes the compact project hierarchy. Its hierarchy defaults to two levels; use `--hierarchy-depth N` when a deeper view is useful. Pass `--prepare` if the source trees need to be initialized first.

## Rules

- This folder is not JetOS runtime code.
- This folder is not part of JetLang.
- This folder is not part of the Langkernel.
- It may be ugly, temporary, and operationally convenient, but its scripts should still be deterministic and testable.
- Do not use absence of a complete LOC baseline as a reason to stop engineering work.
- Do not make one GitHub API request per file to count source. Prefer a local checkout and recursive filesystem/Git traversal.
- Hourly reporting should include a compact two-level hierarchy in the user-visible report, while retaining the deeper/full inventory as an artifact for inspection.
- Skinny Mode must remove the whole `Temporary Bullshit` directory every time.
- Once permanent source-accounting/reporting machinery supersedes this workspace, delete the entire directory rather than carrying it indefinitely.
