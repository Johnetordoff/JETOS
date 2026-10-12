# JETOS Work Bot

JETOS Work Bot is a small local HTTP server for repeatedly **building, testing, qualifying, and improving JETOS through evidence**.

It is intentionally repository-owned Python using only the standard library. It does not use GitHub Actions, does not depend on a hosted CI service, and does not expose an arbitrary shell endpoint.

## Start the server

```text
python jetos.py workbot
```

Default address:

```text
http://127.0.0.1:8787
```

The server binds only to loopback by default. To expose it on another interface, set a bearer token first:

```text
JETOS_WORKBOT_TOKEN='strong-random-token' python jetos.py workbot --host 0.0.0.0
```

Secrets are read from the environment rather than command-line arguments.

## API

### Health

```text
GET /health
```

This is intentionally unauthenticated so local supervisors can determine whether the server process is alive.

### Work Bot status

```text
GET /v1/status
```

Returns available JETOS jobs, current work, queued work, recent results, and the composition of a full work cycle.

### Queue known work

```text
POST /v1/jobs
Content-Type: application/json

{"kind":"test"}
```

Allowed jobs are fixed by JETOS code. The server does **not** accept a command string, argv supplied by the caller, shell snippets, or arbitrary executable paths.

Current jobs:

- `doctor` — inspect required development-host capabilities;
- `test` — run the repository-owned JETOS test suite;
- `build` — build the current JETOS development image without booting it;
- `docker-test` — automatically becomes available when the checkout provides the JETOS `docker-test` command;
- `cycle` — run doctor, tests, Docker qualification when available, and a build in order.

### Inspect results

```text
GET /v1/jobs
GET /v1/jobs/<job-id>
```

Job records contain status, return code, duration, bounded output, cycle-step results, and improvement proposals derived from failures.

## Improvement model

Work Bot does not silently modify source code. Instead it turns failing evidence into structured proposals under:

```text
.build/workbot/proposals/
```

Examples include:

- repair a protected Python qualification regression;
- restore a missing build/runtime artifact;
- restore a missing Python module surface;
- provide a missing Docker/container-engine host capability;
- reduce an otherwise unclassified failure and add a regression test.

That keeps the improvement loop auditable:

```text
run -> capture evidence -> propose change -> review/change in Git -> rerun
```

The server's working history is deliberately bounded and lives under `.build`, consistent with JETOS being a cutting room rather than a permanent archive.

## Continuous local work

A server may enqueue a full cycle periodically when it is idle:

```text
python jetos.py workbot --interval 3600
```

`--interval 0` (the default) disables automatic scheduling. The server never runs more frequently merely because HTTP clients poll it.

For a single non-server run:

```text
python tools/workbot.py run-once cycle
```

This is useful for Jenkins or another native Git worker if desired. CI scheduling remains external; JETOS owns the job definitions, execution, logs, and improvement analysis.

## Security boundary

- loopback-only by default;
- bearer token mandatory for non-loopback binds;
- constant-time bearer-token comparison;
- maximum request body size;
- fixed job allowlist;
- subprocesses run without `shell=True`;
- no endpoint for Git pushes, merges, destructive disk work, or arbitrary commands;
- no GitHub Actions integration or fallback.

A later controller may add explicitly authorized Git/PR operations as separate capabilities, but those are intentionally outside this first server.
