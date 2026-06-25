# Consumer Setup

How a repository wires up the Claude PR review gate (the code-conformance
gate). This documents **this** gate only; it is grounded in
`.github/workflows/claude-pr-review.yml` in this repository.

## Prerequisites

- **Private repository.** This gate reads private ADR and product-spec
  registries and stages their contents as a workflow artifact between jobs. On
  a public repository that artifact would be downloadable by anyone, so the
  workflow fails fast unless the caller repository is private.
- **Secrets** (set in the consuming repo or its organization):
  - `ANTHROPIC_API_KEY` — Anthropic Messages API key.
  - `COMPOSER_RESOLVER_PRIVATE_KEY` — composer-resolver GitHub App private key
    (used to mint short-lived, read-only tokens for the private registries).
- **Variable** (organization-level): `COMPOSER_RESOLVER_CLIENT_ID` — the
  composer-resolver GitHub App client id. This is read automatically through the
  `vars` context and **is not passed** by the caller (unlike secrets).

## Add the workflow

Create `.github/workflows/claude-pr-review.yml` in the consuming repository:

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
    # Pin @v1 (moving major) or @v1.0.0 (locked). Both resolve. Never @main.
    uses: Starisian-Technologies/sparxstar-claude-pr-review/.github/workflows/claude-pr-review.yml@v1
    with:
      contract_ref: v1
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      COMPOSER_RESOLVER_PRIVATE_KEY: ${{ secrets.COMPOSER_RESOLVER_PRIVATE_KEY }}
```

That block is the complete wiring. The sections below explain each part.

## What the caller passes

### Inputs (`with:`)
- `contract_ref` — *optional*, default `v1`. The tag of the ADR and product-spec
  registries to review against. Pin to a real tag: `v1` follows the major,
  `v1.0.0` locks. The registries validate that the ref exists and meets the
  version floor; the caller never hardcodes or computes a version, it only
  requests one. Omit `with:` entirely to accept the `v1` default.

### Secrets (`secrets:`) — passed by name
- `ANTHROPIC_API_KEY`
- `COMPOSER_RESOLVER_PRIVATE_KEY`

Pass each secret explicitly by name as shown. Do **not** use `secrets: inherit`.

### Do not pass
- `COMPOSER_RESOLVER_CLIENT_ID` — this is an organization **variable**, not a
  secret. It propagates to the reusable workflow on its own through the `vars`
  context. Passing it is unnecessary (and `secrets:`/`with:` are the wrong
  channels for it).

## Caller permissions

The calling job needs exactly:

```yaml
permissions:
  contents: read
  pull-requests: write
```

- `contents: read` — read the code under review.
- `pull-requests: write` — post/update the single review comment.

No `actions:` scope is required. The gate passes its trusted context between
jobs as a **same-run** artifact, which authenticates with the runner's
ephemeral `ACTIONS_RUNTIME_TOKEN` (independent of `GITHUB_TOKEN`). `actions: read`
would only be needed to download an artifact from a *different* run or
repository, which this gate never does.

## Trigger requirement

Use a `pull_request` trigger, **never `pull_request_target`**. The gate's review
job checks out PR-head code; under `pull_request_target` that untrusted code
would run in the base-repo context with a read-write token. Under
`pull_request`, fork PRs run with a read-only token and no secrets, and the
review job only ever *reads* PR-head files as data (it never builds, installs,
or executes them).

## How to verify it is working

After adding the workflow, open a pull request in the consuming repository. The
gate will post a single "Claude PR Review" comment (and update that same comment
on subsequent pushes) with a `PASS` / `FAIL` / `CONDITIONAL` verdict. If it
fails fast instead, the error message states the cause directly — a missing
secret/variable, a non-private repository, or missing PR context.

## Reference

- Reusable workflow: `.github/workflows/claude-pr-review.yml`
- Copy-paste example: `examples/consumer-workflow.yml`
- Security model and accepted scan findings: `docs/security-notes.md`
