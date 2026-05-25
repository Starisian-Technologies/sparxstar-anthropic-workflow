# Upgrade and Rollback

## Upgrade guidance
- Prefer pinned release tags in consumer repositories.
- Read changelog before upgrading.
- Test upgrade in one low-risk repository before broad rollout.

## Rollback guidance
1. Repoint consumer workflow ref to previous known-good tag.
2. Re-run PR workflow in affected repositories.
3. Open follow-up issue documenting root cause and corrective actions.

## Compatibility notes
Changes to:
- workflow inputs,
- required permissions,
- or expected context files
must be documented in README and changelog before release.
