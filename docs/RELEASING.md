# Releasing LR-Agent

## Release checklist

1. Ensure default-branch CI is green.
2. Review `docs/research/CLAIM_LEDGER.md` for statements that changed status.
3. Run the example research-manifest validator and artifact fingerprint command.
4. Update `CHANGELOG.md`.
5. Update the version in `pyproject.toml`.
6. Update `CITATION.cff` version and release date.
7. Verify README badges / release links do not point to an older release.
8. Create the tag only after the versioned files are committed.
9. Preserve negative results and known limitations in the release notes.

## Versioning intent

- Patch: bug fixes and documentation corrections that do not change research semantics.
- Minor: new mechanisms, metrics, research infrastructure, CLI/API behavior, or evaluation protocols.
- Major: incompatible public API or persisted-data changes.

A release version must not imply that a research hypothesis has been validated.
