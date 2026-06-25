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

    def test_three_tier_context_steps_present(self) -> None:
        self.assertIn("Load three-tier context", self.workflow)
        self.assertIn("tier_specs.txt", self.workflow)
        self.assertIn("tier_contracts.txt", self.workflow)
        self.assertIn("tier_adrs.txt", self.workflow)

    def test_tier_paths_match_artifact_layout(self) -> None:
        self.assertIn(".sparxstar/specs/agent", self.workflow)
        self.assertIn(".sparxstar/contracts", self.workflow)
        self.assertIn(".sparxstar/adrs", self.workflow)

    def test_tier_truncation_is_capped_per_tier(self) -> None:
        self.assertIn("truncate_to_bytes", self.workflow)
        self.assertIn("25000", self.workflow)  # spec tier cap
        self.assertIn("20000", self.workflow)  # contracts and adrs tier cap
        self.assertIn('data.decode("utf-8")', self.workflow)

    def test_declaration_step_reads_sparxstar_specs_yml(self) -> None:
        self.assertIn("Read repo declaration", self.workflow)
        self.assertIn("sparxstar-specs.yml", self.workflow)
        self.assertIn("specs_ids", self.workflow)
        self.assertIn("contracts_ids", self.workflow)
        self.assertIn("adrs_ids", self.workflow)

    def test_prompt_has_three_named_passes(self) -> None:
        self.assertIn("PASS 1 — SPEC CONFORMANCE", self.workflow)
        self.assertIn("PASS 2 — CONTRACT SEAM CHECK", self.workflow)
        self.assertIn("PASS 3 — ADR DRIFT DETECTION", self.workflow)

    def test_prompt_template_substitution_is_allowlisted(self) -> None:
        self.assertIn('"${DIFF}": Path("pr.diff").read_text(encoding="utf-8")', self.workflow)
        self.assertIn('"${TIER_SPECS}": Path("tier_specs.txt").read_text(encoding="utf-8")', self.workflow)
        self.assertIn('"${TIER_CONTRACTS}": Path("tier_contracts.txt").read_text(encoding="utf-8")', self.workflow)
        self.assertIn('"${TIER_ADRS}": Path("tier_adrs.txt").read_text(encoding="utf-8")', self.workflow)
        self.assertIn(
            r'pattern = re.compile(',
            self.workflow,
        )
        self.assertIn("TIER_SPECS|TIER_CONTRACTS|TIER_ADRS", self.workflow)

    def test_prompt_substitution_validates_no_leftover_tokens(self) -> None:
        self.assertIn('leftover = re.findall(r"\\$\\{[A-Z_]+\\}", prompt)', self.workflow)
        self.assertIn("Unsubstituted template variables in prompt", self.workflow)

    def test_artifact_download_step_present_with_continue_on_error(self) -> None:
        self.assertIn("Download spec artifact", self.workflow)
        self.assertIn("actions/download-artifact@v4", self.workflow)
        self.assertIn("continue-on-error: true", self.workflow)

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

    def test_consumer_example_has_fetch_specs_job(self) -> None:
        self.assertIn("fetch-specs:", self.consumer_example)
        self.assertIn("fetch-specs.yml", self.consumer_example)
        self.assertIn("needs: fetch-specs", self.consumer_example)

    def test_ci_cd_doc_matches_permission_contract(self) -> None:
        self.assertIn("contents: read", self.docs_ci_cd)
        self.assertIn("pull-requests: write", self.docs_ci_cd)
        self.assertIn("ANTHROPIC_API_KEY", self.docs_ci_cd)


if __name__ == "__main__":
    unittest.main()
