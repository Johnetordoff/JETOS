# JetOS Mandate

Status: **active, permanent**
Authority: **Developer One / repository owner**

This is the single canonical JetOS mandate file. New mandate material is appended here; do not create additional mandate files.

## 1. JetOS identity and implementation

- JetOS is a source-oriented, Python/JetLang-first operating system project.
- JetLang is the JetOS language/runtime: an improved, deliberately diverging descendant of CPython. CPython remains its source lineage and compatibility foundation.
- Project-owned high-level executable logic defaults to Python/JetLang. C is reserved for unavoidable or measured native boundaries; assembly is reserved for architecture-required work.
- Node.js and the Node package ecosystem are forbidden. Browser JavaScript is allowed only where a genuine browser frontend requires small native JavaScript and must not introduce a Node-based toolchain.
- Third-party dependencies for project-owned Python logic are zero/minimal by default. Prefer the standard library and direct documented HTTP APIs over SDKs.
- Keep code small, clear, shared, and architecture-neutral wherever practical. Do not duplicate whole implementations when only a narrow platform boundary differs.

## 2. Architecture targets

JetOS has three first-class CPU targets: `x86_64`, `armv7`, and `arm64`/AArch64. They are targets of one JetOS, not separate operating systems.

The ODROID-HC1 is the current physical reference target and is ARMv7. Board qualification includes the real boot path, device tree, target-native userspace, Ethernet, safe SATA discovery, and supported Python/JetLang standard-library behavior. In JetOS terminology, **Gen 2 means the Gentoo/Linux-backed configuration context, never “second generation.”**

A JetOS image must not knowingly mix kernel and userspace architectures. Architecture-specific behavior belongs only at genuine kernel, boot, firmware, device, QEMU, C, or assembly boundaries.

## 3. Canonical source layout and provenance

The repository uses `source/` as the canonical home for external/native source lineages and dependency source needed to build or qualify JetOS.

At minimum:

```text
source/
  linux/
  cpython/
  shared/
  ports/
```

Linux and CPython-derived JetLang source are controlled build inputs. Additional dependency source belongs under `source/` rather than in ad-hoc root-level source directories. Upstream URLs, versions, commits, licenses, and provenance must remain explicit and reproducible.

The long-term source-control target is one outer JETOS Git repository with no nested Git metadata. Until currently pinned gitlinks are safely absorbed, transitional submodules may exist, but they must point into `source/` and must not be deleted before their source has been preserved.

## 4. Qualification rule

Runtime-affecting changes are not fully qualified by testing an old kernel, an old interpreter, or isolated source trees. Where the execution environment supports it, qualification must build the current JetOS kernel from the current Linux lineage and the current JetLang runtime from the current CPython-derived lineage, launch the newly built runtime with/on the newly built system, run relevant JetLang/CPython-derived regression tests through that runtime, run JetOS same-runtime integration tests, and exercise representative networking/runtime behavior. A small web-server/browser-or-client check should be included where practical.

Full global LOC/byte accounting must never block engineering work.

## 5. Fat and Skinny

Fat Mode owns source, build, diagnosis, qualification, and development bulk. Skinny Mode is a qualified projection containing the runtime and compact provenance needed by a target. Skinny must not silently carry full development source trees, test fixtures, or temporary work material.

## 6. Upstream currency

JetLang should track stable CPython maintenance releases promptly, with exact pins and full Fat qualification before a release becomes the Skinny basis. If a Python update exposes a missing Linux/kernel capability, improve the JetOS substrate rather than silently trimming protected Python behavior.

Gentoo is preferred source/build/package intelligence, not JetOS identity and not an unconditional rolling-runtime dependency. Upstream drift must remain visible in the existing Behind-a-Log records.

## 7. No GitHub Actions

Never use GitHub Actions. Do not add `.github/workflows/`, Actions runners, workflow dispatches, hosted CI gates, or Actions-based build/test/release machinery. Use native Git and repository-owned local Python tooling on explicitly controlled machines. GitHub may remain the Git remote and PR/issue/review surface.

## 8. Information lifecycle

Important information has a lifecycle. Track provenance, observation/verification time, dependencies, expected validity, invalidation events, refresh/replacement procedure, and uncertainty. Use explicit states such as CURRENT, AGING, DUE, STALE, EXPIRED, REVOKED, SUPERSEDED, and UNKNOWN. **DUE means judgment is required; it is not permission to delete, replace, or mutate.**

Credentials and other secret material must not be exposed or copied into lifecycle records. Track only non-secret lifecycle metadata and procedures. Unknown validity must remain visible as unknown rather than being assumed current.

## 9. Storage: cutting room, not archive

JetOS is the cutting room, not the archive. Keep the smallest practical working/staging/derived set needed for current responsibilities. Bulk historical data belongs in a designated archive, backup, or source of record after required handoff, integrity, recoverability, provenance, and authorization checks.

`KEEP_Safe` is a protected local-retention exception, not “keep forever.” Its retained bulk payload is compressed and encrypted at rest, key material stays separate, and plaintext working copies remain temporary.

## 10. Unused code retirement

Project-owned code without a current responsibility should eventually be removed after evidence-based checks of imports, references, registries, callbacks, configuration, tests, recovery paths, external consumers, and responsibility transfer. Do not create tracked graveyards of disabled or copied dead code; Git history is the recovery source.

The single `AGENTS.md` file contains the agent-facing deletion-ledger format and any entries. Before recreating retired behavior, inspect that section and native Git history first.

## 11. Work Server and automation

Repository-owned automation must remain bounded, test-backed, reviewable, local/native, and subordinate to these rules. Infrastructure failure is not permission to weaken JetOS or conceal missing prerequisites. Native source-lineage changes require the stronger integrated-runtime qualification described above.

## 12. AI/API integrations

Authorized provider integrations may include OpenAI, Anthropic, Google Gemini, Mistral, Cohere, Cerebras, DeepSeek, Groq, and other explicitly approved non-xAI providers. Prefer direct documented APIs and external credentials. xAI/Grok is explicitly blocked. Groq is distinct from Grok/xAI.

## 13. Safety and evidence

Do not describe planned behavior as implemented. Preserve privacy, containment, provenance, reproducibility, machine safety, backup/recovery, explicit capability boundaries, and owner authorization. When evidence is incomplete, make the uncertainty visible rather than inventing certainty.

## 14. Build acceleration and kernel reduction

Build acceleration must preserve correctness. A cached compiler result or reusable kernel artifact may be accepted only when its cache key covers every material input required to distinguish a valid result, including relevant source/provenance, target architecture, configuration, toolchain identity, and JetOS build-policy inputs. Unknown, incomplete, or changed inputs invalidate the cache; speed is never permission to reuse an unproven artifact.

Do not rebuild an unchanged kernel merely because unrelated JetOS or JetLang code changed when a correctness-preserving kernel cache can prove that all kernel-relevant inputs are identical.

Kernel reduction is conservative and incremental. Remove only capabilities for which there is evidence that JetOS does not require them. A reduced kernel configuration is not proven by compilation alone: before the reduction is treated as qualified, the newly built kernel must satisfy the integrated-runtime qualification in section 4, including the supported JetLang/standard-library surface.
