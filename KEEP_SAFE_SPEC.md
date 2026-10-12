# KEEP_Safe — protected local-retention type

Status: **active design specification**
Governed by: `MANDATE_004F_CUTTING_ROOM_STORAGE.md` and `MANDATE_004E_INFORMATION_LIFECYCLE.md`.

## Purpose

`KEEP_Safe` is JETOS's explicit protected-retention type for data that must remain available locally beyond the ordinary cutting-room working window.

JETOS is still not the archive. `KEEP_Safe` is a bounded exception for material whose local retention has a current responsibility. It must not become a general-purpose bulk historical store.

## Required representation

A `KEEP_Safe` payload is stored in **compressed and encrypted form**. The normal retained representation must not be the plaintext bulk payload.

The surrounding JETOS metadata should remain minimal and must not reveal protected contents. It may record non-secret information needed to operate and recover the item, such as:

- stable item identifier;
- lifecycle state;
- creation/packaging time;
- source/provenance reference;
- compression/encryption format identifiers and version;
- encrypted payload size;
- integrity/check metadata that does not expose the payload;
- archive/source-of-record reference when applicable;
- recovery/decryption procedure reference;
- reason the local `KEEP_Safe` exception still exists;
- next `DUE` judgment point.

## Key boundary

Encryption keys, passwords, private keys, recovery secrets, or equivalent secret material are **not part of the `KEEP_Safe` payload metadata** and must not be embedded alongside the encrypted data merely for convenience.

Key management remains a separate protected capability/lifecycle responsibility. A `KEEP_Safe` item is not considered safely recoverable merely because encrypted bytes exist; the authorized recovery path and required key material must also have a known protected lifecycle.

## Lifecycle semantics

`KEEP_Safe` does not mean KEEP forever.

It means:

1. retain the item locally because a current JETOS responsibility requires it;
2. keep the bulk payload compressed and encrypted at rest;
3. expose only the minimum non-secret metadata needed to understand its state;
4. keep its archive/backup/recovery relationship explicit;
5. periodically place it `DUE` for judgment under Mandate 004E;
6. do not delete or release it merely because it is `DUE`, stale, superseded, or old;
7. release the local copy only after the applicable authorization, dependency, archive/backup, integrity, and recoverability conditions are satisfied.

## Working-copy rule

When authorized work requires plaintext, JETOS may create the smallest practical temporary working representation. That working representation inherits the same protection requirements and should be removed from the active cutting room when the work is complete and its continued presence is no longer required.

Decompression/decryption must not silently convert `KEEP_Safe` into an unbounded persistent plaintext store.

## Format rule

`KEEP_Safe` is a semantic JETOS type, not permission to invent insecure cryptography or a proprietary cipher.

The exact compression container, authenticated-encryption construction, key derivation/key-wrapping method, versioning, and migration rules must be explicitly specified and testable before an implementation claims production-safe `KEEP_Safe` encoding. JETOS should prefer well-established cryptographic primitives exposed through an authorized platform/native boundary rather than custom cryptographic algorithms.

Until the concrete encoding format is implemented and qualified, documentation may define the `KEEP_Safe` lifecycle/type contract but must not falsely claim that protected encoding is already operational.

## Integrity and recovery

A valid `KEEP_Safe` implementation must make corruption or failed authentication visible and must provide a deterministic verification/recovery path. Failure to decrypt, authenticate, decompress, locate required keys, or establish required backup/recovery state must fail visibly rather than returning partial or silently corrupted data.

## Relationship to the cutting-room rule

Ordinary JETOS data should leave the local working set when its active role ends and safe handoff/recovery requirements are satisfied.

`KEEP_Safe` is the named exception when there is a legitimate reason for protected local retention. It keeps that exception explicit, compact where compression permits, encrypted at rest, lifecycle-managed, and reviewable instead of allowing miscellaneous bulk data to accumulate invisibly.
