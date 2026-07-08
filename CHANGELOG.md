# Changelog

All notable changes to this repository should be documented in this file.

The format is based on Keep a Changelog and follows semantic-versioning release intent.

## [Unreleased]
### Fixed
- Replaced the `github.job_workflow_ref` string-parsing used to resolve the platform-reference-docs checkout ref with `github.job_workflow_sha`, a GitHub-resolved commit SHA. This removes the last edge case where a caller-repo run could hand `actions/checkout` a ref that only exists in the caller (the `refs/pull/<n>/merge` / `couldn't find remote ref` failure mode) instead of a ref of this repository.

### Security
- ADR and product-spec registry checkouts now pin to a commit SHA resolved from `contract_ref` via the GitHub API (`Resolve contract ref SHAs`), rather than checking out the mutable tag/branch name directly — the ref cannot move under the job between resolution and checkout.
- The unprivileged `review` job's PR-code checkout no longer falls back to the untrusted PR-head SHA when the PR's merge commit is unavailable; it now fails the job (resolves CodeQL "checkout of untrusted code in a trusted context" for the `pull-requests: write` job).

## [1.1.0] - 2026-07-04
### Added
- Enterprise governance baseline files (`CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`, `CODE_OF_CONDUCT.md`, `CODEOWNERS`, issue templates, PR template).
- Operational documentation set in `docs/` for architecture, CI/CD, deployment, and upgrade/rollback.
- ADR and product-spec registry reads: the reusable workflow mints short-lived, least-privilege read tokens (one per registry) from the composer-resolver GitHub App and checks out `sparxstar-architecture-governance-registry` and `sparxstar-product-specification-registry` at the requested `contract_ref`, injecting the authoritative ADRs and specs into the review context. Read-only — no contract-sync.
- Platform-contracts registry read: the `build-context` job mints a third composer-resolver token scoped to `sparxstar-platform-contracts`, checks it out at `contract_ref`, and folds its canonical interface contracts (the `MANIFEST.json` index plus the PHP interface declarations under `src/`, and any markdown) into the trusted-context artifact as `PLATFORM CONTRACT FILE` sections. The review prompt treats these as canonical interface boundaries the diff must honour. Same security model as the other two registries — App-token mint in the privileged job, read-only, consumed by the unprivileged review job via artifact only. Requires the composer-resolver App to also be scoped to `sparxstar-platform-contracts` with Contents: Read.
- `contract_ref` workflow input (default `v1.0.0`) selecting the registry tag to review against. The gate validates ref shape only; the registry checkout fails if the tag doesn't exist. This gate does not enforce a version floor.
- Required secret `COMPOSER_RESOLVER_PRIVATE_KEY` and required org variable `COMPOSER_RESOLVER_CLIENT_ID` for the composer-resolver GitHub App.
- Three-tier PR review model grafted onto `build-context`/`review`: three independently-attributed passes — Spec Conformance, Contract Seam, and ADR Drift — each citing the specific governing document ID. Consumers declare scope via a `sparxstar-specs.yml` file at their repo root (`specs[]` / `contracts[]` / `adrs[]` ID arrays); the workflow parses it from the PR base commit and surfaces the declared IDs in the prompt so findings name the governing document.
- `specs-artifact` workflow input (default `sparxstar-specs`) — consumes the per-tier `.sparxstar/{specs,contracts,adrs}/` artifact produced by the product-spec registry's `fetch-specs.yml`, falling back to registry-assembled tier content when the artifact is absent or its download fails (contracts tier has no fallback and requires the fetch-specs producer).
- Per-tier context byte caps (specs 25KB, contracts 20KB, ADRs 20KB, platform-ref 15KB, repo-context 10KB), replacing the single flat 50KB cap.

### Changed
- Reusable workflow hardened for deterministic PR usage (`workflow_call` only, concurrency control, timeout, restricted checkout credentials, fail-fast shell mode).
- README updated with governance and operations references.
- Consumer example, README, and `docs/consumer-setup.md` initially pinned the reusable workflow at the immutable release tag `@v1.0.0` (the only published tag at the time — there is no `@v1` moving alias) and passed `COMPOSER_RESOLVER_PRIVATE_KEY` by name; that pin is bumped to `@v1.1.0` later in this same release (see below). `contract_ref` defaults to `v1.0.0` to match the registry version-policy convention — a separate tag on the ADR/product-spec registries, not this repo's own release tag.
- Restructured the README consumer section into a grounded "Setup & Install" walkthrough (prerequisites, `uses:` pin, inputs, secrets, caller setup, copy-paste block, sequencing rule) with every value read from the live workflow; removed the version-floor overclaim and the inaccurate `@v1` moving-alias language across README, the example caller, and `docs/consumer-setup.md`.
- Bumped the review model from the deprecated `claude-sonnet-4-20250514` snapshot to the current `claude-sonnet-4-6`.
- Generalized review execution to both `pull_request` and `push` events: dual-path diff acquisition (`gh pr diff` for PR events, `git diff` with first-commit fallback for pushes) and event-routed output (upsert a single bot PR comment vs. publish to the workflow run summary).
- Expanded context-source coverage to include `AGENTS.md`, `.github/copilot-instructions.md`, root markdown docs, `.github/instructions/**/*.md`, and `docs/specs/**/*.md` alongside existing `specs/**/*.md` and `docs/**/*.md` locations.
- `sparxstar-specs.yml` declaration parsing reimplemented stdlib-only (`re`-based, no `pip install pyyaml`), keeping the reviewer's Python steps dependency-free.

### Fixed
- Cross-repository callers failed in `build-context` with `not our ref` while checking out the platform reference docs: the step resolved its checkout ref from `github.workflow_ref`, which in a reusable-workflow call is the *caller's* top-level ref — on a `pull_request` run that is `refs/pull/<n>/merge`, a ref that exists only in the caller. The privileged job now resolves from `github.job_workflow_ref` (the ref of this reusable workflow for the job), pinning the reference-docs checkout to a valid ref of this repository. The fix preserves the privilege split — `build-context` still checks out only its own repo and the registries, never caller PR-head code. (Surfaced only cross-repo; same-repo self-tests passed because `refs/pull/<n>/merge` resolves locally.)
- Prompt builder now fails fast with a `::error::` annotation if any `${VAR}` template token survives substitution, instead of silently sending a malformed prompt to Claude; added the missing `import sys` needed for that error path to fire.
- Fixed a `printf` banner call in the tier context loader that could be misinterpreted as an option flag (`--- %s ---` starting with `-`), which broke tier markdown aggregation; terminated option parsing explicitly with `--`.
- Hardened PR checkout target resolution: probes for a merge commit via `gh pr view --json mergeCommit` and falls back to the PR head SHA when the merge ref is unavailable (common on forks/restricted contexts), instead of assuming `refs/pull/<n>/merge` always exists.
- Fixed a YAML syntax error in the "Read repo declaration" step: the Python heredoc body was unindented while the surrounding `run: |` block scalar required 10-space indentation, which broke YAML block-scalar parsing (`could not find expected ':'`) and invalidated the entire workflow file for every consumer.

### Security
- Split the workflow into two jobs so the composer-resolver GitHub App key never shares a job with untrusted PR-head code (resolves CodeQL "checkout of untrusted code in a trusted context"). `build-context` (privileged) mints tokens and fetches the registries but never checks out PR-head code; `review` (unprivileged) checks out PR-head code — read-only, never executed — holds only `ANTHROPIC_API_KEY`, and consumes the trusted context via artifact. Consumers must invoke from `pull_request`, never `pull_request_target`.
- Added a fail-fast preflight guard for missing `COMPOSER_RESOLVER_CLIENT_ID` / `COMPOSER_RESOLVER_PRIVATE_KEY` configuration.
- `build-context` refuses to run on non-private caller repositories (before minting any token), since the trusted-context artifact would otherwise leak private registry content on a public repo.
- Validated `contract_ref` against a safe git-ref pattern before any checkout, and routed registry checkouts through the validated value.
- Set `persist-credentials: false` on the platform-reference-docs checkout for consistency with the other checkouts.
- Ordered the trusted ADR/spec/reference context ahead of repo-local context so the canonical contracts survive the 50KB context cap.
- Documented the threat model, controls, and the accepted CodeQL "checkout of untrusted code in a trusted context" dismissal in `docs/security-notes.md`.
- `sparxstar-specs.yml` is read from the PR base commit only, never the PR-head working tree — a fork PR cannot expand its own review scope by editing its own declaration, and a missing/unreadable file is treated as "no declaration" rather than falling back to untrusted content.
- Artifact directories (`.spx-trusted-context`, `.spx-specs-artifact`) are wiped and checked for symlinks before every download, so a PR-head pre-planted symlink or directory cannot inject content into the trusted context even when a download fails.
- The leftover-token guard now scans the prompt *template* before substitution rather than the rendered prompt, avoiding false positives from `${PATH}`-like patterns appearing in diff or spec content.
