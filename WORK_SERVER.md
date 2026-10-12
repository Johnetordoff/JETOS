# JETOS Work Server

The JETOS Work Server is a **self-hosted build, qualification, and controlled-improvement service for JETOS itself**.

It is not GitHub Actions and it never falls back to GitHub Actions. Jenkins may schedule work from Git, but Jenkins is only a scheduler: the repository-owned Python server defines what gets built, tested, accepted, rejected, and retained.

The ordinary Work Server is deliberately distinct from the **Source Brain Weaver** described in `source-brain/README.md`. The Work Server handles bounded JETOS repository improvements. It is not authorized to rewrite the Linux or CPython Source Brain trees.

## What the server actually does

A normal cycle is:

```text
clean JETOS Git checkout
        |
        v
create disposable linked worktree + workbot/* branch
        |
        v
populate Source Brain source submodules
        |
        v
Docker JETOS OS qualification
        |
        v
Fat JETOS build gate
        |
        +-------------------------------+
        |                               |
        | test-only cycle               | improvement cycle
        |                               v
        |                    bounded source/log context
        |                               |
        |                               v
        |                    authorized API improver
        |                               |
        |                               v
        |                       one unified diff
        |                               |
        |                               v
        |                  validate paths / size / tests
        |                               |
        |                               v
        |                    apply only in worktree
        |                               |
        |                               v
        |                  Docker qualification again
        |                               |
        |                               v
        |                       Fat build again
        |                               |
        +-------------------------------+
                                        |
                       pass ------------+------------ fail
                        |                               |
                        v                               v
              commit workbot/* branch          delete candidate branch
                        |
                 optional explicit push
```

The primary rule is **candidate code never becomes retained Git work merely because an AI proposed it**. The full JETOS gate has to pass after the patch.

## Run one server cycle

Qualification/build only:

```text
python jetos.py work-cycle
```

This creates an isolated worktree and runs:

1. `python jetos.py docker-test`
2. `python jetos.py dev --build-only`

The Docker gate treats JETOS as the userspace OS being qualified while accurately reporting that Docker shares the worker host's Linux kernel.

## Controlled automatic improvement

Automatic improvement is opt-in:

```text
export OPENAI_API_KEY='...'
export JETOS_WORKBOT_MODEL='your-authorized-model'
python jetos.py work-cycle --improve
```

The server uses the OpenAI Responses API directly through Python's standard library. No OpenAI Python SDK is required. The model is deliberately **not hard-coded**: the worker administrator chooses it through `JETOS_WORKBOT_MODEL`.

An improvement cycle sends a bounded packet containing qualification output and a small set of relevant JETOS source files to the configured API. The API key is read from the process environment and is never written into Work Server state.

Do not enable automatic improvement if the worker is not authorized to send that repository context to the configured service.

When the current gates already pass, the improver is asked for one small test-backed improvement that advances an existing JETOS objective. When a gate fails for a code reason, it is asked to repair the earliest causal failure without weakening the protected semantics or tests.

Worker-host failures such as missing Docker, an unreachable Docker daemon, DNS/network failure, or disk exhaustion are classified as **infrastructure failures**. They stop the cycle; the improver is not asked to rewrite JETOS to hide them.

## Candidate restrictions

Automatic candidates are deliberately narrow:

- one unified Git diff;
- bounded patch size;
- bounded number of files;
- no renames;
- no changes under `.github/workflows/`;
- no changes to `source-brain/linux` or `source-brain/cpython` in the ordinary automatic candidate path;
- executable code changes require a regression-test change;
- Node.js and JavaScript package/build stacks remain forbidden;
- every applicable JETOS mandate remains binding;
- tests cannot be skipped, deleted, or weakened merely to make a candidate pass.

There is no HTTP endpoint for arbitrary shell commands or arbitrary argv execution.

## Source Brain Weaver boundary

Linux↔CPython co-design is intentionally outside the ordinary bounded Work Bot authority. The dedicated Source Brain Weaver responsibility may examine and propose coordinated changes to those trees, but a Source Brain candidate has a much stronger acceptance burden.

At minimum it must retain exact source/artifact provenance and run the applicable combination of repository tests, CPython regression/stdlib qualification, Linux subsystem/self-tests, sanitizers/static analysis where useful, performance baselines, x86-64/ARMv7/ARM64 builds, QEMU/emulated boots, and physical target qualification for hardware-specific work. See `source-brain/README.md`.

A future automated Source Brain worker may reuse Work Server isolation primitives, but it must not gain Source Brain write authority merely by removing the path block from the ordinary Work Bot. The stronger worker needs explicit source-weaving policy and qualification gates.

## Retention and Git

If the candidate passes every gate, the server commits it to a local branch named like:

```text
workbot/20261012-123456-ab12cd34
```

The disposable worktree is removed after the cycle. The accepted branch remains in the main repository for review.

Pushing is a separate explicit capability. For a one-shot administrator-run cycle:

```text
python jetos.py work-cycle --improve --push
```

For an HTTP service, remote push should only be enabled on a worker whose environment explicitly authorizes it. The initial server does not automatically merge accepted branches and does not bypass normal review.

Rejected candidates are not retained as branches. Their bounded diagnostic/candidate record remains temporarily under `.build/work-server/` for review and is subject to the JETOS cutting-room retention model.

## Run the persistent server

```text
python jetos.py work-server
```

Default bind:

```text
127.0.0.1:8787
```

Endpoints:

```text
GET  /health
GET  /v1/status
GET  /v1/cycles/<id>
POST /v1/cycles
```

Example local request:

```text
POST /v1/cycles
{"improve": true, "push": false}
```

Binding beyond loopback requires `JETOS_WORKSERVER_TOKEN`. Authenticated requests use:

```text
Authorization: Bearer <token>
```

Secrets are environment configuration, not request payloads or committed files.

## Jenkins on Git

The repository `Jenkinsfile` runs one command:

```text
python3 tools/work_server.py run-cycle
```

That is intentional. Jenkins checks out Git and schedules the work. It does not duplicate JETOS test logic.

A Jenkins worker may opt into improvement through its environment:

```text
JETOS_WORKSERVER_IMPROVE=1
OPENAI_API_KEY=...
JETOS_WORKBOT_MODEL=...
```

It may separately opt into pushing validated branches with:

```text
JETOS_WORKSERVER_PUSH=1
```

No GitHub Actions runner, workflow, artifact, status requirement, dispatch, or fallback is part of this design.

## Worker-host requirements

A real Work Server host needs the capabilities required by the work it performs:

- Git, including worktree and submodule support;
- Python 3 to launch the repository-owned controller;
- Docker CLI plus a reachable Docker daemon;
- access to required container base images/package sources when they are not already cached;
- enough disk for Docker images, linked Git worktrees, Source Brain Linux/CPython source, and JETOS build products;
- credentials only for capabilities explicitly enabled, such as the improver API or optional Git push.

The Docker/Fat environment itself carries the C compiler, linker, Linux-kernel build tools, emulators, and related build capabilities. JETOS names those by capability rather than permanently defining a compiler vendor as part of the OS interface.

## State model

Transient state lives under:

```text
.build/work-server/
```

It contains bounded cycle JSON and candidate diffs. Build artifacts and logs remain cutting-room data, not a permanent archive.

The canonical durable record of an accepted improvement is Git: a reviewed commit/branch, and later a normal merge if approved.

## Status meanings

- `passed` — the unchanged revision passed Docker qualification and the Fat build.
- `failed` — a repository/build gate failed for a non-infrastructure reason during a test-only cycle.
- `blocked` — worker infrastructure prevented meaningful qualification; JETOS source is not modified to mask it.
- `rejected` — an improvement candidate was produced but failed the post-change gates.
- `accepted` — the candidate passed all gates and was committed to a `workbot/*` branch.
- `error` — the Work Server itself hit an orchestration/validation error.

## Trust boundary

The Work Server is intentionally more powerful than an ordinary test command because it can create Git branches and, when explicitly enabled, contact an external improver or push a validated branch. Keep it on a controlled build worker. Do not expose it broadly simply because it has an HTTP interface.
