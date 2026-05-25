# Deployment

## Deployment model
Deployment is release-by-reference of workflow files in this repository.
Consumer repositories import the workflow by ref:

`Starisian-Technologies/sparxstar-anthropic-workflow/.github/workflows/claude-pr-review.yml@<ref>`

## Safe deployment process
1. Open PR with workflow and documentation changes.
2. Validate syntax and governance files.
3. Merge after required reviews.
4. Publish a release tag.
5. Update consumer repositories to the approved tag (recommended over floating refs for controlled rollout).

## Post-deploy verification
- Trigger a test PR in a consumer repository.
- Verify diff retrieval, prompt generation, and comment upsert behavior.
- Confirm no secret leakage in logs.
