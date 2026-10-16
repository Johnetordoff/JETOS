# JetOS agent instructions

This is the single canonical agent file. Append future agent-specific instructions and deletion-ledger entries here; do not create additional `AGENT*` files.

Before changing JetOS, read `MANDATE.md`, `ARCHITECTURE.md`, `README.md`, `ODROID_HC1_TARGET.md`, `SKINNY_MODE.md`, `WORK_SERVER.md`, and any directly relevant implementation/source documentation.

## Core rules

- JetLang is the JetOS language/runtime and is CPython-derived. Preserve Python semantics and the supported standard-library surface while allowing deliberate implementation improvement.
- Use Python/JetLang for project-owned high-level logic by default. Keep C/assembly confined to real native boundaries.
- JetOS has first-class `x86_64`, `armv7`, and `arm64` targets; the ODROID-HC1 is the current physical reference target.
- Use `source/` for controlled external/native source and dependency source.
- Do not add Node.js, a JavaScript package/build stack, GitHub Actions, or unnecessary third-party SDK/dependency ecosystems.
- Distinguish implemented behavior from plans. Preserve provenance and exact source pins.
- Runtime-affecting source work must qualify the newly built JetOS kernel and newly built JetLang runtime together where the environment supports it.
- Do not let full-repository LOC/byte accounting block engineering work.
- Treat `Documentation/FUTURE_AI_SPEECH_TORRENT.md` as the long-horizon design direction for AI-native support, speech-to-text/speech-to-command, and torrent/distributed-content services. Preserve its distinction between future architecture and implemented behavior, and prefer JetLang orchestration over premature kernel policy.
- Keep the active tree small. Evidence-confirmed unused project-owned code should be removed rather than archived inside the live source tree.

## Repository layout

```text
MANDATE.md          # canonical governance/directives
AGENTS.md           # canonical agent instructions + deletion ledger
ARCHITECTURE.md     # canonical architecture description
Documentation/      # supporting documentation, logs, and metrics
source/             # external/native/dependency source lineages
src/                # JetOS-owned implementation
tools/              # repository-owned development/build/qualification tools
```

`source/` currently contains the Linux lineage, CPython-derived JetLang lineage, shared native source, and ported dependency source. Additional dependency source should be placed under `source/` rather than creating new root-level source buckets.

## Work and test behavior

Use repository-owned native/local tooling. Never add `.github/workflows/`. A worker-host failure is not permission to change JetOS merely to conceal missing Docker, networking, storage, credentials, or other infrastructure.

Ordinary bounded automation should not rewrite protected native source lineages without the integrated qualification required by `MANDATE.md`.

## Deleted-code ledger

Before recreating, restoring, or replacing behavior that may have existed previously, inspect this ledger and native Git history first.

Typical recovery searches:

```text
git log --all -- <path>
git log -S '<symbol>' --all
git show <pre-deletion-commit>:<path>
```

Append unused-code deletion entries in this format:

```text
<!-- deletion-entry:v1 -->
### DEL-YYYYMMDD-NNN — short name
- date: YYYY-MM-DD
- repository: owner/repository
- kind: function | method | class | module | file | tool | test-helper | adapter | compatibility-path | other
- path: relative/path.py
- symbol: qualified.symbol.name | n/a
- reason_unused: concise reason the item had no current use/responsibility
- evidence_checked: imports/references/registries/runtime/tests/config/external consumers checked
- replacement: replacement or responsibility transfer | none
- pre_deletion_ref: commit/ref containing the retired implementation | unknown
- deletion_pr: PR number/url | unknown
- deletion_commit: commit SHA | unknown
- recovery_hint: path/symbol and useful Git search terms
- notes: distinguishing context or restoration link | none
```

Do not copy deleted source into the ledger. Git history stores the bytes. If behavior later returns, keep the deletion entry and add a restoration note/entry.

### Entries

No unused-code deletions have been recorded under this policy yet.
