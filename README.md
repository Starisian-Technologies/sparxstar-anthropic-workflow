# SPARXSTAR Claude PR Review

Centralized reusable GitHub Actions workflow for Claude-powered pull request review to repository specs across Starisian Technologies repositories.

## What this repository provides
- Reusable PR review workflow: `.github/workflows/claude-pr-review.yml`
- Consumer integration example: `examples/consumer-workflow.yml`
- Governance baseline: contributing, security, support, code ownership, issue/PR templates
- Operational docs for architecture, CI/CD, deployment, and upgrade/rollback
- Platform reference docs injected into review context: `reference/*.md`

## Quick start for consumer repositories
Create `.github/workflows/claude-pr-review.yml`:

```yaml
name: Claude PR Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  review:
    permissions:
      contents: read
      pull-requests: write
    uses: Starisian-Technologies/sparxstar-claude-pr-review/.github/workflows/claude-pr-review.yml@main
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

Required:
- Secret: `ANTHROPIC_API_KEY`
- Permissions: `contents: read` and `pull-requests: write`

## Workflow behavior
1. Loads PR diff from the caller repository.
2. Loads repo-local context (`AGENTS.md`, `.github/copilot-instructions.md`, selected markdown docs) and platform reference docs from `reference/*.md` in this workflow repository.
3. Builds deterministic prompt from diff + context.
4. Calls Anthropic Messages API.
5. Upserts a single review comment on the PR.

## Determinism and safeguards
- Callers must use a `pull_request` trigger; `workflow_call` alone does not restrict invocation to PR events, and the workflow will fail if PR context is missing
- Diff truncation at 80KB and context truncation at 50KB with explicit notices
- Fail-fast handling for missing PR data, empty diff, and missing API key
- Scoped GitHub token permissions and no credential persistence on checkout

## Governance and standards files
- `CONTRIBUTING.md`
- `SECURITY.md`
- `SUPPORT.md`
- `CHANGELOG.md`
- `CODE_OF_CONDUCT.md`
- `CODEOWNERS`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/ISSUE_TEMPLATE/*.yml`

## Operations documentation
- `docs/architecture.md`
- `docs/ci-cd.md`
- `docs/deployment.md`
- `docs/upgrade-rollback.md`

## Troubleshooting
### `not our ref` during platform docs checkout
If a remote workflow run (in a caller repo) fails while checking out `.spx-workflow-repo` with `upload-pack: not our ref`, ensure the reusable workflow is up to date. Current versions resolve the checkout ref from `github.workflow_ref` (instead of using `github.workflow_sha`) so cross-repository calls use a valid ref in this repository.

### PR diff is empty
Confirm the caller uses a `pull_request` event and grants required token permissions.

### Claude API request failed
Verify `ANTHROPIC_API_KEY` exists and is valid in repo/org secrets.

### Unexpected review results
Check that caller repository context files are current and relevant.

## Maintenance
Update `.github/workflows/claude-pr-review.yml` and corresponding docs in the same pull request.

Maintained by [Starisian Technologies](https://github.com/Starisian-Technologies).
