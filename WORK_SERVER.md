# JETOS Work Server

The JETOS Work Server is a **self-hosted build, qualification, and controlled-improvement service for JETOS itself**. It is not GitHub Actions and never falls back to GitHub Actions. Jenkins may schedule work from Git, but repository-owned Python code defines what gets built, tested, accepted, rejected, and retained.

The ordinary Work Server handles bounded repository improvements. It is not authorized to rewrite the protected native lineages under `source/linux` or `source/cpython`; those changes require the integrated-runtime qualification in `MANDATE.md` and `ARCHITECTURE.md`.

## Cycle model

A normal cycle:

```text
clean Git checkout
  -> disposable worktree + workbot/* branch
  -> populate source submodules
  -> Docker JETOS OS qualification
  -> Fat JETOS build
  -> optional bounded improvement proposal
  -> validate/apply only in the disposable worktree
  -> rerun Docker + Fat gates
  -> retain a branch only if every gate passes
```

Candidate code is never retained merely because an AI proposed it.

## Commands

Qualification/build only:

```text
python jetos.py work-cycle
```

Opt-in automatic improvement:

```text
export OPENAI_API_KEY='...'
export JETOS_WORKBOT_MODEL='your-authorized-model'
python jetos.py work-cycle --improve
```

The improver uses the OpenAI Responses API directly through Python's standard library. The model is configured by the worker administrator. Repository context sent externally is bounded; credentials remain process-environment configuration.

Worker-host failures such as missing Docker, unreachable Docker, DNS/network failure, or disk exhaustion block the cycle rather than prompting source changes that conceal infrastructure problems.

## Candidate restrictions

Automatic candidates are deliberately narrow:

- one unified Git diff;
- bounded patch size and file count;
- no automatic renames;
- no `.github/workflows/` changes;
- no changes to `source/linux` or `source/cpython` in the ordinary candidate path;
- executable changes require regression-test changes;
- no Node.js or JavaScript package/build stack;
- `MANDATE.md` remains binding;
- tests may not be skipped, deleted, or weakened merely to obtain a pass.

There is no endpoint for arbitrary shell commands or arbitrary argv execution.

## Native-source qualification boundary

Changes to the Linux and CPython-derived JetLang source lineages are a stronger class of work. They must preserve exact source/artifact provenance and satisfy the current/new kernel + current/new JetLang integrated-runtime qualification required by `MANDATE.md` and `ARCHITECTURE.md`, including relevant regression/integration tests and target-specific qualification where applicable. Removing the ordinary Work Server path block does not grant that authority.

## Retention and Git

Validated improvements are committed to local `workbot/*` branches. The disposable worktree is removed after the cycle. Pushing is separate and explicit:

```text
python jetos.py work-cycle --improve --push
```

Rejected candidates are not retained as branches. Bounded cycle/candidate diagnostics live temporarily under `.build/work-server/` and remain subject to the cutting-room storage policy.

## Persistent server

```text
python jetos.py work-server
```

Default bind is `127.0.0.1:8787`. The service exposes health/status/cycle endpoints and a cycle-creation endpoint. Binding beyond loopback requires `JETOS_WORKSERVER_TOKEN`; secrets remain environment configuration.

## Jenkins

`Jenkinsfile` runs:

```text
python3 tools/work_server.py run-cycle
```

Jenkins schedules; it does not duplicate JETOS test logic. A worker may opt into improvement with `JETOS_WORKSERVER_IMPROVE=1` and separately opt into validated-branch pushing with `JETOS_WORKSERVER_PUSH=1`.

## Worker requirements

A real worker needs Git/worktree/submodule support, Python 3, Docker CLI plus a reachable daemon, required source/container access, adequate disk, and only those credentials needed for explicitly enabled capabilities. The Docker/Fat environment carries build and emulation tooling.

## Status meanings

- `passed` — unchanged revision passed qualification/build gates.
- `failed` — repository/build gate failed for a non-infrastructure reason.
- `blocked` — worker infrastructure prevented meaningful qualification.
- `rejected` — candidate failed post-change gates.
- `accepted` — candidate passed and was committed to a `workbot/*` branch.
- `error` — orchestration/validation failed.

Keep the Work Server on a controlled build worker; its HTTP interface does not make it appropriate for broad exposure.
