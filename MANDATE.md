# JetOS Mandate

Status: **active, permanent**
Authority: **Developer One / repository owner**

This is the single canonical JetOS mandate file. New mandate material is appended here; do not create additional mandate files.

## 1. JetOS identity and implementation

- JetOS is its own source-built Linux distribution and a Python/JetLang-first operating system project.
- JetOS must not adopt Gentoo, Debian, Ubuntu, Alpine, or another distribution as its runtime identity, canonical userspace base, or mandatory build base.
- JetLang is the JetOS language/runtime: an improved, deliberately diverging descendant of CPython. CPython remains its source lineage and compatibility foundation.
- Project-owned high-level executable logic defaults to Python/JetLang. C is reserved for unavoidable or measured native boundaries; assembly is reserved for architecture-required work.
- Node.js and the Node package ecosystem are forbidden. Browser JavaScript is allowed only where a genuine browser frontend requires small native JavaScript and must not introduce a Node-based toolchain.
- Third-party dependencies for project-owned Python logic are zero/minimal by default. Prefer the standard library and direct documented HTTP APIs over SDKs.
- Keep code small, clear, shared, and architecture-neutral wherever practical. Do not duplicate whole implementations when only a narrow platform boundary differs.

## 2. Architecture targets

JetOS has three first-class CPU targets: `x86_64`, `armv7`, and `arm64`/AArch64. They are targets of one JetOS, not separate operating systems.

The ODROID-HC1 is the current physical reference target and is ARMv7. Board qualification includes the real boot path, device tree, target-native userspace, Ethernet, safe SATA discovery, and supported Python/JetLang standard-library behavior. The historical **Gen 2** label records the Gentoo-informed configuration context from which the current source estate emerged; it does not create an ongoing Gentoo dependency or update obligation.

A JetOS image must not knowingly mix kernel and userspace architectures. Architecture-specific behavior belongs only at genuine kernel, boot, firmware, device, QEMU, C, or assembly boundaries.

## 3. Canonical source layout and provenance

The repository uses `source/` as the canonical home for native source lineages and dependency source needed to build or qualify JetOS.

At minimum:

```text
source/
  linux/
  cpython/
  shared/
  ports/
```

Linux and CPython-derived JetLang source are controlled build inputs. Additional dependency source belongs under `source/` rather than in ad-hoc root-level source directories. Upstream URLs, versions, commits, licenses, and provenance must remain explicit and reproducible.

The source-control target is one outer JETOS Git repository with no nested Git metadata. Until currently pinned gitlinks are safely absorbed, transitional submodules may exist, but they must point into `source/` and must not be deleted before their source has been preserved.

Once absorbed, `source/linux` and `source/cpython` are JetOS-owned source trees. They are not rolling mirrors. The recorded upstream commits are provenance baselines, not instructions to pull or rebase merely because Linux, Gentoo, or CPython released something newer.

Linux/kernel changes are integrated deliberately for a defined JetOS reason such as a needed capability, security/correctness fix, supported hardware target, performance improvement, or explicit owner decision. Upstream Linux currency by itself is not an update requirement.

## 4. Bootstrap boundary

Source code requires an already-executable bootstrap toolchain for the first compile. That bootstrap compiler/interpreter environment is external build machinery, not a JetOS runtime dependency and not JetOS's distribution base.

A native Linux host may build JetOS directly when it provides the required compiler and tooling. Docker may be used as optional build/test isolation, but the JetOS repository must not name a default Debian, Gentoo, Ubuntu, Alpine, Python, or other distribution image. Any caller-supplied bootstrap image must already provide the required tooling and must never be copied into the guest as the JetOS runtime.

The kernel installed into JetOS must come from the JetOS-owned `source/linux` tree. The JetLang runtime and supported standard library installed into JetOS must come from the JetOS-owned `source/cpython` lineage after JetOS patching/build/qualification, never from a bootstrap interpreter or prebuilt Python container image.

## 5. Qualification rule

Runtime-affecting changes are not fully qualified by testing an old kernel, an old interpreter, or isolated source trees. Where the execution environment supports it, qualification must build the current JetOS kernel from the current Linux lineage and the current JetLang runtime from the current CPython-derived lineage, launch the newly built runtime with/on the newly built system, run relevant JetLang/CPython-derived regression tests through that runtime, run JetOS same-runtime integration tests, and exercise representative networking/runtime behavior. A small web-server/browser-or-client check should be included where practical.

Full global LOC/byte accounting must never block engineering work.

## 6. Fat and Skinny

Fat Mode owns source, build, diagnosis, qualification, and development bulk. Skinny Mode is a qualified projection containing the runtime and compact provenance needed by a target. Skinny must not silently carry full development source trees, test fixtures, temporary work material, or external bootstrap tooling.

## 7. Upstream currency and JetLang version integration

JetLang's current stabilization baseline is the Python 3.14 lineage. The immediate engineering goal is to make that JetLang baseline build, run, and pass integrated qualification reliably before promoting the next feature-series behavior.

After the initial CPython-derived source has been absorbed into the JetLang-owned tree, upstream CPython is not a replacement tree to pull, rebase, or overwrite onto JetLang. Later CPython releases are change/reference inputs. To advance from the 3.14 baseline to 3.15, JetOS must inspect the upstream 3.15 release notes, diffs, tests, standard-library changes, interpreter/compiler changes, C API/ABI changes, build changes, and relevant bug fixes; reconcile those changes into the existing JetLang code; preserve deliberate JetLang divergences; and record the exact upstream provenance used for that integration.

A JetLang version advance is complete only when the intended upstream change set has been incorporated into the JetLang-owned source and the resulting runtime passes the integrated qualification in section 5. Do not claim that JetLang is at a newer Python feature series merely because upstream source exists or metadata was updated.

The Python Behind-a-Log record is an integration-backlog ledger. It should show the current JetLang compatibility baseline, newer upstream release(s) available for review, changes still to reconcile, and qualification state. It is not an instruction to replace JetLang with a fresh CPython checkout.

The historical Gentoo/Linux Behind-a-Log record is provenance/history only. It is not a rolling update obligation and must not cause JetOS to change merely because Gentoo or upstream Linux advanced.

If a Python update exposes a missing Linux/kernel capability, improve the JetOS substrate rather than silently trimming protected Python behavior.

## 8. No GitHub Actions

Never use GitHub Actions. Do not add `.github/workflows/`, Actions runners, workflow dispatches, hosted CI gates, or Actions-based build/test/release machinery. Use native Git and repository-owned local Python tooling on explicitly controlled machines. GitHub may remain the Git remote and PR/issue/review surface.

## 9. Information lifecycle

Important information has a lifecycle. Track provenance, observation/verification time, dependencies, expected validity, invalidation events, refresh/replacement procedure, and uncertainty. Use explicit states such as CURRENT, AGING, DUE, STALE, EXPIRED, REVOKED, SUPERSEDED, and UNKNOWN. **DUE means judgment is required; it is not permission to delete, replace, or mutate.**

Credentials and other secret material must not be exposed or copied into lifecycle records. Track only non-secret lifecycle metadata and procedures. Unknown validity must remain visible as unknown rather than being assumed current.

## 10. Storage: cutting room, not archive

JetOS is the cutting room, not the archive. Keep the smallest practical working/staging/derived set needed for current responsibilities. Bulk historical data belongs in a designated archive, backup, or source of record after required handoff, integrity, recoverability, provenance, and authorization checks.

`KEEP_Safe` is a protected local-retention exception, not “keep forever.” Its retained bulk payload is compressed and encrypted at rest, key material stays separate, and plaintext working copies remain temporary.

## 11. Unused code retirement

Project-owned code without a current responsibility should eventually be removed after evidence-based checks of imports, references, registries, callbacks, configuration, tests, recovery paths, external consumers, and responsibility transfer. Do not create tracked graveyards of disabled or copied dead code; Git history is the recovery source.

The single `AGENTS.md` file contains the agent-facing deletion-ledger format and any entries. Before recreating retired behavior, inspect that section and native Git history first.

## 12. Work Server and automation

Repository-owned automation must remain bounded, test-backed, reviewable, local/native, and subordinate to these rules. Infrastructure failure is not permission to weaken JetOS or conceal missing prerequisites. Native source-lineage changes require the stronger integrated-runtime qualification described above.

## 13. AI/API integrations

Authorized provider integrations may include OpenAI, Anthropic, Google Gemini, Mistral, Cohere, Cerebras, DeepSeek, Groq, and other explicitly approved non-xAI providers. Prefer direct documented APIs and external credentials. xAI/Grok is explicitly blocked. Groq is distinct from Grok/xAI.

## 14. Safety and evidence

Do not describe planned behavior as implemented. Preserve privacy, containment, provenance, reproducibility, machine safety, backup/recovery, explicit capability boundaries, and owner authorization. When evidence is incomplete, make the uncertainty visible rather than inventing certainty.

## 15. Build acceleration and kernel reduction

Build acceleration must preserve correctness. A cached compiler result or reusable kernel artifact may be accepted only when its cache key covers every material input required to distinguish a valid result, including relevant source/provenance, target architecture, configuration, toolchain identity, and JetOS build-policy inputs. Unknown, incomplete, or changed inputs invalidate the cache; speed is never permission to reuse an unproven artifact.

Do not rebuild an unchanged kernel merely because unrelated JetOS or JetLang code changed when a correctness-preserving kernel cache can prove that all kernel-relevant inputs are identical.

Kernel reduction is conservative and incremental. Remove only capabilities for which there is evidence that JetOS does not require them. A reduced kernel configuration is not proven by compilation alone: before the reduction is treated as qualified, the newly built kernel must satisfy the integrated-runtime qualification in section 5, including the supported JetLang/standard-library surface.
