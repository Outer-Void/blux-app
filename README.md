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

(( • ))
