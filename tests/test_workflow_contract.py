from pathlib import Path
import unittest


class WorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        cls.workflow = (repo_root / ".github/workflows/claude-pr-review.yml").read_text(encoding="utf-8")
        cls.readme = (repo_root / "README.md").read_text(encoding="utf-8")
        cls.docs_ci_cd = (repo_root / "docs/ci-cd.md").read_text(encoding="utf-8")
        cls.consumer_example = (repo_root / "examples/consumer-workflow.yml").read_text(encoding="utf-8")

    def test_reusable_workflow_requires_anthropic_api_key(self) -> None:
        self.assertIn("workflow_call:", self.workflow)
        self.assertIn("ANTHROPIC_API_KEY:", self.workflow)
        self.assertIn("required: true", self.workflow)

    def test_reusable_workflow_declares_contract_ref_input(self) -> None:
        self.assertIn("inputs:", self.workflow)
        self.assertIn("contract_ref:", self.workflow)
        self.assertIn("default: v1", self.workflow)

    def test_reusable_workflow_requires_composer_resolver_private_key(self) -> None:
        self.assertIn("COMPOSER_RESOLVER_PRIVATE_KEY:", self.workflow)

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
        self.assertIn("ref: ${{ inputs.contract_ref }}", self.workflow)

    def test_registry_content_is_loaded_into_spec_context(self) -> None:
        self.assertIn("ADR REGISTRY FILE", self.workflow)
        self.assertIn("PRODUCT SPEC REGISTRY FILE", self.workflow)

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

    def test_consumer_example_pins_v1_and_passes_resolver_secret(self) -> None:
        self.assertIn("claude-pr-review.yml@v1", self.consumer_example)
        self.assertNotIn("claude-pr-review.yml@main", self.consumer_example)
        self.assertIn("COMPOSER_RESOLVER_PRIVATE_KEY: ${{ secrets.COMPOSER_RESOLVER_PRIVATE_KEY }}", self.consumer_example)
        self.assertIn("contract_ref:", self.consumer_example)

    def test_readme_pins_v1_and_documents_resolver_requirements(self) -> None:
        self.assertIn("claude-pr-review.yml@v1", self.readme)
        self.assertNotIn("claude-pr-review.yml@main", self.readme)
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
