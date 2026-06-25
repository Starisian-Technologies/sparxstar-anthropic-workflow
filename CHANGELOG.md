# Changelog

All notable changes to this repository should be documented in this file.

The format is based on Keep a Changelog and follows semantic-versioning release intent.

## [Unreleased]
### Added
- Enterprise governance baseline files (`CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`, `CODE_OF_CONDUCT.md`, `CODEOWNERS`, issue templates, PR template).
- Operational documentation set in `docs/` for architecture, CI/CD, deployment, and upgrade/rollback.
- ADR and product-spec registry reads: the reusable workflow mints short-lived, least-privilege read tokens (one per registry) from the composer-resolver GitHub App and checks out `sparxstar-architecture-governance-registry` and `sparxstar-product-specification-registry` at the requested `contract_ref`, injecting the authoritative ADRs and specs into the review context. Read-only — no contract-sync.
- `contract_ref` workflow input (default `v1`) selecting the registry tag to review against; the registries enforce existence and floor.
- Required secret `COMPOSER_RESOLVER_PRIVATE_KEY` and required org variable `COMPOSER_RESOLVER_CLIENT_ID` for the composer-resolver GitHub App.

### Changed
- Reusable workflow hardened for deterministic PR usage (`workflow_call` only, concurrency control, timeout, restricted checkout credentials, fail-fast shell mode).
- README updated with governance and operations references.
- Consumer example and README now pin the reusable workflow at `@v1` (was `@main`) and pass `COMPOSER_RESOLVER_PRIVATE_KEY` by name.

### Security
- Split the workflow into two jobs so the composer-resolver GitHub App key never shares a job with untrusted PR-head code (resolves CodeQL "checkout of untrusted code in a trusted context"). `build-context` (privileged) mints tokens and fetches the registries but never checks out PR-head code; `review` (unprivileged) checks out PR-head code — read-only, never executed — holds only `ANTHROPIC_API_KEY`, and consumes the trusted context via artifact. Consumers must invoke from `pull_request`, never `pull_request_target`.
- Added a fail-fast preflight guard for missing `COMPOSER_RESOLVER_CLIENT_ID` / `COMPOSER_RESOLVER_PRIVATE_KEY` configuration.
- `build-context` refuses to run on non-private caller repositories (before minting any token), since the trusted-context artifact would otherwise leak private registry content on a public repo.
- Validated `contract_ref` against a safe git-ref pattern before any checkout, and routed registry checkouts through the validated value.
- Set `persist-credentials: false` on the platform-reference-docs checkout for consistency with the other checkouts.
- Ordered the trusted ADR/spec/reference context ahead of repo-local context so the canonical contracts survive the 50KB context cap.
