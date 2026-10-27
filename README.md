# BLUX App

**BLUX Mission Control (2.0):** a local, read-only workbench over the real BLUX tools. It shows what BLUX did
and what each tool reports, and it re-implements none of their logic. Every view is one call to a real
tool's JSON interface:

| View | Source |
|---|---|
| Overview | `blux version`, `blux-system version` |
| Projects | `god index --json` |
| Capabilities | `blux capabilities` |
| Models and providers | `blux models` (logical models and what their routes provide; no credentials) |
| Operations, receipts, sessions, agent tool calls | `blux-system list`, `show --operation`, `graph --root/--session`, `timeline` |
| CogA artifacts, cA patches, DAT findings, LRC outputs | receipts grouped by capability (display only), with their artifact ids |
| Events (hooks, cancellations) | `blux-system timeline` |
| Training and evals | `evals/reports/gen0/report.json` and `blux_training` dataset manifests |
| Devices | `voidforge devices` (read-only; VoidForge authorizes every write on the device, and the app exposes none) |

A missing or failing tool is shown as an explicit error (for example "VoidForge is not reachable"), never as an
empty view.

## Run

```sh
pip install .                     # stdlib only; install outervoid-blux too for BLUX's secret redaction
blux-app serve --store ./truth --evals-report ../blux/evals/reports/gen0/report.json --open
blux-app snapshot --store ./truth          # every view as one JSON document, for scripts
blux-app legacy-view --root RUN_DIR        # the BLUX App 1.0 viewer for pre-contract run directories
```

Tools are found on `PATH`, or set them with `BLUX_APP_BLUX`, `BLUX_APP_SYSTEM`, `BLUX_APP_GOD` and
`BLUX_APP_VOIDFORGE`. They are resolved to absolute paths, so a shell function or alias with the same name
(for example a `blux` function in a startup file) is never used.

## Controls and security

The only controls are read-only checks run by BLUX System: **verify store** and **replay check** for an
operation. Nothing else can be triggered: no capability runs, no writes and no device actions.

- **Network:** the server binds `127.0.0.1` only and answers only requests whose `Host` names it, which
  blocks DNS rebinding.
- **Controls:** each POST needs the per-launch token embedded in the page, and cross-origin requests are
  refused.
- **Input:** operation and session ids are validated against BLUX's ULID format before they reach a tool.
- **Responses:** every response carries a strict CSP (`frame-ancestors 'none'`), `nosniff` and `no-store`.
  Tool output is passed through BLUX's redaction. The page renders all data as text, never as markup.

## Tests

```sh
python -m pytest tests     # security tests always; end-to-end tests need blux and blux-system on PATH
```

The end-to-end test creates a real BLUX System store, records a parent operation and an agent child
operation with `blux run`, and inspects them through the HTTP API: receipts, operation graph, timeline,
session, catalogs, and the two read-only checks (which change nothing in the store). It also checks that a
provider key in the environment never appears in a response.

## License

**BLUX Proprietary License** (proprietary). Copyright (c) 2026 Outer-Void / Justadudeinspace (JADIS). All rights reserved. See [LICENSE](LICENSE).

Contact: outervoid.blux@gmail.com (main) · theoutervoid@outlook.com (fallback)
