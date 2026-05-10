# sparxstar-anthropic-workflow

Centralised GitHub Actions workflows for the [SPARXSTAR platform](https://github.com/Starisian-Technologies). The reusable `claude-pr-review.yml` workflow runs an automated, Claude-powered code review on every pull request — enforcing platform-wide architectural rules, security standards, and spec compliance automatically, without any per-PR manual effort.

---

## How it works

1. A consumer repo adds a **single nine-line workflow file** that calls this repo's reusable workflow.
2. When a PR is opened, updated, or reopened, GitHub runs the review automatically.
3. The workflow pulls the PR diff, reads the repo's own spec docs and Copilot instructions for context, sends everything to Claude with all SPARXSTAR platform rules baked in, and posts the findings as a comment directly on the PR.
4. The review identifies **violations** (must fix before merge) and **warnings** (should fix), and delivers a final **PASS / FAIL / CONDITIONAL** verdict.

Because the logic lives here and is referenced by all consumer repos, a single update to this file propagates to every repo on the next PR.

---

## Setup

### 1. Add the secret

Add `ANTHROPIC_API_KEY` to your organisation secrets (preferred) or to each consumer repo's secrets:

> **Settings → Secrets and variables → Actions → New secret**
> Name: `ANTHROPIC_API_KEY`
> Value: your Anthropic API key

The workflow will fail fast with a clear error message if the secret is missing.

### 2. Add the consumer workflow

In each repo that should receive automated reviews, create `.github/workflows/claude-pr-review.yml` with the following content (also available in [`examples/consumer-workflow.yml`](examples/consumer-workflow.yml)):

```yaml
name: Claude PR Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  review:
    uses: Starisian-Technologies/sparxstar-anthropic-workflow/.github/workflows/claude-pr-review.yml@main
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

That is the entire file. No logic to copy or maintain.

### 3. Optional spec context

The workflow automatically picks up the following files from the consumer repo if they exist and includes them in the review prompt for repo-specific context:

| File | Purpose |
|------|---------|
| `AGENTS.md` | Agent/AI instructions |
| `.github/copilot-instructions.md` | Copilot coding instructions |
| `*.md` (root, excluding README and CHANGELOG) | Spec and design docs |
| `docs/*.md` | Documentation |
| `specs/*.md` | Specification files |

---

## Platform-wide rules enforced on every PR

Every review checks the following rules regardless of which repo triggered it:

| Rule | Description |
|------|-------------|
| `strict_types` | `declare(strict_types=1)` in every PHP file |
| No `error_log()` | Use the platform logging pattern |
| No `SELECT *` | All queries must be explicit |
| No MIT licence | All repos must use a proprietary licence |
| No phantom packages | `wordpress/mcp-adapter` does not exist on Packagist |
| No type redefinition | Never locally redefine types owned by `sparxstar-ouroboros-integrity` |
| No stub directories | `packages/` stubs are forbidden — the real package is published |
| No unrequested test/stub files | Test, stub, and mock files must be explicitly requested |
| Signing method | `GovernanceTokenSigningMaterial::build()` not `canonicalize()` |
| ContextPulse field order | `pulse_id\|context_id\|device_id\|session_id\|site_id\|network_id\|trust_score_4dp\|trust_level\|behavior_flags_json\|geo_zone\|network_effective_type\|session_duration\|issued_at\|expires` |
| Token reference | CI auth must reference `STARISIAN_PACKAGE_TOKEN` not `COPILOT_MCP_TOKEN` |
| Fail-fast token guard | CI auth step must exit if token is empty |
| Genesis hash | `AuditLedger` genesis hash must be `str_repeat('0', 64)` not an empty string |
| SieveKernel boot | `boot()` must check `did_action('muplugins_loaded')` before deferring |
| Governance TTL | Must enforce `Platform::GOVERNANCE_TOKEN_TTL_MIN_SECONDS` floor |
| Encryption | AES-256-GCM only — never CBC |
| No `identity_id` | Must not appear in `ContextPulse` (replay attack surface) |
| `behavior_flags` format | Serialised as a sorted JSON array — never CSV |
| FingerprintJS | Must be a vendored `<script>` tag — never bundled via npm |
| Policy token | `personal_policy_token` must not be returned in REST response body |
| TEXT column defaults | `TEXT` columns in MySQL/MariaDB must not have `DEFAULT NULL` — use `NULL` only |

---

## Review output format

```
REPOSITORY: Starisian-Technologies/example-repo
PR: #42 Add governance token signing

VERDICT: FAIL

VIOLATIONS (must fix before merge):
[CRITICAL] Uses canonicalize() instead of build() on line 87 of src/Signing/Material.php. Rule: GovernanceTokenSigningMaterial::build() not canonicalize().
[HIGH] SELECT * used in query on line 34 of src/Repository/LedgerRepository.php. Rule: No SELECT *.

WARNINGS (should fix):
[MEDIUM] genesis_hash initialised to empty string on line 12. Rule: AuditLedger genesis hash must be str_repeat('0', 64).
```

---

## Updating the rules

Edit `.github/workflows/claude-pr-review.yml` in **this repo**. All consumer repos pick up the changes on their next PR without any action required on their side.

---

## Repository structure

```
sparxstar-anthropic-workflow/
├── .github/
│   └── workflows/
│       └── claude-pr-review.yml   # Reusable workflow (the source of truth)
├── examples/
│   └── consumer-workflow.yml      # Template to copy into consumer repos
└── README.md
```

---

*Maintained by [Starisian Technologies](https://github.com/Starisian-Technologies)*