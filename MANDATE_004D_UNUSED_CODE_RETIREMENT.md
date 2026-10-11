# Mandate 004D — Developer One Super Directive: unused-code retirement and deletion ledger

Status: **active, permanent, SUPER DIRECTIVE / SUB-HYPER-MANDATE**
Issued by: **Developer One** (the repository owner), 2026-10-11.
Parent: **Mandate 004 — Developer One Hyper Mandate**.
Related: **Mandate 004A — responsibility map / map-or-delete retention boundary** where that mandate applies.
Scope: **Mac Brain, Brain Clone, JetOS, Digital Yamin coding work, workers, agents, repository tooling, tests, and future compatible governed systems.**

## The directive

Project-owned code exists to perform a current responsibility. If a function, method, class, module, file, tool, test helper, adapter, compatibility path, or other project-owned implementation is no longer used and no longer has a legitimate current responsibility, it is eligible for deletion and should eventually be removed from the active codebase.

The standing direction is therefore:

**unused code does not remain indefinitely. Keep the active source footprint small. Delete code that is no longer used, subject to the evidence, safety, and retention rules below.**

Deletion is preferred over accumulating dead-code comments, disabled branches, duplicate implementations, abandoned compatibility shims, or "just in case" graveyard source inside the live tree.

## Evidence before deletion

"Unused" must be established from current evidence, not guessed from a name or from a single text search. Before deleting project-owned code, inspect the relevant evidence for its language and runtime, including as applicable:

- imports and direct references;
- entry points, registries, callbacks, plugins, dynamic dispatch, reflection, and configuration-driven loading;
- tests, fixtures, generated outputs, build/install paths, migrations, and recovery paths;
- runtime/process evidence and responsibility-map assignment where present;
- external or cross-repository consumers that are part of the governed architecture;
- user-data, state, provenance, compatibility, or recovery obligations;
- whether the responsibility was transferred to another implementation.

A lack of obvious references is evidence, not by itself proof. Agents must make a reasonable project-specific determination that the implementation has no current use or required responsibility.

## Relationship to responsibility maps

Where Mandate 004A applies, its map-or-delete retention boundary remains authoritative.

- **Mapped/protected material** is not deleted casually. Removing it requires an explicit architectural decision that the responsibility is no longer required or has been safely transferred, followed by the normal dependency/use/safety checks.
- **Unmapped material** is a deletion candidate and must not remain an indefinite gray zone. Investigate it and resolve it through map-or-delete.
- A mapped item may still become unused. Mapping records intentional responsibility; it is not permanent immunity from deletion once that responsibility disappears.

When a mapped item is removed, regenerate/update the responsibility map in the same change where practical.

## Mandatory agent deletion changelog

Every deletion performed because code is unused must be recorded in the repository's dedicated agent-facing deletion changelog:

`AGENT_DELETION_CHANGELOG.md`

This changelog is separate from ordinary human release notes. It is a durable recovery/index surface for coding agents and maintainers. Its purpose is not to preserve duplicate source code; Git history remains the source of the deleted bytes. Its purpose is to record **what disappeared, why it disappeared, and how to find it again**.

The changelog is append-only except for correcting factual mistakes or adding later restoration/commit references. Do not erase old deletion entries merely because the deleted code stays gone.

### Required entry fields

Each unused-code deletion entry must contain, in a consistent machine-scannable format:

- entry id;
- date;
- repository;
- deleted path and, when relevant, qualified symbol name;
- kind of item removed;
- reason it was considered unused;
- evidence checked;
- replacement or responsibility transfer, if any;
- a Git-history recovery hint, including the prior path/symbol and pre-deletion ref/commit when known;
- PR and/or deletion commit when known;
- notes needed to distinguish the retired implementation from later code.

Use the entry schema defined in `AGENT_DELETION_CHANGELOG.md`.

The deletion and its changelog entry should land in the same PR/change whenever practical. A deletion is not considered governance-complete until the ledger entry exists.

## Agent read rule

**Agents-only operational context: read `AGENT_DELETION_CHANGELOG.md` before re-implementing, restoring, or adding a replacement for behavior that may have existed previously.**

When an agent encounters a missing symbol, old reference, apparently removed feature, or temptation to rebuild functionality from scratch, it must search the deletion changelog and relevant Git history first. This prevents the system from repeatedly deleting and recreating the same implementation without understanding why it was retired.

Useful recovery patterns include ordinary native Git history such as:

```text
git log --all -- <path>
git log -S '<symbol>' --all
git show <pre-deletion-commit>:<path>
```

Equivalent native Git inspection is acceptable. GitHub-specific history is never required.

## Restoration rule

Deleted code may be restored when a real responsibility returns. Restoration must be deliberate: inspect the deletion entry and intervening architecture first, then either restore the old implementation or write a smaller/current replacement as appropriate.

If a previously logged deletion is restored, append a restoration note to the same ledger entry or add a linked restoration entry. Do not silently remove the original deletion record.

## No live-code graveyard

Do not satisfy this directive by moving unused implementation into another tracked source directory, commenting it out, renaming it `old_`, or keeping a disabled copy in the active repository. If it is not used, remove it from the live source tree and rely on Git history plus the deletion changelog for recovery.

Archival artifacts that are intentionally retained for evidence, provenance, fixtures, compatibility, or another explicit responsibility are not "dead code" merely because they are not executed. Their retention responsibility must be explicit.

## Safety and authority boundary

This directive does not authorize unsafe deletion of user data, secrets, active state, externally required artifacts, legal/provenance records, boot/recovery artifacts, or material retained by a higher-priority safety rule.

It also does not bypass owner approval, quorum, containment, deployment, machine-safety, provenance, reproducibility, or repository-specific destructive-action rules. Where deletion is required by this directive but temporarily blocked by a higher-priority rule, record the item as a pending cleanup candidate rather than pretending it is in use.

## Source-footprint consequence

Mandate 004's "smallest practical source footprint" rule is active maintenance, not merely a design preference. Agents should continuously notice obsolete implementation and remove it when its responsibility ends.

The intended long-term state is simple:

- current responsibility -> current code;
- no current responsibility -> eventual deletion;
- deleted code -> searchable Git history plus a durable deletion-ledger entry.

## Cross-system propagation

This directive is architectural policy across Mac Brain, Brain Clone, JetOS, and governed coding agents. Each governed repository must carry this mandate or an equivalent binding reference to it and must provide an agent deletion changelog when project-owned code can be retired.

A repository may add stricter deletion checks, but it may not weaken the requirements to remove genuinely unused code eventually or to record unused-code deletions in the agent-facing changelog.

## Acceptance criteria

This directive is operational when:

1. agents are explicitly instructed to read this mandate and the deletion changelog;
2. unused project-owned code is treated as eventual deletion material rather than permanent ballast;
3. deletions are evidence-based and respect higher-priority safety/retention rules;
4. every deletion for non-use is accompanied by a structured ledger entry;
5. the ledger gives enough path/symbol/ref context to locate the retired implementation in native Git history;
6. responsibility maps and other inventories are updated when affected;
7. restoring retired behavior begins by consulting the ledger and Git history rather than blindly recreating it.
