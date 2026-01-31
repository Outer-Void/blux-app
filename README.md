# BLUX App

BLUX App is a **read-only** window into user intent, collaborative model output,
discernment analysis, and execution receipts.

It has no authority and does not execute, enforce, or optimize.

All intelligence and enforcement live outside this application. This repository
exists to prove platform shape, not capability.

## Read-only viewer usage (Phase 1)

Point the viewer at an output directory containing JSON artifacts. The viewer
prints each panel to stdout without executing anything or mutating files.

```bash
python blux_view.py --input-dir /path/to/output
```

Expected files in the directory (missing files are shown as absent panels):

- `intent.json` (ProblemSpec / GoalSpec)
- `coga.json` (CogA reasoning artifact)
- `ca.json` (cA build artifact)
- `verdicts.json` (verdict panel(s))
- `receipt.json` (execution receipt)

For the UI panel contract, see `docs/UI_CONTRACT.md`.

## Read-only viewer usage (Phases 3 + 4)

Phase 3 adds richer CogA/cA output rendering and Phase 4 adds receipts plus
harness reports. The viewer stays read-only and prints any recognized sections
alongside the raw JSON.

```bash
python blux_view.py --input-dir /path/to/phase-3-4-output
```

Expected files for Phase 3/4 (missing files are shown as absent panels):

- `intent.json`
- `coga.json` (CogA options + comparison matrix)
- `ca.json` (multi-file artifacts + patch bundles)
- `verdicts.json`
- `receipt.json` (agent runs, versions, hashes)
- `report.json` (harness summary + per-fixture results)

(( • ))
