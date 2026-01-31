# BLUX App Runbook

## Opening a run directory

Use the stable entrypoint from the repository root:

```bash
./blux-app view --root /path/to/run
```

The viewer is read-only and offline. It renders JSON artifacts to stdout
without modifying any files.

## Expected artifacts

The viewer looks for these files (missing files are listed as absent panels):

- `intent.json`
- `coga.json`
- `ca.json`
- `verdicts.json`
- `receipt.json`
- `execution_receipt.json`
- `replay_report.json`
- `accept_report.json`
- `report.json`

Any additional `*.json` file in the directory renders under a `Raw JSON` panel
as a forward-compatible fallback.

## Legacy usage

The previous Phase 1-4 entrypoint is still available:

```bash
python blux_view.py --input-dir /path/to/run
```
