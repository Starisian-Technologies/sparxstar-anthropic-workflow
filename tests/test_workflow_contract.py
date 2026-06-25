from pathlib import Path
import re
import unittest


class WorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        cls.workflow = (repo_root / ".github/workflows/claude-pr-review.yml").read_text(encoding="utf-8")
        cls.readme = (repo_root / "README.md").read_text(encoding="utf-8")
        cls.docs_ci_cd = (repo_root / "docs/ci-cd.md").read_text(encoding="utf-8")
        cls.consumer_example = (repo_root / "examples/consumer-workflow.yml").read_text(encoding="utf-8")

    def _assert_claude_workflow_pinned_to(self, text: str, expected_ref: str) -> None:
        # Extract every `uses: …/claude-pr-review.yml@<ref>` pin and assert each
        # resolves to exactly expected_ref. \S+ stops at whitespace, so trailing
        # spaces, CRLF line endings, and inline comments (…@v1 # note) are all
        # handled, and the @v1.0.0-contains-@v1 substring trap is avoided.
        refs = re.findall(r"claude-pr-review\.yml@(\S+)", text)
        self.assertTrue(refs, "no claude-pr-review.yml@<ref> pin found")
        for ref in refs:
            self.assertEqual(ref, expected_ref)

    def test_reusable_workflow_requires_anthropic_api_key(self) -> None:
        self.assertIn("workflow_call:", self.workflow)
        self.assertIn("ANTHROPIC_API_KEY:", self.workflow)
        self.assertIn("required: true", self.workflow)

    def test_reusable_workflow_declares_contract_ref_input(self) -> None:
        self.assertIn("inputs:", self.workflow)
        self.assertIn("contract_ref:", self.workflow)
        # Default is the immutable release tag, not the moving major alias.
        self.assertIn("default: v1.0.0", self.workflow)

    def test_reusable_workflow_requires_composer_resolver_private_key(self) -> None:
        self.assertIn("COMPOSER_RESOLVER_PRIVATE_KEY:", self.workflow)

    def test_workflow_validates_resolver_config_before_minting(self) -> None:
        self.assertIn("COMPOSER_RESOLVER_CLIENT_ID variable is not set", self.workflow)
        self.assertIn("COMPOSER_RESOLVER_PRIVATE_KEY secret is not set", self.workflow)
        validate = self.workflow.index("Validate composer-resolver configuration")
        mint = self.workflow.index("Mint ADR read token")
        self.assertLess(validate, mint)

    def test_workflow_mints_scoped_registry_read_tokens(self) -> None:
        self.assertIn("actions/create-github-app-token@v3", self.workflow)
        self.assertIn("client-id: ${{ vars.COMPOSER_RESOLVER_CLIENT_ID }}", self.workflow)
        self.assertIn("private-key: ${{ secrets.COMPOSER_RESOLVER_PRIVATE_KEY }}", self.workflow)
        self.assertIn("repositories: sparxstar-architecture-governance-registry", self.workflow)
        self.assertIn("repositories: sparxstar-product-specification-registry", self.workflow)

    def test_workflow_checks_out_registries_with_minted_tokens_at_contract_ref(self) -> None:
        self.assertIn("repository: Starisian-Technologies/sparxstar-architecture-governance-registry", self.workflow)
        self.assertIn("repository: Starisian-Technologies/sparxstar-product-specification-registry", self.workflow)
        self.assertIn("token: ${{ steps.adr-token.outputs.token }}", self.workflow)
        self.assertIn("token: ${{ steps.spec-token.outputs.token }}", self.workflow)
        # Registry checkouts use the validated contract ref, not the raw input.
        self.assertIn("ref: ${{ steps.contract.outputs.ref }}", self.workflow)

    def test_contract_ref_is_validated_before_checkout(self) -> None:
        self.assertIn("Validate contract_ref", self.workflow)
        self.assertIn("CONTRACT_REF: ${{ inputs.contract_ref }}", self.workflow)
        self.assertIn("[A-Za-z0-9][A-Za-z0-9._/-]*", self.workflow)
        # Plus Git's own ref-name rules (rejects .lock, //, trailing /, ..).
        self.assertIn("git check-ref-format --allow-onelevel", self.workflow)
        # The raw input must not flow directly into a checkout ref.
        self.assertNotIn("ref: ${{ inputs.contract_ref }}", self.workflow)
        validate = self.workflow.index("Validate contract_ref")
        adr_checkout = self.workflow.index("Checkout ADR registry")
        self.assertLess(validate, adr_checkout)

    def test_registry_content_is_loaded_into_spec_context(self) -> None:
        self.assertIn("ADR REGISTRY FILE", self.workflow)
        self.assertIn("PRODUCT SPEC REGISTRY FILE", self.workflow)

    def _job_blocks(self) -> tuple[str, str]:
        # build-context is defined before review; slice the file at the two
        # 2-space-indented job headers.
        a_start = self.workflow.index("\n  build-context:")
        b_start = self.workflow.index("\n  review:")
        self.assertLess(a_start, b_start)
        return self.workflow[a_start:b_start], self.workflow[b_start:]

    def test_workflow_is_split_into_two_jobs(self) -> None:
        self.assertIn("\n  build-context:", self.workflow)
        self.assertIn("\n  review:", self.workflow)
        _, review = self._job_blocks()
        self.assertIn("needs: build-context", review)

    def test_privileged_job_holds_app_key_and_never_checks_out_pr_head(self) -> None:
        build_context, _ = self._job_blocks()
        # The App key and token minting live in the privileged job...
        self.assertIn("actions/create-github-app-token@v3", build_context)
        self.assertIn("secrets.COMPOSER_RESOLVER_PRIVATE_KEY", build_context)
        self.assertIn("actions/upload-artifact", build_context)
        # ...which must never resolve or check out untrusted PR-head code.
        self.assertNotIn("Resolve checkout target", build_context)
        self.assertNotIn("steps.checkout_target.outputs.ref", build_context)

    def test_build_context_refuses_public_caller(self) -> None:
        build_context, _ = self._job_blocks()
        self.assertIn("Guard against public caller repository", build_context)
        self.assertIn("github.event.repository.private", build_context)
        # The guard must run before any token is minted AND before any private
        # content is fetched — it is the first gate, failing the job outright.
        guard = build_context.index("Guard against public caller repository")
        mint = build_context.index("Mint ADR read token")
        fetch = build_context.index("Checkout ADR registry")
        self.assertLess(guard, mint)
        self.assertLess(guard, fetch)
        # The guard is the first step in the job — no other `- name:` precedes it.
        self.assertEqual(
            build_context.index("      - name:"),
            build_context.index("      - name: Guard against public caller repository"),
        )

    def test_all_checkouts_disable_credential_persistence(self) -> None:
        checkouts = self.workflow.count("uses: actions/checkout@v5")
        persist_false = self.workflow.count("persist-credentials: false")
        self.assertGreaterEqual(checkouts, 4)
        self.assertEqual(checkouts, persist_false)

    def test_trusted_context_loaded_before_repo_local(self) -> None:
        _, review = self._job_blocks()
        trusted = review.index("cat .spx-trusted-context/trusted_context.txt")
        repo_local = review.index("REPO-LOCAL FILE: AGENTS.md")
        # Trusted, canonical context must precede repo-local context so it
        # survives the 50KB cap.
        self.assertLess(trusted, repo_local)

    def test_unprivileged_review_job_has_no_app_key_and_only_consumes_artifact(self) -> None:
        _, review = self._job_blocks()
        # The job that checks out untrusted PR-head code...
        self.assertIn("ref: ${{ steps.checkout_target.outputs.ref }}", review)
        # ...must not hold the App key or mint tokens...
        self.assertNotIn("actions/create-github-app-token", review)
        self.assertNotIn("COMPOSER_RESOLVER_PRIVATE_KEY", review)
        # ...and receives trusted context only via artifact (never re-fetched).
        self.assertIn("actions/download-artifact", review)
        self.assertNotIn("Checkout ADR registry", review)
        self.assertNotIn("Checkout product-spec registry", review)

    def test_workflow_has_required_permissions(self) -> None:
        self.assertIn("permissions:", self.workflow)
        self.assertIn("contents: read", self.workflow)
        self.assertIn("pull-requests: write", self.workflow)

    def test_diff_step_has_fail_fast_guards(self) -> None:
        start_marker = "- name: Get PR diff"
        end_marker = "\n      - name:"
        start = self.workflow.index(start_marker)
        end = self.workflow.index(end_marker, start + len(start_marker))
        diff_step = self.workflow[start:end]
        self.assertIn("No pull request number found", diff_step)
        self.assertIn("PR diff is empty", diff_step)
        self.assertIn("set -euo pipefail", diff_step)

    def test_diff_truncation_is_capped_and_flagged(self) -> None:
        start_marker = 'if [ "$(wc -c < pr.diff)" -gt 80000 ]; then'
        end_marker = 'echo "truncated=false" >> "$GITHUB_OUTPUT"'
        start = self.workflow.index(start_marker)
        end = self.workflow.index(end_marker, start) + len(end_marker)
        diff_block = self.workflow[start:end]
        self.assertIn('echo "truncated=true" >> "$GITHUB_OUTPUT"', diff_block)
        self.assertIn('data.decode("utf-8")', diff_block)

    def test_spec_context_truncation_is_capped_and_warned(self) -> None:
        start_marker = 'if [ "$(wc -c < spec_context.txt)" -gt 50000 ]; then'
        end_marker = "Spec context truncated to 50KB"
        start = self.workflow.index(start_marker)
        end = self.workflow.index(end_marker, start) + len(end_marker)
        spec_block = self.workflow[start:end]
        self.assertIn('data.decode("utf-8")', spec_block)

    def test_prompt_template_substitution_is_allowlisted(self) -> None:
        self.assertIn('"${DIFF}": Path("pr.diff").read_text(encoding="utf-8")', self.workflow)
        self.assertIn('"${SPECS}": Path("spec_context.txt").read_text(encoding="utf-8")', self.workflow)
        self.assertIn("pattern = re.compile(r\"\\$\\{(?:DIFF|SPECS|REPO|PR_TITLE|PR_NUMBER|TRUNCATION_LINE)\\}\")", self.workflow)

    def test_review_comment_is_upserted_with_single_marker(self) -> None:
        self.assertIn('COMMENT_MARKER="<!-- claude-pr-review-comment -->"', self.workflow)
        self.assertIn('issues/${PR_NUMBER}/comments', self.workflow)
        self.assertIn('issues/comments/${EXISTING_COMMENT_ID}', self.workflow)
        self.assertIn('gh pr comment "$PR_NUMBER"', self.workflow)

    def test_readme_documents_required_permissions_and_secret(self) -> None:
        self.assertIn("ANTHROPIC_API_KEY", self.readme)
        self.assertIn("contents: read", self.readme)
        self.assertIn("pull-requests: write", self.readme)

    def test_consumer_example_keeps_required_permissions_and_secret(self) -> None:
        self.assertIn("contents: read", self.consumer_example)
        self.assertIn("pull-requests: write", self.consumer_example)
        self.assertIn("ANTHROPIC_API_KEY", self.consumer_example)

    def test_consumer_example_pins_immutable_tag_and_passes_resolver_secret(self) -> None:
        # Platform convention: pin the immutable release tag, not @v1 or @main.
        self._assert_claude_workflow_pinned_to(self.consumer_example, "v1.0.0")
        self.assertIn("COMPOSER_RESOLVER_PRIVATE_KEY: ${{ secrets.COMPOSER_RESOLVER_PRIVATE_KEY }}", self.consumer_example)
        self.assertIn("contract_ref: v1.0.0", self.consumer_example)

    def test_readme_pins_immutable_tag_and_documents_resolver_requirements(self) -> None:
        self._assert_claude_workflow_pinned_to(self.readme, "v1.0.0")
        self.assertIn("COMPOSER_RESOLVER_PRIVATE_KEY", self.readme)
        self.assertIn("COMPOSER_RESOLVER_CLIENT_ID", self.readme)
        self.assertIn("contract_ref", self.readme)

    def test_ci_cd_doc_matches_permission_contract(self) -> None:
        self.assertIn("contents: read", self.docs_ci_cd)
        self.assertIn("pull-requests: write", self.docs_ci_cd)
        self.assertIn("ANTHROPIC_API_KEY", self.docs_ci_cd)

    def test_ci_cd_doc_documents_resolver_and_contract_ref(self) -> None:
        self.assertIn("COMPOSER_RESOLVER_PRIVATE_KEY", self.docs_ci_cd)
        self.assertIn("COMPOSER_RESOLVER_CLIENT_ID", self.docs_ci_cd)
        self.assertIn("contract_ref", self.docs_ci_cd)


if __name__ == "__main__":
    unittest.main()
