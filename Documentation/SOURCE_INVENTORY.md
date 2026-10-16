# Source inventory machinery

JetOS keeps one machine-readable view of the complete source estate so humans and
automation do not have to inspect paths by hand.

## Generate the inventory

From a checkout where the pinned Linux and CPython/JetLang trees are initialized:

```bash
python3 tools/source_inventory.py
```

For a transitional submodule checkout, the existing preparation wrapper can
initialize the pinned trees first:

```bash
python3 "Temporary Bullshit/write_inventory.py" --prepare
```

The default output directory is `artifacts/source-inventory/`.

Generated artifacts:

- `source-inventory.json` — complete document with summary, source-area totals,
  file-type totals, every file record, and unreadable-path diagnostics.
- `source-inventory.jsonl` — one compact JSON object per file, intended for
  streaming tools and path queries.
- `source-inventory.csv` — flat table for spreadsheets, databases, and shell
  tooling.
- `source-tree.txt` — one repository-relative path per line.
- `source-inventory.md` — human summary.

Each file record includes `path`, `source_area`, `directory`, `name`, `type`,
`bytes`, `text_lines`, `binary`, and `symlink`.

Stable source areas are:

- `linux` — `source/linux/**`
- `jetlang-cpython` — `source/cpython/**`
- `shared` — `source/shared/**`
- `ports` — `source/ports/**`
- `source-metadata` — other `source/**` paths
- `jetos` — everything else in the JetOS checkout

## Pull paths without browsing the tree

`tools/source_inventory_query.py` queries the generated inventory and does not
walk the source tree again.

Examples:

```bash
# One exact path as JSONL
python3 tools/source_inventory_query.py \
  --path source/linux/kernel/fork.c

# Every C file under the Linux networking drivers, paths only
python3 tools/source_inventory_query.py \
  --prefix source/linux/drivers/net/ \
  --type .c \
  --format paths

# All CPython/JetLang headers
python3 tools/source_inventory_query.py \
  --area jetlang-cpython \
  --glob '*.h' \
  --format jsonl

# Count matching ported source files
python3 tools/source_inventory_query.py \
  --area ports \
  --count
```

Filters from different categories are combined with AND. Repeated values inside
one category are alternatives, except repeated `--contains` values, all of which
must occur in the path. `--limit` can cap the emitted result set.

Both `source-inventory.jsonl` and `source-inventory.json` are accepted through
`--inventory`; JSONL is the default because it streams large source estates
without loading the complete file list into memory.
