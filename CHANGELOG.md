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
