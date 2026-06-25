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
    # Pin to @v1 (moving major) or @v1.0.0 (locked). Do not reference @main.
    uses: Starisian-Technologies/sparxstar-claude-pr-review/.github/workflows/claude-pr-review.yml@v1
    with:
      contract_ref: v1
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      COMPOSER_RESOLVER_PRIVATE_KEY: ${{ secrets.COMPOSER_RESOLVER_PRIVATE_KEY }}
```

Required:
- Secret: `ANTHROPIC_API_KEY`
- Secret: `COMPOSER_RESOLVER_PRIVATE_KEY` (composer-resolver GitHub App private key; mints read tokens for the private ADR and product-spec registries)
- Variable: `COMPOSER_RESOLVER_CLIENT_ID` (composer-resolver GitHub App client id; org-level variable read via the `vars` context)
- Permissions: `contents: read` and `pull-requests: write`

Inputs:
- `contract_ref` (optional, default `v1`): tag of the ADR and product-spec registries to review against. Pin to a real tag — `v1` follows the major, `v1.0.0` locks. The registries validate that the ref exists and is at or above the supported floor; the reviewer only requests it and never hardcodes or computes a version.

## Workflow behavior
The workflow runs as two jobs to keep the privileged registry credential away from untrusted PR-head code (see [Determinism and safeguards](#determinism-and-safeguards)):

**Job `build-context` (privileged, never checks out PR-head code):**
1. Mints short-lived, least-privilege read tokens (one per registry) from the composer-resolver GitHub App.
2. Checks out the private ADR (`sparxstar-architecture-governance-registry`) and product-spec (`sparxstar-product-specification-registry`) registries at `contract_ref`, plus this repo's `reference/*.md`.
3. Assembles the authoritative ADRs, product specs, and platform reference docs into a trusted-context artifact.

**Job `review` (unprivileged, holds only `ANTHROPIC_API_KEY`):**
4. Loads the PR diff and repo-local context (`AGENTS.md`, `.github/copilot-instructions.md`, selected markdown docs) — reading PR-head files as data only, never executing them.
5. Downloads the trusted-context artifact and builds a deterministic prompt from diff + context.
6. Calls the Anthropic Messages API and upserts a single review comment on the PR.

The reviewer only reads the registries — there is no contract-sync or write-back.

## Determinism and safeguards
- Callers must use a `pull_request` trigger — **never `pull_request_target`**. The review job checks out PR-head code, and `pull_request_target` would run it with a read-write token in the base-repo context. `workflow_call` alone does not restrict invocation to PR events, and the workflow will fail if PR context is missing
- **Privilege split (CodeQL hardening):** the composer-resolver GitHub App key — the only credential that can reach private registries — lives solely in the `build-context` job, which never checks out PR-head code. The `review` job checks out PR-head code but holds no App key and only *reads* those files as data (no build/install/script execution); trusted context crosses between jobs via artifact only
- **Private callers only:** the trusted context (private ADR/spec content) is staged as a workflow artifact, which would be downloadable by anyone on a public repository. `build-context` fails fast (before minting any token) unless the caller repository is private
- Diff truncation at 80KB and context truncation at 50KB with explicit notices; authoritative ADR/spec/reference context is placed first so it survives the cap, and trailing repo-local context is truncated first
- Fail-fast handling for missing PR data, empty diff, missing API key, and unset composer-resolver configuration
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
- `docs/security-notes.md` — threat model, controls, and accepted scan findings

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
