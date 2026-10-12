# Mandate 004F — Developer One Sub-Hyper-Mandate: JETOS is the cutting room, not the archive

Status: **active, permanent, SUB-HYPER-MANDATE**
Issued by: **Developer One** (the repository owner), 2026-10-11.
Parent: **Mandate 004 — Developer One Hyper Mandate**.
Related: **Mandate 004E — information lifecycle analysis worker**.
Scope: **JETOS storage behavior, workers, services, agents, staging areas, caches, working datasets, derived artifacts, lifecycle metadata, and integrations with designated archive/backup systems.**

## Core principle

**JETOS is the cutting room, not the archive.**

JETOS is an operating and transformation environment. It may ingest, inspect, compare, transform, validate, route, summarize, derive from, and temporarily stage data needed for current work, but it must not become the default long-term home for bulk historical data.

Long-term bulk retention belongs in a designated archive, backup, source-of-record, or other explicitly assigned storage system. JETOS should retain enough metadata and references to know what the data is, where its protected archival copy belongs, what work was performed on it, and how to recover or reacquire it when authorized.

## Working-set rule

JETOS should keep the smallest practical working set needed for current responsibilities.

Data may remain locally while it is:

- actively being processed, inspected, transformed, indexed, validated, or judged;
- needed by a current service, boot path, capability, recovery path, or explicitly active project;
- awaiting a safe handoff to an archive/backup/source-of-record destination;
- needed to verify that an archival or transformed copy is complete and recoverable;
- retained by another explicit JETOS safety, provenance, reproducibility, legal, recovery, or owner rule.

Once bulk data is no longer part of the active working set, JETOS should not retain a redundant long-term copy merely because storage is available.

## Archive boundary

JETOS must distinguish at least these roles:

- **working copy** — data presently needed for active work;
- **staging copy** — temporary data awaiting processing, validation, transfer, or handoff;
- **derived artifact** — output created from source data and retained only as long as its current purpose requires;
- **archive/source-of-record reference** — non-secret metadata identifying where the durable protected copy belongs or can be recovered;
- **protected exception** — data that another explicit rule requires JETOS itself to retain.

JETOS must not silently redefine a working or staging copy as the permanent archive.

## Handoff before cleanup

The cutting-room principle is not permission to discard data casually.

Before JETOS removes a local bulk-data copy because its active role has ended, it must have sufficient evidence that the applicable retention requirement has been satisfied. Depending on the data, that may include establishing that:

- the designated archive/source-of-record copy exists;
- the transfer or backup completed successfully;
- integrity can be checked by size, hash, manifest, record count, or another suitable method;
- the archived copy is recoverable through a known procedure;
- required provenance and lifecycle metadata have been preserved;
- no active dependency still requires the local working copy;
- deletion or local release is otherwise authorized by applicable policy.

If JETOS cannot establish the required archival/backup state, the local item must remain protected or explicitly unresolved rather than being deleted merely to satisfy a storage-minimization goal.

## Hidden and protected data

The cutting-room model preserves the data-protection rules of Mandate 004E.

Protected data remains hidden by default. JETOS should expose lifecycle, provenance, location, integrity, dependency, and handoff metadata without unnecessarily displaying or duplicating protected payloads.

Moving data out of JETOS's active working set does not weaken its protection. Archive and backup destinations must preserve the applicable confidentiality, integrity, recovery, and access-control requirements.

## KEEP_Safe protected-retention type

JETOS has a special protected-retention type named **`KEEP_Safe`** for data that has a legitimate current reason to remain available locally beyond the normal cutting-room working window.

A `KEEP_Safe` item is a **protected exception**, not a declaration that JETOS has become the archive. Its normal retained payload must be stored in **compressed and encrypted form** rather than as an ordinary persistent plaintext bulk copy.

The canonical semantic/type contract is defined in `KEEP_SAFE_SPEC.md`.

At minimum, `KEEP_Safe` means:

- the data has an explicit current JETOS retention responsibility;
- the retained bulk representation is compressed and encrypted at rest;
- secret key material is kept separate from the payload and its ordinary metadata;
- only minimal non-secret lifecycle/provenance/integrity/recovery metadata is exposed;
- authorized plaintext/decompressed working copies are temporary working-set material and must not silently become a second persistent store;
- the item remains lifecycle-managed and may become **DUE for judgment** without becoming automatically deletable;
- local release still requires the applicable dependency, authorization, archive/backup, integrity, and recoverability checks.

`KEEP_Safe` does not mean **KEEP forever**. It means **keep safely while the local retention responsibility exists**.

The exact compression container, authenticated-encryption construction, key-management boundary, versioning, and migration rules must be explicitly specified and qualified. This mandate does not authorize custom cryptography or allow documentation to claim an encoding is operational before it has been implemented and tested.

## Information Lifecycle Worker responsibility

The Information Lifecycle Worker established by Mandate 004E must understand this storage boundary.

For bulk or potentially accumulating data, the worker should be able to identify:

- whether the item is active working data, staging data, a derived artifact, archive-referenced data, or a `KEEP_Safe` protected exception;
- why JETOS still needs a local copy;
- whether a protected archive/source-of-record destination is known;
- whether archival/backup handoff is complete and verified;
- whether the local copy is DUE for judgment about continued working-set necessity;
- what dependencies block release from the working set;
- what evidence would permit a later authorized cleanup decision.

For `KEEP_Safe`, the worker should additionally know whether the protected representation, recovery/key path, and required backup state are established without exposing the payload or secret key material.

**DUE remains a judgment state.** DUE for storage review does not itself mean move, delete, archive, or purge. It means the continued local role should be judged.

## What JETOS may retain long term

This principle does not require JETOS to forget its own operating system or discard information that is genuinely part of its maintained state.

JETOS may retain long-term data that has an explicit JETOS responsibility, including as applicable:

- operating-system source, configuration, policy, manifests, and provenance needed for reproducibility;
- current boot, recovery, diagnostic, and machine-state information with an active responsibility;
- compact indexes, lifecycle metadata, references, hashes, manifests, and catalogs needed to locate or validate archived material;
- durable governance records and deletion/provenance ledgers;
- `KEEP_Safe` protected-retention items while their explicit local retention responsibility remains active;
- data explicitly required by another higher-priority retention, recovery, or owner mandate.

The distinction is functional: JETOS may preserve **operational state and compact knowledge about bulk data** without becoming the warehouse for the bulk data itself.

## No accidental data lake

Workers and integrations must not create an undeclared data lake inside JETOS through convenience copies, ever-growing caches, duplicate imports, abandoned staging directories, repeated downloads, unbounded logs, or copied historical datasets.

Where accumulation is useful only temporarily, storage should have an explicit working purpose and lifecycle. Unbounded accumulation without a current JETOS responsibility is an architectural defect.

`KEEP_Safe` must not be used as a loophole to relabel miscellaneous bulk data and bypass this rule. Every `KEEP_Safe` item must have an explicit local-retention reason and lifecycle.

## Archive independence

JETOS must not hard-code one universal archive product or location unless Developer One explicitly designates one.

The storage boundary should be expressed through a small, explicit interface/metadata model so different protected archive, backup, or source-of-record systems can satisfy it without changing JETOS's core architecture.

If the archive is unavailable, JETOS may continue permitted work using its current authorized working set where safe, but it must not falsely mark archival handoff as complete.

## Acceptance criteria

This mandate is operational when JETOS can:

1. distinguish active/staging/derived data from durable archive/source-of-record data and `KEEP_Safe` protected exceptions;
2. avoid using JETOS local storage as the default permanent home for bulk historical data;
3. retain only the working set and explicit protected exceptions needed for current responsibilities;
4. preserve compact provenance, lifecycle, integrity, and archive-reference metadata without unnecessarily retaining bulk payloads;
5. store `KEEP_Safe` retained payloads in a qualified compressed-and-encrypted representation with key material kept separately;
6. verify required archive/backup handoff before treating a local working copy as releasable;
7. keep data protected and unresolved when required handoff/recovery evidence is missing;
8. let the Information Lifecycle Worker surface data that is DUE for a storage-role judgment without equating DUE with deletion;
9. prevent unbounded caches, staging areas, logs, repeated imports, convenience copies, or misuse of `KEEP_Safe` from silently becoming long-term stores;
10. preserve operating-system, recovery, reproducibility, governance, and other explicitly retained JETOS state;
11. respect all deletion, backup, privacy, provenance, approval, containment, cryptographic-key, and machine-safety rules when releasing or recovering working data.

## Governing phrase

**JETOS is the cutting room, not the archive: bring data in to work on it, know where the protected durable copy belongs, use `KEEP_Safe` only for explicit protected local-retention exceptions, preserve the metadata needed to find and trust the data, and do not let the operating system become a bulk historical warehouse by accident.**
