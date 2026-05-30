# SPARXSTAR Anthropic Workflow

Centralized reusable GitHub Actions workflow for Claude-powered pull request and commit review across Starisian Technologies repositories.

## What this repository provides
- Reusable review workflow: `.github/workflows/claude-pr-review.yml`
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
  push:

jobs:
  review:
    permissions:
      contents: read
      pull-requests: write
    uses: Starisian-Technologies/sparxstar-anthropic-workflow/.github/workflows/claude-pr-review.yml@main
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

Required:
- Secret: `ANTHROPIC_API_KEY`
- Permissions: `contents: read` and `pull-requests: write`

## Workflow behavior
1. Loads a diff from the caller repository (PR diff for `pull_request`, git diff for `push`).
2. Loads repo-local context (`AGENTS.md`, `.github/copilot-instructions.md`, root markdown files, `.github/instructions/**/*.md`, `docs/specs/**/*.md`, and additional docs/spec markdown files) plus platform reference docs from `reference/*.md` in this workflow repository.
3. Builds deterministic prompt from diff + context.
4. Calls Anthropic Messages API.
5. Publishes the review (upserts one PR comment for pull requests; writes workflow summary for push events).

## Determinism and safeguards
- Callers should use `pull_request` and `push` triggers so every PR update and commit gets reviewed
- Diff truncation at 80KB and context truncation at 50KB with explicit notices
- Fail-fast handling for unsupported events, empty diffs, and missing API key
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

### Change diff is empty
Confirm the caller uses `pull_request` or `push`, and that the event includes code changes.

### Claude API request failed
Verify `ANTHROPIC_API_KEY` exists and is valid in repo/org secrets.

### Unexpected review results
Check that caller repository context files are current and relevant.

## Maintenance
Update `.github/workflows/claude-pr-review.yml` and corresponding docs in the same pull request.

Maintained by [Starisian Technologies](https://github.com/Starisian-Technologies).
