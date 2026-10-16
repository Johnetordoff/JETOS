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

## Qualification priority — Linux x86_64 first

This ordering is mandatory for JetOS engineering and qualification work until explicitly superseded by the owner.

1. **Linux x86_64 is the first and gating environment.** Do not spend qualification runs on other host environments or architectures while Linux x86_64 still has an unbuilt stage, an unbooted stage, an unrun required test, or an actual failing required test.
2. On one exact revision, Linux x86_64 must build a **NEW x86_64 JetLang**, a **NEW x86_64 JetOS kernel**, and the required **NEW Fat image/initramfs**; boot the new kernel under the repository-supported x86_64 QEMU path; start the new JetLang inside that new JetOS runtime; and reach the interactive interpreter prompt.
3. The Linux x86_64 gate is not green until basic interpreter/runtime behavior passes and the full available Python/JetLang test surface is accounted for. Run all repository-native Python/JetLang tests and the broadest practical CPython-derived standard-library regression suite using canonical machinery such as `python -m test` or the repository equivalent. The intent is **every available relevant standard-library test module/library**, not a hand-picked subset.
4. Record passed, failed, skipped, unavailable, interrupted, and remaining tests separately. Skipped, unavailable, or interrupted tests are not passes. Do not call Linux x86_64 green while any actual failure remains or any required test remains unrun.
5. Use the shortest failure loop: execute the canonical Linux x86_64 path, capture the first concrete failure, make the smallest evidence-supported repair, rerun that failure first, then immediately resume the remaining deterministic suite.
6. Only after Linux x86_64 is genuinely green may qualification move to the next environments. The current order after Linux x86_64 is:
   1. Intel macOS x86_64;
   2. Apple Silicon M1/macOS arm64;
   3. remaining ARM environments and targets, including ODROID/Linux arm variants;
   4. Windows and other declared environments, unless the owner explicitly changes the order.
7. Success on one environment or architecture must never be inferred as success on another. Each later environment needs its own build/boot/runtime/test evidence.
8. No source-reduction or unrelated portability detours should displace an unfinished Linux x86_64 full-qualification run.

## Private native Git authentication

JetOS is private by design. Native/local workers must authenticate with native Git using credentials injected through the worker's secret environment. Never put a password, personal access token, installation token, or other secret in a Git remote URL, repository file, commit, PR, task prompt, command transcript, or chat message.

- Preferred environment variables are `JETOS_GIT_TOKEN`, then `GH_TOKEN`, then `GITHUB_TOKEN`.
- `JETOS_GIT_USERNAME` is optional and defaults to `x-access-token`.
- Use a repository-scoped token with the minimum permissions required by the worker. Read-only clone/fetch workers need only repository read access; workers that must push repair branches need repository-content write access.
- Account passwords are not the authentication mechanism for native HTTPS Git. Do not ask the owner to paste a GitHub password or token into chat.
- `tools/private_git_clone.py` performs an authenticated native `git clone` using a temporary `GIT_ASKPASS` helper. It does not place the token in the command line, remote URL, or Git configuration.
- A fresh worker still needs the credential provisioned by its runtime/secret manager before the first private clone. Repository code cannot bootstrap authorization for a host that has no credential yet.
- Treat DNS/network failures separately from authentication failures. `Could not resolve host` is connectivity; 401/403, credential prompts, or a private-repository not-found response can indicate missing/insufficient authorization.
- See `Documentation/NATIVE_GIT_AUTH.md` for the canonical procedure.

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
