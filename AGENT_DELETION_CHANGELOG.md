# Agent Deletion Changelog

> **AGENTS-ONLY OPERATIONAL CONTEXT — READ THIS BEFORE RECREATING OR RESTORING CODE THAT MAY HAVE EXISTED BEFORE.**
>
> This is the dedicated JetOS coding-agent deletion ledger required by `MANDATE_004D_UNUSED_CODE_RETIREMENT.md`. It is separate from ordinary human-facing release/change notes.

## Purpose

Unused project-owned code is removed from the live tree rather than retained as dead code. The deleted bytes remain recoverable from native Git history. This file records enough structured context for an agent or maintainer to understand what was removed, why it was removed, and where to look in Git before re-implementing it.

**Do not copy the deleted implementation into this file.** Keep the active repository small. Record identifiers and recovery context; use Git for the source itself.

Before rebuilding a missing symbol or feature, search this ledger first, then search Git history.

## Native Git recovery

Typical searches:

```text
git log --all -- <path>
git log -S '<symbol>' --all
git show <pre-deletion-commit>:<path>
```

Equivalent native Git commands are fine. A GitHub-specific interface is never required.

## Entry format

Append entries in chronological order using this exact field-oriented shape so humans and agents can scan it consistently:

```text
<!-- deletion-entry:v1 -->
### DEL-YYYYMMDD-NNN — short name
- date: YYYY-MM-DD
- repository: owner/repository
- kind: function | method | class | module | file | tool | test-helper | adapter | compatibility-path | other
- path: relative/path.py
- symbol: qualified.symbol.name | n/a
- reason_unused: concise reason the item had no current use/responsibility
- evidence_checked: concise list of imports/references/registries/runtime/tests/config/external consumers/etc. checked
- replacement: path/symbol/responsibility that superseded it | none
- pre_deletion_ref: commit/ref containing the retired implementation | unknown
- deletion_pr: PR number/url | unknown
- deletion_commit: commit SHA | unknown
- recovery_hint: exact path/symbol and useful Git search terms
- notes: distinguishing context, safety constraints, or later restoration link | none
```

Use `unknown` only when the information is genuinely unavailable at entry time; backfill PR/commit references later when practical. A deletion is governance-complete only when an entry exists.

## Restoration notes

If retired code later becomes useful again, do not erase its deletion entry. Add a `RESTORE-...` entry or append a clearly dated restoration note linking the new path/commit and explaining why the responsibility returned.

## Entries

No unused-code deletions have been recorded under Mandate 004D yet.
