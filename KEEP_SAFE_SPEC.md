# KEEP_Safe — protected local-retention type

Status: **active design specification**
Governed by: `MANDATE.md`.

## Purpose

`KEEP_Safe` is JETOS's explicit protected-retention type for data that must remain available locally beyond the ordinary cutting-room working window.

JETOS is still not the archive. `KEEP_Safe` is a bounded exception for material whose local retention has a current responsibility. It must not become a general-purpose bulk historical store.

## Required representation

A `KEEP_Safe` payload is stored in **compressed and encrypted form**. The normal retained representation must not be the plaintext bulk payload.

Surrounding metadata should remain minimal and non-secret. It may record a stable identifier, lifecycle state, packaging time, provenance, format/version, encrypted size, integrity metadata, archive/source-of-record reference, recovery procedure, the reason the local exception exists, and the next `DUE` judgment point.

## Key boundary

Encryption keys, passwords, private keys, recovery secrets, or equivalent secret material are **not part of the `KEEP_Safe` payload metadata** and must not be embedded alongside encrypted data for convenience. Key management remains a separate protected capability/lifecycle responsibility.

## Lifecycle semantics

`KEEP_Safe` does not mean KEEP forever. It means retain locally while a current JETOS responsibility requires it; keep the bulk payload compressed/encrypted at rest; expose only minimal non-secret metadata; keep backup/recovery relationships explicit; place it `DUE` for judgment when appropriate; and release the local copy only after applicable authorization, dependency, archive/backup, integrity, and recoverability conditions are satisfied.

`DUE` is a judgment state, not automatic permission to delete or mutate.

## Working-copy rule

When authorized work requires plaintext, JETOS may create the smallest practical temporary working representation. That working representation inherits the same protection requirements and should be removed from the active cutting room when the work is complete and continued presence is no longer required.

## Format rule

`KEEP_Safe` is a semantic JETOS type, not permission to invent insecure cryptography. The exact compression container, authenticated-encryption construction, key derivation/wrapping method, versioning, and migration rules must be explicitly specified and tested before production-safe encoding is claimed. Prefer established cryptographic primitives exposed through an authorized platform/native boundary rather than custom algorithms.

## Integrity and recovery

A valid implementation must make corruption or failed authentication visible and provide a deterministic verification/recovery path. Failure to decrypt, authenticate, decompress, locate required keys, or establish required recovery state must fail visibly rather than return partial or silently corrupted data.

## Relationship to the cutting-room rule

Ordinary JETOS data should leave the local working set when its active role ends and safe handoff/recovery requirements are satisfied. `KEEP_Safe` is the named exception for legitimate protected local retention, keeping that exception explicit, encrypted, lifecycle-managed, and reviewable.
