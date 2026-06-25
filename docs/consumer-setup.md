# Consumer Setup — Claude PR Review (code-conformance gate)

How a consuming repository wires up the **code-conformance gate**: an AI review
of each pull request against the SPARXSTAR platform's ADRs and product specs.
This documents **this** gate only (`claude-pr-review.yml` in this repo); the
ADR and tech-spec gates publish their own setup docs.

This gate is a **reader, not an owner**. It pulls the canonical ADRs and specs
fresh on every run from the two registries and reviews your PR diff against
them — it never stores them in your repo and never writes back to the
registries (no contract-sync).

This gate is **advisory by design** (see Section 8). It posts a single review
comment with a `PASS` / `FAIL` / `CONDITIONAL` verdict; it does not block merge
on its own. Setup/runtime errors (missing secret, public caller, bad
`contract_ref`) fail the job hard; a `FAIL` *verdict* does not.

Three refs it touches: only **`contract_ref`** — the pinned registry version the
review is performed against. (There is no agent-ref/release-ref here; this gate
reviews, it doesn't fetch specs into your tree.)

---

## Setup & Install (consuming repos)

Every value below is read from this repo's live `.github/workflows/claude-pr-review.yml`
— match it exactly; a wrong secret name or tag startup-fails the gate.

### Section 0 — Prerequisites (do this first; the gate cannot run without it)

The gate mints GitHub App tokens to clone the private registries. The following
org-level infrastructure must exist before any consumer can call it. If you see
a *repository not found* or empty-credential error, the cause is almost always a
missing item here — not your caller YAML.

**GitHub App — composer-resolver (required).** The `Mint ADR read token` and
`Mint spec read token` steps mint installation tokens to read the registries.
The consuming org must have this App installed and scoped to **both** registry
repos with **Contents: Read**:

- `Starisian-Technologies/sparxstar-architecture-governance-registry` (ADRs)
- `Starisian-Technologies/sparxstar-product-specification-registry` (specs)

Verify in org Settings → GitHub Apps → composer-resolver → Repository access
that the installation includes both. An App existing org-wide is not the same
as it being scoped to the repos the gate reads — that mismatch is the most
common silent failure.

There is **no write App** for this gate. It only reads — no contract-sync.

**Caller repository must be private.** The gate stages the fetched (private)
ADR/spec content as a workflow artifact between its two jobs. On a public repo
that artifact is downloadable by anyone, so `build-context` refuses to run
unless `github.event.repository.private == true`. Run this gate only from
private repositories.

**Org Secrets** (Settings → Secrets and variables → Actions → Secrets) — exact
names from `on.workflow_call.secrets`:

| Secret | Required | Used for |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Yes | Anthropic Messages API key — the review call |
| `COMPOSER_RESOLVER_PRIVATE_KEY` | Yes | Private key for the composer-resolver App (mints the registry read tokens) |

**Org Variables** (same screen → Variables, **not** Secrets) — read by the mint
steps:

| Variable | Holds | Used for |
| --- | --- | --- |
| `COMPOSER_RESOLVER_CLIENT_ID` | the App client-id string (`create-github-app-token@v3` uses `client-id:`, not a numeric app-id) | read-token mint |

These are **Variables, not Secrets** — a client-id placed in a Secret slot (or a
private key placed in a Variable) fails the mint. Org Variables propagate into a
reusable workflow automatically; secrets do not (see Section 7).

**The `v1.0.0` tag of this repo must exist** so the `uses:` pin resolves. It
does (the platform release tag is cut).

**Who provisions these:** App installation and org Secret/Variable creation
require org-admin rights. A consuming-repo developer may not have them and may
need to request setup. Check these prerequisites first when an auth error
appears — the failure surfaces as *repository not found* or an empty-credential
error, never as a clear "you forgot to install the App."

### Section 1 — What this gate does

`claude-pr-review.yml` is a reusable workflow (`on: workflow_call`) that reviews
a consuming repo's PR against the canonical platform contracts. It runs as two
jobs so the registry credential never shares a job with untrusted PR-head code:

- **`build-context`** (privileged) — validates config, mints per-registry read
  tokens, checks out the ADR + product-spec registries at `contract_ref` and
  this repo's platform `reference/` docs, assembles the trusted context, and
  uploads it as the `spx-trusted-context` artifact. **Never checks out PR-head
  code.**
- **`review`** (unprivileged) — checks out the PR head (read-only — no build,
  install, or script execution), reads the diff and repo-local context, downloads
  the trusted-context artifact, sends it all to the Anthropic Messages API, and
  upserts a single review comment on the PR. Holds only `ANTHROPIC_API_KEY`.

It guarantees the PR was reviewed against the pinned ADR/spec versions. It does
**not** run your tests, and it does **not** block merge — see Section 8.

### Section 2 — The `uses:` line and which tag to pin

```yaml
uses: Starisian-Technologies/sparxstar-claude-pr-review/.github/workflows/claude-pr-review.yml@v1.0.0
```

Live tags:

| Tag | Kind | Use it when |
| --- | --- | --- |
| `v1.0.0` | Immutable release — never moves | **Platform default.** Frozen, reproducible workflow version. |
| `v1` | Moving major alias — advances to the latest `v1.x.y` | Available, but **not** the recommended pin. |

**Pin `@v1.0.0`.** The platform-wide pin is the immutable release tag. `@v1`
still resolves but is not the documented consumer default — bumping the pin is a
deliberate adoption act, not an automatic pick-up. **Never pin `@main` in
production.**

### Section 3 — Inputs (from `on.workflow_call.inputs`)

| Input | Required | Type | Default | Purpose / valid values |
| --- | --- | --- | --- | --- |
| `contract_ref` | No | string | `v1.0.0` | Registry tag (ADR + product-spec) the review is performed against. Pin the immutable release tag (`v1.0.0`); `v1` is the moving alias and is not recommended; never `main`. Validated by the gate (safe-character regex + `git check-ref-format`) and by the registry side (must exist and be at/above the floor) — a non-existent or below-floor ref hard-fails the build. |

Outputs: none. The gate's product is the PR review comment, not a workflow
output.

### Section 4 — Secrets the consumer must pass

Declared in `on.workflow_call.secrets`. Pass each **by name** — `secrets: inherit`
is prohibited (pass only the named secrets a workflow needs):

```yaml
    secrets:
      ANTHROPIC_API_KEY:             ${{ secrets.ANTHROPIC_API_KEY }}
      COMPOSER_RESOLVER_PRIVATE_KEY: ${{ secrets.COMPOSER_RESOLVER_PRIVATE_KEY }}
```

- `ANTHROPIC_API_KEY` — **required.** The Anthropic Messages API key used for the
  review call.
- `COMPOSER_RESOLVER_PRIVATE_KEY` — **required.** Private key for the
  composer-resolver App. The mint steps pair it with the `COMPOSER_RESOLVER_CLIENT_ID`
  org Variable, which propagates on its own — you pass only the private key
  across the `workflow_call` boundary.

### Section 5 — Required caller setup

**Trigger:** call from `pull_request` (and/or its types). Use `pull_request`,
**never `pull_request_target`**: the `review` job checks out PR-head code, and
`pull_request_target` would run that in the base-repo context with a read-write
token. Under `pull_request`, fork PRs run with a read-only token and no secrets,
and the review job only ever *reads* PR-head files as data.

**Minimum permissions for the calling job:**

```yaml
    permissions:
      contents: read
      pull-requests: write
```

`contents: read` to read the code under review; `pull-requests: write` to post
the review comment. **No `actions:` scope is required** — trusted context passes
between the two jobs as a *same-run* artifact, which authenticates with the
runner's ephemeral `ACTIONS_RUNTIME_TOKEN`, independent of `GITHUB_TOKEN`.

**Required files in your repo:** none. The gate is self-contained — it fetches
its own context and posts its own comment. (Contrast the tech-spec gate, which
requires you to gitignore `.sparxstar/specs/` and write conformance tests.)

### Section 6 — Minimal copy-paste caller block

Every value below is read from the live workflow.

```yaml
# .github/workflows/claude-pr-review.yml  (in your consuming repo)
name: Claude PR Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  review:
    permissions:
      contents: read
      pull-requests: write
    # Pin the immutable release tag @v1.0.0 (platform default). @v1 is the
    # moving major alias and is not recommended; never reference @main.
    uses: Starisian-Technologies/sparxstar-claude-pr-review/.github/workflows/claude-pr-review.yml@v1.0.0
    with:
      contract_ref: v1.0.0           # ← a real registry tag (v1.0.0 is the current floor)
    secrets:
      ANTHROPIC_API_KEY:             ${{ secrets.ANTHROPIC_API_KEY }}
      COMPOSER_RESOLVER_PRIVATE_KEY: ${{ secrets.COMPOSER_RESOLVER_PRIVATE_KEY }}
```

### Section 7 — The sequencing rule (cross-repo)

Org Variables propagate into a reusable workflow automatically, but **secrets do
not cross the `workflow_call` boundary** — this workflow must declare a secret
under `on.workflow_call.secrets` before any consumer can pass it, and this repo
must re-tag after such an edit so the pinned tag (`v1.0.0`) actually contains the
declaration. If a consumer passes a secret the pinned tag doesn't yet declare,
the gate startup-fails (*"the secret … is not defined"*). So when wiring a
freshly added secret: land + re-tag this repo first, then push the caller. The
current `v1.0.0` already declares `ANTHROPIC_API_KEY` (required) and
`COMPOSER_RESOLVER_PRIVATE_KEY` (required).

### Section 8 — Enforcement mode: advisory by design

This gate has **no `enforcement_mode` input** and is **advisory**. It posts (and
updates) a single review comment with a `PASS` / `FAIL` / `CONDITIONAL` verdict;
a `FAIL` verdict does **not** fail the job or block merge. The review is a
signal for humans, not a hard gate.

What *does* hard-fail the job (unconditionally — these are setup/contract errors,
not verdicts): a missing `ANTHROPIC_API_KEY` or `COMPOSER_RESOLVER_PRIVATE_KEY`,
an unset `COMPOSER_RESOLVER_CLIENT_ID`, a public caller repository, a missing PR
context, and a `contract_ref` that is malformed or below the registry floor.

To make conformance *blocking*, the consumer adds its own gate (e.g. branch
protection requiring your conformance tests, or requiring this review comment to
read `PASS` via your own check) — this gate does not block on your behalf.
Platform-wide expectation mirrors the other gates: start advisory, earn blocking
deliberately; never wire a hard block on a repo that isn't clean yet.

---

## What this repo guarantees and does not guarantee

| Guarantee | Mechanism |
| --- | --- |
| The PR was reviewed against the declared ADR/spec versions | `build-context` fetch at `contract_ref` + Claude review |
| The requested `contract_ref` exists and is at/above the supported floor | `Validate contract_ref` (regex + `git check-ref-format`) + registry version-policy |
| Private registry content never leaks to a public caller | public-caller fail-fast guard |
| The registry credential never shares a job with untrusted PR code | two-job privilege split; `persist-credentials: false` on all checkouts |
| A single, updated review comment (no comment sprawl) | upsert by marker |

**What this repo does not guarantee:** that your code conforms to the specs. The
verdict is Claude's advisory judgment, not a proof, and it does not block merge.
The fetch proves the review used the right truth; *conformance* — proving your
code satisfies it — remains your repo's responsibility (your tests, your gate).

## Repository structure (this repo)

```
.github/workflows/
  claude-pr-review.yml     # Reusable workflow — consumers reference @v1.0.0
  ci.yml                   # This repo's own contract tests
examples/
  consumer-workflow.yml    # Drop-in caller (mirrors Section 6)
reference/
  ref-*.md                 # Platform reference docs injected into the review context
docs/
  consumer-setup.md        # This file
  architecture.md          # Platform architecture overview
  ci-cd.md                 # CI/CD and workflow operations
  deployment.md            # Deployment guidance
  upgrade-rollback.md      # Upgrade and rollback guidance
  security-notes.md        # Threat model + accepted scan findings
tests/
  test_workflow_contract.py  # Locks the workflow interface (secrets, inputs, pin, split)
```

## Governance and security

- Security model, threat analysis, and accepted scan findings: `docs/security-notes.md`
- Security policy: `SECURITY.md`
- Code ownership: `CODEOWNERS`

## Reference

- Reusable workflow: `.github/workflows/claude-pr-review.yml`
- Copy-paste example: `examples/consumer-workflow.yml`
- The registries this gate reads:
  `sparxstar-architecture-governance-registry` (ADRs),
  `sparxstar-product-specification-registry` (specs)
