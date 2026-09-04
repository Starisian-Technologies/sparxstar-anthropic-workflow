"""Behavioural tests for the `Resolve checkout target` merge gate.

The other suite asserts on workflow *text*. That could not have caught the
defect these tests cover: the gate queried GraphQL `mergeCommit`, which is
populated only once a PR has been merged, so the step failed on every open
PR — while still looking entirely reasonable as a string.

So these tests extract the step's actual shell body from the workflow and run
it under `bash` with a stubbed `gh` on PATH. Stdlib only, matching this repo's
zero-dependency test setup.
"""

from pathlib import Path
import os
import re
import shlex
import subprocess
import tempfile
import textwrap
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github/workflows/claude-pr-review.yml"


def extract_checkout_target_script(text: str | None = None) -> str:
    """Return the `run:` body of the `Resolve checkout target` step.

    Located by step id rather than by line number so the test keeps working
    when the workflow is edited above it.

    `text` is injectable so the extractor's own robustness can be tested against
    YAML formatting variants without editing the real workflow.
    """
    if text is None:
        text = WORKFLOW.read_text(encoding="utf-8")

    start = text.index("id: checkout_target")

    # Accept the block-scalar variants YAML allows: `run: |`, `|-`, `|+`.
    run_match = re.search(r"^\s*run:\s*\|[-+]?\s*$", text[start:], re.MULTILINE)
    if run_match is None:
        raise AssertionError("no run: block found for the checkout_target step")
    body_start = start + run_match.end() + 1

    lines = text[body_start:].split("\n")

    # Indentation comes from the first non-blank line. Taking it from lines[0]
    # meant a leading blank line — valid YAML — produced indent 0, and the
    # extractor then swallowed the rest of the workflow.
    indent = next(
        (len(line) - len(line.lstrip()) for line in lines if line.strip()),
        None,
    )
    if indent is None or indent == 0:
        raise AssertionError("could not determine block indentation")

    body: list[str] = []
    for line in lines:
        if line.strip() and (len(line) - len(line.lstrip())) < indent:
            break
        body.append(line)

    script = textwrap.dedent("\n".join(body))
    if "GITHUB_OUTPUT" not in script:
        raise AssertionError("extracted script does not look like the gate body")
    return script


class CheckoutTargetGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = extract_checkout_target_script()

    def _run(self, *, pr_number: str, gh_stdout: str = "", gh_stderr: str = "", gh_exit: int = 0):
        """Run the gate with a stubbed `gh`; return (returncode, outputs, stdout)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            bin_dir = tmp_path / "bin"
            bin_dir.mkdir()
            gh_stub = bin_dir / "gh"
            gh_stub.write_text(
                "#!/usr/bin/env bash\n"
                f"printf '%s' {shlex.quote(gh_stdout)}\n"
                f"printf '%s' {shlex.quote(gh_stderr)} >&2\n"
                f"exit {gh_exit}\n",
                encoding="utf-8",
            )
            gh_stub.chmod(0o755)

            github_output = tmp_path / "github_output"
            github_output.touch()

            env = dict(os.environ)
            env.update(
                PATH=f"{bin_dir}:{env['PATH']}",
                PR_NUMBER=pr_number,
                GITHUB_REPOSITORY_SAFE="Starisian-Technologies/sparxstar-sky-hermes",
                GITHUB_SHA_SAFE="0000000000000000000000000000000000000000",
                GH_REPO="Starisian-Technologies/sparxstar-sky-hermes",
                GH_TOKEN="stub-token",
                GITHUB_OUTPUT=str(github_output),
            )

            proc = subprocess.run(
                ["bash", "-c", self.script],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            outputs = dict(
                line.split("=", 1)
                for line in github_output.read_text(encoding="utf-8").splitlines()
                if "=" in line
            )
            return proc.returncode, outputs, proc.stdout

    # --- the case the old gate could never satisfy ---------------------------

    def test_open_mergeable_pr_resolves_to_the_test_merge_commit(self) -> None:
        """An open, mergeable PR must pass and check out the test-merge commit.

        GitHub returns a non-null `merge_commit_sha` for an open mergeable PR.
        The previous `mergeCommit` query returned null here, so this is the
        regression that matters.
        """
        merge_sha = "1d4e08526e647946c04e8d02ebc3cc941e075eef"
        code, outputs, _ = self._run(pr_number="23", gh_stdout=merge_sha)

        self.assertEqual(code, 0, "gate must pass for an open mergeable PR")
        self.assertEqual(outputs.get("ref"), merge_sha)
        self.assertEqual(
            outputs.get("repository"),
            "Starisian-Technologies/sparxstar-sky-hermes",
        )

    # --- fail-closed behaviour ----------------------------------------------

    def test_missing_merge_preview_fails_closed(self) -> None:
        """No test-merge (conflict, or not yet computed) must fail the job."""
        code, outputs, stdout = self._run(pr_number="23", gh_stdout="")

        self.assertNotEqual(code, 0, "gate must fail when no test merge exists")
        self.assertIn("::error::", stdout)
        self.assertNotIn("ref", outputs)

    def test_query_failure_fails_closed(self) -> None:
        """A failing `gh api` call must fail the job, not fall through."""
        code, outputs, stdout = self._run(
            pr_number="23", gh_stderr="gh: not found", gh_exit=1
        )

        self.assertNotEqual(code, 0)
        self.assertIn("::error::", stdout)
        self.assertNotIn("ref", outputs)

    def test_never_falls_back_to_pr_head_on_failure(self) -> None:
        """The head SHA must never become the checkout ref.

        This is the security property: the job holds `pull-requests: write`,
        so it must not check out contributor-controlled code.
        """
        head_sha = "c5a8d00eeaafc68f94a5341b9e6bc4b848137011"
        code, outputs, stdout = self._run(pr_number="23", gh_stdout="")

        self.assertNotEqual(code, 0)
        self.assertNotIn(head_sha, outputs.get("ref", ""))
        self.assertNotIn(head_sha, stdout)

    # --- non-PR invocations --------------------------------------------------

    def test_non_pr_invocation_uses_github_sha(self) -> None:
        """With no PR number the gate is skipped and github.sha is used."""
        code, outputs, _ = self._run(pr_number="")

        self.assertEqual(code, 0)
        self.assertEqual(
            outputs.get("ref"), "0000000000000000000000000000000000000000"
        )

    def test_non_numeric_pr_number_is_not_interpolated(self) -> None:
        """A non-numeric PR number must not reach the shell as code."""
        code, outputs, _ = self._run(pr_number="23; touch /tmp/pwned")

        self.assertEqual(code, 0)
        self.assertEqual(
            outputs.get("ref"), "0000000000000000000000000000000000000000"
        )
        self.assertFalse(Path("/tmp/pwned").exists())


class ExtractorRobustnessTests(unittest.TestCase):
    """The extractor must survive valid YAML formatting variants.

    A brittle extractor produces confusing failures that look like gate bugs, so
    these guard the harness itself rather than the workflow.
    """

    TEMPLATE = """jobs:
  review:
    steps:
      - name: Resolve checkout target
        id: checkout_target
        run: {scalar}
{blank}          echo "ref=abc" >> "$GITHUB_OUTPUT"
      - name: Next step
        run: |
          echo unrelated
"""

    def _extract(self, scalar: str, blank: str = "") -> str:
        return extract_checkout_target_script(
            self.TEMPLATE.format(scalar=scalar, blank=blank)
        )

    def test_plain_block_scalar(self) -> None:
        self.assertIn("GITHUB_OUTPUT", self._extract("|"))

    def test_strip_and_keep_chomping_indicators(self) -> None:
        # `|-` and `|+` are valid and mean the same thing for our purposes.
        for scalar in ("|-", "|+"):
            with self.subTest(scalar=scalar):
                self.assertIn("GITHUB_OUTPUT", self._extract(scalar))

    def test_leading_blank_line_does_not_swallow_the_workflow(self) -> None:
        script = self._extract("|", blank="\n")

        self.assertIn("GITHUB_OUTPUT", script)
        self.assertNotIn("echo unrelated", script, "extraction ran past the step")

    def test_missing_block_raises_a_clear_error(self) -> None:
        with self.assertRaises(AssertionError):
            extract_checkout_target_script("jobs:\n  x:\n    steps:\n      - id: checkout_target\n")


class CheckoutTargetGateContractTests(unittest.TestCase):
    """Text assertions guarding against a regression to the wrong API."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_gate_uses_rest_merge_commit_sha(self) -> None:
        self.assertIn("merge_commit_sha", self.workflow)

    def test_gate_does_not_use_graphql_merge_commit(self) -> None:
        """`gh pr view --json mergeCommit` is null for every open PR."""
        self.assertNotIn("--json mergeCommit", self.workflow)
        self.assertNotIn(".mergeCommit.oid", self.workflow)

    def test_gate_requires_a_non_empty_sha(self) -> None:
        """Without the -n guard an empty result silently yields an empty ref."""
        self.assertIn('[ -n "$MERGE_COMMIT_SHA" ]', self.workflow)



if __name__ == "__main__":
    unittest.main()
