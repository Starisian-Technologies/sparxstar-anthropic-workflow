# Contributing to SPARXSTAR Anthropic Workflow

## Scope
This repository ships reusable GitHub Actions governance workflows for Starisian Technologies repositories.

## Contribution requirements
- Open an issue before large changes.
- Keep changes minimal and production-safe.
- Preserve deterministic workflow behavior.
- Never commit secrets, tokens, or private data.
- Keep documentation aligned with implementation.

## Local validation
This repository currently has no local build system.
Validate by:
- Checking YAML syntax for workflow and template files.
- Reviewing shell blocks for fail-fast behavior and safe variable handling.
- Verifying docs and examples match live workflow inputs and required permissions.

## Pull request expectations
All pull requests must include:
- Problem statement
- Risk assessment
- Testing notes
- Rollback plan
- Migration impact (if any)

Use the repository PR template and complete all required checklist items.
