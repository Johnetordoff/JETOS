# Native Git authentication for the private JetOS repository

JetOS is private by design. Qualification workers that use native Git must therefore receive repository credentials through the worker's secret environment. Credentials must never be committed, pasted into repository files, embedded in clone URLs, printed in logs, or stored in Git configuration.

## Supported credential path

Use a repository-scoped token supplied through one of these environment variables, in priority order:

1. `JETOS_GIT_TOKEN`
2. `GH_TOKEN`
3. `GITHUB_TOKEN`

`JETOS_GIT_USERNAME` is optional and defaults to `x-access-token`.

For a worker that must both fetch and push branches, prefer a fine-grained GitHub personal access token restricted to `Johnetordoff/JETOS` with only the repository permissions required for native Git read/write. A read-only worker may use a token with read-only repository-content access.

Do not use an account password. Do not send account passwords or tokens through chat. Provision the token using the worker/runtime's secret-management mechanism so it is exposed only as an environment variable at execution time.

## Bootstrap clone

On a host that already has this repository tooling available:

```text
python3 tools/private_git_clone.py /path/to/JETOS
```

The helper invokes native `git clone`, supplies credentials through a temporary `GIT_ASKPASS` program, disables interactive credential prompting, and deletes the temporary askpass program when the clone attempt ends. The token is not placed in the command line, remote URL, repository config, or output.

For the very first bootstrap of a fresh worker, the worker runner itself must inject the token before native Git can access this private repository. Repository code cannot authenticate a host that has not yet been granted a credential.

## Failure interpretation

- `Could not resolve host: github.com` is DNS/network reachability, not an authentication failure.
- `Authentication failed`, `could not read Username`, HTTP 401, or HTTP 403 normally indicates missing/invalid credentials or insufficient repository permission.
- A private-repository `Repository not found` response can also indicate missing authorization.

Qualification reports must distinguish network reachability failures from credential failures instead of treating both as a generic clone failure.
