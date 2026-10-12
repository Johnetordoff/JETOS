# Mandate 004E — Developer One Sub-Hyper-Mandate: information lifecycle analysis worker

Status: **active, permanent, SUB-HYPER-MANDATE**
Issued by: **Developer One** (the repository owner), 2026-10-11.
Parent: **Mandate 004 — Developer One Hyper Mandate**.
Scope: **JetOS and JetOS-owned workers, services, agents, control-plane logic, metadata, documentation, configuration, provenance records, credentials metadata, caches, indexes, generated knowledge, and external-integration state.**

## The mandate

JetOS must treat important information as having a lifecycle, not as permanently valid merely because it exists on disk or was once correct.

JetOS must provide a dedicated **Information Lifecycle Worker** capable of analyzing the lifecycle state of important information used by the operating system, its services, agents, integrations, and maintenance procedures.

The worker's purpose is to answer, continuously and evidence-first:

- what information exists;
- where it came from;
- when it was created, observed, verified, or last refreshed;
- what depends on it;
- how long it is expected to remain valid;
- what event makes it stale, superseded, expired, revoked, or unsafe to rely on;
- how it is refreshed, renewed, replaced, re-derived, or retired;
- what evidence confirms that the replacement is valid;
- what should happen when lifecycle state cannot be determined.

JetOS must not silently treat unknown-age or unknown-validity information as current.

## Information covered

The worker should analyze lifecycle metadata for information classes including, where present:

- credentials, certificates, tokens, signing material metadata, and authentication configuration;
- provider/API endpoint knowledge and authentication procedures;
- machine, device, network, storage, and capability discovery results;
- cached facts and externally sourced metadata;
- configuration values whose correctness depends on time, environment, hardware, or upstream state;
- source/provenance manifests, pinned upstream revisions, hashes, and imported substrate metadata;
- generated indexes, catalogs, responsibility maps, inventories, and derived reports;
- operational procedures and runbooks;
- policy/rule snapshots whose source may change over time;
- package/release/update metadata;
- compatibility and architecture assumptions;
- recovery and bootstrap information;
- any other information that can become misleading, invalid, dangerous, or operationally useless when stale.

This mandate is about **information validity and continuity**, not merely file age. A very old fact may still be valid; a newly written fact may already be obsolete.

## Lifecycle record

For each tracked information item or class, the worker should preserve non-secret metadata sufficient to determine, where applicable:

- stable identifier or category;
- source/origin and provenance;
- acquisition or creation time;
- last verification time;
- expected validity period, expiry, rotation interval, review interval, or invalidation event;
- current lifecycle state;
- confidence in that state;
- dependencies/consumers;
- refresh, renewal, replacement, re-derivation, or retirement procedure;
- validation procedure after refresh/replacement;
- fallback/recovery procedure when refresh fails;
- authoritative source or local evidence used to judge validity;
- date the lifecycle procedure itself was last verified.

Lifecycle state should use explicit language such as **CURRENT**, **AGING**, **DUE**, **STALE**, **EXPIRED**, **REVOKED**, **SUPERSEDED**, **UNKNOWN**, or another narrowly defined state where needed.

### Meaning of DUE

**DUE means the item has come up for judgment.** It is a review state, not a conclusion.

A DUE item is not automatically stale, invalid, expired, replaceable, deletable, or eligible for mutation. It means the item's lifecycle rule says that the system, owner, or authorized worker should now inspect the evidence and decide whether to keep it current as-is, verify it again, refresh it, replace it, re-derive it, archive it, or take some other authorized action.

The lifecycle worker must not collapse **DUE** into **STALE** or **EXPIRED**. Those stronger states require their own evidence.

## Data hiding, protection, and backup

Lifecycle management must not turn protected data into exposed data.

The underlying data being tracked remains **hidden by default**, **protected**, and **backed up according to its applicable retention/recovery policy**. The lifecycle worker should operate primarily on metadata, provenance, timestamps, identifiers, hashes, dependency relationships, validity rules, and procedures rather than displaying or duplicating the data payload itself.

A lifecycle inspection surface may reveal enough metadata for Developer One to understand an item's state and make a judgment, but it must not expose protected contents merely for convenience.

Where the tracked item is important enough that loss would impair operation, provenance, recovery, auditability, or continuity, lifecycle management must verify or reference an appropriate backup/recovery path. A DUE, STALE, SUPERSEDED, or EXPIRED state does not by itself authorize deletion of the protected or backed-up data.

Backup status is part of lifecycle safety. If an item is supposed to be backed up but the worker cannot establish that a valid recoverable copy exists, that uncertainty must be visible rather than silently treated as safe.

This section does not require every transient cache or regenerable artifact to receive permanent backup. Backup requirements remain contextual to the item's role, recoverability, provenance value, owner policy, and other active retention rules.

## Credentials and expiring security material

Credentials are a critical special case of the information lifecycle.

When a credential, certificate, token class, or other security material has an expiry or mandatory rotation schedule, JetOS must track the non-secret lifecycle metadata and the exact replacement procedure early enough that replacement can occur before expiry.

The worker must not collect or persist credential values, passwords, private keys, bearer tokens, recovery codes, session cookies, or other secret contents. It may track only non-secret lifecycle metadata, dependencies, procedures, and validation state.

If expiry is known but the replacement procedure is missing or incomplete, that is a lifecycle coverage failure. If expiry itself cannot be established, the state must remain **UNKNOWN** rather than silently becoming current.

## Worker behavior

The Information Lifecycle Worker must be analysis-first and conservative.

By default it may:

- inspect authorized local state;
- compare timestamps, versions, hashes, provenance, and dependency metadata;
- evaluate declared validity/expiry/review rules;
- identify stale, expired, superseded, or unverifiable information;
- identify missing refresh/replacement procedures;
- identify items that are DUE for judgment without prejudging the result;
- verify or reference required backup/recovery coverage using non-secret metadata;
- generate owner-readable reports and machine-readable lifecycle records;
- recommend the next refresh/replacement/verification action.

It must not, merely by virtue of this mandate:

- reveal protected data contents;
- delete information;
- overwrite canonical state;
- rotate credentials;
- revoke credentials;
- modify external accounts;
- fetch arbitrary Internet content outside JetOS's explicit network policy;
- bypass approval, containment, provenance, backup, retention, or machine-safety rules.

A separate explicit authorization is required for destructive or externally mutating action.

## Network and authority boundary

Lifecycle analysis must respect JetOS's explicit capability and network policy.

When the worker can establish validity entirely from local evidence, it should do so locally. When authoritative verification requires a network source, the worker may only perform that verification through an explicitly authorized JetOS network capability and approved endpoint.

Network unavailability must not convert UNKNOWN into CURRENT. The worker must record that authoritative verification could not be completed.

## Freshness is contextual

JetOS must not impose one universal freshness interval on all information.

Freshness/expiry may be determined by:

- explicit provider expiration;
- certificate validity period;
- token rotation policy;
- source revision/change detection;
- hardware rediscovery events;
- boot/session lifetime;
- configuration generation;
- package/release cadence;
- documented review interval;
- dependency changes;
- environment changes;
- explicit owner policy.

Where no authoritative lifetime exists, the worker may use a documented review interval, but it must distinguish a review deadline from a real expiry. Reaching the review deadline ordinarily produces **DUE**, meaning judgment is required; it does not by itself prove staleness.

## Dependency awareness

Lifecycle analysis must include the consequences of stale information.

The worker should identify which services, workers, boot paths, integrations, recovery procedures, or user-facing capabilities depend on tracked information. Higher-impact information should be surfaced earlier and more prominently when nearing invalidation.

A lifecycle problem is more serious when stale information can prevent boot, block recovery, break authentication, corrupt provenance, misconfigure hardware, or cause an agent to act from an invalid assumption.

## Procedures are information too

The refresh/replacement procedure itself has a lifecycle.

If a provider, API, command path, file layout, hardware target, authentication flow, source tree, or JetOS architecture changes materially, the worker must consider whether the documented procedure has become stale even if the underlying credential/data has not yet expired.

After a real refresh/replacement is performed, the procedure should be corrected when the observed process differs from the documented one.

## Integration with JetOS architecture

The worker must follow Mandate 004:

- CPython-first;
- Python standard library and JetOS-owned code by default;
- zero/minimal third-party dependencies;
- no Node.js or server-side JavaScript stack;
- shared architecture-neutral logic across `x86_64`, `armv7`, and `arm64` wherever practical;
- explicit capability boundaries;
- provenance-accounted behavior;
- no hidden dependence on an optional delegate node.

The ODROID-HC1 remains a first-class physical target. Lifecycle analysis required for the HC1 must work on the HC1 itself unless a capability is explicitly delegated and the HC1 remains independently bootable and maintainable.

## Human-readable inspection surface

JetOS should expose the worker's current lifecycle analysis in a simple owner-readable form, alongside a machine-readable representation suitable for other JetOS workers.

At minimum the owner must be able to inspect:

- what is being tracked, without unnecessarily exposing the protected data payload;
- current lifecycle state;
- what is DUE for judgment;
- what is stale/expired/unknown;
- what depends on each item;
- whether required backup/recovery coverage is known;
- what procedure restores or revalidates it when action is actually warranted;
- what evidence was used.

A browser-viewable local HTML representation is preferred where JetOS already provides a browser inspection surface, but the canonical data model must not depend on a browser or JavaScript stack.

## Fail-visible rule

The lifecycle system must prefer visible uncertainty over false confidence.

If JetOS cannot establish the age, provenance, validity, expiry, replacement procedure, required backup state, or authoritative source for important information, that gap must be visible as **UNKNOWN** or another explicit unresolved state.

Silently assuming that information remains valid indefinitely, or that required backup exists when it has not been established, is prohibited.

## Acceptance criteria

This mandate is operational when JetOS has a worker or worker-capability that can:

1. inventory important lifecycle-managed information without unnecessarily revealing protected contents or collecting secret values;
2. record provenance, age, verification time, lifecycle rule, dependency, and replacement/refresh procedure;
3. distinguish current, aging, DUE-for-judgment, stale, expired/superseded, and unknown states;
4. preserve the rule that DUE requests judgment rather than automatically authorizing replacement, mutation, or deletion;
5. surface upcoming credential/certificate replacement before expiry;
6. identify information whose validity cannot be established;
7. show what JetOS components depend on stale or expiring information;
8. preserve or reference required backup/recovery coverage for protected important data;
9. preserve a human-readable procedure for restoring validity;
10. validate refreshed/replaced information using appropriate evidence;
11. operate under JetOS's Python-first, minimal-dependency, capability, network, provenance, privacy, backup, and multi-architecture rules;
12. avoid destructive or external mutation unless separately authorized.

## Relationship to other mandates

This mandate complements source provenance, responsibility mapping, deletion governance, reproducibility, credential lifecycle controls, data protection, and backup/recovery policy. It does not weaken retention, security, privacy, containment, machine-safety, deletion, backup, or approval rules.

The governing principle is:

**Important information must have an understood lifecycle. JetOS should know not only what it knows, but when that knowledge comes up for judgment, when it actually stops being safe to trust, and how to preserve, protect, back up, verify, or replace it without exposing the underlying data.**
