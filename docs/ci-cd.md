# CI/CD and Workflow Operations

## Primary workflow
- `.github/workflows/claude-pr-review.yml` (reusable workflow)

## Required caller permissions
Consumer repositories must grant:
- `contents: read`
- `pull-requests: write`

## Required secrets
- `ANTHROPIC_API_KEY`
- `COMPOSER_RESOLVER_PRIVATE_KEY` — composer-resolver GitHub App private key; passed by name (not `secrets: inherit`). Used to mint short-lived, least-privilege read tokens for the private ADR and product-spec registries.

## Required variable
- `COMPOSER_RESOLVER_CLIENT_ID` — composer-resolver GitHub App client id; org-level variable read by the reusable workflow via the `vars` context.

## Inputs
- `contract_ref` (optional, default `v1`) — tag of the ADR (`sparxstar-architecture-governance-registry`) and product-spec (`sparxstar-product-specification-registry`) registries to review against. Pass a real tag (`v1` follows the major; `v1.0.0` locks). The registries enforce existence and floor; the reviewer never hardcodes or computes a version. The reviewer only reads — no contract-sync.

## Job structure (privilege split)
The reusable workflow runs as two jobs so the composer-resolver App key never shares a job with untrusted PR-head code (CodeQL "checkout of untrusted code in a trusted context"):
- `build-context` — privileged; holds `COMPOSER_RESOLVER_PRIVATE_KEY`, mints per-registry tokens, checks out the ADR/product-spec registries at `contract_ref` and the platform reference docs, and uploads the assembled trusted context as an artifact. Never checks out PR-head code.
- `review` (`needs: build-context`) — unprivileged; checks out PR-head code but only reads it as data (no build/install/script execution), downloads the trusted-context artifact, holds only `ANTHROPIC_API_KEY`, and posts the review comment.

## Determinism controls
- Consumer workflows must use a `pull_request` trigger — **never `pull_request_target`** (the `review` job checks out PR-head code). `workflow_call` alone does not restrict invocation to PR events, and the workflow will fail if PR context is missing
- Diff and spec byte limits with explicit truncation notes
- Single-comment update marker to avoid noisy comment sprawl

## Operational checks for maintainers
- Validate workflow syntax before merge
- Ensure README examples match workflow interface
- Confirm required secret handling and permission guidance are up to date
