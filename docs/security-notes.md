# Security Notes

Operational security decisions for the Claude PR review workflow, recorded so
the rationale lives next to the code and is not re-litigated on every scan.

## Threat model

The reusable workflow (`.github/workflows/claude-pr-review.yml`) reviews a pull
request against authoritative platform contracts. Two facts drive its design:

- It reads **private** registries (`sparxstar-architecture-governance-registry`,
  `sparxstar-product-specification-registry`) via short-lived, least-privilege
  tokens minted from the composer-resolver GitHub App.
- It reviews **untrusted PR-head code** — by definition the thing under review.

The danger is letting those two meet: untrusted PR code executing in a job that
holds a credential able to reach private repositories. The workflow is
structured so they never do.

## Controls in place

- **Privilege split.** `build-context` (privileged) mints the registry tokens
  and fetches the contracts; it **never checks out PR-head code**. `review`
  (unprivileged) checks out PR-head code but holds no App key and only *reads*
  those files as data (`git checkout`, `gh pr diff`, `cat` into a prompt — no
  build, install, or script execution). Trusted context crosses between jobs by
  artifact only.
- **Private callers only.** `build-context`'s first step refuses to run (before
  any token is minted or content fetched) unless `github.event.repository.private`
  is `true`. The trusted-context artifact contains raw private registry content,
  which would be downloadable by anyone on a public repository.
- **`contract_ref` validation.** The caller-supplied ref is constrained to a safe
  git-ref shape before any checkout; registry checkouts use the validated value.
- **No credential persistence.** Every checkout sets `persist-credentials: false`.
- **`pull_request` only.** Consumers must not invoke the workflow from
  `pull_request_target`.

## Accepted finding: CodeQL "Checkout of untrusted code in a trusted context"

**Identify by query + location, not alert number.** Alert IDs are not stable
(they change as alerts are dismissed/reopened, rules change, or the query
re-fires), so this finding is identified by the query name —
*Checkout of untrusted code in a trusted context* (`actions/unsafe-checkout`) —
and its location: the **`build-context`** job of
`.github/workflows/claude-pr-review.yml`, on the registry-checkout / token-mint
steps whose ref derives from `inputs.contract_ref`.

**Status:** dismissed in the Security tab as a false positive — this query
against the `build-context` job, including any later re-fire (which may surface
under a new alert number).

**Why it fires.** CodeQL flags `build-context` because it is privileged (mints
tokens with a secret) and performs a checkout whose ref derives from
`inputs.contract_ref`. The query traces the ref back to a workflow input and
treats it as externally controllable; it does not recognize the regex barrier in
the `Validate contract_ref` step as a sanitizer, so it re-fires (and relocates
its representative line) on each edit.

**Why it is a false positive here.** `build-context` checks out **no PR-head
code** and **executes nothing** it checks out — it only `cat`s markdown from
*fixed, trusted* repositories (`Starisian-Technologies/sparxstar-*-registry`,
plus this repo's `reference/`). The single input-influenced element is *which
ref/tag of a trusted private repo* to read, and that ref is:

- supplied by the **trusted caller workflow** (base-branch-defined under
  `pull_request`, not reachable by a PR author), and
- constrained to a safe ref shape by `Validate contract_ref`.

There is no path by which untrusted PR code runs beside the registry credential.
This is the privileged-job-without-PR-code shape, distinct from the genuine
"reviewer checks out PR-head code *and* holds the token" risk — which the
privilege split eliminated.

**Why not a repo-wide suppression.** A `paths-ignore` / query filter that
silences this rule for the file would also hide a *real* future occurrence — for
example, if someone later added a PR-head checkout to a privileged job. The
finding is therefore handled by a **scoped, per-alert dismissal with
justification** so a genuinely new or changed occurrence re-alerts.

**Re-evaluate the dismissal if** `build-context` ever gains a checkout of
PR-head code or the PR's repository, executes anything from a checked-out tree,
or the registry checkouts switch from fixed repositories to an input-controlled
repository (not just an input-controlled ref).

## Fixed finding: same query, `review` job's checkout-target resolution

A second occurrence of the same CodeQL query — *Checkout of untrusted code in
a trusted context* — fired on the **`review`** job's `Resolve checkout target`
/ `Checkout code` steps: that job holds `pull-requests: write`, and its
resolved ref could previously fall back to the raw, untrusted PR-head SHA
(`github.event.pull_request.head.sha`) whenever the PR's merge commit was
unavailable (e.g. `gh pr view` failure, or the PR not currently mergeable).
Unlike the `build-context` finding above, this one was **not** dismissed —
`review` genuinely holds a live token. The fix is fail-closed, not a
justification: `Resolve checkout target` now requires a merge commit SHA (via
`gh pr view --json mergeCommit`) for PR runs and fails the job if one cannot be
resolved, instead of silently checking out the untrusted head.
