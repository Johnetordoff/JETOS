# MANDATE_004G — No GitHub Actions

Status: **PERMANENT DEVELOPER ONE HYPER DIRECTIVE**
Scope: **all repositories, present and future**
Authority: Developer One / repository owner

## Directive

**Never use GitHub Actions in any repository.**

This is a cross-repository architectural rule, not a project-local preference. It applies to JETOS and to every other repository governed by Developer One.

## Prohibited

- files under `.github/workflows/`;
- GitHub-hosted or self-hosted Actions runners;
- `workflow_dispatch`, push/PR Actions jobs, scheduled Actions, reusable Actions workflows, or Actions-based release/deployment machinery;
- Actions artifacts as the execution, test, build, qualification, deployment, or provenance system;
- GitHub hosted checks/statuses as a required CI or qualification gate;
- introducing Actions as a fallback when local/native execution is inconvenient.

## Required replacement model

Repository work must remain host-neutral and executable through native Git plus repository-owned local tooling, with Python as the default orchestration language under the existing Developer One architecture rules.

Tests, qualification, builds, benchmarks, packaging, release preparation, and other automation must run locally or on explicitly controlled machines through repository-owned commands rather than through GitHub Actions.

GitHub may still be used as a Git remote and as a pull-request/issue/review collaboration surface. Those collaboration features do not make GitHub part of the execution architecture.

## Remediation

If a GitHub Actions workflow is discovered:

1. stop relying on it immediately;
2. preserve any useful test/build intent in native repository tooling;
3. remove the workflow file;
4. add or retain a repository guard that rejects `.github/workflows/` where practical;
5. never treat historical Actions results as a current required qualification mechanism.

## Conflict rule

If another document, proposal, generated recommendation, tool, or agent suggests GitHub Actions, this Hyper Directive wins. The correct response is to redesign the workflow without GitHub Actions, not to create an exception.
