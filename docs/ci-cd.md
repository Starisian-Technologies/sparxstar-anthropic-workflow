# CI/CD and Workflow Operations

## Primary workflow
- `.github/workflows/claude-pr-review.yml` (reusable workflow)

## Required caller permissions
Consumer repositories must grant:
- `contents: read`
- `pull-requests: write`

## Required secret
- `ANTHROPIC_API_KEY`

## Determinism controls
- PR-only invocation via `workflow_call`
- Diff and spec byte limits with explicit truncation notes
- Single-comment update marker to avoid noisy comment sprawl

## Operational checks for maintainers
- Validate workflow syntax before merge
- Ensure README examples match workflow interface
- Confirm required secret handling and permission guidance are up to date
