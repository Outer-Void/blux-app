# BLUX App Compatibility

> **Legacy (BLUX App 1.0):** describes the pre-contract run-directory viewer, now `blux-app legacy-view`
> (code in `legacy/`). BLUX App 2.0 is described in the [README](../README.md).

BLUX App is a read-only, offline viewer that remains forward compatible by
rendering unknown fields as raw JSON.

## Supported output ranges

The viewer is validated against fixtures from:

- **0.1** (early/legacy schemas)
- **0.6** (mid-series output)
- **1.0-pro** (release-candidate output)

## Compatibility guarantees

- Missing optional fields are tolerated.
- Unknown fields are preserved and rendered verbatim.
- Multiple report variants (`report.json`, `replay_report.json`,
  `accept_report.json`) can be present simultaneously.

## Version negotiation rendering

If `requested` / `resolved` version fields appear in receipts, the viewer
renders them under a Version Negotiation section without making decisions.
