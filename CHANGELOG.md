# Changelog

All notable changes to this repository should be documented in this file.

The format is based on Keep a Changelog and follows semantic-versioning release intent.

## [Unreleased]
### Added
- Enterprise governance baseline files (`CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`, `CODE_OF_CONDUCT.md`, `CODEOWNERS`, issue templates, PR template).
- Operational documentation set in `docs/` for architecture, CI/CD, deployment, and upgrade/rollback.
- ADR and product-spec registry reads: the reusable workflow mints short-lived, least-privilege read tokens (one per registry) from the composer-resolver GitHub App and checks out `sparxstar-architecture-governance-registry` and `sparxstar-product-specification-registry` at the requested `contract_ref`, injecting the authoritative ADRs and specs into the review context. Read-only — no contract-sync.
- `contract_ref` workflow input (default `v1.0.0`) selecting the registry tag to review against. The gate validates ref shape only; the registry checkout fails if the tag doesn't exist. This gate does not enforce a version floor.
- Required secret `COMPOSER_RESOLVER_PRIVATE_KEY` and required org variable `COMPOSER_RESOLVER_CLIENT_ID` for the composer-resolver GitHub App.

### Changed
- Reusable workflow hardened for deterministic PR usage (`workflow_call` only, concurrency control, timeout, restricted checkout credentials, fail-fast shell mode).
- README updated with governance and operations references.
- Consumer example, README, and `docs/consumer-setup.md` now pin the reusable workflow at the immutable release tag `@v1.0.0` (the only published tag — there is no `@v1` moving alias) and pass `COMPOSER_RESOLVER_PRIVATE_KEY` by name. `contract_ref` defaults to `v1.0.0` to match the registry version-policy convention.
- Restructured the README consumer section into a grounded "Setup & Install" walkthrough (prerequisites, `uses:` pin, inputs, secrets, caller setup, copy-paste block, sequencing rule) with every value read from the live workflow; removed the version-floor overclaim and the inaccurate `@v1` moving-alias language across README, the example caller, and `docs/consumer-setup.md`.
- Bumped the review model from the deprecated `claude-sonnet-4-20250514` snapshot to the current `claude-sonnet-4-6`.

### Security
- Split the workflow into two jobs so the composer-resolver GitHub App key never shares a job with untrusted PR-head code (resolves CodeQL "checkout of untrusted code in a trusted context"). `build-context` (privileged) mints tokens and fetches the registries but never checks out PR-head code; `review` (unprivileged) checks out PR-head code — read-only, never executed — holds only `ANTHROPIC_API_KEY`, and consumes the trusted context via artifact. Consumers must invoke from `pull_request`, never `pull_request_target`.
- Added a fail-fast preflight guard for missing `COMPOSER_RESOLVER_CLIENT_ID` / `COMPOSER_RESOLVER_PRIVATE_KEY` configuration.
- `build-context` refuses to run on non-private caller repositories (before minting any token), since the trusted-context artifact would otherwise leak private registry content on a public repo.
- Validated `contract_ref` against a safe git-ref pattern before any checkout, and routed registry checkouts through the validated value.
- Set `persist-credentials: false` on the platform-reference-docs checkout for consistency with the other checkouts.
- Ordered the trusted ADR/spec/reference context ahead of repo-local context so the canonical contracts survive the 50KB context cap.
- Documented the threat model, controls, and the accepted CodeQL "checkout of untrusted code in a trusted context" dismissal in `docs/security-notes.md`.
